import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.branch import Branch
from app.models.catalog import ProductVariant
from app.models.commerce import CartItem, Notification, Order, OrderItem, Payment, Reservation, ReservationItem
from app.models.inventory import Inventory, InventoryMovement
from app.models.user import Role, User
from app.schemas import (
    CartItemCreate,
    CartItemResponse,
    CartItemUpdate,
    CartSummary,
    NotificationResponse,
    OrderCreate,
    OrderItemResponse,
    OrderResponse,
    OrderStatusUpdate,
    PayRequest,
    PosSaleCreate,
    ReservationCreate,
    ReservationItemResponse,
    ReservationResponse,
)
from app.services.payments import get_gateway
from app.services.promotions import promotion_discount_for_variant

router = APIRouter()

_STAFF_ROLES = {"Administrador", "Encargado de Sucursal", "Cajero"}

_ALLOWED_ORDER_TRANSITIONS = {
    "PENDIENTE": {"PAGADO", "CANCELADO"},
    "PAGADO": {"ENVIADO", "CANCELADO"},
    "ENVIADO": {"ENTREGADO", "CANCELADO"},
    "ENTREGADO": set(),
    "CANCELADO": set(),
}


def require_staff(user: User) -> User:
    if user.role_name not in _STAFF_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requiere rol de administrador o de sucursal")
    return user


def _notify(db: Session, user_ids: list[int], title: str, message: str) -> None:
    for uid in user_ids:
        if uid is not None:
            db.add(Notification(user_id=uid, title=title, message=message))


def _variant_info(variant: ProductVariant) -> dict:
    product = variant.product
    return {
        "product_id": product.id if product else None,
        "product_name": product.name if product else None,
        "image_url": product.image_url if product else None,
        "size_name": variant.size_name,
        "color_name": variant.color_name,
        "sku": variant.sku,
    }


def _get_variant_or_404(db: Session, variant_id: int) -> ProductVariant:
    variant = db.get(ProductVariant, variant_id)
    if variant is None or not variant.is_active or not variant.product.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variante no encontrada")
    return variant


def _get_inventory(db: Session, variant_id: int, branch_id: int, for_update: bool = False) -> Inventory | None:
    query = (
        db.query(Inventory)
        .filter(Inventory.variant_id == variant_id, Inventory.branch_id == branch_id)
    )
    if for_update:
        query = query.with_for_update()
    return query.first()


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _aware_to_utc_naive(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _movement(db: Session, inventory: Inventory, movement_type: str, quantity: int,
              reason: str | None, user_id: int | None) -> None:
    new_value = inventory.available + quantity
    if new_value < 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stock insuficiente para la variante {inventory.variant_id} (disponible {inventory.available})",
        )
    inventory.available = new_value
    db.add(InventoryMovement(
        inventory_id=inventory.id,
        movement_type=movement_type,
        quantity=quantity,
        reason=reason,
        user_id=user_id,
    ))


def _expire_late(db: Session, reservation: Reservation, user: User) -> bool:
    """Marca como VENCIDA una reserva pendiente caducada y libera su stock. Devuelve True si se expiró."""
    if reservation.status == "PENDIENTE" and _aware_to_utc_naive(reservation.expiration_date) < _utcnow_naive():
        reservation.status = "VENCIDA"
        for item in reservation.items:
            inventory = _get_inventory(db, item.variant_id, reservation.branch_id, for_update=True)
            if inventory is not None:
                _movement(db, inventory, "DEVOLUCION", item.quantity,
                          reason=f"Liberación por reserva vencida {reservation.code}", user_id=user.id)
        db.commit()
        db.refresh(reservation)
        return True
    return False


def _reservation_response(db: Session, r: Reservation) -> ReservationResponse:
    client = db.get(User, r.client_id) if r.client_id else None
    branch = db.get(Branch, r.branch_id) if r.branch_id else None
    items = []
    for item in r.items:
        variant = db.get(ProductVariant, item.variant_id)
        info = _variant_info(variant) if variant else {}
        items.append(ReservationItemResponse(
            id=item.id,
            variant_id=item.variant_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
            subtotal=item.subtotal,
            **info,
        ))
    return ReservationResponse(
        id=r.id,
        code=r.code,
        client_id=r.client_id,
        client_name=client.full_name if client else None,
        branch_id=r.branch_id,
        branch_name=branch.name if branch else None,
        status=r.status,
        reservation_date=r.reservation_date,
        expiration_date=r.expiration_date,
        attend_date=r.attend_date,
        items=items,
        total=r.total,
        item_count=r.item_count,
    )


# ======================================================================
# PAGOS E INVENTARIO (CU19, CU20, CU18)
# ======================================================================


def _receipt_number(order: Order) -> str:
    ts = order.created_at or datetime.now()
    return f"VC-{ts.strftime('%Y%m%d')}-{order.id}"


def _staff_to_alert(db: Session) -> list[int]:
    return [
        u.id for u in db.query(User)
        .join(Role, User.role_id == Role.id)
        .filter(User.is_active.is_(True),
                Role.name.in_(["Administrador", "Encargado de Sucursal"]))
        .all()
    ]


def _deduct_order_stock(db: Session, order: Order, user: User) -> None:
    """CU20: descuenta el stock de la sucursal y registra los movimientos SALIDA.

    Se invoca únicamente cuando el pago se completa (CU18/CU19), de modo que un
    pago fallido jamás decrementa inventario.
    """
    for item in order.items:
        inventory = _get_inventory(db, item.variant_id, order.branch_id, for_update=True)
        if inventory is None or inventory.available < item.quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Stock insuficiente del item {item.variant_id} al confirmar el pago "
                       f"(disponible {inventory.available if inventory else 0})",
            )
        _movement(db, inventory, "SALIDA", -item.quantity,
                  reason=f"Venta del pedido #{order.id}", user_id=user.id)
        if inventory.available == 0:
            _alert_out_of_stock(db, inventory, item.variant_id)


def _alert_out_of_stock(db: Session, inventory: Inventory, variant_id: int) -> None:
    """CU20: notifica al personal cuando una prenda queda agotada tras una venta."""
    variant = db.get(ProductVariant, variant_id)
    if variant is None:
        label = f"la variante {variant_id}"
    else:
        product = variant.product
        label = f"'{product.name}' ({variant.size_name}/{variant.color_name})"
    _notify(db, _staff_to_alert(db), "Producto agotado",
            f"El producto {label} quedó agotado en la sucursal #{inventory.branch_id}. "
            "Repón stock o revisa los movimientos.")


def _complete_order_sale(db: Session, order: Order, user: User) -> None:
    """Confirma la venta: descuenta stock (si aplica) y marca el pedido como PAGADO."""
    if order.branch_id:
        _deduct_order_stock(db, order, user)
    order.status = "PAGADO"
    _notify(db, [order.client_id], "Pedido pagado",
            f"Tu pedido #{order.id} por ${order.total:,.2f} fue pagado correctamente.")


def _process_payment(db: Session, order: Order, method: str, user: User,
                     card_number: str | None = None) -> Payment:
    """CU19: procesa el pago a través de la pasarela sandbox (o efectivo en tienda).

    - Éxito (tarjeta válida / efectivo / transferencia): COMPLETADO + `_complete_order_sale`.
    - Rechazo (tarjetas de prueba declinadas): FALLIDO; el pedido permanece PENDIENTE
      para poder reintentar (POST /orders/{id}/pay). El stock jamás se descuenta aquí.
    """
    payment = order.payment
    if payment is None:
        payment = Payment(order=order, amount=order.total, method=method, status="PENDIENTE")
        db.add(payment)
        db.flush()

    payment.method = method
    payment.amount = round(order.total, 2)

    if method == "EFECTIVO":
        payment.status = "COMPLETADO"
        payment.stripe_payment_id = f"pi_cash_{secrets.token_hex(8)}"
        payment.paid_at = datetime.now()
        _complete_order_sale(db, order, user)
        return payment

    result = get_gateway().charge(order.total, method, {"card_number": card_number})
    if result.success:
        payment.status = "COMPLETADO"
        payment.stripe_payment_id = result.transaction_id
        payment.paid_at = datetime.now()
        _complete_order_sale(db, order, user)
    else:
        payment.status = "FALLIDO"
        payment.stripe_payment_id = result.transaction_id
    return payment


def _get_or_create_mostrador(db: Session) -> User:
    """Cliente genérico para ventas de POS sin cliente registrado (CU18)."""
    user = db.query(User).filter(User.email == "mostrador@fashionstore.com").first()
    if user:
        return user
    role = db.query(Role).filter(Role.name == "Cliente").first()
    if role is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="El rol Cliente no está configurado")
    user = User(first_name="Cliente", last_name="Mostrador",
                email="mostrador@fashionstore.com", hashed_password="!",
                is_active=True, role_id=role.id)
    db.add(user)
    db.flush()
    return user


def _order_response(db: Session, o: Order) -> OrderResponse:
    client = db.get(User, o.client_id) if o.client_id else None
    branch = db.get(Branch, o.branch_id) if o.branch_id else None
    items = []
    for item in o.items:
        variant = db.get(ProductVariant, item.variant_id)
        info = _variant_info(variant) if variant else {}
        items.append(OrderItemResponse(
            id=item.id,
            variant_id=item.variant_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
            discount=item.discount or 0.0,
            subtotal=item.subtotal,
            **info,
        ))
    payment = None
    if o.payment:
        payment = {
            "id": o.payment.id,
            "method": o.payment.method,
            "amount": o.payment.amount,
            "status": o.payment.status,
            "stripe_payment_id": o.payment.stripe_payment_id,
            "created_at": o.payment.created_at,
            "paid_at": o.payment.paid_at,
        }
    return OrderResponse(
        id=o.id,
        client_id=o.client_id,
        client_name=client.full_name if client else None,
        branch_id=o.branch_id,
        branch_name=branch.name if branch else None,
        order_type=o.order_type,
        status=o.status,
        total=o.total,
        shipping_address=o.shipping_address,
        receipt_number=_receipt_number(o),
        created_at=o.created_at,
        items=items,
        payment=payment,
    )


# ======================================================================
# CARRITO (CU16)
# ======================================================================


def _cart_item_response(db: Session, item: CartItem) -> CartItemResponse:
    variant = db.get(ProductVariant, item.variant_id)
    info = _variant_info(variant) if variant else {}
    unit_price = variant.effective_price if variant else 0
    discount = 0.0
    if variant:
        _, per_unit_discount = promotion_discount_for_variant(db, variant)
        discount = round(per_unit_discount * item.quantity, 2)
    return CartItemResponse(
        id=item.id,
        variant_id=item.variant_id,
        quantity=item.quantity,
        unit_price=unit_price,
        discount=discount,
        subtotal=round(unit_price * item.quantity - discount, 2),
        added_at=item.added_at,
        **info,
    )


@router.get("/cart", response_model=CartSummary, summary="Ver mi carrito (CU16)")
def get_cart(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.query(CartItem).filter(CartItem.client_id == user.id).order_by(CartItem.added_at.desc()).all()
    rows = [_cart_item_response(db, it) for it in items]
    return CartSummary(
        items=rows,
        total_items=sum(r.quantity for r in rows),
        total_amount=round(sum(r.subtotal for r in rows), 2),
        total_discount=round(sum(r.discount for r in rows), 2),
    )


@router.post("/cart", response_model=CartSummary, status_code=status.HTTP_201_CREATED,
             summary="Agregar un producto al carrito (CU16)")
def add_to_cart(payload: CartItemCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _get_variant_or_404(db, payload.variant_id)

    existing = db.query(CartItem).filter(
        CartItem.client_id == user.id, CartItem.variant_id == payload.variant_id
    ).first()
    if existing:
        existing.quantity = min(existing.quantity + payload.quantity, 99)
    else:
        db.add(CartItem(client_id=user.id, variant_id=payload.variant_id, quantity=payload.quantity))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        item = db.query(CartItem).filter(
            CartItem.client_id == user.id, CartItem.variant_id == payload.variant_id
        ).with_for_update().first()
        if item is None:
            raise
        item.quantity = min(item.quantity + payload.quantity, 99)
        db.commit()
    return get_cart(user=user, db=db)


@router.patch("/cart/{item_id}", response_model=CartSummary, summary="Editar cantidad del carrito (CU16)")
def update_cart_item(item_id: int, payload: CartItemUpdate,
                     user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.get(CartItem, item_id)
    if item is None or item.client_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item de carrito no encontrado")
    item.quantity = min(payload.quantity, 99)
    db.commit()
    return get_cart(user=user, db=db)


@router.delete("/cart/{item_id}", response_model=CartSummary, summary="Quitar item del carrito (CU16)")
def remove_cart_item(item_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.get(CartItem, item_id)
    if item is None or item.client_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item de carrito no encontrado")
    db.delete(item)
    db.commit()
    return get_cart(user=user, db=db)


@router.delete("/cart", response_model=CartSummary, summary="Vaciar carrito (CU16)")
def clear_cart(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(CartItem).filter(CartItem.client_id == user.id).delete()
    db.commit()
    return CartSummary()


# ======================================================================
# RESERVAS (CU13, CU14, CU15)
# ======================================================================


@router.post("/reservations", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED,
             summary="Reservar varias prendas (CU13)")
def create_reservation(payload: ReservationCreate,
                       user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    branch = db.get(Branch, payload.branch_id)
    if branch is None or not branch.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no encontrada")

    now = datetime.now()
    expiration = now + timedelta(hours=payload.expiration_hours)

    reservation = Reservation(
        code=f"RSV-{now.strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}",
        client_id=user.id,
        branch_id=branch.id,
        status="PENDIENTE",
        expiration_date=expiration,
    )
    db.add(reservation)
    db.flush()

    # Valida existencias y reserva el stock antes de confirmar
    for item in payload.items:
        variant = _get_variant_or_404(db, item.variant_id)
        inventory = _get_inventory(db, variant.id, branch.id, for_update=True)
        if inventory is None or inventory.available < item.quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Stock insuficiente de '{variant.product.name}' ({variant.size_name}/{variant.color_name}) en {branch.name}",
            )

        db.add(ReservationItem(
            reservation=reservation,
            variant_id=variant.id,
            quantity=item.quantity,
            unit_price=variant.effective_price,
        ))
        _movement(db, inventory, "RESERVA", -item.quantity,
                  reason=f"Reserva {reservation.code}", user_id=user.id)

    staff_ids = [
        u.id for u in db.query(User)
        .join(Role, User.role_id == Role.id)
        .filter(Role.name.in_(["Administrador", "Encargado de Sucursal"]))
        .all()
    ]
    _notify(db, [user.id], "Reserva creada",
            f"Tu reserva {reservation.code} en {branch.name} vence el {expiration.strftime('%d/%m/%Y %H:%M')}.")
    _notify(db, staff_ids, "Nueva reserva",
            f"Reserva {reservation.code} recibida: {sum(i.quantity for i in payload.items)} prendas en {branch.name}.")

    db.commit()
    db.refresh(reservation)
    return _reservation_response(db, reservation)


@router.get("/reservations", response_model=list[ReservationResponse], summary="Listar reservas (CU14)")
def list_reservations(status_filter: Optional[str] = None,
                      all_reservations: bool = False,
                      user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    if all_reservations:
        require_staff(user)
        query = db.query(Reservation)
    else:
        query = db.query(Reservation).filter(Reservation.client_id == user.id)

    if status_filter:
        query = query.filter(Reservation.status == status_filter)

    rows = query.order_by(Reservation.id.desc()).all()
    out = []
    for r in rows:
        _expire_late(db, r, user)
        out.append(_reservation_response(db, r))
    return out


@router.get("/reservations/{reservation_id}", response_model=ReservationResponse, summary="Consultar una reserva (CU14)")
def get_reservation(reservation_id: int,
                    user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    r = db.get(Reservation, reservation_id)
    if r is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reserva no encontrada")
    if r.client_id != user.id and user.role_name not in _STAFF_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No puedes consultar esta reserva")
    _expire_late(db, r, user)
    return _reservation_response(db, r)


@router.post("/reservations/expire-stale", summary="Expirar reservas pendientes vencidas (admin/sucursal)")
def expire_stale_reservations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_staff(user)
    rows = db.query(Reservation).filter(Reservation.status == "PENDIENTE").all()
    expired = sum(1 for r in rows if _expire_late(db, r, user))
    db.commit()
    return {"expired": expired}


def _release_reserved_stock(db: Session, reservation: Reservation, user: User) -> None:
    for item in reservation.items:
        inventory = _get_inventory(db, item.variant_id, reservation.branch_id, for_update=True)
        if inventory is not None:
            _movement(db, inventory, "DEVOLUCION", item.quantity,
                      reason=f"Liberación de {reservation.code}", user_id=user.id)


@router.patch("/reservations/{reservation_id}/cancel", response_model=ReservationResponse,
              summary="Cancelar reserva pendiente y liberar stock (CU14)")
def cancel_reservation(reservation_id: int,
                       user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    r = db.get(Reservation, reservation_id)
    if r is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reserva no encontrada")
    if r.client_id != user.id and user.role_name not in _STAFF_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No puedes cancelar esta reserva")
    if _expire_late(db, r, user):
        db.commit()
        db.refresh(r)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="La reserva ya venció; no se puede cancelar")
    if r.status != "PENDIENTE":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"No se puede cancelar una reserva en estado {r.status} (solo pendientes)")
    r.status = "CANCELADA"
    _release_reserved_stock(db, r, user)
    _notify(db, [r.client_id], "Reserva cancelada", f"Tu reserva {r.code} fue cancelada.")
    db.commit()
    db.refresh(r)
    return _reservation_response(db, r)


@router.patch("/reservations/{reservation_id}/attend", response_model=ReservationResponse,
              summary="Validar vigencia y atender retiro (CU15, encargado/cajero)")
def attend_reservation(reservation_id: int,
                       user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    require_staff(user)
    r = db.get(Reservation, reservation_id)
    if r is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reserva no encontrada")
    if _expire_late(db, r, user):
        db.commit()
        db.refresh(r)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="La reserva venció; ya no se puede atender")
    if r.status != "PENDIENTE":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"No se puede atender una reserva en estado {r.status} (solo pendientes vigentes)")
    r.status = "ATENDIDA"
    r.attend_date = datetime.now()
    _notify(db, [r.client_id], "Reserva entregada", f"Recogiste tu reserva {r.code}. ¡Gracias!")
    db.commit()
    db.refresh(r)
    return _reservation_response(db, r)


# ======================================================================
# PEDIDOS Y PAGOS (CU16)
# ======================================================================


@router.post("/orders/checkout", response_model=OrderResponse, status_code=status.HTTP_201_CREATED,
             summary="Generar pedido desde carrito/sucursal y registrar pago (CU16, CU17, CU19)")
def checkout(payload: OrderCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order_type = payload.order_type or "DIGITAL"

    if order_type == "PRESENCIAL":
        require_staff(user)
        if not payload.items:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La venta presencial requiere items")
        source_items: list[tuple[int, int, ProductVariant]] = []
        for it in payload.items:
            variant = _get_variant_or_404(db, it.variant_id)
            source_items.append((it.quantity, variant.id, variant))
    else:
        cart_rows = db.query(CartItem).filter(CartItem.client_id == user.id).all()
        if not cart_rows:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El carrito está vacío")
        source_items = []
        for row in cart_rows:
            variant = db.get(ProductVariant, row.variant_id)
            if variant is None:
                continue
            source_items.append((row.quantity, variant.id, variant))

    if not source_items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No hay productos válidos en el pedido")

    branch = None
    if payload.branch_id:
        branch = db.get(Branch, payload.branch_id)
        if branch is None or not branch.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no encontrada")

    order = Order(
        client_id=user.id,
        branch_id=payload.branch_id,
        order_type=order_type,
        status="PENDIENTE",
        shipping_address=payload.shipping_address,
    )
    db.add(order)
    db.flush()

    total = 0.0
    for quantity, variant_id, variant in source_items:
        # Validación previa de existencias (el descuento real ocurre al pagar, CU20)
        if branch is not None:
            inventory = _get_inventory(db, variant_id, branch.id, for_update=True)
            if inventory is None or inventory.available < quantity:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Stock insuficiente de '{variant.product.name}' en {branch.name}",
                )

        unit_price = variant.effective_price
        promotion_id, per_unit_discount = promotion_discount_for_variant(db, variant)
        line_discount = round(per_unit_discount * quantity, 2)
        total += unit_price * quantity - line_discount
        db.add(OrderItem(order=order, variant_id=variant_id, quantity=quantity,
                         unit_price=unit_price, discount=line_discount, promotion_id=promotion_id))

    order.total = round(total, 2)

    if order_type == "DIGITAL":
        db.query(CartItem).filter(CartItem.client_id == user.id).delete()

    payment = _process_payment(db, order, payload.payment_method or "TARJETA", user,
                               payload.card_number)
    db.flush()

    # CU19: compra digital con pago rechazado → el pedido se cancela y NO se cobra ni descuenta.
    if order_type == "DIGITAL" and payment.status == "FALLIDO":
        order.status = "CANCELADO"
        _notify(db, [user.id], "Pago rechazado",
                f"El pago de tu pedido #{order.id} fue rechazado por la pasarela. "
                "El pedido fue cancelado y puedes volver a intentarlo.")

    db.commit()
    db.refresh(order)
    return _order_response(db, order)


@router.post("/pos/sale", response_model=OrderResponse, status_code=status.HTTP_201_CREATED,
             summary="Registrar venta presencial en caja (CU18, cajero/encargado)")
def pos_sale(payload: PosSaleCreate, user: User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    require_staff(user)

    branch = db.get(Branch, payload.branch_id)
    if branch is None or not branch.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no encontrada")

    client_id = payload.client_id or _get_or_create_mostrador(db).id
    if db.get(User, client_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cliente no encontrado")

    # Valida existencias antes de cobrar; el descuento ocurre solo al confirmar el pago.
    source_items = []
    for it in payload.items:
        variant = _get_variant_or_404(db, it.variant_id)
        inventory = _get_inventory(db, variant.id, branch.id, for_update=True)
        if inventory is None or inventory.available < it.quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Stock insuficiente de '{variant.product.name}' ({variant.size_name}/{variant.color_name}) en {branch.name}",
            )
        source_items.append((it.quantity, variant.id, variant))

    order = Order(client_id=client_id, branch_id=branch.id, order_type="PRESENCIAL",
                  status="PENDIENTE")
    db.add(order)
    db.flush()

    total = 0.0
    for quantity, variant_id, variant in source_items:
        unit_price = variant.effective_price
        promotion_id, per_unit_discount = promotion_discount_for_variant(db, variant)
        line_discount = round(per_unit_discount * quantity, 2)
        total += unit_price * quantity - line_discount
        db.add(OrderItem(order=order, variant_id=variant_id, quantity=quantity,
                         unit_price=unit_price, discount=line_discount, promotion_id=promotion_id))
    order.total = round(total, 2)

    # Efectivo/transferencia confirma al instante; tarjeta declinada deja el pedido
    # PENDIENTE para reintentar con POST /orders/{id}/pay (CU19).
    payment = _process_payment(db, order, payload.payment_method, user, payload.card_number)
    db.flush()

    db.commit()
    db.refresh(order)
    return _order_response(db, order)


@router.post("/orders/{order_id}/pay", response_model=OrderResponse,
             summary="Completar o reintentar el pago de un pedido pendiente (CU19)")
def pay_order(order_id: int, payload: PayRequest, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    o = db.get(Order, order_id)
    if o is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado")
    if o.client_id != user.id and user.role_name not in _STAFF_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No puedes pagar este pedido")
    if o.status != "PENDIENTE":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"El pedido #{o.id} no está pendiente de pago (estado: {o.status})")

    payment = _process_payment(db, o, payload.payment_method, user, payload.card_number)
    db.flush()

    if o.order_type == "DIGITAL" and payment.status == "FALLIDO":
        o.status = "CANCELADO"
        _notify(db, [o.client_id], "Pago rechazado",
                f"El pago de tu pedido #{o.id} fue rechazado. El pedido fue cancelado.")

    db.commit()
    db.refresh(o)
    return _order_response(db, o)


@router.get("/orders", response_model=list[OrderResponse], summary="Listar pedidos")
def list_orders(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role_name in _STAFF_ROLES:
        rows = db.query(Order).order_by(Order.id.desc()).all()
    else:
        rows = db.query(Order).filter(Order.client_id == user.id).order_by(Order.id.desc()).all()
    return [_order_response(db, o) for o in rows]


@router.get("/orders/{order_id}", response_model=OrderResponse, summary="Consultar un pedido")
def get_order(order_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    o = db.get(Order, order_id)
    if o is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado")
    if o.client_id != user.id and user.role_name not in _STAFF_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No puedes consultar este pedido")
    return _order_response(db, o)


@router.patch("/orders/{order_id}/status", response_model=OrderResponse,
              summary="Actualizar estado del pedido")
def update_order_status(order_id: int, payload: OrderStatusUpdate,
                        user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    require_staff(user)
    o = db.get(Order, order_id)
    if o is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado")

    new_status = payload.status
    allowed = _ALLOWED_ORDER_TRANSITIONS.get(o.status, set())
    if new_status == o.status:
        return _order_response(db, o)
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transición no permitida: {o.status} → {new_status}",
        )

    if new_status == "CANCELADO" and o.status in ("PAGADO", "ENVIADO") and o.branch_id:
        for item in o.items:
            inventory = _get_inventory(db, item.variant_id, o.branch_id, for_update=True)
            if inventory is not None:
                _movement(db, inventory, "DEVOLUCION", item.quantity,
                          reason=f"Anulación del pedido #{o.id}", user_id=user.id)
        _notify(db, [o.client_id], "Pedido cancelado", f"Tu pedido #{o.id} fue cancelado.")
    o.status = new_status
    db.commit()
    db.refresh(o)
    return _order_response(db, o)


# ======================================================================
# NOTIFICACIONES
# ======================================================================


@router.get("/notifications", response_model=list[NotificationResponse], summary="Mis notificaciones")
def list_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(Notification).filter(Notification.user_id == user.id).order_by(
        Notification.created_at.desc()).all()
    return [NotificationResponse(
        id=n.id, user_id=n.user_id, title=n.title, message=n.message, is_read=n.is_read, created_at=n.created_at,
    ) for n in rows]


@router.patch("/notifications/{notification_id}/read", response_model=NotificationResponse,
              summary="Marcar notificación como leída")
def mark_notification_read(notification_id: int,
                           user: User = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    n = db.get(Notification, notification_id)
    if n is None or n.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notificación no encontrada")
    n.is_read = True
    db.commit()
    db.refresh(n)
    return NotificationResponse(id=n.id, user_id=n.user_id, title=n.title, message=n.message,
                                is_read=n.is_read, created_at=n.created_at)
import secrets
import json
import hashlib
from decimal import Decimal
from app.core.money import money as _money
from app.core.config import settings
from app.models.sync import CambioPrenda
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_business_user as get_current_user
from app.core.tenant import ensure_tenant_owns, scope_to_empresa
from app.models.branch import Branch
from app.models.catalog import ProductVariant
from app.models.commerce import CartItem, Notification, Order, OrderItem, Payment, Reservation, ReservationItem
from app.models.inventory import Inventory, InventoryMovement
from app.models.user import Role, User
from app.schemas import (
    ExchangeRequest,
    ReservationCheckoutRequest,
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
from app.services.refunds import order_financials, refund_all, create_refund, complete_refund, refund_response
from app.models.commerce import Refund, RefundStockReturn
from app.schemas import RefundCreate, RefundDecision, StockReturnInput
from app.services.promotions import promotion_discount_for_variant

router = APIRouter()

_STAFF_ROLES = {"Administrador", "Encargado de Sucursal", "Cajero"}

_ALLOWED_ORDER_TRANSITIONS = {
    "PENDIENTE": {"CANCELADO"},
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


def _get_variant_or_404(db: Session, variant_id: int, user: User) -> ProductVariant:
    variant = db.get(ProductVariant, variant_id)
    if variant is None or not variant.is_active or not variant.product.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variante no encontrada")
    ensure_tenant_owns(variant.product, user, label="Producto")
    return variant


def _get_inventory(db: Session, variant_id: int, branch_id: int, for_update: bool = False) -> Inventory | None:
    query = (
        db.query(Inventory)
        .filter(Inventory.variant_id == variant_id, Inventory.branch_id == branch_id)
    )
    if for_update:
        # Hacer visibles los cambios propios antes de releer evita perder deltas
        # de una reserva/cambio en esta misma transacción (autoflush=False).
        db.flush()
        query = query.populate_existing().with_for_update()
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
    db.refresh(reservation, with_for_update=True)
    if reservation.status == "PENDIENTE" and _aware_to_utc_naive(reservation.expiration_date) < _utcnow_naive():
        reservation.status = "VENCIDA"
        for item in sorted(reservation.items, key=lambda row: row.variant_id):
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


def _staff_to_alert(db: Session, empresa_id: int | None) -> list[int]:
    return [
        u.id for u in db.query(User)
        .join(Role, User.role_id == Role.id)
        .filter(User.empresa_id == empresa_id, User.is_active.is_(True),
                Role.name.in_(["Administrador", "Encargado de Sucursal"]))
        .all()
    ]


def _deduct_order_stock(db: Session, order: Order, user: User) -> None:
    """CU20: descuenta el stock de la sucursal y registra los movimientos SALIDA.

    Se invoca únicamente cuando el pago se completa (CU18/CU19), de modo que un
    pago fallido jamás decrementa inventario.
    """
    stocks = _check_order_stock(db, order)
    for item in sorted(order.items, key=lambda row: row.variant_id):
        inventory = stocks[item.variant_id]
        _movement(db, inventory, "SALIDA", -item.quantity,
                  reason=f"Venta del pedido #{order.id}", user_id=user.id)
        if inventory.available == 0:
            _alert_out_of_stock(db, inventory, item.variant_id)


def _check_order_stock(db, order):
    stocks = {}
    quantities = {}
    for item in order.items:
        quantities[item.variant_id] = quantities.get(item.variant_id, 0) + item.quantity
    for variant_id, quantity in sorted(quantities.items()):
        inventory = _get_inventory(db, variant_id, order.branch_id, for_update=True)
        if inventory is None or inventory.available < quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Stock insuficiente del item {variant_id} al confirmar el pago "
                       f"(disponible {inventory.available if inventory else 0})",
            )
        stocks[variant_id] = inventory
    return stocks


def _alert_out_of_stock(db: Session, inventory: Inventory, variant_id: int) -> None:
    """CU20: notifica al personal cuando una prenda queda agotada tras una venta."""
    variant = db.get(ProductVariant, variant_id)
    if variant is None:
        label = f"la variante {variant_id}"
    else:
        product = variant.product
        label = f"'{product.name}' ({variant.size_name}/{variant.color_name})"
    _notify(db, _staff_to_alert(db, inventory.branch.empresa_id), "Producto agotado",
            f"El producto {label} quedó agotado en la sucursal #{inventory.branch_id}. "
            "Repón stock o revisa los movimientos.")


def _complete_order_sale(db: Session, order: Order, user: User) -> None:
    """Confirma la venta: descuenta stock (si aplica) y marca el pedido como PAGADO."""
    if order.status != 'PENDIENTE':
        raise HTTPException(409, 'La venta ya fue procesada; no puede descontarse otra vez')
    if order.branch_id:
        _deduct_order_stock(db, order, user)
    order.stock_deducted = True
    order.status = "PAGADO"
    order.user_id = user.id
    order.payment_method = order.payment.method if order.payment else None
    _notify(db, [order.client_id], "Pedido pagado",
            f"Tu pedido #{order.id} por ${order.total:,.2f} fue pagado correctamente.")


def _process_payment(db: Session, order: Order, method: str, user: User,
                     card_number: str | None = None, cash_received: float | None = None) -> Payment:
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
    payment.cash_received = None
    payment.change_amount = 0
    if order.branch_id:
        _check_order_stock(db, order)

    def confirm_or_refund():
        try:
            _complete_order_sale(db, order, user)
        except HTTPException as error:
            if error.status_code != 409: raise
            order.status = 'CANCELADO'
            refund_all(db, order, user, 'Pago confirmado sin existencias para entregar la compra',
                'SIN_STOCK', restock=False, gateway=get_gateway())

    if method == "EFECTIVO":
        received = _money(order.total if cash_received is None else cash_received)
        if received < _money(order.total):
            raise HTTPException(422, 'El efectivo recibido no cubre el total de la venta')
        payment.cash_received = float(received)
        payment.change_amount = float(received - _money(order.total))
        payment.status = "COMPLETADO"
        payment.stripe_payment_id = f"pi_cash_{secrets.token_hex(8)}"
        payment.paid_at = datetime.now()
        confirm_or_refund()
        return payment

    result = get_gateway().charge(order.total, method, {"card_number": card_number})
    if result.success:
        payment.status = "COMPLETADO"
        payment.stripe_payment_id = result.transaction_id
        payment.paid_at = datetime.now()
        confirm_or_refund()
    else:
        payment.status = "FALLIDO"
        payment.stripe_payment_id = result.transaction_id
    return payment


def _get_or_create_mostrador(db: Session, empresa_id: int | None) -> User:
    """Cliente genérico para ventas de POS sin cliente registrado (CU18)."""
    email = f"mostrador-{empresa_id}@fashionstore.com" if empresa_id else "mostrador@fashionstore.com"
    user = db.query(User).filter(User.email == email, User.empresa_id == empresa_id).first()
    if user:
        return user
    role = db.query(Role).filter(Role.name == "Cliente").first()
    if role is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="El rol Cliente no está configurado")
    user = User(first_name="Cliente", last_name="Mostrador",
                empresa_id=empresa_id, email=email, hashed_password="!",
                is_active=True, role_id=role.id)
    try:
        with db.begin_nested():
            db.add(user)
            db.flush()
    except IntegrityError:
        user = db.query(User).filter(User.email == email, User.empresa_id == empresa_id).one()
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
            "cash_received": o.payment.cash_received,
            "change_amount": o.payment.change_amount or 0,
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
        stock_deducted=o.stock_deducted,
        **order_financials(db, o),
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
    _get_variant_or_404(db, payload.variant_id, user)

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
    branch = ensure_tenant_owns(db.get(Branch, payload.branch_id), user, include_global=False, label="Sucursal")
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
    for quantity, variant_id, variant in _normalized_items([
        (item.quantity, item.variant_id, _get_variant_or_404(db, item.variant_id, user)) for item in payload.items]):
        inventory = _get_inventory(db, variant.id, branch.id, for_update=True)
        if inventory is None or inventory.available < quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Stock insuficiente de '{variant.product.name}' ({variant.size_name}/{variant.color_name}) en {branch.name}",
            )

        db.add(ReservationItem(
            reservation=reservation,
            variant_id=variant.id,
            quantity=quantity,
            unit_price=float(_money(variant.effective_price)),
        ))
        _movement(db, inventory, "RESERVA", -quantity,
                  reason=f"Reserva {reservation.code}", user_id=user.id)

    staff_ids = [
        u.id for u in db.query(User)
        .join(Role, User.role_id == Role.id)
        .filter(User.empresa_id == branch.empresa_id, Role.name.in_(["Administrador", "Encargado de Sucursal"]))
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
        query = db.query(Reservation).join(Branch).filter(Branch.empresa_id == user.empresa_id)
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
    r = db.query(Reservation).filter(Reservation.id == reservation_id).with_for_update().first()
    if r is not None:
        ensure_tenant_owns(db.get(Branch, r.branch_id), user, include_global=False, label="Reserva")
    if r is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reserva no encontrada")
    if r.client_id != user.id and user.role_name not in _STAFF_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No puedes consultar esta reserva")
    _expire_late(db, r, user)
    return _reservation_response(db, r)


@router.post("/reservations/expire-stale", summary="Expirar reservas pendientes vencidas (admin/sucursal)")
def expire_stale_reservations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_staff(user)
    rows = db.query(Reservation).join(Branch).filter(Branch.empresa_id == user.empresa_id, Reservation.status == "PENDIENTE").with_for_update().all()
    expired = sum(1 for r in rows if _expire_late(db, r, user))
    db.commit()
    return {"expired": expired}


def _release_reserved_stock(db: Session, reservation: Reservation, user: User) -> None:
    for item in sorted(reservation.items, key=lambda row: row.variant_id):
        inventory = _get_inventory(db, item.variant_id, reservation.branch_id, for_update=True)
        if inventory is not None:
            _movement(db, inventory, "DEVOLUCION", item.quantity,
                      reason=f"Liberación de {reservation.code}", user_id=user.id)


@router.patch("/reservations/{reservation_id}/cancel", response_model=ReservationResponse,
              summary="Cancelar reserva pendiente y liberar stock (CU14)")
def cancel_reservation(reservation_id: int,
                       user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    r = db.query(Reservation).filter(Reservation.id == reservation_id).with_for_update().first()
    if r is not None:
        ensure_tenant_owns(db.get(Branch, r.branch_id), user, include_global=False, label="Reserva")
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
    r = db.query(Reservation).filter(Reservation.id == reservation_id).with_for_update().first()
    if r is not None:
        ensure_tenant_owns(db.get(Branch, r.branch_id), user, include_global=False, label="Reserva")
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


@router.post("/reservations/{reservation_id}/expire", response_model=ReservationResponse,
              summary="Marcar una reserva pendiente como vencida y liberar stock (staff)")
def expire_reservation(reservation_id: int,
                       user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    require_staff(user)
    r = db.query(Reservation).filter(Reservation.id == reservation_id).with_for_update().first()
    if r is not None:
        ensure_tenant_owns(db.get(Branch, r.branch_id), user, include_global=False, label="Reserva")
    if r is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reserva no encontrada")
    if r.status != "PENDIENTE":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"No se puede vencer una reserva en estado {r.status}")
    r.status = "VENCIDA"
    _release_reserved_stock(db, r, user)
    _notify(db, [r.client_id], "Reserva vencida", f"Tu reserva {r.code} venció.")
    db.commit()
    db.refresh(r)
    return _reservation_response(db, r)


@router.delete("/reservations/{reservation_id}", response_model=ReservationResponse,
               summary="Eliminar (cancelar) una reserva pendiente (CU14)")
def delete_reservation(reservation_id: int,
                       user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    r = db.query(Reservation).filter(Reservation.id == reservation_id).with_for_update().first()
    if r is not None:
        ensure_tenant_owns(db.get(Branch, r.branch_id), user, include_global=False, label="Reserva")
    if r is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reserva no encontrada")
    if r.client_id != user.id and user.role_name not in _STAFF_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="No puedes eliminar esta reserva")
    if r.status != "PENDIENTE":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"No se puede eliminar una reserva en estado {r.status}")
    r.status = "CANCELADA"
    _release_reserved_stock(db, r, user)
    _notify(db, [r.client_id], "Reserva cancelada", f"Tu reserva {r.code} fue cancelada.")
    db.commit()
    db.refresh(r)
    return _reservation_response(db, r)


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
            variant = _get_variant_or_404(db, it.variant_id, user)
            source_items.append((it.quantity, variant.id, variant))
    else:
        cart_rows = db.query(CartItem).filter(CartItem.client_id == user.id).all()
        if not cart_rows:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El carrito está vacío")
        source_items = []
        for row in cart_rows:
            variant = _get_variant_or_404(db, row.variant_id, user)
            source_items.append((row.quantity, variant.id, variant))

    if not source_items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No hay productos válidos en el pedido")

    source_items = _normalized_items(source_items)

    branch = None
    if payload.branch_id:
        branch = ensure_tenant_owns(db.get(Branch, payload.branch_id), user, include_global=False, label="Sucursal")
        if branch is None or not branch.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no encontrada")

    if branch is None:
        quantities = {}
        for qty, vid, _ in source_items:
            quantities[vid] = quantities.get(vid, 0) + qty
        for candidate in db.query(Branch).filter(Branch.empresa_id == user.empresa_id, Branch.is_active.is_(True)).order_by(Branch.id):
            if all((stock := _get_inventory(db, vid, candidate.id, for_update=True)) is not None and stock.available >= qty for vid, qty in quantities.items()):
                branch = candidate
                break
        if branch is None:
            raise HTTPException(status_code=409, detail="No hay una sucursal con existencias para completar la compra")

    order = Order(
        client_id=user.id,
        branch_id=branch.id,
        empresa_id=branch.empresa_id if branch is not None else user.empresa_id,
        order_type=order_type,
        status="PENDIENTE",
        shipping_address=payload.shipping_address,
    )
    db.add(order)
    db.flush()

    total = Decimal('0.00')
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
        unit_price = float(_money(unit_price))
        line_discount = float(_money(per_unit_discount) * quantity)
        total += _money(unit_price) * quantity - _money(line_discount)
        db.add(OrderItem(order=order, variant_id=variant_id, quantity=quantity,
                         unit_price=unit_price, discount=line_discount, promotion_id=promotion_id))

    order.total = float(total)

    payment = _process_payment(db, order, payload.payment_method or "TARJETA", user,
                               payload.card_number)
    db.flush()

    # CU19: compra digital con pago rechazado → el pedido se cancela y NO se cobra ni descuenta.
    # El carrito se conserva para que el cliente pueda reintentar el pago.
    if order_type == "DIGITAL" and payment.status == "FALLIDO":
        order.status = "CANCELADO"
        _notify(db, [user.id], "Pago rechazado",
                f"El pago de tu pedido #{order.id} fue rechazado por la pasarela. "
                "El pedido fue cancelado y puedes volver a intentarlo.")
    elif order_type == "DIGITAL":
        db.query(CartItem).filter(CartItem.client_id == user.id).delete()

    db.commit()
    db.refresh(order)
    return _order_response(db, order)


def _normalized_items(source_items):
    combined = {}
    for quantity, variant_id, variant in source_items:
        if variant_id not in combined: combined[variant_id] = [0, variant_id, variant]
        combined[variant_id][0] += quantity
    return [tuple(combined[key]) for key in sorted(combined)]


def _repeated_sale(db, payload, user, fingerprint):
    if not payload.request_id: return None
    previous = db.query(Order).filter(Order.request_id == payload.request_id.lower()).first()
    if previous is None: return None
    if previous.empresa_id != user.empresa_id or previous.user_id != user.id or previous.request_fingerprint != fingerprint:
        raise HTTPException(409, 'Este identificador ya corresponde a otra operación')
    return _order_response(db, previous)


@router.post("/pos/sale", response_model=OrderResponse, status_code=status.HTTP_201_CREATED,
             summary="Registrar venta presencial en caja (CU18, cajero/encargado)")
def pos_sale(payload: PosSaleCreate, user: User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    require_staff(user)

    fingerprint = hashlib.sha256(json.dumps({
        'branch': payload.branch_id, 'client': payload.client_id, 'method': payload.payment_method,
        'cash': payload.cash_received,
        'items': sorted((item.variant_id, item.quantity) for item in payload.items),
    }, sort_keys=True).encode()).hexdigest()
    repeated = _repeated_sale(db, payload, user, fingerprint)
    if repeated is not None: return repeated

    branch = ensure_tenant_owns(db.get(Branch, payload.branch_id), user, include_global=False, label="Sucursal")
    if branch is None or not branch.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no encontrada")

    client_id = payload.client_id or _get_or_create_mostrador(db, user.empresa_id).id
    ensure_tenant_owns(db.get(User, client_id), user, include_global=False, label="Cliente")

    # Valida existencias antes de cobrar; el descuento ocurre solo al confirmar el pago.
    source_items = []
    for quantity, variant_id, variant in _normalized_items([
        (it.quantity, it.variant_id, _get_variant_or_404(db, it.variant_id, user)) for it in payload.items]):
        inventory = _get_inventory(db, variant.id, branch.id, for_update=True)
        # Un reintento concurrente puede haber esperado a que el primero termine.
        repeated = _repeated_sale(db, payload, user, fingerprint)
        if repeated is not None: return repeated
        if inventory is None or inventory.available < quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Stock insuficiente de '{variant.product.name}' ({variant.size_name}/{variant.color_name}) en {branch.name}",
            )
        source_items.append((quantity, variant.id, variant))

    order = Order(client_id=client_id, branch_id=branch.id,
                  empresa_id=branch.empresa_id, order_type="PRESENCIAL",
                  user_id=user.id, request_id=payload.request_id.lower() if payload.request_id else None,
                  request_fingerprint=fingerprint, status="PENDIENTE")
    db.add(order)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        repeated = _repeated_sale(db, payload, user, fingerprint)
        if repeated is not None: return repeated
        raise

    total = Decimal('0.00')
    for quantity, variant_id, variant in source_items:
        unit_price = variant.effective_price
        promotion_id, per_unit_discount = promotion_discount_for_variant(db, variant)
        unit_price = float(_money(unit_price))
        line_discount = float(_money(per_unit_discount) * quantity)
        total += _money(unit_price) * quantity - _money(line_discount)
        db.add(OrderItem(order=order, variant_id=variant_id, quantity=quantity,
                         unit_price=unit_price, discount=line_discount, promotion_id=promotion_id))
    order.total = float(total)

    # Efectivo/transferencia confirma al instante; tarjeta declinada deja el pedido
    # PENDIENTE para reintentar con POST /orders/{id}/pay (CU19).
    payment = _process_payment(db, order, payload.payment_method, user, payload.card_number, payload.cash_received)
    db.flush()

    db.commit()
    db.refresh(order)
    return _order_response(db, order)


@router.post("/orders/{order_id}/pay", response_model=OrderResponse,
             summary="Completar o reintentar el pago de un pedido pendiente (CU19)")
def pay_order(order_id: int, payload: PayRequest, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    o = db.query(Order).filter(Order.id == order_id).with_for_update().first()
    if o is not None:
        ensure_tenant_owns(o, user, include_global=False, label="Pedido")
    if o is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado")
    if o.client_id != user.id and user.role_name not in _STAFF_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No puedes pagar este pedido")
    if o.status != "PENDIENTE":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"El pedido #{o.id} no está pendiente de pago (estado: {o.status})")

    payment = _process_payment(db, o, payload.payment_method, user, payload.card_number, payload.cash_received)
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
        rows = scope_to_empresa(db.query(Order), Order, user, include_global=False).order_by(Order.id.desc()).all()
    else:
        rows = db.query(Order).filter(Order.client_id == user.id).order_by(Order.id.desc()).all()
    return [_order_response(db, o) for o in rows]


@router.get("/orders/{order_id}", response_model=OrderResponse, summary="Consultar un pedido")
def get_order(order_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    o = db.query(Order).filter(Order.id == order_id).with_for_update().first()
    if o is not None:
        ensure_tenant_owns(o, user, include_global=False, label="Pedido")
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
    o = db.query(Order).filter(Order.id == order_id).with_for_update().first()
    if o is not None:
        ensure_tenant_owns(o, user, include_global=False, label="Pedido")
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

    if new_status == "CANCELADO" and o.status in ("PAGADO", "ENVIADO"):
        if user.role_name not in {'Administrador','Encargado de Sucursal'}:
            raise HTTPException(403,'Solo administración o el encargado pueden anular una compra pagada')
        if o.status == 'ENVIADO':
            raise HTTPException(409, 'Una compra enviada requiere registrar la devolución de las prendas recibidas en Reembolsos')
        refund_all(db, o, user, f'Cancelación del pedido #{o.id}', 'CANCELACION', restock=o.stock_deducted)
        _notify(db, [o.client_id], "Pedido cancelado", f"Tu pedido #{o.id} fue cancelado.")
    o.status = new_status
    db.commit()
    db.refresh(o)
    return _order_response(db, o)


@router.post('/orders/{order_id}/refunds', response_model=OrderResponse, status_code=201)
def refund_order(order_id:int, payload:RefundCreate, user:User=Depends(get_current_user), db:Session=Depends(get_db)):
    if user.role_name not in {'Administrador','Encargado de Sucursal'}:
        raise HTTPException(403,'Solo administración o el encargado pueden confirmar reembolsos')
    order=db.query(Order).filter(Order.id==order_id).with_for_update().first()
    ensure_tenant_owns(order,user,include_global=False,label='Pedido')
    create_refund(db,order,user,payload,gateway=get_gateway())
    db.commit();db.refresh(order)
    return _order_response(db,order)


@router.post('/orders/{order_id}/refunds/{refund_id}/retry', response_model=OrderResponse)
def retry_refund(order_id:int,refund_id:int,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    if user.role_name not in {'Administrador','Encargado de Sucursal'}:
        raise HTTPException(403,'Solo administración o el encargado pueden confirmar reembolsos')
    order=db.query(Order).filter(Order.id==order_id).with_for_update().first()
    ensure_tenant_owns(order,user,include_global=False,label='Pedido')
    refund=db.query(Refund).filter_by(id=refund_id,order_id=order_id).first()
    if refund is None: raise HTTPException(404,'Reembolso no encontrado')
    if refund.status not in {'PENDIENTE','COMPLETADO'}:
        raise HTTPException(409,'La solicitud requiere una decisión del encargado antes de procesarse')
    complete_refund(db,refund,user,gateway=get_gateway())
    db.commit();db.refresh(order)
    return _order_response(db,order)


@router.post('/orders/{order_id}/refund-requests',response_model=OrderResponse,status_code=201)
def request_refund(order_id:int,payload:RefundCreate,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    order=db.query(Order).filter(Order.id==order_id).with_for_update().first()
    ensure_tenant_owns(order,user,include_global=False,label='Pedido')
    if order.client_id!=user.id: raise HTTPException(403,'Solo puedes solicitar devoluciones de tus compras')
    if payload.restock: raise HTTPException(422,'El encargado verificará la recepción de las prendas')
    create_refund(db,order,user,payload,source='SOLICITUD_CLIENTE',execute=False)
    db.commit();db.refresh(order)
    return _order_response(db,order)


@router.post('/orders/{order_id}/refunds/{refund_id}/restock',response_model=OrderResponse)
def return_refunded_stock(order_id:int,refund_id:int,payload:StockReturnInput,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    if user.role_name not in {'Administrador','Encargado de Sucursal'}: raise HTTPException(403,'Requiere administración o encargado')
    order=db.query(Order).filter_by(id=order_id).with_for_update().first()
    ensure_tenant_owns(order,user,include_global=False,label='Pedido')
    previous=db.query(RefundStockReturn).filter_by(request_id=payload.request_id.lower()).first()
    if previous:
        if previous.order_id!=order_id or previous.refund_item_id!=payload.refund_item_id or previous.quantity!=payload.quantity:
            raise HTTPException(409,'El identificador pertenece a otra recepción')
        return _order_response(db,order)
    refund=db.query(Refund).filter_by(id=refund_id,order_id=order_id,status='COMPLETADO').first()
    if refund is None: raise HTTPException(404,'Reembolso confirmado no encontrado')
    item=next((item for item in refund.items if item.id==payload.refund_item_id),None)
    if not item or payload.quantity > item.quantity-item.restocked_quantity: raise HTTPException(409,'La cantidad supera las prendas pendientes de recepción')
    if not order.stock_deducted or not order.branch_id: raise HTTPException(409,'Esta compra no descontó inventario')
    inventory=_get_inventory(db,item.variant_id,order.branch_id,for_update=True)
    if inventory is None: raise HTTPException(409,'Registra el inventario de la variante en la sucursal antes de recibirla')
    _movement(db,inventory,'DEVOLUCION',payload.quantity,f'Recepción posterior a RF-{refund.id:08d}, sin nuevo pago',user.id)
    item.restocked_quantity+=payload.quantity
    db.add(RefundStockReturn(request_id=payload.request_id.lower(),order_id=order.id,refund_item_id=item.id,quantity=payload.quantity,user_id=user.id))
    db.commit();db.refresh(order)
    return _order_response(db,order)


@router.post('/orders/{order_id}/refunds/{refund_id}/decision',response_model=OrderResponse)
def decide_refund(order_id:int,refund_id:int,payload:RefundDecision,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    if user.role_name not in {'Administrador','Encargado de Sucursal'}: raise HTTPException(403,'Requiere administración o encargado')
    order=db.query(Order).filter(Order.id==order_id).with_for_update().first()
    ensure_tenant_owns(order,user,include_global=False,label='Pedido')
    refund=db.query(Refund).filter_by(id=refund_id,order_id=order_id).first()
    if refund is None: raise HTTPException(404,'Solicitud no encontrada')
    if refund.status=='COMPLETADO' and payload.approve: return _order_response(db,order)
    if refund.status!='SOLICITADO': raise HTTPException(409,'Esta solicitud ya fue resuelta')
    if not payload.approve:
        refund.status='RECHAZADO';refund.error=payload.comment.strip() or 'Solicitud rechazada por el encargado'
    else:
        for item in refund.items: item.restock=payload.restock and item.quantity>0
        refund.status='PENDIENTE'
        complete_refund(db,refund,user,gateway=get_gateway())
    db.commit();db.refresh(order)
    return _order_response(db,order)


@router.post('/orders/{order_id}/refunds/{refund_id}/withdraw',response_model=OrderResponse)
def withdraw_refund_request(order_id:int,refund_id:int,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    order=db.query(Order).filter_by(id=order_id).with_for_update().first()
    ensure_tenant_owns(order,user,include_global=False,label='Pedido')
    if order.client_id!=user.id: raise HTTPException(403,'Solo puedes retirar tus propias solicitudes')
    refund=db.query(Refund).filter_by(id=refund_id,order_id=order_id).first()
    if refund is None: raise HTTPException(404,'Solicitud no encontrada')
    if refund.status=='CANCELADO': return _order_response(db,order)
    if refund.status!='SOLICITADO': raise HTTPException(409,'La devolución ya fue procesada; no puede retirarse')
    refund.status='CANCELADO';refund.error='Solicitud retirada por el cliente'
    db.commit();db.refresh(order)
    return _order_response(db,order)


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


@router.post('/reservations/{reservation_id}/checkout', response_model=OrderResponse, status_code=201)
def checkout_reservation(reservation_id: int, payload: ReservationCheckoutRequest,
    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_staff(user)
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).with_for_update().first()
    if reservation is None:
        raise HTTPException(404, 'Reserva no encontrada')
    ensure_tenant_owns(db.get(Branch, reservation.branch_id), user, include_global=False, label='Reserva')
    if _expire_late(db, reservation, user) or reservation.status not in {'PENDIENTE', 'ATENDIDA'}:
        raise HTTPException(409, 'La reserva ya no est? disponible para comprar')
    reserved, requested = {}, {}
    for item in reservation.items:
        reserved[item.variant_id] = reserved.get(item.variant_id, 0) + item.quantity
    for item in payload.items:
        requested[item.variant_id] = requested.get(item.variant_id, 0) + item.quantity
    if any(qty > reserved.get(vid, 0) for vid, qty in requested.items()):
        raise HTTPException(422, 'Solo se pueden comprar las cantidades reservadas')
    _release_reserved_stock(db, reservation, user)
    reservation.status = 'COMPRADA'
    reservation.attend_date = datetime.now(timezone.utc)
    sale = PosSaleCreate(branch_id=reservation.branch_id, client_id=reservation.client_id,
        items=[{'variant_id': vid, 'quantity': qty} for vid, qty in requested.items()], payment_method='EFECTIVO')
    return pos_sale(sale, user=user, db=db)


@router.post('/reservations/{reservation_id}/finish', response_model=ReservationResponse)
def finish_reservation(reservation_id: int, user: User=Depends(get_current_user), db: Session=Depends(get_db)):
    require_staff(user)
    reservation = db.query(Reservation).filter(Reservation.id==reservation_id).with_for_update().first()
    if not reservation:
        raise HTTPException(404, 'Reserva no encontrada')
    ensure_tenant_owns(db.get(Branch, reservation.branch_id), user, include_global=False, label='Reserva')
    if reservation.status != 'ATENDIDA':
        raise HTTPException(409, 'Solo se puede finalizar una reserva atendida')
    _release_reserved_stock(db, reservation, user)
    reservation.status = 'FINALIZADA'
    db.commit(); db.refresh(reservation)
    return _reservation_response(db, reservation)


def _exchange_response(record):
    return {'id': record.id, 'venta_id': record.venta_id, 'empresa_id': record.empresa_id,
        'estado': record.estado, 'fecha_solicitud': record.fecha_solicitud, 'fecha_limite': record.fecha_limite,
        'monto_diferencia': record.monto_diferencia, 'detalle': json.loads(record.detalle_json or '{}'), 'observaciones': record.observaciones}


@router.get('/orders/{order_id}/exchanges')
def list_exchanges(order_id: int, user: User=Depends(get_current_user), db: Session=Depends(get_db)):
    order = db.get(Order, order_id)
    ensure_tenant_owns(order, user, include_global=False, label='Pedido')
    if user.role_name not in _STAFF_ROLES and order.client_id != user.id:
        raise HTTPException(403, 'No puedes consultar este pedido')
    return [_exchange_response(row) for row in db.query(CambioPrenda).filter(CambioPrenda.venta_id==order_id).order_by(CambioPrenda.id.desc())]


@router.post('/orders/{order_id}/exchanges', status_code=201)
def exchange_garment(order_id: int, payload: ExchangeRequest, user: User=Depends(get_current_user), db: Session=Depends(get_db)):
    require_staff(user)
    order = db.query(Order).filter(Order.id==order_id).with_for_update().first()
    ensure_tenant_owns(order, user, include_global=False, label='Pedido')
    if order.empresa_id is None:
        raise HTTPException(409, 'Asigna la venta a una empresa antes de registrar cambios')
    deadline = _aware_to_utc_naive(order.created_at) + timedelta(days=settings.EXCHANGE_WINDOW_DAYS)
    if order.status not in {'PAGADO', 'ENVIADO', 'ENTREGADO'} or not order.branch_id or deadline < _utcnow_naive():
        raise HTTPException(409, f'El cambio requiere una venta confirmada dentro de {settings.EXCHANGE_WINDOW_DAYS} d?as')
    item = next((i for i in order.items if i.id == payload.order_item_id), None)
    if item is None:
        raise HTTPException(404, 'Prenda no encontrada en la venta')
    previous = db.query(CambioPrenda).filter(CambioPrenda.venta_id==order_id, CambioPrenda.estado=='APROBADO').all()
    returned = 0
    if any(r.status in {'PENDIENTE','SOLICITADO'} for r in order.refunds):
        raise HTTPException(409,'Resuelve el reembolso pendiente antes de cambiar prendas')
    for refund in order.refunds:
        if refund.status == 'COMPLETADO':
            returned += sum(r.quantity for r in refund.items if r.lot_key == f'item:{item.id}')
    for old in previous:
        details = json.loads(old.detalle_json or '{}')
        if details.get('order_item_id') == item.id:
            returned += details.get('quantity', 0)
    if returned + payload.quantity > item.quantity:
        raise HTTPException(409, 'La cantidad supera las prendas que a?n pueden cambiarse')
    replacement = _get_variant_or_404(db, payload.replacement_variant_id, user)
    from app.services.refunds import returnable_lots
    lot = next((lot for lot in returnable_lots(db,order) if lot['key']==f'item:{item.id}'),None)
    if not lot or not lot['quantity']:
        raise HTTPException(409,'Esta prenda ya no tiene unidades pendientes para cambiar')
    old_unit_price = float(lot['amount']/lot['quantity'])
    _, discount = promotion_discount_for_variant(db, replacement)
    new_unit_price = float(_money(replacement.effective_price) - _money(discount))
    difference = float(_money(Decimal(str(new_unit_price-old_unit_price))*payload.quantity))
    if abs(difference-payload.cash_difference)>0.01:
        raise HTTPException(422, f'Registra la diferencia exacta en efectivo: Bs {difference:.2f}. Un monto negativo representa devoluci?n al cliente.')
    # Orden estable de bloqueos para evitar interbloqueos entre cambios cruzados.
    stocks = {vid: _get_inventory(db, vid, order.branch_id, for_update=True) for vid in sorted({item.variant_id, replacement.id})}
    source, target = stocks[item.variant_id], stocks[replacement.id]
    if source is None or target is None:
        raise HTTPException(409, 'No hay inventario de las prendas en la sucursal de la venta')
    effective_available = target.available + (payload.quantity if item.variant_id == replacement.id else 0)
    if effective_available < payload.quantity:
        raise HTTPException(409, 'No hay existencias suficientes de la prenda de reemplazo')
    _movement(db, source, 'DEVOLUCION', payload.quantity, f'Cambio de la venta #{order.id}', user.id)
    _movement(db, target, 'SALIDA', -payload.quantity, f'Entrega por cambio de la venta #{order.id}', user.id)
    record = CambioPrenda(empresa_id=order.empresa_id, venta_id=order.id, usuario_id=user.id,
        fecha_limite=deadline, estado='APROBADO', monto_diferencia=difference, observaciones=payload.observations,
        detalle_json=json.dumps({'order_item_id': item.id, 'original_variant_id': item.variant_id,
            'replacement_variant_id': replacement.id, 'quantity': payload.quantity, 'old_unit_price': old_unit_price,
            'new_unit_price': new_unit_price, 'forma_pago': 'EFECTIVO'}))
    db.add(record); db.commit(); db.refresh(record)
    return _exchange_response(record)

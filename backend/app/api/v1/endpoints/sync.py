import json
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db
from app.core.tenant import get_current_empresa, get_current_user, ensure_tenant_owns
from app.models.branch import Branch
from app.models.catalog import ProductVariant
from app.models.commerce import Order, OrderItem, Payment, Reservation, ReservationItem, Notification
from app.models.inventory import Inventory, InventoryMovement
from app.models.sync import ConflictoSync, OperacionSync
from app.models.user import User, Role
from app.schemas import (
    ConflictoResponse,
    ResolverConflictoRequest,
    SyncItemResult,
    SyncRequest,
    SyncResponse,
)

router = APIRouter()

_STAFF_ROLES = {"Administrador", "Encargado de Sucursal", "Cajero"}


class _StockConflict(Exception):
    def __init__(self, available: int, requested: int, variant_id: int) -> None:
        self.available = available
        self.requested = requested
        self.variant_id = variant_id
        super().__init__("Stock insuficiente")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _require_staff(user: User) -> None:
    if user.role_name not in _STAFF_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requiere rol de administrador o de sucursal",
        )


def _payload_json(op) -> str:
    return json.dumps(op.model_dump(mode="json"), default=str)


def _get_operacion(db: Session, uuid: str, empresa_id: int) -> OperacionSync | None:
    return (
        db.query(OperacionSync)
        .filter(OperacionSync.uuid == uuid, OperacionSync.empresa_id == empresa_id)
        .with_for_update().first()
    )


def _upsert_operacion(
    db: Session,
    op,
    empresa_id: int,
    sucursal_id: int,
    usuario_id: int,
    estado: str,
    respuesta: dict,
    existente: OperacionSync | None,
) -> OperacionSync:
    if existente is None:
        existente = OperacionSync(
            uuid=op.uuid,
            empresa_id=empresa_id,
            sucursal_id=sucursal_id,
            usuario_id=usuario_id,
            tipo_operacion=op.tipo_operacion,
            payload_json=_payload_json(op),
            estado=estado,
            intentos=1,
            fecha_local=op.fecha_local,
            fecha_sync=_now(),
            respuesta_servidor=json.dumps(respuesta, default=str),
        )
        db.add(existente)
    else:
        existente.sucursal_id = sucursal_id
        existente.usuario_id = usuario_id
        existente.tipo_operacion = op.tipo_operacion
        existente.payload_json = _payload_json(op)
        existente.estado = estado
        existente.intentos = (existente.intentos or 0) + 1
        existente.fecha_sync = _now()
        existente.respuesta_servidor = json.dumps(respuesta, default=str)
    db.flush()
    return existente


def _normalize_items(items: list[dict]) -> list[dict]:
    if not items:
        raise ValueError("La operación no contiene ítems")
    grouped = {}
    for raw in items:
        try:
            vid = raw.get("variante_id", raw.get("variant_id"))
            qty = raw.get("cantidad", raw.get("quantity"))
            if isinstance(vid, bool) or isinstance(qty, bool):
                raise ValueError()
            variant_id, quantity = int(vid), int(qty)
            if Decimal(str(qty)) != quantity or Decimal(str(vid)) != variant_id:
                raise ValueError()
        except (TypeError, ValueError, InvalidOperation, OverflowError):
            raise ValueError("Ítem inválido: variante o cantidad no numérica")
        if quantity <= 0 or variant_id <= 0:
            raise ValueError("La cantidad debe ser mayor a cero")
        price = next((raw[k] for k in ("precio", "precio_unitario", "unit_price") if k in raw), None)
        if price is not None:
            try:
                price = Decimal(str(price))
                if not price.is_finite() or price < 0:
                    raise ValueError()
                price = float(price.quantize(Decimal("0.01")))
            except (ValueError, InvalidOperation):
                raise ValueError("El precio debe ser finito y no negativo")
        if variant_id in grouped:
            if grouped[variant_id].get("precio") != price:
                raise ValueError("Una variante no puede tener precios diferentes en la misma operación")
            grouped[variant_id]["cantidad"] += quantity
        else:
            grouped[variant_id] = {"variante_id": variant_id, "cantidad": quantity, "precio": price}
    return [grouped[key] for key in sorted(grouped)]


def _validate_items(db: Session, branch_id: int, items: list[dict]):
    branch = db.get(Branch, branch_id)
    validated = []
    for raw in _normalize_items(items):
        variant_id, quantity = raw["variante_id"], raw["cantidad"]

        variant = db.query(ProductVariant).filter(ProductVariant.id == variant_id).first()
        if (not variant or not variant.is_active or not variant.product.is_active
                or variant.product.empresa_id not in (None, branch.empresa_id)):
            raise ValueError(f"Variante {variant_id} no válida o inactiva")

        inventory = (
            db.query(Inventory)
            .filter(Inventory.branch_id == branch_id, Inventory.variant_id == variant_id)
            .populate_existing().with_for_update()
            .first()
        )
        available = inventory.available if inventory else 0
        if available < quantity:
            raise _StockConflict(available=available, requested=quantity, variant_id=variant_id)

        price = raw.get("precio")
        unit_price = float(price if price is not None else variant.effective_price)
        if unit_price < 0:
            raise ValueError("El precio no puede ser negativo")

        validated.append(
            {
                "variant": variant,
                "inventory": inventory,
                "quantity": quantity,
                "unit_price": unit_price,
            }
        )
    return validated


def _discount_stock(
    db: Session, inventory: Inventory, quantity: int, movement_type: str, reason: str, user_id: int
) -> None:
    if inventory.available < quantity:
        raise ValueError("Stock insuficiente al confirmar la operación")
    inventory.available -= quantity
    db.add(
        InventoryMovement(
            inventory_id=inventory.id,
            movement_type=movement_type,
            quantity=-quantity,
            reason=reason,
            user_id=user_id,
        )
    )


def _create_sale(
    db: Session,
    empresa_id: int,
    user: User,
    op,
    validated: list[dict],
) -> Order:
    total = round(
        sum(item["quantity"] * item["unit_price"] for item in validated), 2
    )
    from app.api.commerce import _get_or_create_mostrador
    order = Order(
        created_at=op.fecha_local or _now(),
        empresa_id=empresa_id,
        client_id=op.cliente_id or _get_or_create_mostrador(db, empresa_id).id,
        user_id=op.usuario_id,
        branch_id=op.sucursal_id,
        order_type="PRESENCIAL",
        status="PAGADO",
        stock_deducted=True,
        subtotal=total,
        total=total,
        es_offline=True,
        origen="OFFLINE",
        order_number=f"OFF-{op.uuid[:12].upper()}",
        payment_method=op.forma_pago or "EFECTIVO",
    )
    db.add(order)
    db.flush()

    for item in validated:
        db.add(
            OrderItem(
                order_id=order.id,
                variant_id=item["variant"].id,
                quantity=item["quantity"],
                unit_price=item["unit_price"],
                discount=0.0,
            )
        )
        _discount_stock(
            db,
            item["inventory"],
            item["quantity"],
            "SALIDA",
            f"Venta offline {op.uuid}",
            user.id,
        )

    db.add(
        Payment(
            order_id=order.id,
            amount=total,
            method=op.forma_pago or "EFECTIVO",
            status="COMPLETADO",
            cash_received=total,
            change_amount=0,
            paid_at=_now(),
        )
    )
    return order


def _create_reservation(
    db: Session,
    user: User,
    op,
    validated: list[dict],
) -> Reservation:
    created = op.fecha_local or _now()
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    hours = int((getattr(op, "payload_extra", None) or {}).get("expiration_hours", 24))
    if not 1 <= hours <= 720:
        raise ValueError("La duración de la reserva debe estar entre 1 y 720 horas")
    expires = created + timedelta(hours=hours)
    if expires <= _now():
        raise ValueError("La reserva local ya venció antes de sincronizar")
    reservation = Reservation(
        code=f"RSV-OFF-{op.uuid[:8].upper()}",
        client_id=op.cliente_id or user.id,
        branch_id=op.sucursal_id,
        status="PENDIENTE",
        reservation_date=created,
        expiration_date=expires,
    )
    db.add(reservation)
    db.flush()

    for item in validated:
        db.add(
            ReservationItem(
                reservation_id=reservation.id,
                variant_id=item["variant"].id,
                quantity=item["quantity"],
                unit_price=item["unit_price"],
            )
        )
        _discount_stock(
            db,
            item["inventory"],
            item["quantity"],
            "RESERVA",
            f"Reserva offline {op.uuid}",
            user.id,
        )
    staff = db.query(User.id).join(Role).filter(User.empresa_id == user.empresa_id,
        User.is_active.is_(True), Role.name.in_(("Administrador", "Encargado de Sucursal"))).all()
    for uid in {user.id, *(row.id for row in staff)}:
        db.add(Notification(user_id=uid, title="Reserva sincronizada",
            message=f"Reserva {reservation.code} recibida en la sucursal #{op.sucursal_id}."))
    return reservation


def _save_conflict(
    db: Session,
    op_sync: OperacionSync,
    motivo: str,
    available: int,
    requested: int,
) -> None:
    conflicto = (
        db.query(ConflictoSync)
        .filter(ConflictoSync.operacion_sync_id == op_sync.id)
        .first()
    )
    if conflicto is None:
        conflicto = ConflictoSync(
            empresa_id=op_sync.empresa_id,
            operacion_sync_id=op_sync.id,
            motivo=motivo,
            stock_disponible=available,
            cantidad_solicitada=requested,
            resuelto=False,
        )
        db.add(conflicto)
    else:
        conflicto.motivo = motivo
        conflicto.stock_disponible = available
        conflicto.cantidad_solicitada = requested
        conflicto.resuelto = False
        conflicto.resuelto_por = None
        conflicto.fecha_resolucion = None
        conflicto.accion_tomada = None


@router.post("", response_model=SyncResponse)
@router.post("/sync", response_model=SyncResponse, include_in_schema=False)
def sincronizar_operaciones(
    request: SyncRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    empresa=Depends(get_current_empresa),
):
    resultados: List[SyncItemResult] = []

    for op in request.operaciones:
        if op.usuario_id != current_user.id:
            resultados.append(SyncItemResult(uuid=op.uuid, estado="RECHAZADA", mensaje="El responsable no coincide con el usuario autenticado"))
            continue
        existente = _get_operacion(db, op.uuid, empresa.id)
        if existente and existente.usuario_id != current_user.id:
            resultados.append(SyncItemResult(uuid=op.uuid, estado="RECHAZADA", mensaje="La operación pertenece a otro responsable"))
            continue
        if existente and existente.estado in {"CONFIRMADA", "RECHAZADA", "EN_CONFLICTO"}:
            resultados.append(
                SyncItemResult(
                    uuid=op.uuid,
                    estado=existente.estado,
                    mensaje="Operación registrada previamente; conserva su resultado",
                    operacion_sync_id=existente.id,
                )
            )
            continue

        duplicado_otra_empresa = (
            db.query(OperacionSync)
            .filter(OperacionSync.uuid == op.uuid, OperacionSync.empresa_id != empresa.id)
            .first()
        )
        if duplicado_otra_empresa:
            resultados.append(
                SyncItemResult(
                    uuid=op.uuid,
                    estado="RECHAZADA",
                    mensaje="El uuid ya fue utilizado por otra empresa",
                )
            )
            continue

        sucursal = (
            db.query(Branch)
            .filter(Branch.id == op.sucursal_id, Branch.empresa_id == empresa.id, Branch.is_active.is_(True))
            .first()
        )
        if not sucursal:
            resultados.append(
                SyncItemResult(
                    uuid=op.uuid,
                    estado="RECHAZADA",
                    mensaje="Sucursal no pertenece a la empresa",
                )
            )
            continue

        if op.tipo_operacion not in {"VENTA_CONTADO", "RESERVA"}:
            resultados.append(
                SyncItemResult(
                    uuid=op.uuid,
                    estado="RECHAZADA",
                    mensaje="Tipo de operación no soportado",
                )
            )
            continue

        try:
            if op.tipo_operacion == "RESERVA":
                try:
                    hours = int((op.payload_extra or {}).get("expiration_hours", 24))
                except (ValueError, TypeError):
                    raise ValueError("La duración de la reserva debe ser numérica")
                created = op.fecha_local or _now()
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                if not 1 <= hours <= 720 or created + timedelta(hours=hours) <= _now():
                    raise ValueError("La reserva local no está vigente")
            if op.usuario_id != current_user.id:
                raise ValueError("El responsable no coincide con el usuario autenticado")
            if op.tipo_operacion == "VENTA_CONTADO":
                _require_staff(current_user)
                if op.forma_pago != "EFECTIVO":
                    raise ValueError("Las ventas offline solo admiten efectivo")
            elif current_user.role_name not in _STAFF_ROLES | {"Cliente"}:
                raise ValueError("Usuario no autorizado para registrar reservas")
            if op.cliente_id:
                client = db.get(User, op.cliente_id)
                if not client or not client.is_active or client.empresa_id != empresa.id:
                    raise ValueError("Cliente no pertenece a la empresa")
                if current_user.role_name == "Cliente" and client.id != current_user.id:
                    raise ValueError("Solo puedes registrar tus propias reservas")
            op = op.model_copy(update={"items": _normalize_items(op.items)})
            # Reclamar el UUID antes de crear la venta evita duplicados concurrentes.
            if existente is None:
                try:
                    with db.begin_nested():
                        existente = _upsert_operacion(db, op, empresa.id, sucursal.id,
                            current_user.id, "ENVIADA", {}, None)
                except IntegrityError:
                    existente = _get_operacion(db, op.uuid, empresa.id)
                    if existente is None:
                        raise ValueError("UUID no disponible")
                    resultados.append(SyncItemResult(uuid=op.uuid, estado=existente.estado,
                        mensaje="Operación ya procesada", operacion_sync_id=existente.id))
                    db.commit()
                    continue
            validated = _validate_items(db, sucursal.id, op.items or [])
            expected_total = round(sum(i["quantity"] * i["unit_price"] for i in validated), 2)
            if op.tipo_operacion == "VENTA_CONTADO" and op.total is not None and abs(op.total - expected_total) > 0.01:
                raise ValueError("El total no coincide con los precios y cantidades registrados")
        except _StockConflict as conflict:
            op_sync = _upsert_operacion(
                db,
                op,
                empresa.id,
                sucursal.id,
                current_user.id,
                "EN_CONFLICTO",
                {"motivo": "Stock insuficiente", "variante_id": conflict.variant_id},
                existente,
            )
            _save_conflict(
                db,
                op_sync,
                "Stock insuficiente al sincronizar operación offline",
                conflict.available,
                conflict.requested,
            )
            db.commit()
            resultados.append(
                SyncItemResult(
                    uuid=op.uuid,
                    estado="EN_CONFLICTO",
                    mensaje="Conflicto por stock",
                    operacion_sync_id=op_sync.id,
                )
            )
            continue
        except ValueError as exc:
            # No hay efectos comerciales hasta completar todas las validaciones.
            op_sync = _upsert_operacion(
                db,
                op,
                empresa.id,
                sucursal.id,
                current_user.id,
                "RECHAZADA",
                {"motivo": str(exc)},
                existente,
            )
            db.commit()
            resultados.append(
                SyncItemResult(
                    uuid=op.uuid,
                    estado="RECHAZADA",
                    mensaje=str(exc),
                    operacion_sync_id=op_sync.id,
                )
            )
            continue

        try:
            if op.tipo_operacion == "VENTA_CONTADO":
                entidad = _create_sale(db, empresa.id, current_user, op, validated)
                respuesta = {"order_id": entidad.id, "order_number": entidad.order_number}
                mensaje = "Venta sincronizada"
            else:
                entidad = _create_reservation(db, current_user, op, validated)
                respuesta = {"reservation_id": entidad.id, "code": entidad.code}
                mensaje = "Reserva sincronizada"

            op_sync = _upsert_operacion(
                db,
                op,
                empresa.id,
                sucursal.id,
                current_user.id,
                "CONFIRMADA",
                respuesta,
                existente,
            )
            if existente and existente.conflicto and not existente.conflicto.resuelto:
                existente.conflicto.resuelto = True
                existente.conflicto.resuelto_por = current_user.id
                existente.conflicto.fecha_resolucion = _now()
                existente.conflicto.accion_tomada = "REINTENTO"
            db.commit()
        except Exception:
            db.rollback()
            raise

        resultados.append(
            SyncItemResult(
                uuid=op.uuid,
                estado="CONFIRMADA",
                mensaje=mensaje,
                operacion_sync_id=op_sync.id,
            )
        )

    return SyncResponse(resultados=resultados)


@router.get("/conflictos", response_model=List[ConflictoResponse])
def listar_conflictos(
    solo_pendientes: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    empresa=Depends(get_current_empresa),
):
    _require_staff(current_user)
    query = db.query(ConflictoSync).filter(ConflictoSync.empresa_id == empresa.id)
    if solo_pendientes:
        query = query.filter(ConflictoSync.resuelto.is_(False))
    return query.order_by(ConflictoSync.created_at.asc()).all()


@router.post("/conflictos/{conflicto_id}/resolver", response_model=ConflictoResponse)
def resolver_conflicto(
    conflicto_id: int,
    request: ResolverConflictoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    empresa=Depends(get_current_empresa),
):
    _require_staff(current_user)

    conflicto = (
        db.query(ConflictoSync)
        .filter(
            ConflictoSync.id == conflicto_id,
            ConflictoSync.empresa_id == empresa.id,
        )
        .with_for_update().first()
    )
    if not conflicto:
        raise HTTPException(status_code=404, detail="Conflicto no encontrado")
    if conflicto.resuelto:
        raise HTTPException(status_code=400, detail="El conflicto ya fue resuelto")

    operacion = conflicto.operacion
    accion = (request.accion or "").strip().upper()

    if accion == "RECHAZAR":
        operacion.estado = "RECHAZADA"
        operacion.respuesta_servidor = json.dumps(
            {"motivo": request.observaciones or "Rechazado por el usuario"}
        )
        conflicto.resuelto = True
        conflicto.resuelto_por = current_user.id
        conflicto.fecha_resolucion = _now()
        conflicto.accion_tomada = "RECHAZAR"
        db.commit()
        db.refresh(conflicto)
        return conflicto

    if accion != "AJUSTAR_CANTIDAD":
        raise HTTPException(status_code=400, detail="Acción no válida")

    if not request.cantidad_aceptada or request.cantidad_aceptada <= 0:
        raise HTTPException(
            status_code=400, detail="La cantidad aceptada debe ser mayor a cero"
        )

    payload = json.loads(operacion.payload_json or "{}")
    items = _normalize_items(payload.get("items") or [])
    if not items:
        raise HTTPException(status_code=400, detail="La operación no tiene ítems")

    solicitada = int(conflicto.cantidad_solicitada or 0)
    aceptada = min(int(request.cantidad_aceptada), solicitada or int(request.cantidad_aceptada))

    conflict_variant = json.loads(operacion.respuesta_servidor or "{}").get("variante_id")
    for item in items:
        cantidad = int(item.get("cantidad") or item.get("quantity") or 0)
        if item.get("variante_id") == conflict_variant or (not conflict_variant and (cantidad == solicitada or len(items) == 1)):
            item["cantidad"] = aceptada
            item.pop("quantity", None)
            break

    try:
        validated = _validate_items(db, operacion.sucursal_id, items)
    except _StockConflict as conflict:
        conflicto.stock_disponible = conflict.available
        db.commit()
        raise HTTPException(
            status_code=409,
            detail=f"Stock insuficiente: disponible {conflict.available}, solicitado {conflict.requested}",
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))

    op_data = SimpleNamespace(
        uuid=operacion.uuid,
        usuario_id=operacion.usuario_id,
        sucursal_id=operacion.sucursal_id,
        cliente_id=payload.get("cliente_id"),
        forma_pago=payload.get("forma_pago") or "EFECTIVO",
        fecha_local=operacion.fecha_local,
        payload_extra=payload.get("payload_extra"),
    )

    try:
        if operacion.tipo_operacion == "VENTA_CONTADO":
            entidad = _create_sale(db, empresa.id, current_user, op_data, validated)
            respuesta = {"order_id": entidad.id, "order_number": entidad.order_number}
        else:
            entidad = _create_reservation(db, current_user, op_data, validated)
            respuesta = {"reservation_id": entidad.id, "code": entidad.code}

        operacion.estado = "CONFIRMADA"
        operacion.respuesta_servidor = json.dumps(respuesta, default=str)
        operacion.fecha_sync = _now()
        conflicto.resuelto = True
        conflicto.resuelto_por = current_user.id
        conflicto.fecha_resolucion = _now()
        conflicto.accion_tomada = "AJUSTAR_CANTIDAD"
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(conflicto)
    return conflicto

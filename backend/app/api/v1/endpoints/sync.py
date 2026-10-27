import json
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.tenant import get_current_empresa, get_current_user
from app.models.sync import OperacionSync, ConflictoSync
from app.models.inventory import Inventory
from app.models.commerce import Order, OrderItem, Reservation, ReservationItem
from app.models.catalog import ProductVariant
try:
    from app.schemas.sync import (
        SyncRequest,
        SyncResponse,
        SyncItemResult,
        ResolverConflictoRequest,
        ConflictoResponse,
    )
except Exception:
    from app.schemas import (
        SyncRequest,
        SyncResponse,
        SyncItemResult,
        ResolverConflictoRequest,
        ConflictoResponse,
    )
from app.models.user import User
from app.models.branch import Branch

router = APIRouter()


@router.post("/sync", response_model=SyncResponse)
def sincronizar_operaciones(
    request: SyncRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    empresa = Depends(get_current_empresa),
):
    resultados: List[SyncItemResult] = []

    for op in request.operaciones:
        # Idempotencia: buscar por UUID
        existente = db.query(OperacionSync).filter(OperacionSync.uuid == op.uuid).first()
        if existente and existente.estado == "CONFIRMADA":
            resultados.append(
                SyncItemResult(
                    uuid=op.uuid,
                    estado="CONFIRMADA",
                    mensaje="Ya sincronizada previamente (idempotencia)",
                    operacion_sync_id=existente.id,
                )
            )
            continue

        sucursal = db.query(Branch).filter(Branch.id == op.sucursal_id, Branch.empresa_id == empresa.id).first()
        if not sucursal:
            resultados.append(SyncItemResult(uuid=op.uuid, estado="RECHAZADA", mensaje="Sucursal no pertenece a la empresa"))
            continue

        if op.tipo_operacion == "VENTA_CONTADO":
            # Validar inventario por items
            conflicto_detectado = False
            items_payload = op.items or []
            for it in items_payload:
                variante_id = it.get("variante_id")
                cantidad = int(it.get("cantidad", 0))
                inv = (
                    db.query(Inventory)
                    .join(ProductVariant, Inventory.variant_id == ProductVariant.id)
                    .filter(
                        Inventory.branch_id == sucursal.id,
                        Inventory.empresa_id == empresa.id,
                        ProductVariant.id == variante_id,
                    )
                    .first()
                )
                if not inv or inv.quantity < cantidad:
                    conflicto_detectado = True
                    break

            if conflicto_detectado:
                op_sync = OperacionSync(
                    uuid=op.uuid,
                    empresa_id=empresa.id,
                    sucursal_id=sucursal.id,
                    usuario_id=current_user.id,
                    tipo_operacion=op.tipo_operacion,
                    payload_json=json.dumps(op.model_dump()),
                    estado="EN_CONFLICTO",
                    intentos=(existente.intentos + 1) if existente else 1,
                    fecha_local=op.fecha_local,
                    fecha_sync=datetime.utcnow(),
                    respuesta_servidor=json.dumps({"motivo": "Stock insuficiente"}),
                )
                if existente:
                    db.delete(existente)
                db.add(op_sync)
                db.commit()
                db.refresh(op_sync)
                conflicto = ConflictoSync(
                    empresa_id=empresa.id,
                    operacion_sync_id=op_sync.id,
                    motivo="Stock insuficiente al sincronizar venta de contado",
                    stock_disponible=0,
                    cantidad_solicitada=items_payload[0].get("cantidad", 0) if items_payload else 0,
                    resuelto=False,
                )
                db.add(conflicto)
                db.commit()
                resultados.append(SyncItemResult(uuid=op.uuid, estado="EN_CONFLICTO", mensaje="Conflicto por stock", operacion_sync_id=op_sync.id))
                continue

            # Crear venta confirmada
            order = Order(
                empresa_id=empresa.id,
                branch_id=sucursal.id,
                user_id=current_user.id,
                order_number=f"OFF-{op.uuid[:8].upper()}",
                status="PAGADO",
                payment_method=op.forma_pago or "EFECTIVO",
                subtotal=op.total or 0,
                total=op.total or 0,
                es_offline=True,
                origen="OFFLINE",
            )
            db.add(order)
            db.commit()
            db.refresh(order)

            op_sync = OperacionSync(
                uuid=op.uuid,
                empresa_id=empresa.id,
                sucursal_id=sucursal.id,
                usuario_id=current_user.id,
                tipo_operacion=op.tipo_operacion,
                payload_json=json.dumps(op.model_dump()),
                estado="CONFIRMADA",
                intentos=(existente.intentos + 1) if existente else 1,
                fecha_local=op.fecha_local,
                fecha_sync=datetime.utcnow(),
                respuesta_servidor=json.dumps({"order_id": order.id}),
            )
            if existente:
                db.delete(existente)
            db.add(op_sync)
            db.commit()

            resultados.append(SyncItemResult(uuid=op.uuid, estado="CONFIRMADA", mensaje="Venta sincronizada", operacion_sync_id=op_sync.id))
            continue

        # Otros tipos
            resultados.append(SyncItemResult(uuid=op.uuid, estado="RECHAZADA", mensaje="Tipo de operación no soportado en esta versión"))

    return SyncResponse(resultados=resultados)


@router.get("/conflictos", response_model=List[ConflictoResponse])
def listar_conflictos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    empresa = Depends(get_current_empresa),
    solo_pendientes: bool = True,
):
    query = db.query(ConflictoSync).filter(ConflictoSync.empresa_id == empresa.id)
    if solo_pendientes:
        query = query.filter(ConflictoSync.resuelto == False)
    return query.order_by(ConflictoSync.created_at.desc()).all()


@router.post("/conflictos/{conflicto_id}/resolver")
def resolver_conflicto(
    conflicto_id: int,
    req: ResolverConflictoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    empresa = Depends(get_current_empresa),
):
    conflicto = (
        db.query(ConflictoSync)
        .filter(ConflictoSync.id == conflicto_id, ConflictoSync.empresa_id == empresa.id)
        .first()
    )
    if not conflicto:
        raise HTTPException(status_code=404, detail="Conflicto no encontrado")
    if conflicto.resuelto:
        raise HTTPException(status_code=400, detail="Conflicto ya resuelto")

    operacion = db.query(OperacionSync).filter(OperacionSync.id == conflicto.operacion_sync_id).first()
    if not operacion:
        raise HTTPException(status_code=404, detail="Operación asociada no encontrada")

    if req.accion == "RECHAZAR":
        operacion.estado = "RECHAZADA"
        operacion.respuesta_servidor = json.dumps({"motivo": "Rechazado por encargado", "observaciones": req.observaciones})
        operacion.fecha_sync = datetime.utcnow()
        conflicto.resuelto = True
        conflicto.resuelto_por = current_user.id
        conflicto.fecha_resolucion = datetime.utcnow()
        conflicto.accion_tomada = "RECHAZADO"
        db.commit()
        return {"mensaje": "Conflicto resuelto: operación rechazada", "uuid": operacion.uuid}

    if req.accion == "AJUSTAR_CANTIDAD":
        operacion.estado = "RECHAZADA"
        operacion.respuesta_servidor = json.dumps(
            {
                "motivo": "Ajuste de cantidad requerido",
                "cantidad_aceptada": req.cantidad_aceptada,
                "observaciones": req.observaciones,
            }
        )
        operacion.fecha_sync = datetime.utcnow()
        conflicto.resuelto = True
        conflicto.resuelto_por = current_user.id
        conflicto.fecha_resolucion = datetime.utcnow()
        conflicto.accion_tomada = "AJUSTADO"
        db.commit()
        return {"mensaje": "Conflicto resuelto con ajuste", "uuid": operacion.uuid, "cantidad_aceptada": req.cantidad_aceptada}

    raise HTTPException(status_code=400, detail="Acción no válida. Usar AJUSTAR_CANTIDAD o RECHAZAR")

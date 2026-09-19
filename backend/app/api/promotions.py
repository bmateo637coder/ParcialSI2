"""Gestión de promociones (exclusivo administración).

CRUD de promociones con alcance global, por categoría o por producto, descontos
porcentuales o fijos, ventana de fechas opcional y habilitación/deshabilitación.
El descuento se aplica en el carrito, el checkout y el POS seleccionando la
mejor promoción vigente por variante (ver app/services/promotions.py).
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.models.promotion import Promotion
from app.schemas import PromotionCreate, PromotionResponse, PromotionUpdate
from app.services.promotions import validate_target

router = APIRouter()


def _get_promo_or_404(db: Session, promotion_id: int) -> Promotion:
    promo = db.get(Promotion, promotion_id)
    if promo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promoción no encontrada")
    return promo


def _validate_payload(payload: PromotionCreate) -> None:
    if payload.discount_type == "PERCENTAGE" and not (0 < payload.value <= 100):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="El porcentaje debe estar entre 0 y 100")
    if payload.discount_type == "FIXED" and payload.value <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="El descuento fijo debe ser mayor a 0")
    if payload.target_type != "GLOBAL" and payload.target_id is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"target_id es obligatorio para el alcance {payload.target_type}")
    if payload.start_date and payload.end_date and payload.start_date > payload.end_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="start_date no puede ser posterior a end_date")


@router.get("/", response_model=list[PromotionResponse], summary="Listar promociones")
def list_promotions(include_inactive: bool = False,
                    user=Depends(get_current_user),
                    db: Session = Depends(get_db)):
    if user.role_name != "Administrador":
        include_inactive = False
    query = db.query(Promotion)
    if not include_inactive:
        query = query.filter(Promotion.is_active == True)  # noqa: E712
    return query.order_by(Promotion.id.desc()).all()


@router.post("/", response_model=PromotionResponse, status_code=status.HTTP_201_CREATED,
             summary="Crear promoción (admin)")
def create_promotion(payload: PromotionCreate, _admin=Depends(require_admin),
                     db: Session = Depends(get_db)):
    _validate_payload(payload)
    promo = Promotion(**payload.model_dump())
    try:
        validate_target(db, promo)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    db.add(promo)
    db.commit()
    db.refresh(promo)
    return promo


@router.patch("/{promotion_id}", response_model=PromotionResponse,
              summary="Actualizar promoción (admin)")
def update_promotion(promotion_id: int, payload: PromotionUpdate,
                     _admin=Depends(require_admin), db: Session = Depends(get_db)):
    promo = _get_promo_or_404(db, promotion_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(promo, field, value)
    _validate_payload(promo)
    try:
        validate_target(db, promo)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    db.commit()
    db.refresh(promo)
    return promo


@router.delete("/{promotion_id}", response_model=PromotionResponse,
               summary="Deshabilitar promoción (admin, soft-delete)")
def deactivate_promotion(promotion_id: int, _admin=Depends(require_admin),
                         db: Session = Depends(get_db)):
    promo = _get_promo_or_404(db, promotion_id)
    promo.is_active = False
    db.commit()
    db.refresh(promo)
    return promo
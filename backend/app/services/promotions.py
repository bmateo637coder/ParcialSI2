"""Selección del descuento vigente para una variante (regla de negocio CU Admin).

Solo se aplica la MEJOR promoción vigente por variante:
- GLOBAL  : todas los productos activos.
- CATEGORY: productos de la categoría indicada.
- PRODUCT : el producto indicado.

Una promoción está vigente si está habilitada (is_active) y la fecha actual
está dentro de [start_date, end_date] (inclusive; fechas opcionales = sin límite).
En empate (mismo importe en Bs) gana el id menor.
"""

from datetime import date, datetime, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.catalog import Category, Product, ProductVariant
from app.models.promotion import Promotion


def _discount_amount(discount_type: str, value: float, effective_price: float) -> float:
    if discount_type == "PERCENTAGE":
        return round(effective_price * value / 100.0, 2)
    return round(min(float(value), effective_price), 2)


def _is_current(promo: Promotion, today: date) -> bool:
    if not promo.is_active:
        return False
    if promo.start_date is not None and today < promo.start_date:
        return False
    if promo.end_date is not None and today > promo.end_date:
        return False
    return True


def promotion_discount_for_variant(db: Session, variant: ProductVariant) -> tuple[int | None, float]:
    """Devuelve (promotion_id, descuento_unitario_en_Bs) para la variante.

    El descuento es el mayor ahorro en Bs entre las promociones vigentes que
    aplican a la variante; si ninguna aplica devuelve (None, 0.0).
    """
    today = datetime.now(timezone.utc).date()
    effective: float = variant.effective_price

    empresa_id = variant.product.empresa_id
    if empresa_id is None and variant.product.category:
        empresa_id = variant.product.category.empresa_id

    promos_query = db.query(Promotion)
    if empresa_id is not None:
        promos_query = promos_query.filter(or_(Promotion.empresa_id == empresa_id,
                                               Promotion.empresa_id.is_(None)))
    else:
        promos_query = promos_query.filter(Promotion.empresa_id.is_(None))
    promos = promos_query.all()
    best_id: int | None = None
    best_discount: float = 0.0

    # 1) PRODUCT
    for promo in promos:
        if promo.target_type != "PRODUCT" or promo.target_id != variant.product_id:
            continue
        if not _is_current(promo, today):
            continue
        discount = _discount_amount(promo.discount_type, promo.value, effective)
        if discount > best_discount or (discount == best_discount and (best_id is None or promo.id < best_id)):
            best_discount = discount
            best_id = promo.id

    # 2) CATEGORY
    product = variant.product
    category_id = product.category_id if product else None
    if category_id is not None:
        for promo in promos:
            if promo.target_type != "CATEGORY" or promo.target_id != category_id:
                continue
            if not _is_current(promo, today):
                continue
            discount = _discount_amount(promo.discount_type, promo.value, effective)
            if discount > best_discount or (discount == best_discount and (best_id is None or promo.id < best_id)):
                best_discount = discount
                best_id = promo.id

    # 3) GLOBAL
    for promo in promos:
        if promo.target_type != "GLOBAL":
            continue
        if not _is_current(promo, today):
            continue
        discount = _discount_amount(promo.discount_type, promo.value, effective)
        if discount > best_discount or (discount == best_discount and (best_id is None or promo.id < best_id)):
            best_discount = discount
            best_id = promo.id

    return best_id, best_discount


def _belongs_to_tenant(category: Category | None, empresa_id: int | None) -> bool:
    if empresa_id is None or category is None:
        return True
    return category.empresa_id in (None, empresa_id)


def validate_target(db: Session, promo, empresa_id: int | None = None) -> None:
    """Valida que un objetivo exista y no cruce el límite de la empresa."""
    if promo.target_type == "PRODUCT":
        product = db.get(Product, promo.target_id) if promo.target_id is not None else None
        if promo.target_id is not None and product is None:
            raise ValueError(f"El producto {promo.target_id} no existe")
        if product is not None:
            if product.empresa_id not in (None, empresa_id):
                raise ValueError(f"El producto {promo.target_id} no existe")
            category = db.get(Category, product.category_id) if product.category_id else None
            if not _belongs_to_tenant(category, empresa_id):
                raise ValueError(f"El producto {promo.target_id} no existe")
    elif promo.target_type == "CATEGORY":
        category = db.get(Category, promo.target_id) if promo.target_id is not None else None
        if promo.target_id is not None and category is None:
            raise ValueError(f"La categoría {promo.target_id} no existe")
        if category is not None and not _belongs_to_tenant(category, empresa_id):
            raise ValueError(f"La categoría {promo.target_id} no existe")
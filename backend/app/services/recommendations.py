"""CU22 — Recomendar prendas.

Servicio de "IA" basado en reglas sobre el historial real de compras del
cliente: prioriza la categoría que más compra, ajusta por cercanía de precio
y excluye productos ya comprados. Sin historial, cae a productos destacados
del catálogo (tal como exige el documento del enunciado).
"""

from app.models.catalog import Product, ProductVariant
from app.models.commerce import Order, OrderItem
from app.models.inventory import Inventory
from app.schemas import RecommendedItem, RecommendationResponse

_DEFAULT_LIMIT = 8


def _category_name(product: Product) -> str:
    cat = product.category
    return cat.name if cat else "Categoría general"


def recommend(db, user_id: int, limit: int = _DEFAULT_LIMIT) -> RecommendationResponse:
    rows = (
        db.query(OrderItem, Product, ProductVariant)
        .join(Order, OrderItem.order_id == Order.id)
        .join(ProductVariant, OrderItem.variant_id == ProductVariant.id)
        .join(Product, ProductVariant.product_id == Product.id)
        .filter(Order.client_id == user_id, Order.status != "CANCELADO")
        .all()
    )

    if not rows:
        return _featured(db, limit)

    purchased_ids = set()
    category_freq: dict = {}
    amount = 0.0
    units = 0

    for item, product, _variant in rows:
        purchased_ids.add(product.id)
        category_freq[product.category_id] = (
            category_freq.get(product.category_id, 0) + item.quantity
        )
        amount += item.unit_price * item.quantity
        units += item.quantity

    avg_price = amount / units if units else None
    top_categories = {c for c, _ in sorted(category_freq.items(), key=lambda kv: -kv[1])}

    candidates = (
        db.query(Product, ProductVariant, Inventory)
        .join(ProductVariant, ProductVariant.product_id == Product.id)
        .join(Inventory, Inventory.variant_id == ProductVariant.id)
        .filter(
            Product.is_active.is_(True),
            ProductVariant.is_active.is_(True),
            Inventory.available > 0,
        )
        .all()
    )

    seen: dict[int, Product] = {}
    for product, _variant, _inventory in candidates:
        if product.id in purchased_ids or product.id in seen:
            continue
        seen[product.id] = product

    scored = []
    for product in seen.values():
        score = 0.0
        reasons = []
        if product.category_id in top_categories:
            score += 3.0
            reasons.append(f"por tu interés en {_category_name(product)}")
        if avg_price and product.base_price:
            ratio = min(avg_price, product.base_price) / max(avg_price, product.base_price)
            score += ratio
            if ratio >= 0.8:
                reasons.append("dentro de tu rango de precio habitual")
        if not reasons:
            reasons.append("para complementar tu guardarropa")
        scored.append((score, product, reasons))

    scored.sort(key=lambda s: s[0], reverse=True)

    items = [
        RecommendedItem(
            product_id=product.id,
            name=product.name,
            category=_category_name(product),
            base_price=round(product.base_price or 0.0, 2),
            in_stock=True,
            reason=f"Te recomendamos {product.name} {'. '.join(reasons)}.",
            score=round(score, 4),
        )
        for score, product, reasons in scored[:limit]
    ]

    return RecommendationResponse(source="ai", items=items)


def _featured(db, limit: int) -> RecommendationResponse:
    rows = (
        db.query(Product)
        .join(ProductVariant, ProductVariant.product_id == Product.id)
        .join(Inventory, Inventory.variant_id == ProductVariant.id)
        .filter(
            Product.is_active.is_(True),
            ProductVariant.is_active.is_(True),
            Inventory.available > 0,
        )
        .all()
    )

    seen: dict[int, Product] = {}
    for product in rows:
        if product.id not in seen:
            seen[product.id] = product

    items = [
        RecommendedItem(
            product_id=product.id,
            name=product.name,
            category=_category_name(product),
            base_price=round(product.base_price or 0.0, 2),
            in_stock=True,
            reason=f"Te recomendamos {product.name}: una prenda destacada de nuestro catálogo.",
            score=round(1.0, 4),
        )
        for product in list(seen.values())[:limit]
    ]

    return RecommendationResponse(source="featured", items=items)
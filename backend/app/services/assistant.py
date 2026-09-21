"""CU23 — Consultar asistente virtual (chatbot).

Motor conversacional por reconocimiento de intención con MEMORIA DE CONTEXTO:
recibe el historial previo de la conversación para resolver preguntas de
seguimiento ("¿y en qué tallas?", "¿y cuánto cuesta?") sobre el producto que
se estuvo hablando, y devuelve sugerencias de respuesta rápida.

Consulta datos reales de la base de datos (productos, tallas, sucursales,
horarios, pedidos del cliente) y, cuando no puede interpretar la consulta,
informa y sugiere contactar a soporte en lugar de inventar una respuesta.
"""

import unicodedata

from sqlalchemy import func

from app.models.branch import Branch
from app.models.catalog import Product, ProductVariant
from app.models.commerce import Order
from app.models.inventory import Inventory


def _norm(text: str) -> str:
    """Normaliza: minúsculas y sin tildes/diacríticos para comparar palabras."""
    text = text.lower()
    text = "".join(c for c in unicodedata.normalize("NFD", text)
                   if unicodedata.category(c) != "Mn")
    return " ".join(text.split())


_GREETINGS = {"hola", "buenas", "buenos", "hey", "hi", "saludos", "ola", "buen dia"}


def _contains(text: str, *terms: str) -> bool:
    return any(term in text for term in terms)


def _latest_order(db, user_id: int) -> Order | None:
    return (
        db.query(Order)
        .filter(Order.client_id == user_id)
        .order_by(Order.id.desc())
        .first()
    )


def _find_products(db, text: str, limit: int = 3) -> list[Product]:
    tokens = {
        "".join(ch for ch in t if ch.isalnum()) for t in text.split(" ")
        if len("".join(ch for ch in t if ch.isalnum())) >= 4
    }
    tokens.discard("")
    candidates = set(tokens)
    for t in tokens:
        if len(t) > 4 and t.endswith("s"):
            candidates.add(t[:-1])
    if not candidates:
        return []
    matches: list[Product] = []
    seen = set()
    for product in db.query(Product).filter(Product.is_active.is_(True)).all():
        name = _norm(product.name)
        if product.id in seen:
            continue
        if any(c in name for c in candidates):
            matches.append(product)
            seen.add(product.id)
        if len(matches) >= limit:
            break
    return matches


def _list_sizes(db) -> list[str]:
    from app.models.catalog import Size

    return [s.name for s in db.query(Size).order_by(Size.name).all()]


def _branches_summary(db) -> str:
    rows = db.query(Branch).filter(Branch.is_active.is_(True)).all()
    if not rows:
        return ""
    parts = [f"{b.name} ({b.city}{', ' + b.address if b.address else ''})" for b in rows]
    return "Cartagena, " if len(parts) == 1 else " ".join(parts)


def _product_listing_reply(db, products: list[Product]) -> str:
    lines = []
    for product in products:
        total = (
            db.query(Inventory)
            .join(ProductVariant, ProductVariant.id == Inventory.variant_id)
            .filter(ProductVariant.product_id == product.id, Inventory.available > 0)
            .count()
        )
        price = product.base_price or 0.0
        stock = "tiene unidades disponibles" if total else "no tiene disponibilidad por el momento"
        lines.append(f"  - {product.name}: ${price:,.2f} — {stock}")
    reply = "Encontré para ti:\n" + "\n".join(lines)
    reply += "\nPuedes ver más detalle y tallas en la sección de productos."
    return reply


def _availability_lines(db, product: Product) -> list[str]:
    rows = (
        db.query(Branch, func.sum(Inventory.available).label("total"))
        .join(Inventory, Inventory.branch_id == Branch.id)
        .join(ProductVariant, ProductVariant.id == Inventory.variant_id)
        .filter(ProductVariant.product_id == product.id, Inventory.available > 0)
        .group_by(Branch.id)
        .order_by(Branch.name)
        .all()
    )
    if not rows:
        return ["No hay unidades disponibles por el momento."]
    return [f"  - {b.name}: {int(total)} unidades" for b, total in rows]


def _product_detail_reply(db, product: Product, text: str) -> str:
    """Responde una pregunta de seguimiento sobre un producto concreto."""
    variants = [v for v in product.variants if v.is_active]
    if _contains(text, "talla", "tallas", "medida", "medidas", "que tallas"):
        sizes = sorted({v.size_name for v in variants if v.size_name})
        detail = ", ".join(sizes)
        return (f"La {product.name} está disponible en las tallas: "
                f"{detail or 'sin definir'}. ¿Te interesa alguna en especial?")
    if _contains(text, "color", "colores", "tono"):
        colors = sorted({v.color_name for v in variants if v.color_name})
        detail = ", ".join(colors)
        return (f"La {product.name} la tenemos en los colores: "
                f"{detail or 'sin definir'}.")
    if _contains(text, "precio", "cuesta", "costo", "valor", "vale", "costo"):
        price = product.base_price or 0.0
        return (f"La {product.name} tiene un precio base de ${price:,.2f}. "
                "El precio final puede variar según la talla o color elegido.")
    if _contains(text, "dispon", "stock", "sucursal", "tienda", "donde", "hay"):
        lines = "\n".join(_availability_lines(db, product))
        return f"Disponibilidad de la {product.name}:\n{lines}"
    return _product_listing_reply(db, [product])


def _stock_reply(db) -> str:
    branches = db.query(Branch).filter(Branch.is_active.is_(True)).count()
    total_msgs = (
        db.query(Product)
        .join(ProductVariant, ProductVariant.product_id == Product.id)
        .join(Inventory, Inventory.variant_id == ProductVariant.id)
        .filter(Inventory.available > 0)
        .count()
    )
    return (
        f"Tenemos stock disponible en {branches} sucursal(es) y más de {total_msgs} "
        "variantes listas para ti. Puedes consultar la disponibilidad por sucursal "
        "en la página correspondiente."
    )


# ======================================================================
# Sugerencias de respuesta rápida
# ======================================================================

_GREETING_SUGGESTIONS = [
    "¿Cuál es el estado de mi pedido?",
    "¿Qué prendas me recomiendas?",
    "¿Hacen envíos a domicilio?",
    "¿Cuál es el horario de atención?",
]

_PRODUCT_SUGGESTIONS = [
    "¿En qué tallas hay?",
    "¿De qué colores está?",
    "¿Cuánto cuesta?",
    "¿Dónde hay stock?",
]

_ORDER_SUGGESTIONS = [
    "¿Cuánto tarda el envío?",
    "¿Puedo cancelar mi pedido?",
    "¿Qué métodos de pago aceptan?",
]

_SHIPPING_SUGGESTIONS = [
    "¿Cuál es el estado de mi pedido?",
    "¿Puedo retirar en tienda?",
    "¿Qué horario tienen?",
]

_PAYMENT_SUGGESTIONS = [
    "¿Cuál es el estado de mi pedido?",
    "¿Puedo cancelar mi pedido?",
    "¿Dónde hay stock?",
]

_CANCEL_SUGGESTIONS = [
    "¿Cómo hago un cambio o devolución?",
    "¿Cuál es el estado de mi pedido?",
]

_FALLBACK_SUGGESTIONS = [
    "Hablar con un asesor",
    "¿Qué prendas me recomiendas?",
    "¿Cuál es el estado de mi pedido?",
]


def _context_subject(db, history) -> Product | None:
    """Recupera la prenda que se venía hablando (última mencionada)."""
    if not history:
        return None
    for item in reversed(history):
        content = item["content"] if isinstance(item, dict) else getattr(item, "content", "")
        if not content:
            continue
        products = _find_products(db, content, limit=1)
        if products:
            return products[0]
    return None


def generate_answer(db, user, message: str, history=None) -> tuple[str, list[str]]:
    """Genera la respuesta del asistente y sugerencias de seguimiento.

    Devuelve ``(reply, suggestions)``. ``history`` es la lista previa de
    mensajes (dicts con ``role``/``content`` o instancias de ``ChatMessage``)
    usada para resolver preguntas de seguimiento según el contexto.
    """
    text = _norm(message)
    first = (user.first_name or "").strip() or "usuario"

    if any(g in text for g in _GREETINGS):
        return (
            f"¡Hola, {first}! Soy el asistente de FashionStore. Puedo ayudarte con "
            "productos, tallas, disponibilidad, precios, envíos, horarios de sucursales "
            "y el estado de tus pedidos.",
            _GREETING_SUGGESTIONS,
        )

    if _contains(text, "pedido", "orden", "estado de mi compra", "compra") and (
        "estado" in text or "pedido" in text or "orden" in text
    ):
        order = _latest_order(db, user.id)
        if order is None:
            return (
                "Aún no tienes pedidos registrados. Cuando confirmes tu primera compra "
                "te ayudaré a darle seguimiento.",
                ["¿Qué prendas me recomiendas?", "¿Dónde hay stock?"],
            )
        method = order.payment.method if order.payment else "S/D"
        return (
            f"Tu último pedido #{order.id} está en estado {order.status} "
            f"(método de pago: {method}, total ${order.total:,.2f}).",
            _ORDER_SUGGESTIONS,
        )

    if _contains(text, "correo", "enviar", "contact",
                 "envio", "envio", "entrega", "domicilio", "llega"):
        return (
            "Los pedidos digitales se preparan en 24 h y el envío tarda de 2 a 4 días "
            "hábiles; también puedes retirar gratis en cualquier sucursal. "
            "Para el envío necesitamos tu dirección de entrega al confirmar la compra.",
            _SHIPPING_SUGGESTIONS,
        )

    if _contains(text, "horario", "abre", "abierto", "abren", "cierra", "atencion", "apertura"):
        branches = _branches_summary(db)
        return (
            "Nuestras sucursales atienden de lunes a sábado de 10:00 a 20:00 y los "
            f"domingos de 11:00 a 19:00.{(' Contamos con: ' + branches + '.') if branches else ''}",
            _GREETING_SUGGESTIONS,
        )

    if _contains(text, "pago", "pagar", "pago electrónico", "tarjeta", "transferencia",
                 "efectivo", "pasarela"):
        return (
            "Aceptamos tarjetas, transferencias y efectivo en tienda. Los pagos "
            "electrónicos se procesan de forma segura a través de nuestra pasarela "
            "de pagos; si la tarjeta es rechazada, el pedido no se cobra y puedes "
            "reintentar con otro método.",
            _PAYMENT_SUGGESTIONS,
        )

    if _contains(text, "recomend", "sugeren", "sugerencia", "que me conviene"):
        return (
            "Revisa la sección 'Recomendados para ti' en el catálogo: es una selección "
            "basada en tu historial de compras y en lo que está de moda.",
            _PRODUCT_SUGGESTIONS,
        )

    if _contains(text, "cancelar", "cancelacion", "cancelación", "devolucion", "devolución",
                 "cambiar", "cambio"):
        return (
            "Puedes cancelar un pedido siempre que aún no haya sido pagado. Para "
            "cambios o devoluciones, acércate a la sucursal donde realizaste la "
            "compra dentro de los 15 días con tu comprobante.",
            _CANCEL_SUGGESTIONS,
        )

    products = _find_products(db, text)
    if products:
        reply = _product_listing_reply(db, products)
        return reply, _PRODUCT_SUGGESTIONS

    subject = _context_subject(db, history)
    if subject is not None:
        detail = _product_detail_reply(db, subject, text)
        if _contains(text, "talla", "tallas", "medidas", "color", "colores", "dispon",
                     "stock", "sucursal", "donde", "cuesta", "precio", "costo", "valor"):
            return detail, _PRODUCT_SUGGESTIONS

    if _contains(text, "talla", "tallas", "medida", "medidas"):
        sizes = _list_sizes(db)
        return (
            f"Contamos con las tallas: {', '.join(sizes)}. "
            "Puedes filtrar por talla en el catálogo.",
            ["Hazme una recomendación", "¿Qué hay en stock?"],
        )
    if _contains(text, "dispon", "stock", "hay", "sucursal", "tienda"):
        return _stock_reply(db), ["¿Qué prendas me recomiendas?", "¿Qué prendas hay?"]
    if _contains(text, "precio", "cuanto cuesta", "costo", "valor"):
        return (
            "Puedes consultar el precio exacto de cada producto en el catálogo, donde "
            "se aplican los descuentos por talla.",
            _PRODUCT_SUGGESTIONS,
        )

    if _contains(text, "soporte", "ayuda", "humano", "asesor", "contacto", "queja"):
        return (
            "Puedes escribirnos a soporte@fashionstore.com o llamar a nuestras "
            "sucursales en horario de atención; un asesor te atenderá a la brevedad.",
            _FALLBACK_SUGGESTIONS,
        )

    return (
        "Lo siento, no logré interpretar tu consulta. Prueba reformularla o "
        "contáctate con soporte en soporte@fashionstore.com, donde un asesor "
        "te atenderá a la brevedad.",
        _FALLBACK_SUGGESTIONS,
    )
"""Endpoints de reportes y dashboards (CU25) y reporte por comando de voz (CU24).

CU25 — Consultar reportes y dashboards: indicadores operativos (ventas, inventario,
reservas) con filtros de periodo, sucursal y categoría. Si no hay datos suficientes
para el filtro, se devuelve `empty: true` para que la interfaz muestre un mensaje
informativo en lugar del gráfico.

CU24 — Generar reporte por comando de voz: el navegador transcribe el audio
(Web Speech API) y envía el texto; aquí se interpreta la intención (tipo de reporte,
periodo, sucursal y categoría) de forma determinista y se genera el reporte
(análogo a CU25). Si no se reconoce la intención, se sugiere repetir el comando o
usar el panel del dashboard.
"""

import json
import unicodedata
import urllib.request
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_business_user as get_current_user
from app.models.branch import Branch
from app.models.catalog import Category, Product, ProductVariant
from app.models.commerce import Order, OrderItem, Reservation, ReservationItem
from app.models.inventory import Inventory
from app.models.promotion import Promotion
from app.models.user import User
from app.schemas import (
    CategoryReport,
    DashboardReport,
    ReportKpis,
    SalesPoint,
    TopProductReport,
    VoiceCommand,
    VoiceReportIntent,
    VoiceReportResponse,
)

router = APIRouter()

# Roles que pueden consultar reportes (CU25/CU24: administración).
_REPORT_ROLES = {"Administrador", "Encargado de Sucursal"}

# Umbral de "stock bajo" consistente con el filtro de inventario existente (CU21).
_LOW_STOCK_THRESHOLD = 5

_SALE_STATUSES = ("PAGADO", "ENVIADO", "ENTREGADO")


def _require_reports(user: User) -> User:
    if user.role_name not in _REPORT_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Requiere rol de administrador o encargado de sucursal")
    return user


def _normalize(text: str) -> str:
    """Minúsculas, sin acentos y solo caracteres alfanuméricos para comparar intenciones."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return "".join(ch for ch in text.lower() if ch.isalnum() or ch.isspace())


def _utc_today() -> date:
    """Día 'hoy' según UTC: las marcas de tiempo (created_at / reservation_date) se guardan en UTC."""
    return datetime.now(timezone.utc).date()


def _parse_date(value: Optional[str], field_name: str) -> Optional[date]:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"{field_name} debe tener formato YYYY-MM-DD")


def _default_range() -> tuple[date, date]:
    """Rango por defecto: los últimos 30 días hasta hoy (UTC)."""
    end = _utc_today()
    start = end - timedelta(days=29)
    return start, end


def _sales_orders_query(db: Session, date_from: date, date_to: date,
                        branch_id: Optional[int], category_id: Optional[int],
                        empresa_id: Optional[int] = None):
    """Query base: pedidos de venta (confirmados) con filtros aplicados."""
    query = db.query(Order).filter(
        Order.status.in_(_SALE_STATUSES),
        func.date(Order.created_at) >= date_from.isoformat(),
        func.date(Order.created_at) <= date_to.isoformat(),
    )
    query = query.filter(Order.empresa_id == empresa_id)
    if branch_id is not None:
        query = query.filter(Order.branch_id == branch_id)
    if category_id is not None:
        query = query.join(Order.items).join(ProductVariant, OrderItem.variant_id == ProductVariant.id) \
            .filter(ProductVariant.product_id.in_(
                db.query(Product.id).filter(Product.category_id == category_id)
            ))
    return query


def _count_active_promotions(db: Session, empresa_id: Optional[int] = None) -> int:
    """Promociones habilitadas y dentro de su ventana de fechas (hoy inclusive)."""
    today = _utc_today()
    query = db.query(Promotion).filter(Promotion.is_active == True)  # noqa: E712
    from sqlalchemy import or_
    query = query.filter(or_(Promotion.empresa_id == empresa_id,
                             Promotion.empresa_id.is_(None)))
    promos = query.all()
    return sum(
        1 for p in promos
        if (p.start_date is None or p.start_date <= today)
        and (p.end_date is None or p.end_date >= today)
    )


def _build_dashboard(db: Session, date_from: date, date_to: date,
                     branch_id: Optional[int], category_id: Optional[int],
                     narrative: bool = False, report_type: Optional[str] = None,
                     empresa_id: Optional[int] = None) -> DashboardReport:
    from collections import defaultdict
    from decimal import Decimal
    from app.services.financial_reporting import financial_events, pending_refunds, summary
    events = financial_events(db, empresa_id, date_from, date_to, branch_id, category_id)
    amounts = summary(events)
    total_sales, total_orders = amounts['total_sales'], amounts['total_orders']
    avg_order = round(total_sales / total_orders, 2) if total_orders else 0.0
    discount_amount = float(sum((event['discount'] for event in events), Decimal('0.00')))

    reservations_query = db.query(Reservation).filter(
        func.date(Reservation.reservation_date) >= date_from.isoformat(),
        func.date(Reservation.reservation_date) <= date_to.isoformat(),
    )
    reservations_query = reservations_query.join(
        Branch, Reservation.branch_id == Branch.id
    ).filter(Branch.empresa_id == empresa_id)
    if branch_id is not None:
        reservations_query = reservations_query.filter(Reservation.branch_id == branch_id)
    if category_id is not None:
        reservations_query = reservations_query.join(Reservation.items) \
            .join(ProductVariant, ReservationItem.variant_id == ProductVariant.id) \
            .filter(ProductVariant.product_id.in_(
                db.query(Product.id).filter(Product.category_id == category_id)
            ))
    reservations = reservations_query.count()

    # Inventario es estado actual: no aplica el periodo, solo sucursal/categoría.
    inv_query = db.query(Inventory).join(ProductVariant, Inventory.variant_id == ProductVariant.id)
    inv_query = inv_query.join(Branch, Inventory.branch_id == Branch.id)             .filter(Branch.empresa_id == empresa_id)
    if branch_id is not None:
        inv_query = inv_query.filter(Inventory.branch_id == branch_id)
    if category_id is not None:
        inv_query = inv_query.filter(ProductVariant.product_id.in_(
            db.query(Product.id).filter(Product.category_id == category_id)
        ))
    inv_rows = inv_query.all()
    total_units_available = sum(r.available for r in inv_rows)
    low_stock_variants = sum(1 for r in inv_rows if r.available <= _LOW_STOCK_THRESHOLD)

    pending = float(pending_refunds(db, empresa_id, date_from, date_to, branch_id, category_id))
    empty = not events and reservations == 0 and pending == 0
    daily = defaultdict(lambda: {'amount': Decimal('0.00'), 'orders': set()})
    categories, products = {}, {}
    for event in events:
        day = daily[event['date']]
        day['amount'] += event['amount']
        if event['type'] == 'COBRO': day['orders'].add(event['order_id'])
        category = categories.setdefault(event['category_id'], {'name':event['category_name'], 'amount':Decimal('0.00'), 'units':0})
        category['amount'] += event['amount']; category['units'] += event['quantity']
        if event['product_id'] is not None:
            product = products.setdefault(event['product_id'], {'name':event['product_name'], 'amount':Decimal('0.00'), 'units':0})
            product['amount'] += event['amount']; product['units'] += event['quantity']
    sales_series = [SalesPoint(date=day, amount=float(data['amount']), orders=len(data['orders'])) for day,data in sorted(daily.items())]
    by_category = [CategoryReport(category_id=key, category_name=data['name'], sales=float(data['amount']), units=data['units']) for key,data in categories.items()]
    top_products = [TopProductReport(product_id=key,name=data['name'],units=data['units'],revenue=float(data['amount']))
        for key,data in sorted(products.items(),key=lambda pair:pair[1]['amount'],reverse=True)[:5]]

    effective_narrative = _generate_narrative(
        db, report_type=report_type,
        total_orders=total_orders, total_sales=total_sales,
        avg_order=avg_order, reservations=reservations,
        total_units_available=total_units_available,
        low_stock_variants=low_stock_variants,
        discount_amount=discount_amount,
        active_promotions=_count_active_promotions(db, empresa_id),
    ) if narrative else None

    return DashboardReport(
        empty=empty,
        date_from=date_from.isoformat(),
        date_to=date_to.isoformat(),
        kpis=ReportKpis(
            gross_sales=amounts["gross_sales"],
            refund_amount=amounts["refund_amount"],
            refund_pending=pending,
            total_sales=total_sales,
            total_orders=total_orders,
            avg_order=avg_order,
            reservations=reservations,
            total_units_available=total_units_available,
            low_stock_variants=low_stock_variants,
            active_promotions=_count_active_promotions(db, empresa_id),
            discount_amount=discount_amount,
        ),
        sales_series=sales_series,
        by_category=by_category,
        top_products=top_products,
        narrative=effective_narrative,
    )


@router.get("/dashboard", response_model=DashboardReport, summary="Reportes y dashboards (CU25)")
def get_dashboard(
    desde: Optional[str] = Query(default=None, description="Fecha inicial YYYY-MM-DD"),
    hasta: Optional[str] = Query(default=None, description="Fecha final YYYY-MM-DD"),
    branch_id: Optional[int] = None,
    category_id: Optional[int] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_reports(user)
    date_from = _parse_date(desde, "desde")
    date_to = _parse_date(hasta, "hasta")
    if date_from is None and date_to is None:
        date_from, date_to = _default_range()
    else:
        if date_from is None:
            date_from = date_to or _utc_today()
        if date_to is None:
            date_to = date_from
    if date_from > date_to:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="desde no puede ser posterior a hasta")
    return _build_dashboard(db, date_from, date_to, branch_id, category_id,
                            empresa_id=user.empresa_id)


# ======================================================================
# CU24 — REPORTE POR COMANDO DE VOZ
# ======================================================================


def _build_narrative_local(report_type: Optional[str], total_orders: int, total_sales: float,
                           avg_order: float, reservations: int, total_units_available: int,
                           low_stock_variants: int, discount_amount: float,
                           active_promotions: int) -> str:
    """Plantilla NLG en español: resumen ejecutivo determinista del negocio."""
    opening = {
        "INVENTARIO": ("El estado del inventario es el siguiente: hay "
                       f"{total_units_available} unidades disponibles en las sucursales"),
        "RESERVAS": "En cuanto a las reservas, se registraron",
        "VENTAS": "Resumen del período: se registraron",
    }.get(report_type, "Resumen del período: se registraron")

    narrative = (
        f"{opening} {total_orders} pedidos de venta por un total de Bs {total_sales:,.2f}. "
        f"El ticket promedio fue de Bs {avg_order:,.2f}. "
        f"Se contabilizaron {reservations} reservas y {total_units_available} unidades "
        f"disponibles en inventario. "
    )
    if discount_amount > 0:
        narrative += (f"Las promociones vigentes ({active_promotions} activas) "
                      f"sumaron Bs {discount_amount:,.2f} en descuentos aplicados a las ventas. ")
    if low_stock_variants > 0:
        narrative += (f"Hay {low_stock_variants} variantes con stock bajo que conviene reponer. ")
    return narrative


def _generate_narrative(db: Session, report_type: Optional[str], total_orders: int,
                        total_sales: float, avg_order: float, reservations: int,
                        total_units_available: int, low_stock_variants: int,
                        discount_amount: float, active_promotions: int) -> str:
    """Narrativa generativa: usa el LLM configurado si hay API key; si no, plantilla local."""
    if settings.GENAI_API_KEY:
        prompt = (
            "Eres el asistente de voz de una tienda de ropa. Redacta un resumen "
            "ejecutivo DE 3 A 5 ORACIONES en español, natural y amable, a partir de "
            f"estos datos del reporte {report_type}: {total_orders} pedidos, "
            f"Bs {total_sales} en ventas, ticket promedio Bs {avg_order}, "
            f"{reservations} reservas, {total_units_available} unidades disponibles, "
            f"{low_stock_variants} variantes con stock bajo, Bs {discount_amount} en "
            f"descuentos con {active_promotions} promociones activas. "
            "No inventes cifras, preséntalas como las leíste."
        )
        try:
            url = (f"{settings.GENAI_BASE_URL}/models/{settings.GENAI_MODEL}:generateContent"
                   f"?key={settings.GENAI_API_KEY}")
            body = json.dumps({
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": 300, "temperature": 0.4},
            }).encode("utf-8")
            request = urllib.request.Request(url, data=body,
                                             headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(request, timeout=5) as response:  # noqa: S310
                data = json.loads(response.read().decode("utf-8"))
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            if text:
                return text
        except Exception:
            # Fallback determinista ante cualquier fallo de red/API.
            pass
    return _build_narrative_local(report_type, total_orders, total_sales, avg_order,
                                  reservations, total_units_available, low_stock_variants,
                                  discount_amount, active_promotions)


def _detect_period(command: str) -> tuple[Optional[date], Optional[date]]:
    """Periodo según palabras completas del comando (evita falsos positivos tipo 'dia' en 'diapositiva')."""
    today = _utc_today()
    words = set(command.split())
    if any(w in words for w in ("hoy", "dia")):
        return today, today
    if "semana" in words:
        return today - timedelta(days=6), today
    if "mes" in words:
        return today.replace(day=1), today
    if any(w in words for w in ("ano", "anual")):
        return today.replace(month=1, day=1), today
    return None, None


def _resolve_voice(db: Session, command: str,
                   empresa_id: Optional[int] = None) -> VoiceReportResponse:
    normalized = _normalize(command)
    words = set(normalized.split())

    report_type = None
    if words & {"venta", "ventas", "vendido", "vendida"}:
        report_type = "VENTAS"
    elif words & {"inventario", "stock", "existencias"}:
        report_type = "INVENTARIO"
    elif words & {"reserva", "reservas", "apartado"}:
        report_type = "RESERVAS"

    if report_type is None:
        return VoiceReportResponse(
            recognized=False,
            message="No reconocí el tipo de reporte que pides. Repite el comando "
                    "mencionando ventas, inventario o reservas, o usa el panel "
                    "de reportes (CU25).",
            intent=VoiceReportIntent(recognized=False),
        )

    date_from, date_to = _detect_period(normalized)

    # Sucursal por coincidencia de nombre.
    branch_id: Optional[int] = None
    branches_query = db.query(Branch).filter(Branch.is_active == True)  # noqa: E712
    branches_query = branches_query.filter(Branch.empresa_id == empresa_id)
    for branch in branches_query.all():
        if _normalize(branch.name) and _normalize(branch.name) in normalized:
            branch_id = branch.id
            break

    # Categoría por coincidencia de nombre.
    category_id: Optional[int] = None
    categories_query = db.query(Category)
    categories_query = categories_query.filter(Category.empresa_id == empresa_id)
    for category in categories_query.all():
        if _normalize(category.name) and _normalize(category.name) in normalized:
            category_id = category.id
            break

    data = _build_dashboard(db, date_from or _default_range()[0],
                            date_to or _default_range()[1], branch_id, category_id,
                            narrative=True, report_type=report_type,
                            empresa_id=empresa_id)

    message = f"Reporte de {report_type.lower()} generado con éxito."
    return VoiceReportResponse(
        recognized=True,
        message=message,
        intent=VoiceReportIntent(
            recognized=True,
            report_type=report_type,
            date_from=data.date_from,
            date_to=data.date_to,
            branch_id=branch_id,
            category_id=category_id,
        ),
        data=data,
    )


@router.post("/voice", response_model=VoiceReportResponse, summary="Generar reporte por voz (CU24)")
def voice_report(payload: VoiceCommand, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    _require_reports(user)
    return _resolve_voice(db, payload.command, empresa_id=user.empresa_id)

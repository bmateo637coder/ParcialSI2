"""Interpretación y consultas de reportes con un contrato cerrado, sin SQL generado."""

import re
import unicodedata
from collections import defaultdict
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import func

from app.models.branch import Branch
from app.models.catalog import Category, Product, ProductVariant
from app.models.commerce import Order, OrderItem, Reservation
from app.models.inventory import Inventory
from app.services.report_intent import classify
from app.services.report_language import report_period, report_limit

PAID = ("PAGADO", "ENVIADO", "ENTREGADO")


def normalize(text):
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")


def build_report(db, empresa_id, question, supplied_filters=None):
    text = normalize(question)
    intent, confidence = classify(question)
    if not text.strip() or len(text) > 1000:
        raise HTTPException(422, "Escribe una solicitud de entre 1 y 1000 caracteres")
    filters = dict(supplied_filters or {})
    allowed = {"fecha_desde", "fecha_hasta", "sucursal_id", "categoria_id", "producto_id", "limite"}
    if set(filters) - allowed:
        raise HTTPException(422, "Hay filtros no soportados")
    for key, model in (("sucursal_id", Branch), ("categoria_id", Category), ("producto_id", Product)):
        if key in filters:
            try:
                filters[key] = int(filters[key])
            except (ValueError, TypeError):
                raise HTTPException(422, f"{key} debe ser un identificador numérico")
            resource = db.get(model, filters[key])
            if not resource or resource.empresa_id != empresa_id:
                raise HTTPException(404, "El filtro no corresponde a un recurso de tu empresa")
        else:
            resources = db.query(model).filter(model.empresa_id == empresa_id).all()
            matches = [r for r in resources if re.search(r'(?<!\w)' + re.escape(normalize(r.name)) + r'(?!\w)', text)]
            # Un nombre corto contenido en otro se resuelve por el nombre completo.
            matches = [r for r in matches if not any(r.id != other.id and normalize(r.name) != normalize(other.name)
                and normalize(r.name) in normalize(other.name) for other in matches)]
            if len(matches) > 1:
                raise HTTPException(422, f'Hay varios recursos para {key}. Indica uno solo o utiliza su identificador como filtro.')
            if matches:
                filters[key] = matches[0].id
            label = {'sucursal_id': 'sucursal', 'categoria_id': 'categoria', 'producto_id': 'producto'}[key]
            named = re.findall(label + r"\s+[\"']([^\"']+)[\"']", text)
            if named and (len(named) > 1 or not matches or normalize(matches[0].name) != named[0]):
                raise HTTPException(422, f'No se pudo identificar una {label} de tu empresa. Revisa el nombre o utiliza su identificador.')
    start, end = report_period(text, filters)
    filters.update(fecha_desde=start.isoformat(), fecha_hasta=end.isoformat())
    limit = report_limit(text, filters)
    filters["limite"] = limit
    branch_id, category_id, product_id = (filters.get(k) for k in ("sucursal_id", "categoria_id", "producto_id"))

    is_stock = any(t in text for t in ("inventario", "stock", "existencia"))
    is_reservation = "reserva" in text
    is_sale = any(t in text for t in ("venta", "vendid", "ingreso", "factur", "recaud"))
    if not any((is_stock, is_reservation, is_sale)) and confidence >= 0.55:
        is_stock, is_reservation = intent == "inventario", intent == "reservas"
        is_sale = intent in {"ventas", "productos", "categorias"}
        if intent == "productos":
            text += " productos vendidos"
        elif intent == "categorias":
            text += " ingresos por categoria"
    if sum((is_stock, is_reservation, is_sale)) != 1:
        raise HTTPException(422, "Indica un solo reporte: ventas por sucursal/semana, productos vendidos, ingresos por categoría, inventario o reservas")

    if is_stock:
        query = (db.query(Product.name, ProductVariant.sku, Branch.name, Inventory.available)
            .select_from(Inventory).join(Branch).join(ProductVariant).join(Product)
            .filter(Branch.empresa_id == empresa_id, (Product.empresa_id == empresa_id) | Product.empresa_id.is_(None),
                Product.is_active.is_(True), ProductVariant.is_active.is_(True)))
        if branch_id:
            query = query.filter(Branch.id == branch_id)
        if category_id:
            query = query.filter(Product.category_id == category_id)
        if product_id:
            query = query.filter(Product.id == product_id)
        rows = [{"producto": p, "sku": sku, "sucursal": b, "cantidad": qty}
            for p, sku, b, qty in query.order_by(Inventory.available, Product.name).limit(limit)]
        kind, columns, label, value = "INVENTARIO_BAJO", ["producto", "sku", "sucursal", "cantidad"], "producto", "cantidad"
    elif is_reservation:
        query = (db.query(Reservation.status, func.count(Reservation.id)).join(Branch)
            .filter(Branch.empresa_id == empresa_id, func.date(Reservation.reservation_date) >= start,
                func.date(Reservation.reservation_date) <= end))
        if branch_id:
            query = query.filter(Branch.id == branch_id)
        if category_id or product_id:
            from app.models.commerce import ReservationItem
            detail = db.query(ReservationItem.reservation_id).join(ProductVariant).join(Product)
            if category_id:
                detail = detail.filter(Product.category_id == category_id)
            if product_id:
                detail = detail.filter(Product.id == product_id)
            query = query.filter(Reservation.id.in_(detail))
        rows = [{"estado": status, "cantidad": count} for status, count in query.group_by(Reservation.status)]
        kind, columns, label, value = "RESERVAS_POR_ESTADO", ["estado", "cantidad"], "estado", "cantidad"
    else:
        from datetime import date
        from decimal import Decimal
        from app.services.financial_reporting import financial_events
        events = financial_events(db, empresa_id, start, end, branch_id, category_id, product_id)
        product_words = re.search(r'\b(?:producto|prenda|articulo)s?\b', text)
        if product_words and any(t in text for t in ("vend", "top", "venta")) or "categoria" in text:
            by_category = "categoria" in text
            key = "categoria" if by_category else "producto"
            groups = {}
            for event in events:
                name = event['category_name'] if by_category else event['product_name']
                data = groups.setdefault(name, {'quantity':0, 'amount':Decimal('0.00')})
                data['quantity'] += event['quantity']; data['amount'] += event['amount']
            rows = [{key:name, 'cantidad_vendida':data['quantity'], 'ingresos':float(data['amount'])}
                for name,data in sorted(groups.items(), key=lambda pair:(-pair[1]['amount'] if by_category else -pair[1]['quantity'],-pair[1]['amount'],pair[0]))[:limit]]
            kind = 'INGRESOS_POR_CATEGORIA' if by_category else 'TOP_PRODUCTOS_VENDIDOS'
            columns, label, value = [key,'cantidad_vendida','ingresos'], key, 'ingresos'
        else:
            grouped = {}
            weekly, monthly = 'semana' in text, 'compara' in text or 'meses' in text
            for event in events:
                day = date.fromisoformat(event['date'])
                key = (day-timedelta(days=day.weekday())).isoformat() if weekly else (day.strftime('%Y-%m')+' / '+event['branch_name']) if monthly else event['branch_name']
                data = grouped.setdefault(key, {'orders':set(),'gross':Decimal('0.00'),'refunds':Decimal('0.00'),'total':Decimal('0.00')})
                if event['type']=='COBRO': data['orders'].add(event['order_id'])
                data['gross'] += event['cash_in']; data['refunds'] += event['cash_out']; data['total'] += event['amount']
            key_name = 'semana' if weekly else 'periodo_sucursal' if monthly else 'sucursal'
            rows = [{key_name:key,'cantidad_ventas':len(data['orders']),'cobros':float(data['gross']),
                'devoluciones':float(data['refunds']),'total_ventas':float(data['total'])} for key,data in sorted(grouped.items())]
            kind = 'VENTAS_POR_SEMANA' if weekly else 'COMPARACION_MENSUAL' if monthly else 'VENTAS_POR_SUCURSAL'
            columns, label, value = [key_name,'cantidad_ventas','cobros','devoluciones','total_ventas'],key_name,'total_ventas'
    return {"solicitud_id": 0, "tipo_reporte": kind, "empresa_id": empresa_id, "pregunta_natural": question,
        "columnas": columns, "filas": rows, "filtros_aplicados": filters,
        "grafico": {"tipo": "line" if "SEMANA" in kind else "bar", "labels": [r[label] for r in rows], "datos": [r[value] for r in rows]},
        "mensaje": f"{len(rows)} resultado(s), desde {start.isoformat()} hasta {end.isoformat()}. Ventas netas por fecha del cobro y de la devolucion."}

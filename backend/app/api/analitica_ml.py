import json
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.tenant import require_plan_profesional
from app.models.analytics import AnalyticsRun
from app.models.branch import Branch
from app.models.catalog import Product, ProductVariant
from app.models.commerce import Order, OrderItem
from app.models.inventory import Inventory
from app.services.analytics import train, predict, features
from app.services.promotions import promotion_discount_for_variant

router = APIRouter()


def analytics_context(ctx=Depends(require_plan_profesional)):
    if not ctx['plan'].permite_analitica_ml:
        raise HTTPException(403, 'El plan no incluye analítica ML')
    return ctx


@router.post('/entrenar')
def entrenar_modelos(ctx=Depends(analytics_context), db: Session=Depends(get_db)):
    model = train()
    record = AnalyticsRun(empresa_id=ctx['empresa'].id, user_id=ctx['user'].id, model_json=json.dumps(model))
    db.add(record); db.commit(); db.refresh(record)
    return {'id': record.id, 'estado': 'ENTRENADO', 'algoritmos': ['REGRESION_LINEAL', 'KMEANS'],
        'fuente_entrenamiento': 'SINTETICA', 'variables': model['variables'], 'metricas': model['evaluacion']}


@router.get('/dashboard')
def dashboard_analitico(ctx=Depends(analytics_context), db: Session=Depends(get_db)):
    company = ctx['empresa'].id
    now = datetime.now(timezone(timedelta(hours=-4)))
    first = now.date().replace(day=1)
    sales = db.query(Order).filter(Order.empresa_id==company, Order.status.in_(['PAGADO','ENVIADO','ENTREGADO']), func.date(Order.created_at)>=first).all()
    amount = sum(order.total for order in sales)
    result = {'kpi': {'ventas_mes': round(amount,2), 'productos_vendidos': sum(item.quantity for order in sales for item in order.items),
        'ticket_promedio': round(amount/len(sales),2) if sales else 0}, 'entrenado': False,
        'prediccion_demanda': [], 'segmentacion': [], 'anomalias': [], 'recomendaciones': []}
    run = db.query(AnalyticsRun).filter(AnalyticsRun.empresa_id==company).order_by(AnalyticsRun.id.desc()).first()
    if run is None:
        return result
    model = json.loads(run.model_json)
    result.update(entrenado=True, modelo_id=run.id, fecha_entrenamiento=run.created_at,
        metricas=model['evaluacion'], fuente_entrenamiento='SINTETICA',
        advertencia='Modelo entrenado con datos sintéticos. Las estimaciones usan los productos e inventarios actuales de tu empresa y deben validarse antes de tomar decisiones.')
    rows = (db.query(Inventory, ProductVariant, Product, Branch).select_from(Inventory)
        .join(ProductVariant, ProductVariant.id==Inventory.variant_id).join(Product, Product.id==ProductVariant.product_id).join(Branch, Branch.id==Inventory.branch_id)
        .filter(Branch.empresa_id==company, (Product.empresa_id==company) | Product.empresa_id.is_(None),
            Product.is_active.is_(True), ProductVariant.is_active.is_(True)).order_by(Product.name).limit(500).all())
    for inventory, variant, product, branch in rows:
        _, discount = promotion_discount_for_variant(db, variant)
        price = variant.effective_price
        values = features(price, inventory.available, discount/price if price else 0, now.month, now.weekday())
        demand, group, distance = predict(model, values)
        item = {'producto': product.name, 'sku': variant.sku, 'sucursal': branch.name, 'sucursal_id': branch.id,
            'precio': price, 'stock': inventory.available,
            'demanda_diaria_estimada': round(demand,2), 'grupo': group+1}
        result['prediccion_demanda'].append(item)
        if distance > model['umbral_anomalia']:
            result['anomalias'].append({'sku': variant.sku, 'sucursal': branch.name, 'distancia': round(distance,2)})
        if inventory.available < demand:
            result['recomendaciones'].append({'sku': variant.sku, 'sucursal': branch.name, 'mensaje': 'Revisar reposición por demanda estimada superior a las existencias.'})
    for index, centroid in enumerate(model['centroides']):
        result['segmentacion'].append({'grupo': index+1, 'variantes': sum(item['grupo']==index+1 for item in result['prediccion_demanda']),
            'perfil': dict(zip(model['variables'], [round(center*scale+avg,2) for center,scale,avg in zip(centroid, model['escalas'], model['medias'])]))})
    return result

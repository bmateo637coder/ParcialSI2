"""Movimientos de ventas por fecha del cobro o del reembolso, sin borrar historia."""
import json
from decimal import Decimal
from sqlalchemy.orm import selectinload
from app.core.money import money
from app.models.commerce import Order, Refund
from app.models.catalog import ProductVariant
from app.models.sync import CambioPrenda


def financial_events(db,empresa_id,start,end,branch_id=None,category_id=None,product_id=None):
    orders=db.query(Order).options(selectinload(Order.items),selectinload(Order.payment),selectinload(Order.refunds).selectinload(Refund.items)).filter(Order.empresa_id==empresa_id)
    if branch_id is not None: orders=orders.filter(Order.branch_id==branch_id)
    orders=orders.all()
    result=[]
    def add(order,when,amount,quantity,variant_id,kind,discount=0,cash_in=None,cash_out=None):
        if when is None or not start <= when.date() <= end: return
        variant=db.get(ProductVariant,variant_id) if variant_id else None
        product=variant.product if variant else None
        if product_id is not None and (not product or product.id!=product_id): return
        if category_id is not None and (not product or product.category_id!=category_id): return
        amount=money(amount)
        # Con filtro de producto/categoría se muestran ingresos y devoluciones de esa prenda.
        if category_id is not None or product_id is not None: cash_in=cash_out=None
        result.append({'date':when.date().isoformat(),'order_id':order.id,'branch_id':order.branch_id,
            'branch_name':order.branch.name if order.branch else 'Sin sucursal',
            'product_id':product.id if product else None,'product_name':product.name if product else 'Venta histórica',
            'category_id':product.category_id if product else None,
            'category_name':product.category.name if product and product.category else 'Sin categoría',
            'amount':amount,'quantity':quantity,'type':kind,'discount':money(discount),
            'cash_in':max(Decimal('0.00'),amount) if cash_in is None else money(cash_in),
            'cash_out':max(Decimal('0.00'),-amount) if cash_out is None else money(cash_out)})
    for order in orders:
        payment=order.payment
        # Ventas antiguas sin pago asociado mantienen la compatibilidad del historial.
        paid=payment is not None and payment.paid_at is not None
        legacy=payment is None and order.status in {'PAGADO','ENVIADO','ENTREGADO'}
        if not paid and not legacy: continue
        when=payment.paid_at if paid else order.created_at
        total=Decimal('0.00')
        for item in order.items:
            value=money(item.subtotal);total+=value
            add(order,when,value,item.quantity,item.variant_id,'COBRO',item.discount or 0)
        expected=money(payment.amount if paid else order.total)
        if total!=expected: add(order,when,expected-total,0,None,'COBRO')
        for change in db.query(CambioPrenda).filter_by(venta_id=order.id,estado='APROBADO'):
            detail=json.loads(change.detalle_json or '{}')
            if not detail: continue
            qty=int(detail['quantity']);old=money(Decimal(str(detail['old_unit_price']))*qty)
            difference=money(change.monto_diferencia);new=old+difference
            add(order,change.fecha_solicitud,-old,-qty,detail['original_variant_id'],'CAMBIO',cash_in=0,cash_out=max(Decimal('0.00'),-difference))
            add(order,change.fecha_solicitud,new,qty,detail['replacement_variant_id'],'CAMBIO',cash_in=max(Decimal('0.00'),difference),cash_out=0)
        for refund in order.refunds:
            if refund.status!='COMPLETADO': continue
            for item in refund.items:
                add(order,refund.completed_at,-money(item.amount),-item.quantity,item.variant_id,'REEMBOLSO')
    return result


def pending_refunds(db,empresa_id,start,end,branch_id=None,category_id=None,product_id=None):
    query=db.query(Refund).join(Order).filter(Refund.empresa_id==empresa_id,Refund.status=='PENDIENTE')
    if branch_id is not None: query=query.filter(Order.branch_id==branch_id)
    value=Decimal('0.00')
    for refund in query:
        if not start <= refund.created_at.date() <= end: continue
        for item in refund.items:
            variant=db.get(ProductVariant,item.variant_id)
            if category_id is not None and variant.product.category_id!=category_id: continue
            if product_id is not None and variant.product_id!=product_id: continue
            value+=money(item.amount)
    return value


def summary(events):
    gross=sum((e['cash_in'] for e in events),Decimal('0.00'))
    returned=sum((e['cash_out'] for e in events),Decimal('0.00'))
    return {'gross_sales':float(gross),'refund_amount':float(returned),
        'total_sales':float(sum((e['amount'] for e in events),Decimal('0.00'))),
        'total_orders':len({e['order_id'] for e in events if e['type']=='COBRO'})}

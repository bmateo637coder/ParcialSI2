"""Devoluciones monetarias y de prendas, conservando el cobro original."""
import hashlib
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.money import money
from app.models.catalog import ProductVariant
from app.models.commerce import Refund, RefundItem, Notification
from app.models.inventory import Inventory, InventoryMovement
from app.models.sync import CambioPrenda
from app.services.payments import get_gateway


def exchanges(db, order):
    return db.query(CambioPrenda).filter(CambioPrenda.venta_id == order.id,
        CambioPrenda.estado == 'APROBADO').order_by(CambioPrenda.id).all()


def collected(db, order):
    if not order.payment or not order.payment.paid_at:
        return Decimal('0.00')
    return money(order.payment.amount) + sum((money(e.monto_diferencia) for e in exchanges(db, order)), Decimal('0.00'))


def refunded(order, include_pending=False):
    states = {'COMPLETADO','PENDIENTE','SOLICITADO'} if include_pending else {'COMPLETADO'}
    return sum((money(r.amount) for r in order.refunds if r.status in states), Decimal('0.00'))


def returnable_lots(db, order, include_pending=True):
    lots = []
    records = exchanges(db, order)
    for item in order.items:
        changed = [(e,json.loads(e.detalle_json or '{}')) for e in records]
        changed = [(e,d) for e,d in changed if d.get('order_item_id') == item.id]
        old_quantity = sum(int(d.get('quantity',0)) for _,d in changed)
        old_value = sum((money(Decimal(str(d['old_unit_price']))*int(d['quantity'])) for _,d in changed), Decimal('0.00'))
        lots.append({'key':f'item:{item.id}', 'order_item_id':item.id, 'variant_id':item.variant_id,
            'quantity':max(0,item.quantity-old_quantity), 'amount':max(Decimal('0.00'), money(item.subtotal)-old_value)})
        for record, detail in changed:
            lots.append({'key':f'exchange:{record.id}', 'order_item_id':item.id,
                'variant_id':int(detail['replacement_variant_id']), 'quantity':int(detail['quantity']),
                'amount':money(Decimal(str(detail['new_unit_price']))*int(detail['quantity']))})
    # Absorber un eventual centavo de redondeo de cambios antiguos.
    if lots:
        difference = collected(db,order) - sum((lot['amount'] for lot in lots),Decimal('0.00'))
        if abs(difference) <= Decimal('0.05'):
            next((lot for lot in reversed(lots) if lot['quantity']),lots[-1])['amount'] += difference
    states = {'COMPLETADO','PENDIENTE','SOLICITADO'} if include_pending else {'COMPLETADO'}
    for refund in order.refunds:
        if refund.status not in states: continue
        for item in refund.items:
            lot = next((lot for lot in lots if lot['key'] == item.lot_key),None)
            if lot:
                lot['quantity'] -= item.quantity
                lot['amount'] -= money(item.amount)
    for lot in lots:
        lot['quantity'] = max(0,lot['quantity'])
        lot['amount'] = max(Decimal('0.00'),lot['amount'])
        variant = db.get(ProductVariant,lot['variant_id'])
        lot.update(product_name=variant.product.name if variant else 'Prenda',
            size_name=variant.size_name if variant else None, color_name=variant.color_name if variant else None)
    return lots


def refund_response(refund):
    return {'id':refund.id, 'order_id':refund.order_id, 'amount':refund.amount,
        'status':refund.status, 'reason':refund.reason, 'source':refund.source,
        'reference':refund.reference, 'receipt_number':f'RF-{refund.id:08d}',
        'created_at':refund.created_at, 'completed_at':refund.completed_at,
        'error':refund.error, 'payouts':json.loads(refund.payouts_json or '[]'),
        'items':[{'id':item.id,'lot_key':item.lot_key,'variant_id':item.variant_id,'quantity':item.quantity,
            'amount':item.amount,'restock':item.restock,'restocked_quantity':item.restocked_quantity,
            'pending_return':max(0,item.quantity-item.restocked_quantity)} for item in refund.items]}


def order_financials(db,order):
    captured = collected(db,order)
    returned = refunded(order)
    pending = sum((money(r.amount) for r in order.refunds if r.status == 'PENDIENTE'),Decimal('0.00'))
    return {'collected_total':float(captured), 'refunded_total':float(returned),
        'refund_pending':float(pending), 'net_total':float(captured-returned),
        'refunds':[refund_response(r) for r in order.refunds],
        'returnable_items':[{**lot,'amount':float(lot['amount'])} for lot in returnable_lots(db,order)
            if lot['quantity'] > 0 or lot['amount'] > 0]}


def _allocate(amount, lots):
    """Distribución en centavos sin perder importes por redondeo."""
    remaining = int(amount*100)
    capacity = sum(int(lot['amount']*100) for lot in lots)
    amounts = []
    for lot in lots:
        cents = min(int(lot['amount']*100), remaining if capacity == 0 else int(amount*100)*int(lot['amount']*100)//capacity)
        amounts.append(cents)
        remaining -= cents
    for i, lot in enumerate(lots):
        extra = min(remaining,int(lot['amount']*100)-amounts[i])
        amounts[i] += extra; remaining -= extra
    if remaining: raise HTTPException(409,'El monto supera el saldo pendiente de devolución')
    return [Decimal(cents)/100 for cents in amounts]


def _payouts(db,order,amount):
    method = order.payment.method
    if method == 'EFECTIVO': return [{'method':'EFECTIVO','amount':float(amount)}] if amount else []
    bank_returned = sum((money(p['amount']) for r in order.refunds if r.status == 'COMPLETADO'
        for p in json.loads(r.payouts_json or '[]') if p['method'] == method),Decimal('0.00'))
    bank = min(amount,max(Decimal('0.00'),money(order.payment.amount)-bank_returned))
    payouts = [{'method':method,'amount':float(bank)}] if bank else []
    if amount > bank: payouts.append({'method':'EFECTIVO','amount':float(amount-bank)})
    return payouts


def _lock_return_inventory(db,order,items):
    db.flush()
    stocks = {}
    for vid in sorted({item.variant_id for item in items if item.restock and item.quantity}):
        if not order.stock_deducted or order.branch_id is None:
            raise HTTPException(409,'Esta venta no descontó inventario; no corresponde reponer prendas')
        stock = db.query(Inventory).filter_by(variant_id=vid,branch_id=order.branch_id).populate_existing().with_for_update().first()
        if stock is None:
            stock=Inventory(variant_id=vid,branch_id=order.branch_id,available=0)
            db.add(stock);db.flush()
        stocks[vid]=stock
    return stocks


def complete_refund(db:Session,refund,user,gateway=None):
    if refund.status == 'COMPLETADO': return refund
    order = refund.order
    stocks = _lock_return_inventory(db,order,refund.items)
    payouts = json.loads(refund.payouts_json or '[]')
    bank = sum((money(p['amount']) for p in payouts if p['method'] != 'EFECTIVO'),Decimal('0.00'))
    reference = f'cash_refund_{refund.request_id}'
    if bank:
        try:
            result=(gateway or get_gateway()).refund(order.payment.stripe_payment_id or f'offline_{order.id}',float(bank),refund.request_id)
        except Exception:
            result=None
        if result is None or not result.success:
            refund.status='PENDIENTE'
            refund.error='La devolución no fue confirmada por la pasarela. Reintenta esta misma operación.'
            return refund
        reference=result.transaction_id
    for item in refund.items:
        if not item.restock or not item.quantity: continue
        stock=stocks[item.variant_id];stock.available += item.quantity
        item.restocked_quantity=item.quantity
        db.add(InventoryMovement(inventory_id=stock.id,movement_type='DEVOLUCION',quantity=item.quantity,
            reason=f'Reembolso RF-{refund.id:08d} del pedido #{order.id}',user_id=user.id))
    refund.status='COMPLETADO';refund.reference=reference;refund.error=None
    refund.completed_at=datetime.now(timezone.utc)
    returned=refunded(order)
    order.payment.status='REEMBOLSADO' if returned >= collected(db,order) else 'REEMBOLSO_PARCIAL'
    if order.payment.status == 'REEMBOLSADO' and order.status != 'CANCELADO': order.status='REEMBOLSADO'
    db.add(Notification(user_id=order.client_id,title='Reembolso confirmado',
        message=f'Se devolvieron Bs {refund.amount:.2f} del pedido #{order.id}. Comprobante RF-{refund.id:08d}.'))
    return refund


def create_refund(db,order,user,payload,source='MANUAL',gateway=None,execute=True):
    if len(payload.reason.strip()) < 5: raise HTTPException(422,'Indica un motivo de al menos cinco caracteres')
    request_id=payload.request_id.lower()
    values=payload.model_dump()
    values.update(request_id=request_id,reason=payload.reason.strip())
    fingerprint=hashlib.sha256(json.dumps(values,sort_keys=True).encode()).hexdigest()
    existing=db.query(Refund).filter(Refund.request_id==request_id).first()
    if existing:
        if existing.order_id != order.id or existing.fingerprint != fingerprint:
            raise HTTPException(409,'El identificador pertenece a otro reembolso')
        return existing
    if not order.payment or not order.payment.paid_at:
        raise HTTPException(409,'No hay un cobro confirmado para reembolsar')
    if any(r.status in {'PENDIENTE','SOLICITADO'} for r in order.refunds):
        raise HTTPException(409,'Hay un reembolso pendiente. Resuélvelo antes de iniciar otro')
    if payload.restock and not order.stock_deducted:
        raise HTTPException(409,'No se puede reponer inventario que nunca se descontó')
    lots=returnable_lots(db,order)
    lines=[]
    if payload.items:
        if payload.amount is not None: raise HTTPException(422,'Selecciona prendas o un ajuste de importe, no ambos')
        quantities={}
        for item in payload.items: quantities[item.lot_key]=quantities.get(item.lot_key,0)+item.quantity
        for key,qty in quantities.items():
            lot=next((lot for lot in lots if lot['key']==key),None)
            if not lot or qty > lot['quantity']: raise HTTPException(409,'La cantidad supera las prendas que aún pueden devolverse')
            amount=money(lot['amount']*qty/lot['quantity'])
            lines.append((lot,qty,amount,payload.restock))
    elif payload.amount is not None:
        if payload.restock: raise HTTPException(422,'Para reponer inventario selecciona las prendas devueltas')
        amount=money(payload.amount)
        for lot,value in zip(lots,_allocate(amount,lots)):
            if value: lines.append((lot,0,value,False))
    else:
        lines=[(lot,lot['quantity'],lot['amount'],payload.restock) for lot in lots if lot['quantity'] or lot['amount']]
    total=sum((value for _,_,value,_ in lines),Decimal('0.00'))
    if not lines or (total == 0 and not any(qty for _,qty,_,restock in lines)):
        raise HTTPException(409,'No queda dinero ni prendas pendientes para esta devolución')
    if total > collected(db,order)-refunded(order): raise HTTPException(409,'El importe supera el saldo de la venta')
    refund=Refund(empresa_id=order.empresa_id,order=order,payment_id=order.payment.id,user_id=user.id,
        request_id=request_id,fingerprint=fingerprint,amount=float(total),reason=payload.reason.strip(),source=source,
        status='PENDIENTE' if execute else 'SOLICITADO',payouts_json=json.dumps(_payouts(db,order,total)))
    for lot,quantity,amount,restock in lines:
        refund.items.append(RefundItem(order_item_id=lot['order_item_id'],lot_key=lot['key'],
            variant_id=lot['variant_id'],quantity=quantity,amount=float(amount),restock=restock))
    db.add(refund);db.flush()
    return complete_refund(db,refund,user,gateway) if execute else refund


def refund_all(db,order,user,reason,source,restock,gateway=None):
    from app.schemas import RefundCreate
    pending=next((r for r in order.refunds if r.status in {'PENDIENTE','SOLICITADO'}),None)
    if pending: raise HTTPException(409,'Primero debe completarse el reembolso pendiente de esta venta')
    return create_refund(db,order,user,RefundCreate(request_id=str(uuid.uuid4()),reason=reason,restock=restock),source,gateway)


def register_legacy_cancellations(db):
    """No dar por devuelto el dinero de anulaciones antiguas sin comprobante."""
    from app.models.commerce import Order, Payment
    orders=db.query(Order).join(Payment).filter(Order.status=='CANCELADO',
        Payment.status=='ANULADO',Payment.paid_at.isnot(None)).all()
    for order in orders:
        if order.refunds or not order.items: continue
        key=str(uuid.uuid5(uuid.NAMESPACE_URL,f'fashionstore/legacy-refund/{order.id}'))
        refund=Refund(empresa_id=order.empresa_id,order=order,payment_id=order.payment.id,
            user_id=order.user_id or order.client_id,request_id=key,fingerprint=hashlib.sha256(key.encode()).hexdigest(),
            amount=order.payment.amount,reason='Anulación antigua: devolución de dinero pendiente de confirmar',
            source='ANULACION_ANTIGUA',status='PENDIENTE',
            payouts_json=json.dumps([{'method':order.payment.method,'amount':order.payment.amount}]))
        for item in order.items:
            refund.items.append(RefundItem(order_item_id=item.id,lot_key=f'item:{item.id}',variant_id=item.variant_id,
                quantity=item.quantity,amount=item.subtotal,restock=False,restocked_quantity=item.quantity))
        db.add(refund)
    db.commit()

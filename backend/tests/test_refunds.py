import uuid
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from fastapi import HTTPException
import pytest
from sqlalchemy import func
from app.core.database import SessionLocal, engine
from app.models.commerce import Order, Payment, Refund, RefundStockReturn
from app.models.inventory import Inventory, InventoryMovement
from app.models.catalog import Product, ProductVariant
from app.services.payments import SandboxPaymentGateway, GatewayResult
from test_business_integrity import business


def paid(client,catalog,headers,qty=3,method='EFECTIVO'):
    response=client.post('/api/pos/sale',headers=headers,json={'branch_id':catalog['branch_id'],
        'items':[{'variant_id':catalog['variant_id'],'quantity':qty}],'payment_method':method})
    assert response.status_code==201,response.text
    return response.json()


def payload(**changes):
    return {'request_id':str(uuid.uuid4()),'reason':'Devolución solicitada por el cliente','restock':False,**changes}


def check_stock(catalog,quantity):
    with SessionLocal() as db:
        inv=db.query(Inventory).filter_by(branch_id=catalog['branch_id'],variant_id=catalog['variant_id']).one()
        assert inv.available==quantity
        assert db.query(func.sum(InventoryMovement.quantity)).filter_by(inventory_id=inv.id).scalar()==quantity


def test_full_refund_is_idempotent_and_restock_not_repeated(client,catalog,auth_headers):
    order=paid(client,catalog,auth_headers)
    body=payload(restock=True)
    path=f"/api/orders/{order['id']}/refunds"
    for _ in range(2):
        result=client.post(path,headers=auth_headers,json=body)
        assert result.status_code==201,result.text
        assert result.json()['refunded_total']==360
        assert result.json()['net_total']==0
        assert result.json()['status']=='REEMBOLSADO'
        assert len(result.json()['refunds'])==1
    check_stock(catalog,10)
    assert client.post(path,headers=auth_headers,json=payload(restock=True)).status_code==409


def test_partial_items_then_remaining_balance(client,catalog,auth_headers):
    order=paid(client,catalog,auth_headers)
    path=f"/api/orders/{order['id']}/refunds"
    partial=payload(restock=True,items=[{'lot_key':order['returnable_items'][0]['key'],'quantity':1}])
    result=client.post(path,headers=auth_headers,json=partial)
    assert result.status_code==201,result.text
    assert result.json()['refunded_total']==120
    assert result.json()['net_total']==240
    assert result.json()['payment']['status']=='REEMBOLSO_PARCIAL'
    check_stock(catalog,8)
    result=client.post(path,headers=auth_headers,json=payload(restock=True))
    assert result.status_code==201,result.text
    assert result.json()['refunded_total']==360
    check_stock(catalog,10)


def test_money_refund_does_not_restock_and_later_reception_no_second_payment(client,catalog,auth_headers):
    order=paid(client,catalog,auth_headers)
    result=client.post(f"/api/orders/{order['id']}/refunds",headers=auth_headers,json=payload())
    assert result.status_code==201,result.text
    check_stock(catalog,7)
    refund=result.json()['refunds'][0]
    path=f"/api/orders/{order['id']}/refunds/{refund['id']}/restock"
    body={'request_id':str(uuid.uuid4()),'refund_item_id':refund['items'][0]['id'],'quantity':3}
    for _ in range(2):
        result=client.post(path,headers=auth_headers,json=body)
        assert result.status_code==200,result.text
        assert result.json()['refunded_total']==360
    check_stock(catalog,10)
    assert client.post(path,headers=auth_headers,json={**body,'request_id':str(uuid.uuid4())}).status_code==409


def test_amount_adjustment_and_rounding_do_not_exceed_collected(client,catalog,auth_headers):
    order=paid(client,catalog,auth_headers)
    path=f"/api/orders/{order['id']}/refunds"
    assert client.post(path,headers=auth_headers,json=payload(amount=360.01)).status_code==409
    result=client.post(path,headers=auth_headers,json=payload(amount=10.01))
    assert result.status_code==201,result.text
    assert result.json()['refunded_total']==10.01
    check_stock(catalog,7)
    lot=result.json()['returnable_items'][0]
    for _ in range(3):
        result=client.post(path,headers=auth_headers,json=payload(restock=True,items=[{'lot_key':lot['key'],'quantity':1}]))
        assert result.status_code==201,result.text
    assert result.json()['refunded_total']==360
    assert result.json()['net_total']==0
    check_stock(catalog,10)


def test_pending_gateway_refund_can_retry_once_without_premature_stock_or_net_change(client,catalog,auth_headers,monkeypatch):
    order=paid(client,catalog,auth_headers,method='TARJETA')
    class Gateway(SandboxPaymentGateway):
        fail=True
        keys=[]
        def refund(self,transaction_id,amount,idempotency_key):
            self.keys.append(idempotency_key)
            return GatewayResult(False,None,'fallo') if self.fail else super().refund(transaction_id,amount,idempotency_key)
    gateway=Gateway();monkeypatch.setattr('app.api.commerce.get_gateway',lambda:gateway)
    path=f"/api/orders/{order['id']}/refunds"
    result=client.post(path,headers=auth_headers,json=payload(restock=True))
    assert result.status_code==201,result.text
    assert result.json()['refund_pending']==360
    assert result.json()['net_total']==360
    check_stock(catalog,7)
    assert client.post(path,headers=auth_headers,json=payload()).status_code==409
    refund=result.json()['refunds'][0]
    gateway.fail=False
    for _ in range(2):
        result=client.post(path+f"/{refund['id']}/retry",headers=auth_headers)
        assert result.status_code==200,result.text
        assert result.json()['refunded_total']==360
    assert len(gateway.keys)==2
    assert len(set(gateway.keys))==1
    check_stock(catalog,10)


def test_payment_confirmed_but_fulfillment_fails_is_refunded_without_phantom_stock(client,catalog,auth_headers,monkeypatch):
    def unavailable(*args,**kwargs): raise HTTPException(409,'Sin existencias')
    monkeypatch.setattr('app.api.commerce._complete_order_sale',unavailable)
    order=paid(client,catalog,auth_headers,method='TARJETA')
    assert order['status']=='CANCELADO'
    assert order['refunded_total']==360
    assert order['net_total']==0
    assert order['refunds'][0]['source']=='SIN_STOCK'
    assert order['stock_deducted'] is False
    check_stock(catalog,10)


def test_known_insufficient_stock_is_never_charged(client,catalog,auth_headers,monkeypatch):
    class Gateway(SandboxPaymentGateway):
        calls=0
        def charge(self,*args,**kwargs): self.calls+=1;return super().charge(*args,**kwargs)
    gateway=Gateway();monkeypatch.setattr('app.api.commerce.get_gateway',lambda:gateway)
    result=client.post('/api/pos/sale',headers=auth_headers,json={'branch_id':catalog['branch_id'],'items':[{'variant_id':catalog['variant_id'],'quantity':11}],'payment_method':'TARJETA'})
    assert result.status_code==409
    assert gateway.calls==0
    check_stock(catalog,10)


def test_client_request_requires_approval_and_cannot_cross_tenants(client,business):
    order=paid(client,business,business['ha'])
    # Usar un pedido del cliente real de la empresa.
    with SessionLocal() as db:
        db.get(Order,order['id']).client_id=business['customer'];db.commit()
    path=f"/api/orders/{order['id']}"
    assert client.post(path+'/refunds',headers=business['hc'],json=payload()).status_code==403
    assert client.post(path+'/refund-requests',headers=business['hb'],json=payload()).status_code==404
    result=client.post(path+'/refund-requests',headers=business['hc'],json=payload())
    assert result.status_code==201,result.text
    assert result.json()['refunded_total']==0
    refund=result.json()['refunds'][0]
    assert refund['status']=='SOLICITADO'
    assert client.post(path+f"/refunds/{refund['id']}/retry",headers=business['ha']).status_code==409
    assert client.post(path+f"/refunds/{refund['id']}/decision",headers=business['hc'],json={'approve':True}).status_code==403
    approved=client.post(path+f"/refunds/{refund['id']}/decision",headers=business['ha'],json={'approve':True,'restock':True})
    assert approved.status_code==200,approved.text
    assert approved.json()['refunded_total']==360
    check_stock(business,10)


def test_rejected_request_releases_refundable_balance(client,business):
    order=paid(client,business,business['ha'])
    with SessionLocal() as db: db.get(Order,order['id']).client_id=business['customer'];db.commit()
    path=f"/api/orders/{order['id']}"
    result=client.post(path+'/refund-requests',headers=business['hc'],json=payload())
    rid=result.json()['refunds'][0]['id']
    rejected=client.post(path+f'/refunds/{rid}/decision',headers=business['ha'],json={'approve':False,'comment':'No se ha devuelto el producto'})
    assert rejected.status_code==200,rejected.text
    assert rejected.json()['returnable_items'][0]['quantity']==3
    assert rejected.json()['refunded_total']==0


def test_old_cancelled_payment_requires_explicit_money_refund_without_restocking_twice(client,catalog,auth_headers):
    from app.services.refunds import register_legacy_cancellations
    order=paid(client,catalog,auth_headers)
    with SessionLocal() as db:
        old=db.get(Order,order['id']);old.status='CANCELADO';old.stock_deducted=False;old.payment.status='ANULADO'
        stock=db.query(Inventory).filter_by(branch_id=catalog['branch_id']).one()
        stock.available+=3
        db.add(InventoryMovement(inventory_id=stock.id,movement_type='DEVOLUCION',quantity=3))
        db.commit();register_legacy_cancellations(db);register_legacy_cancellations(db)
    current=client.get(f"/api/orders/{order['id']}",headers=auth_headers).json()
    assert current['refund_pending']==360
    assert len(current['refunds'])==1
    assert current['refunded_total']==0
    refund=current['refunds'][0]
    result=client.post(f"/api/orders/{order['id']}/refunds/{refund['id']}/retry",headers=auth_headers)
    assert result.status_code==200,result.text
    assert result.json()['net_total']==0
    check_stock(catalog,10)


def test_customer_can_withdraw_unprocessed_request(client,business):
    order=paid(client,business,business['ha'])
    with SessionLocal() as db: db.get(Order,order['id']).client_id=business['customer'];db.commit()
    path=f"/api/orders/{order['id']}"
    requested=client.post(path+'/refund-requests',headers=business['hc'],json=payload()).json()
    refund=requested['refunds'][0]
    withdrawn=client.post(path+f"/refunds/{refund['id']}/withdraw",headers=business['hc'])
    assert withdrawn.status_code==200,withdrawn.text
    assert withdrawn.json()['refunds'][0]['status']=='CANCELADO'
    assert withdrawn.json()['returnable_items'][0]['quantity']==3
    assert withdrawn.json()['refunded_total']==0


def test_refund_in_later_period_is_negative_without_rewriting_original_sale(client,catalog,auth_headers):
    order=paid(client,catalog,auth_headers)
    old=datetime.now(timezone.utc)-timedelta(days=40)
    with SessionLocal() as db:
        db.get(Order,order['id']).created_at=old
        db.query(Payment).filter_by(order_id=order['id']).one().paid_at=old
        db.commit()
    assert client.post(f"/api/orders/{order['id']}/refunds",headers=auth_headers,json=payload()).status_code==201
    today=datetime.now(timezone.utc).date()
    path=f"/api/reports/dashboard?branch_id={catalog['branch_id']}"
    report=client.get(path+f'&desde={old.date()}&hasta={old.date()}',headers=auth_headers).json()
    assert report['kpis']['total_sales']==360
    report=client.get(path+f'&desde={today}&hasta={today}',headers=auth_headers).json()
    assert report['empty'] is False
    assert report['kpis']['gross_sales']==0
    assert report['kpis']['refund_amount']==360
    assert report['kpis']['total_sales']==-360
    assert report['sales_series'][0]['amount']==-360
    assert sum(c['sales'] for c in report['by_category'])==-360


@pytest.mark.parametrize('replacement_price',[100,150])
def test_exchange_cash_difference_then_refund_correct_garment_and_total(client,business,replacement_price):
    with SessionLocal() as db:
        original=db.get(ProductVariant,business['variant_id'])
        product=Product(empresa_id=business['a'],name='Reemplazo',base_price=replacement_price)
        db.add(product);db.flush()
        replacement=ProductVariant(product_id=product.id,size_id=original.size_id,color_id=original.color_id,sku=str(uuid.uuid4()),price=replacement_price)
        db.add(replacement);db.flush()
        db.add(Inventory(branch_id=business['branch_id'],variant_id=replacement.id,available=10));db.flush()
        inv=db.query(Inventory).filter_by(branch_id=business['branch_id'],variant_id=replacement.id).one()
        db.add(InventoryMovement(inventory_id=inv.id,movement_type='INGRESO',quantity=10));rid=replacement.id;db.commit()
    order=paid(client,business,business['ha'],qty=1,method='TARJETA')
    path=f"/api/orders/{order['id']}"
    exchange=client.post(path+'/exchanges',headers=business['ha'],json={'order_item_id':order['items'][0]['id'],'replacement_variant_id':rid,'quantity':1,'cash_difference':replacement_price-120})
    assert exchange.status_code==201,exchange.text
    current=client.get(path,headers=business['ha']).json()
    assert current['net_total']==replacement_price
    result=client.post(path+'/refunds',headers=business['ha'],json=payload(restock=True))
    assert result.status_code==201,result.text
    assert result.json()['refunded_total']==replacement_price
    assert result.json()['net_total']==0
    assert result.json()['refunds'][0]['items'][0]['variant_id']==rid
    with SessionLocal() as db:
        assert db.query(Inventory).filter_by(branch_id=business['branch_id'],variant_id=rid).one().available==10
    report=client.get(f"/api/reports/dashboard?branch_id={business['branch_id']}",headers=business['ha']).json()
    assert report['kpis']['total_sales']==0
    assert report['kpis']['gross_sales']==report['kpis']['refund_amount']


@pytest.mark.parametrize('same_id',[True,False])
def test_concurrent_refunds_never_exceed_original_payment(client,business,same_id):
    if engine.dialect.name!='postgresql': pytest.skip('Concurrencia real en PostgreSQL')
    order=paid(client,business,business['ha'])
    first=payload(restock=True);second=dict(first) if same_id else payload(restock=True)
    barrier=Barrier(2)
    def send(body):
        barrier.wait(timeout=10)
        return client.post(f"/api/orders/{order['id']}/refunds",headers=business['ha'],json=body).status_code
    with ThreadPoolExecutor(max_workers=2) as pool: states=list(pool.map(send,[first,second]))
    assert sorted(states)==([201,201] if same_id else [201,409])
    current=client.get(f"/api/orders/{order['id']}",headers=business['ha']).json()
    assert current['refunded_total']==360
    check_stock(business,10)

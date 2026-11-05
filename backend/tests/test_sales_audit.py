import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import func
from app.core.database import SessionLocal, engine
from app.models.audit import AuditEvent
from app.models.commerce import Order, Payment
from app.models.inventory import Inventory, InventoryMovement
from app.models.catalog import ProductVariant
from app.models.user import User
from app.services.audit import identify_actor
from test_business_integrity import business


def sale(catalog, **changes):
    return {'branch_id': catalog['branch_id'], 'payment_method': 'EFECTIVO',
        'items': [{'variant_id': catalog['variant_id'], 'quantity': 2}], **changes}


def balance(catalog):
    with SessionLocal() as db:
        stock = db.query(Inventory).filter_by(branch_id=catalog['branch_id'], variant_id=catalog['variant_id']).one()
        ledger = db.query(func.sum(InventoryMovement.quantity)).filter_by(inventory_id=stock.id).scalar()
        return stock.available, ledger


def test_pos_duplicate_request_debits_once_and_receipt_has_change(client, catalog, cajero_headers):
    payload = sale(catalog, request_id=str(uuid.uuid4()), cash_received=300)
    first = client.post('/api/pos/sale', json=payload, headers=cajero_headers)
    second = client.post('/api/pos/sale', json=payload, headers=cajero_headers)
    assert first.status_code == second.status_code == 201, first.text
    assert first.json()['id'] == second.json()['id']
    assert first.json()['payment']['cash_received'] == 300
    assert first.json()['payment']['change_amount'] == 60
    assert first.json()['receipt_number']
    assert balance(catalog) == (8, 8)
    changed = client.post('/api/pos/sale', json={**payload, 'cash_received': 500}, headers=cajero_headers)
    assert changed.status_code == 409
    assert balance(catalog) == (8, 8)


@pytest.mark.parametrize('path', ['/api/pos/sale', '/api/orders/checkout'])
def test_duplicate_lines_cannot_oversell_or_commit_partial_order(client, catalog, cajero_headers, path):
    payload = sale(catalog, order_type='PRESENCIAL', items=[{'variant_id': catalog['variant_id'], 'quantity': 6}] * 2)
    with SessionLocal() as db:
        before = db.query(Order).count()
        audits = db.query(AuditEvent).count()
    response = client.post(path, json=payload, headers=cajero_headers)
    assert response.status_code == 409, response.text
    assert balance(catalog) == (10, 10)
    with SessionLocal() as db:
        assert db.query(Order).count() == before
        assert db.query(AuditEvent).count() == audits


def test_short_cash_rolls_back_sale_payment_and_audit(client, catalog, cajero_headers):
    with SessionLocal() as db:
        counts = [db.query(model).count() for model in (Order, Payment, AuditEvent)]
    response = client.post('/api/pos/sale', json=sale(catalog, cash_received=239.99), headers=cajero_headers)
    assert response.status_code == 422
    assert balance(catalog) == (10, 10)
    with SessionLocal() as db:
        assert [db.query(model).count() for model in (Order, Payment, AuditEvent)] == counts


def test_decline_retry_cancel_keeps_ledger_and_records_actor(client, catalog, cajero_headers, auth_headers):
    declined = client.post('/api/pos/sale', json=sale(catalog, payment_method='TARJETA', card_number='4000000000000002'), headers=cajero_headers)
    assert declined.status_code == 201, declined.text
    order = declined.json()
    assert order['status'] == 'PENDIENTE'
    assert balance(catalog) == (10, 10)
    paid = client.post(f"/api/orders/{order['id']}/pay", json={'payment_method':'EFECTIVO','cash_received':250}, headers=cajero_headers)
    assert paid.status_code == 200, paid.text
    assert paid.json()['payment']['change_amount'] == 10
    assert balance(catalog) == (8, 8)
    cancelled = client.patch(f"/api/orders/{order['id']}/status", json={'status':'CANCELADO'}, headers=auth_headers)
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()['payment']['status'] == 'REEMBOLSADO'
    assert balance(catalog) == (10, 10)
    client.patch(f"/api/orders/{order['id']}/status", json={'status':'CANCELADO'}, headers=auth_headers)
    assert balance(catalog) == (10, 10)
    with SessionLocal() as db:
        events = db.query(AuditEvent).filter_by(entity='inventory', entity_id=str(db.query(Inventory).filter_by(branch_id=catalog['branch_id']).one().id)).all()
        assert any(json.loads(e.changes_json).get('available') == {'antes':10,'despues':8} for e in events)
        assert all(e.actor_name and e.actor_id for e in events)
        assert '4000000000000002' not in ''.join(e.changes_json for e in db.query(AuditEvent).all())


def test_decimal_total_and_combined_items(client, catalog, cajero_headers):
    with SessionLocal() as db:
        db.get(ProductVariant, catalog['variant_id']).price = 19.995
        db.commit()
    displayed = client.get(f"/api/inventory/availability?branch_id={catalog['branch_id']}",headers=cajero_headers)
    assert displayed.json()[0]['price'] == 20
    response = client.post('/api/pos/sale', json=sale(catalog, items=[{'variant_id':catalog['variant_id'],'quantity':1}]*3, cash_received=100), headers=cajero_headers)
    assert response.status_code == 201, response.text
    assert response.json()['total'] == 60
    assert len(response.json()['items']) == 1
    assert response.json()['payment']['change_amount'] == 40
    assert balance(catalog) == (7, 7)


def test_audit_permission_tenant_filter_and_pagination(client, business, cajero_headers):
    response = client.post('/api/pos/sale', json=sale(business), headers=business['ha'])
    assert response.status_code == 201, response.text
    aid = response.json()['id']
    own = client.get('/api/bitacora?entity=orders&page_size=1', headers=business['ha'])
    assert own.status_code == 200, own.text
    assert own.json()['total'] >= 1
    assert len(own.json()['items']) == 1
    assert own.json()['items'][0]['empresa_id'] == business['a']
    other = client.get('/api/bitacora?entity=orders', headers=business['hb']).json()
    assert not any(row['entity_id'] == str(aid) for row in other['items'])
    assert client.get('/api/bitacora', headers=cajero_headers).status_code == 403
    assert client.get('/api/bitacora', headers=business['hc']).status_code == 403
    assert client.get('/api/bitacora').status_code == 401
    assert client.get('/api/bitacora?page=0', headers=business['ha']).status_code == 422
    assert client.get('/api/bitacora?desde=2026-11-10T00:00:00&hasta=2026-11-01T00:00:00', headers=business['ha']).status_code == 422


def test_audit_never_records_password_and_rollback_discards_changes(client, auth_headers):
    with SessionLocal() as db:
        user = db.query(User).filter_by(email='admin@test.com').one()
        identify_actor(db,user)
        before = db.query(AuditEvent).count()
        user.first_name = 'Cambio temporal'
        db.flush()
        db.rollback()
        assert db.query(AuditEvent).count() == before
        assert 'hashed_password' not in ''.join(row.changes_json for row in db.query(AuditEvent).all())
    result = client.get('/api/bitacora?action=ACCESO', headers=auth_headers)
    assert result.status_code == 200
    assert result.json()['total'] > 0


def test_reconciliation_detects_missing_movement_without_changing_stock(client, catalog, auth_headers):
    endpoint=f"/api/inventory/reconciliation?branch_id={catalog['branch_id']}"
    assert client.get(endpoint,headers=auth_headers).json()['consistent'] is True
    with SessionLocal() as db:
        db.query(Inventory).filter_by(branch_id=catalog['branch_id']).one().available = 9
        db.commit()
    result=client.get(endpoint,headers=auth_headers)
    assert result.status_code==200, result.text
    assert result.json()['differences']==1
    assert result.json()['items'][0]['difference']==-1
    assert balance(catalog)==(9,10)


def test_duplicate_reservation_items_are_combined_and_cancelled_once(client,catalog,auth_headers):
    too_many={'branch_id':catalog['branch_id'],'items':[{'variant_id':catalog['variant_id'],'quantity':6}]*2}
    assert client.post('/api/reservations',json=too_many,headers=auth_headers).status_code==409
    assert balance(catalog)==(10,10)
    valid={**too_many,'items':[{'variant_id':catalog['variant_id'],'quantity':2}]*2}
    result=client.post('/api/reservations',json=valid,headers=auth_headers)
    assert result.status_code==201,result.text
    assert len(result.json()['items'])==1
    assert balance(catalog)==(6,6)
    cancelled=client.delete('/api/reservations/'+str(result.json()['id']),headers=auth_headers)
    assert cancelled.status_code==200,cancelled.text
    assert balance(catalog)==(10,10)


@pytest.mark.parametrize('same_request',[True,False])
def test_concurrent_pos_no_duplicate_no_oversell(client,business,same_request):
    if engine.dialect.name!='postgresql': pytest.skip('Requiere bloqueos PostgreSQL')
    first=sale(business,request_id=str(uuid.uuid4()),items=[{'variant_id':business['variant_id'],'quantity':7}])
    second=dict(first) if same_request else {**first,'request_id':str(uuid.uuid4())}
    barrier=Barrier(2)
    def send(payload):
        barrier.wait(timeout=10)
        response=client.post('/api/pos/sale',json=payload,headers=business['ha'])
        return response.status_code,response.json()
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(send,[first,second]))
    assert sorted(r[0] for r in results)==([201,201] if same_request else [201,409]),results
    if same_request: assert results[0][1]['id']==results[1][1]['id']
    assert balance(business)==(3,3)

import uuid
from datetime import date, datetime, timedelta
from io import BytesIO

import pytest
from openpyxl import load_workbook

from app.core.database import SessionLocal
from app.core.security import create_access_token
from app.models.branch import Branch
from app.models.catalog import Product, ProductVariant, Provider, ProductProposal
from app.models.commerce import Order, OrderItem
from app.models.inventory import Inventory, InventoryMovement
from app.models.tenant import Empresa, Plan, Suscripcion
from app.models.user import Role, User


@pytest.fixture
def business(client, catalog):
    suffix = uuid.uuid4().hex[:8]
    with SessionLocal() as db:
        a = Empresa(razon_social=f"Business A {suffix}", nit=f"BA-{suffix}")
        b = Empresa(razon_social=f"Business B {suffix}", nit=f"BB-{suffix}")
        plan = Plan(nombre=f"Plan {suffix}", max_sucursales=2, permite_reportes_ia=True, permite_analitica_ml=True)
        db.add_all([a, b, plan]); db.flush()
        for company in (a, b):
            db.add(Suscripcion(empresa_id=company.id, plan_id=plan.id, fecha_inicio=date.today(),
                fecha_vencimiento=date.today() + timedelta(days=30), estado="ACTIVA"))
        users = []
        for company, role_name, label in ((a, "Administrador", "a"), (b, "Administrador", "b"), (a, "Cliente", "customer")):
            role = db.query(Role).filter(Role.name == role_name).first()
            user = User(empresa_id=company.id, first_name=label, last_name="Test", email=f"{label}-{suffix}@test.com", hashed_password="!", role_id=role.id)
            db.add(user); db.flush(); users.append(user)
        branch_a = db.get(Branch, catalog["branch_id"]); branch_a.empresa_id = a.id
        product_a = db.get(Product, catalog["product_id"]); product_a.empresa_id = a.id
        variant_a = db.get(ProductVariant, catalog["variant_id"])
        branch_b = Branch(name=f"Private branch B {suffix}", city="Test", empresa_id=b.id)
        product_b = Product(name=f"Private product B {suffix}", base_price=120, empresa_id=b.id)
        provider_b = Provider(name=f"Private supplier B {suffix}", empresa_id=b.id)
        db.add_all([branch_b, product_b, provider_b]); db.flush()
        variant_b = ProductVariant(product_id=product_b.id, size_id=variant_a.size_id, color_id=variant_a.color_id, sku=f"BB-{suffix}", price=120)
        db.add(variant_b); db.flush()
        db.add(Inventory(branch_id=branch_b.id, variant_id=variant_b.id, available=10))
        proposal_b = ProductProposal(provider_id=provider_b.id, name="Private proposal", base_price=120)
        db.add(proposal_b); db.flush()
        result = {**catalog, "a": a.id, "b": b.id, "branch_b": branch_b.id, "variant_b": variant_b.id, "product_b": product_b.id, "proposal_b": proposal_b.id,
            "admin_a": users[0].id, "admin_b": users[1].id, "customer": users[2].id,
            "ha": {"Authorization": "Bearer " + create_access_token(users[0].email, users[0].role_name)},
            "hb": {"Authorization": "Bearer " + create_access_token(users[1].email, users[1].role_name)},
            "hc": {"Authorization": "Bearer " + create_access_token(users[2].email, users[2].role_name)}}
        db.commit()
        return result


def operation(business, **changes):
    return {"uuid": str(uuid.uuid4()), "tipo_operacion": "VENTA_CONTADO", "sucursal_id": business["branch_id"],
        "usuario_id": business["admin_a"], "items": [{"variant_id": business["variant_id"], "quantity": 2, "precio": 120}],
        "forma_pago": "EFECTIVO", "total": 240, **changes}


@pytest.mark.parametrize('same_uuid', [True, False])
def test_concurrent_sync_does_not_duplicate_or_oversell(client, business, same_uuid):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from app.core.database import engine
    if engine.dialect.name != 'postgresql':
        pytest.skip('Los bloqueos de filas se verifican con PostgreSQL')
    first = operation(business, items=[{'variant_id': business['variant_id'], 'quantity': 7, 'precio': 120}], total=840)
    second = dict(first) if same_uuid else {**first, 'uuid': str(uuid.uuid4())}
    barrier = Barrier(2)

    def send(op):
        barrier.wait(timeout=10)
        response = client.post('/api/sync', json={'operaciones': [op]}, headers=business['ha'])
        assert response.status_code == 200, response.text
        return response.json()['resultados'][0]['estado']

    with ThreadPoolExecutor(max_workers=2) as pool:
        states = list(pool.map(send, [first, second]))
    assert sorted(states) == (['CONFIRMADA', 'CONFIRMADA'] if same_uuid else ['CONFIRMADA', 'EN_CONFLICTO'])
    with SessionLocal() as db:
        assert db.query(Inventory).filter_by(branch_id=business['branch_id'], variant_id=business['variant_id']).one().available == 3
        assert db.query(Order).filter_by(empresa_id=business['a']).count() == 1


@pytest.mark.parametrize("path", ["/api/reservations", "/api/pos/sale"])
def test_cannot_create_commerce_in_another_company(client, business, path):
    result = client.post(path, json={"branch_id": business["branch_b"], "items": [{"variant_id": business["variant_b"], "quantity": 1}]}, headers=business["ha"])
    assert result.status_code == 404


def test_private_products_unavailable_to_anonymous_and_unassigned_users(client, business, auth_headers):
    assert client.get(f"/api/products/{business['product_b']}").status_code == 404
    assert client.get(f"/api/products/{business['product_b']}", headers=auth_headers).status_code == 404


def test_reservations_orders_and_notifications_stay_in_company(client, business):
    reservation = client.post("/api/reservations", json={"branch_id": business["branch_b"], "items": [{"variant_id": business["variant_b"], "quantity": 1}]}, headers=business["hb"])
    assert reservation.status_code == 201, reservation.text
    rid = reservation.json()["id"]
    assert all(r["id"] != rid for r in client.get("/api/reservations?all_reservations=true", headers=business["ha"]).json())
    for suffix, method in (("", "GET"), ("/attend", "PATCH"), ("/cancel", "PATCH"), ("/expire", "POST")):
        assert client.request(method, f"/api/reservations/{rid}{suffix}", headers=business["ha"]).status_code == 404
    notifications = client.get("/api/notifications", headers=business["ha"]).json()
    assert all(reservation.json()["code"] not in n["message"] for n in notifications)
    sale = client.post("/api/pos/sale", json={"branch_id": business["branch_b"], "items": [{"variant_id": business["variant_b"], "quantity": 1}]}, headers=business["hb"]).json()
    assert client.get(f"/api/orders/{sale['id']}", headers=business["ha"]).status_code == 404
    assert all(o["id"] != sale["id"] for o in client.get("/api/orders", headers=business["ha"]).json())
    assert client.patch(f"/api/orders/{sale['id']}/status", json={"status": "CANCELADO"}, headers=business["ha"]).status_code == 404


def test_proposals_and_recommendations_are_isolated(client, business):
    assert all(r["id"] != business["proposal_b"] for r in client.get("/api/providers/proposals", headers=business["ha"]).json())
    assert client.patch(f"/api/providers/proposals/{business['proposal_b']}/approve", json={}, headers=business["ha"]).status_code == 404
    suggestions = client.get("/api/recommendations", headers=business["hc"]).json()
    assert all(r["product_id"] != business["product_b"] for r in suggestions["items"])


def test_duplicate_sync_lines_cannot_oversell(client, business):
    op = operation(business, items=[{"variant_id": business["variant_id"], "quantity": 6, "precio": 120}] * 2, total=1440)
    result = client.post("/api/sync", json={"operaciones": [op]}, headers=business["ha"])
    assert result.json()["resultados"][0]["estado"] == "EN_CONFLICTO", result.text
    with SessionLocal() as db:
        assert db.query(Inventory).filter_by(branch_id=business["branch_id"]).one().available == 10
        assert db.query(Order).filter_by(empresa_id=business["a"]).count() == 0


@pytest.mark.parametrize("changes", [
    {"forma_pago": "TARJETA"}, {"total": 999}, {"usuario_id": -1},
    {"items": [{"variant_id": 1, "quantity": 1, "precio": -5}]},
    {"items": [{"variant_id": 1, "quantity": 1.5, "precio": 120}]},
])
def test_sync_rejects_invalid_commercial_data(client, business, changes):
    result = client.post("/api/sync", json={"operaciones": [operation(business, **changes)]}, headers=business["ha"])
    assert result.status_code == 200, result.text
    assert result.json()["resultados"][0]["estado"] == "RECHAZADA", result.text


def test_sync_rejects_foreign_client_and_preserves_movement_sign(client, business):
    bad = operation(business, cliente_id=business["admin_b"])
    assert client.post("/api/sync", json={"operaciones": [bad]}, headers=business["ha"]).json()["resultados"][0]["estado"] == "RECHAZADA"
    op = operation(business)
    for _ in range(2):
        assert client.post("/api/sync", json={"operaciones": [op]}, headers=business["ha"]).json()["resultados"][0]["estado"] == "CONFIRMADA"
    with SessionLocal() as db:
        inv = db.query(Inventory).filter_by(branch_id=business["branch_id"]).one()
        assert inv.available == 8
        movements = db.query(InventoryMovement).filter_by(inventory_id=inv.id, movement_type="SALIDA").all()
        assert len(movements) == 1 and movements[0].quantity == -2


@pytest.mark.parametrize("state", ["SUSPENDIDA", "CANCELADA", "VENCIDA"])
def test_subscription_blocks_business_operations(client, business, state):
    with SessionLocal() as db:
        db.query(Suscripcion).filter_by(empresa_id=business["a"]).one().estado = state
        db.commit()
    assert client.post("/api/sync", json={"operaciones": [operation(business)]}, headers=business["ha"]).status_code == 403
    assert client.post("/api/pos/sale", json={"branch_id": business["branch_id"], "items": [{"variant_id": business["variant_id"], "quantity": 1}]}, headers=business["ha"]).status_code == 403


def test_report_dates_status_authorization_and_exported_data(client, business):
    assert client.post("/api/reportes/ia", json={"pregunta_natural": "ventas"}, headers=business["hc"]).status_code == 403
    with SessionLocal() as db:
        for when, status, total in [(datetime(2026, 9, 30, 18), "PAGADO", 240), (datetime(2026, 9, 12), "CANCELADO", 999), (datetime(2025, 1, 1), "PAGADO", 555)]:
            db.add(Order(empresa_id=business["a"], client_id=business["customer"], branch_id=business["branch_id"], order_type="DIGITAL", status=status, total=total, created_at=when))
        db.commit()
    response = client.post("/api/reportes/ia", json={"pregunta_natural": "ventas de septiembre de 2026 por sucursal"}, headers=business["ha"])
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["filas"][0]["total_ventas"] == 240
    assert data["filtros_aplicados"]["fecha_hasta"] == "2026-09-30"
    path = f"/api/reportes/ia/{data['solicitud_id']}/archivo"
    assert client.get(path).status_code == 401
    assert client.get(path, headers=business["hb"]).status_code == 404
    response = client.get(path, headers=business["ha"])
    workbook = load_workbook(BytesIO(response.content), read_only=True)
    assert any(240 in row for row in workbook.active.values)
    workbook.close()
    assert client.get(path + "?formato=pdf", headers=business["ha"]).content.startswith(b"%PDF")


def test_reactivating_branch_respects_plan_limit(client, business):
    with SessionLocal() as db:
        db.add_all([Branch(name="Second", city="Test", empresa_id=business["a"]), Branch(name="Disabled", city="Test", empresa_id=business["a"], is_active=False)])
        db.commit()
        disabled = db.query(Branch).filter_by(empresa_id=business["a"], is_active=False).one().id
    assert client.patch(f"/api/branches/{disabled}", json={"is_active": True}, headers=business["ha"]).status_code == 409


def test_ml_trains_evaluates_and_uses_only_company_inventory(client, business):
    assert client.post('/api/analitica/entrenar', headers=business['hc']).status_code == 403
    response = client.post('/api/analitica/entrenar', headers=business['ha'])
    assert response.status_code == 200, response.text
    metrics = response.json()['metricas']
    assert metrics['muestras_entrenamiento'] == 384
    assert metrics['muestras_validacion'] == 96
    assert 0 < metrics['mae'] < 5 and 0.5 < metrics['r2'] <= 1
    assert -1 <= metrics['silhouette'] <= 1
    result = client.get('/api/analitica/dashboard', headers=business['ha'])
    assert result.status_code == 200, result.text
    data = result.json()
    assert data['entrenado'] is True and len(data['prediccion_demanda']) == 1
    assert all(p['sku'] != f"BB-" for p in data['prediccion_demanda'])
    assert client.get('/api/analitica/dashboard', headers=business['hb']).json()['entrenado'] is False


def test_reservation_purchase_releases_unselected_items_without_double_discount(client, business):
    response = client.post('/api/reservations', headers=business['hc'], json={
        'branch_id': business['branch_id'], 'items': [{'variant_id': business['variant_id'], 'quantity': 5}]})
    assert response.status_code == 201, response.text
    rid = response.json()['id']
    response = client.post(f'/api/reservations/{rid}/checkout', headers=business['ha'],
        json={'items': [{'variant_id': business['variant_id'], 'quantity': 2}]})
    assert response.status_code == 201, response.text
    assert response.json()['total'] == 240
    with SessionLocal() as db:
        assert db.query(Inventory).filter_by(branch_id=business['branch_id']).one().available == 8
    assert client.post(f'/api/reservations/{rid}/checkout', headers=business['ha'],
        json={'items': [{'variant_id': business['variant_id'], 'quantity': 2}]}).status_code == 409


def test_finish_fitting_without_purchase_releases_reserved_stock(client, business):
    reservation = client.post('/api/reservations', headers=business['hc'], json={
        'branch_id': business['branch_id'], 'items': [{'variant_id': business['variant_id'], 'quantity': 3}]}).json()
    rid = reservation['id']
    assert client.patch(f'/api/reservations/{rid}/attend', headers=business['ha']).status_code == 200
    assert client.post(f'/api/reservations/{rid}/finish', headers=business['ha']).status_code == 200
    with SessionLocal() as db:
        assert db.query(Inventory).filter_by(branch_id=business['branch_id']).one().available == 10


def test_exchange_limits_returns_and_preserves_stock(client, business):
    sale = client.post('/api/pos/sale', headers=business['ha'], json={
        'branch_id': business['branch_id'], 'items': [{'variant_id': business['variant_id'], 'quantity': 2}]}).json()
    body = {'order_item_id': sale['items'][0]['id'], 'replacement_variant_id': business['variant_id'], 'quantity': 2, 'cash_difference': 0}
    path = f"/api/orders/{sale['id']}/exchanges"
    assert client.post(path, headers=business['hb'], json=body).status_code == 404
    result = client.post(path, headers=business['ha'], json=body)
    assert result.status_code == 201, result.text
    assert result.json()['monto_diferencia'] == 0
    assert client.post(path, headers=business['ha'], json=body).status_code == 409
    with SessionLocal() as db:
        assert db.query(Inventory).filter_by(branch_id=business['branch_id']).one().available == 8
    cancelled=client.patch(f"/api/orders/{sale['id']}/status", headers=business['ha'], json={'status': 'CANCELADO'})
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()['net_total'] == 0
    assert cancelled.json()['payment']['status'] == 'REEMBOLSADO'


def test_exchange_expired_purchase_is_rejected(client, business):
    sale = client.post('/api/pos/sale', headers=business['ha'], json={
        'branch_id': business['branch_id'], 'items': [{'variant_id': business['variant_id'], 'quantity': 1}]}).json()
    with SessionLocal() as db:
        db.get(Order, sale['id']).created_at = datetime.now() - timedelta(days=20)
        db.commit()
    result = client.post(f"/api/orders/{sale['id']}/exchanges", headers=business['ha'], json={
        'order_item_id': sale['items'][0]['id'], 'replacement_variant_id': business['variant_id'], 'quantity': 1})
    assert result.status_code == 409


def test_customer_can_sync_reservation_and_rejected_operation_stays_rejected(client, business):
    op = operation(business, tipo_operacion='RESERVA', usuario_id=business['customer'], cliente_id=business['customer'])
    result = client.post('/api/sync', json={'operaciones': [op]}, headers=business['hc'])
    assert result.status_code == 200 and result.json()['resultados'][0]['estado'] == 'CONFIRMADA', result.text
    bad = operation(business, forma_pago='TARJETA')
    assert client.post('/api/sync', json={'operaciones': [bad]}, headers=business['ha']).json()['resultados'][0]['estado'] == 'RECHAZADA'
    bad['forma_pago'] = 'EFECTIVO'
    assert client.post('/api/sync', json={'operaciones': [bad]}, headers=business['ha']).json()['resultados'][0]['estado'] == 'RECHAZADA'


@pytest.mark.parametrize('question,kind', [('top 5 productos vendidos','TOP_PRODUCTOS_VENDIDOS'), ('ingresos por categoria','INGRESOS_POR_CATEGORIA'),
    ('ventas por semana','VENTAS_POR_SEMANA'), ('reservas por estado','RESERVAS_POR_ESTADO')])
def test_additional_report_types_use_real_data(client, business, question, kind):
    sale = client.post('/api/pos/sale', headers=business['ha'], json={
        'branch_id': business['branch_id'], 'items': [{'variant_id': business['variant_id'], 'quantity': 1}]})
    assert sale.status_code == 201, sale.text
    result = client.post('/api/reportes/ia', json={'pregunta_natural':question}, headers=business['ha'])
    assert result.status_code == 200, result.text
    assert result.json()['tipo_reporte'] == kind
    if kind != 'RESERVAS_POR_ESTADO':
        assert len(result.json()['filas']) == 1

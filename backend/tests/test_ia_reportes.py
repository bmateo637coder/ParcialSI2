import uuid
from datetime import date, timedelta

import pytest

from app.core.database import SessionLocal
from app.core.security import create_access_token, hash_password
from app.models.branch import Branch
from app.models.commerce import Order, OrderItem
from app.models.tenant import Empresa, Plan, Suscripcion
from app.models.user import Role, User


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def ia_catalog(catalog):
    uid = uuid.uuid4().hex[:8]
    with SessionLocal() as db:
        empresa = Empresa(
            razon_social=f"Empresa IA {uid}",
            nit=f"IA-{uid}",
            is_active=True,
        )
        db.add(empresa)
        db.flush()

        plan = Plan(
            nombre=f"PROFESIONAL-{uid}",
            permite_reportes_ia=True,
            permite_analitica_ml=True,
            is_active=True,
        )
        db.add(plan)
        db.flush()
        db.add(
            Suscripcion(
                empresa_id=empresa.id,
                plan_id=plan.id,
                fecha_inicio=date.today(),
                fecha_vencimiento=date.today() + timedelta(days=30),
                estado="ACTIVA",
            )
        )

        branch = db.query(Branch).filter(Branch.id == catalog["branch_id"]).first()
        branch.empresa_id = empresa.id

        role = db.query(Role).filter(Role.name == "Administrador").first()
        admin = User(
            first_name="Admin",
            last_name="IA",
            email=f"admin_ia_{uid}@test.com",
            hashed_password=hash_password("admin123"),
            is_active=True,
            role_id=role.id,
            empresa_id=empresa.id,
        )
        db.add(admin)
        db.flush()
        token = create_access_token(subject=admin.email, role="Administrador")

        order = Order(
            empresa_id=empresa.id,
            client_id=admin.id,
            user_id=admin.id,
            branch_id=branch.id,
            order_type="PRESENCIAL",
            status="PAGADO",
            subtotal=240.0,
            total=240.0,
        )
        db.add(order)
        db.flush()
        db.add(
            OrderItem(
                order_id=order.id,
                variant_id=catalog["variant_id"],
                quantity=2,
                unit_price=120.0,
                discount=0.0,
            )
        )

        otra = Empresa(
            razon_social=f"Otra Empresa {uid}",
            nit=f"OTRA-{uid}",
            is_active=True,
        )
        db.add(otra)
        db.flush()
        otra_branch = Branch(
            name=f"Sucursal Otra {uid}",
            city="Otra City",
            address="Calle 2",
            phone="+591 1111 1111",
            is_active=True,
            empresa_id=otra.id,
        )
        db.add(otra_branch)
        db.flush()
        db.add(
            Order(
                empresa_id=otra.id,
                client_id=admin.id,
                user_id=admin.id,
                branch_id=otra_branch.id,
                order_type="PRESENCIAL",
                status="PAGADO",
                subtotal=999.0,
                total=999.0,
            )
        )
        db.commit()

        return {
            **catalog,
            "empresa_id": empresa.id,
            "branch_name": branch.name,
            "admin_token": token,
        }


def test_ia_sales_report_uses_tenant_data(client, ia_catalog):
    res = client.post(
        "/api/reportes/ia",
        json={"pregunta_natural": "ventas por sucursal"},
        headers=_headers(ia_catalog["admin_token"]),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["tipo_reporte"] == "VENTAS_POR_SUCURSAL"
    assert body["empresa_id"] == ia_catalog["empresa_id"]
    assert body["filas"][0]["sucursal"] == ia_catalog["branch_name"]
    assert body["filas"][0]["total_ventas"] == 240.0
    assert len(body["filas"]) == 1


def test_ia_inventory_report_uses_available_stock(client, ia_catalog):
    res = client.post(
        "/api/reportes/ia",
        json={"pregunta_natural": "productos con stock bajo"},
        headers=_headers(ia_catalog["admin_token"]),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["tipo_reporte"] == "INVENTARIO_BAJO"
    row = next(r for r in body["filas"] if r["sku"].startswith("TEST-"))
    assert row["cantidad"] == 10


def test_ia_export_is_downloadable(client, ia_catalog):
    generated = client.post("/api/reportes/ia", json={"pregunta_natural": "ventas por sucursal"}, headers=_headers(ia_catalog["admin_token"]))
    res = client.post(
        "/api/reportes/ia/export",
        json={"solicitud_id": generated.json()["solicitud_id"], "formato": "excel"},
        headers=_headers(ia_catalog["admin_token"]),
    )
    assert res.status_code == 200, res.text
    url = res.json()["archivo_url"]

    assert client.get(url).status_code == 401
    download = client.get(url, headers=_headers(ia_catalog["admin_token"]))
    assert download.status_code == 200
    assert len(download.content) > 0


@pytest.mark.parametrize('phrase,limit', [
    ('cinco productos más vendidos', 5), ('las diez prendas más vendidas', 10),
    ('top veinticinco productos vendidos', 25), ('los treinta y dos productos más vendidos', 32),
])
def test_report_understands_written_quantities(client, ia_catalog, phrase, limit):
    response = client.post('/api/reportes/ia', json={'pregunta_natural': phrase}, headers=_headers(ia_catalog['admin_token']))
    assert response.status_code == 200, response.text
    assert response.json()['filtros_aplicados']['limite'] == limit
    assert response.json()['tipo_reporte'] == 'TOP_PRODUCTOS_VENDIDOS'


@pytest.mark.parametrize('phrase,start,end', [
    ('ventas de septiembre a octubre de 2026', '2026-09-01', '2026-10-31'),
    ('ventas desde diciembre de 2025 hasta enero de 2026', '2025-12-01', '2026-01-31'),
    ('ventas de 2026-09-10 a 2026-09-25', '2026-09-10', '2026-09-25'),
])
def test_report_understands_explicit_periods(client, ia_catalog, phrase, start, end):
    response = client.post('/api/reportes/ia', json={'pregunta_natural': phrase}, headers=_headers(ia_catalog['admin_token']))
    assert response.status_code == 200, response.text
    assert response.json()['filtros_aplicados']['fecha_desde'] == start
    assert response.json()['filtros_aplicados']['fecha_hasta'] == end


@pytest.mark.parametrize('phrase', [
    'ventas de septiembre u octubre de 2026', 'ventas y reservas',
    'top cinco o diez productos más vendidos', 'cero productos más vendidos',
    'ventas de los últimos cero días', 'ventas en sucursal "Inexistente"',
])
def test_report_requests_clarification_instead_of_silently_ignoring_ambiguity(client, ia_catalog, phrase):
    response = client.post('/api/reportes/ia', json={'pregunta_natural': phrase}, headers=_headers(ia_catalog['admin_token']))
    assert response.status_code == 422, response.text


def test_products_are_ranked_by_quantity_sold_instead_of_price(client, ia_catalog):
    from app.models.catalog import Product, ProductVariant
    with SessionLocal() as db:
        product = Product(empresa_id=ia_catalog['empresa_id'], name='Prenda económica', base_price=10)
        db.add(product); db.flush()
        original = db.get(ProductVariant, ia_catalog['variant_id'])
        variant = ProductVariant(product_id=product.id, size_id=original.size_id, color_id=original.color_id,
            sku='CHEAP-' + uuid.uuid4().hex, price=10)
        db.add(variant); db.flush()
        admin = db.query(User).filter_by(empresa_id=ia_catalog['empresa_id']).first()
        order = Order(empresa_id=ia_catalog['empresa_id'], client_id=admin.id,
            branch_id=ia_catalog['branch_id'], order_type='PRESENCIAL', status='PAGADO', total=30)
        db.add(order); db.flush()
        db.add(OrderItem(order_id=order.id, variant_id=variant.id, quantity=3, unit_price=10, discount=0)); db.commit()
    response = client.post('/api/reportes/ia', json={'pregunta_natural': 'el producto más vendido', 'filtros': {'limite': 1}}, headers=_headers(ia_catalog['admin_token']))
    assert response.status_code == 200, response.text
    assert response.json()['filas'][0]['producto'] == 'Prenda económica'
    assert response.json()['filas'][0]['cantidad_vendida'] == 3

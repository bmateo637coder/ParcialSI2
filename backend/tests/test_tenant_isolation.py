"""Aislamiento multitenant (CU4/CU5 modificados y CU27/CU30).

Cada empresa solo debe ver y administrar sus propios recursos. Estos tests
crean dos tenants independientes y verifican que un administrador de una
empresa no pueda leer ni modificar datos de la otra.
"""

from datetime import date, timedelta

import pytest
from conftest import subscribe_empresa

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.branch import Branch
from app.models.catalog import Category, Color, Product, ProductVariant, Size
from app.models.inventory import Inventory
from app.models.tenant import Empresa, Plan, Suscripcion
from app.models.user import Role, User


def _login(client, email, password):
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture(scope="module")
def tenants(client):
    with SessionLocal() as db:
        role = db.query(Role).filter(Role.name == "Administrador").first()

        empresa_a = Empresa(razon_social="Tenant A", nit="NIT-A-001")
        empresa_b = Empresa(razon_social="Tenant B", nit="NIT-B-001")
        db.add_all([empresa_a, empresa_b])
        db.flush()
        subscribe_empresa(db, empresa_a.id)
        subscribe_empresa(db, empresa_b.id)

        admin_a = User(
            empresa_id=empresa_a.id,
            first_name="Admin",
            last_name="A",
            email="admin.a@tenant.example.com",
            hashed_password=hash_password("tenant123"),
            role_id=role.id,
            is_active=True,
        )
        admin_b = User(
            empresa_id=empresa_b.id,
            first_name="Admin",
            last_name="B",
            email="admin.b@tenant.example.com",
            hashed_password=hash_password("tenant123"),
            role_id=role.id,
            is_active=True,
        )
        db.add_all([admin_a, admin_b])
        db.commit()

        return {
            "empresa_a": empresa_a.id,
            "empresa_b": empresa_b.id,
            "admin_a": admin_a.id,
            "admin_b": admin_b.id,
        }


@pytest.fixture(scope="module")
def headers_a(client, tenants):
    return _login(client, "admin.a@tenant.example.com", "tenant123")


@pytest.fixture(scope="module")
def headers_b(client, tenants):
    return _login(client, "admin.b@tenant.example.com", "tenant123")


def test_platform_endpoints_block_tenant_admin(client, headers_a):
    res = client.get("/api/plataforma/empresas", headers=headers_a)
    assert res.status_code == 403


def test_branches_are_isolated(client, headers_a, headers_b):
    created = client.post(
        "/api/branches/",
        json={"name": "Sucursal A", "city": "La Paz"},
        headers=headers_a,
    )
    assert created.status_code == 201, created.text
    branch_id = created.json()["id"]

    seen_by_b = {b["id"] for b in client.get("/api/branches/", headers=headers_b).json()}
    assert branch_id not in seen_by_b

    assert client.patch(
        f"/api/branches/{branch_id}", json={"phone": "+591 1"}, headers=headers_b
    ).status_code == 404
    assert client.delete(f"/api/branches/{branch_id}", headers=headers_b).status_code == 404


def test_users_are_isolated_and_bound_to_empresa(client, headers_a, headers_b, tenants):
    roles = client.get("/api/users/roles", headers=headers_a).json()
    cajero = next(r for r in roles if r["name"] == "Cajero")

    created = client.post(
        "/api/users/",
        json={
            "first_name": "Cajero",
            "last_name": "A",
            "email": "cajero.a@tenant.example.com",
            "password": "tenant123",
            "role_id": cajero["id"],
        },
        headers=headers_a,
    )
    assert created.status_code == 201, created.text

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "cajero.a@tenant.example.com").first()
        assert user.empresa_id == tenants["empresa_a"]

    visible_to_b = {
        u["email"] for u in client.get("/api/users/?q=cajero.a", headers=headers_b).json()
    }
    assert "cajero.a@tenant.example.com" not in visible_to_b

    user_id = created.json()["id"]
    assert client.patch(
        f"/api/users/{user_id}", json={"phone": "+591 2"}, headers=headers_b
    ).status_code == 404
    assert client.delete(f"/api/users/{user_id}", headers=headers_b).status_code == 404


def test_products_and_variants_are_isolated(client, headers_a, headers_b):
    category = client.post(
        "/api/products/catalog/categories",
        json={"name": "Categoria A", "description": "A"},
        headers=headers_a,
    )
    assert category.status_code == 201, category.text

    created = client.post(
        "/api/products/",
        json={
            "name": "Prenda A",
            "description": "Solo tenant A",
            "base_price": 50,
            "category_id": category.json()["id"],
        },
        headers=headers_a,
    )
    assert created.status_code == 201, created.text
    product_id = created.json()["id"]

    visible_to_b = {p["id"] for p in client.get("/api/products/", headers=headers_b).json()}
    assert product_id not in visible_to_b

    assert client.patch(
        f"/api/products/{product_id}", json={"base_price": 1}, headers=headers_b
    ).status_code == 404
    assert client.delete(f"/api/products/{product_id}", headers=headers_b).status_code == 404

    created_variant = client.post(
        f"/api/products/{product_id}/variants",
        json={"size_id": 1, "color_id": 1, "sku": "TENANT-A-SKU", "price": 55},
        headers=headers_a,
    )
    assert created_variant.status_code in (201, 400)
    if created_variant.status_code == 201:
        variant_id = created_variant.json()["id"]
        assert client.patch(
            f"/api/products/variants/{variant_id}",
            json={"price": 1},
            headers=headers_b,
        ).status_code == 404


def test_inventory_is_isolated(client, headers_a, headers_b, tenants):
    with SessionLocal() as db:
        category = Category(name="Inv Cat", description="A", empresa_id=tenants["empresa_a"])
        db.add(category)
        db.flush()
        product = Product(
            name="Inv Product",
            base_price=10,
            category_id=category.id,
            empresa_id=tenants["empresa_a"],
        )
        db.add(product)
        db.flush()
        size = db.query(Size).first() or Size(name="M")
        color = db.query(Color).first() or Color(name="Negro")
        db.add_all([size, color])
        db.flush()
        variant = ProductVariant(
            product_id=product.id,
            size_id=size.id,
            color_id=color.id,
            sku="INV-A-SKU",
            price=10,
        )
        branch = Branch(name="Inv Branch A", city="La Paz", empresa_id=tenants["empresa_a"])
        db.add_all([variant, branch])
        db.flush()
        inventory = Inventory(variant_id=variant.id, branch_id=branch.id, available=5)
        db.add(inventory)
        db.commit()
        inventory_id = inventory.id
        variant_id = variant.id
        branch_id = branch.id

    listed = {row["id"] for row in client.get("/api/inventory/", headers=headers_b).json()}
    assert inventory_id not in listed

    assert client.patch(
        f"/api/inventory/{inventory_id}", json={"available": 0}, headers=headers_b
    ).status_code == 404

    res = client.post(
        "/api/inventory/",
        json={"variant_id": variant_id, "branch_id": branch_id, "available": 1},
        headers=headers_b,
    )
    assert res.status_code in (400, 403, 404)


def test_branch_limit_is_enforced(client, tenants):
    with SessionLocal() as db:
        role = db.query(Role).filter(Role.name == "Administrador").first()
        plan = Plan(
            nombre="LIMITADO",
            max_sucursales=1,
            permite_reportes_ia=False,
            permite_analitica_ml=False,
        )
        db.add(plan)
        db.flush()
        empresa = Empresa(razon_social="Tenant Limite", nit="NIT-LIMITE-001")
        db.add(empresa)
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
        admin = User(
            empresa_id=empresa.id,
            first_name="Admin",
            last_name="Limite",
            email="admin.limite@tenant.example.com",
            hashed_password=hash_password("tenant123"),
            role_id=role.id,
            is_active=True,
        )
        db.add(admin)
        db.commit()

    headers = _login(client, "admin.limite@tenant.example.com", "tenant123")
    first = client.post(
        "/api/branches/", json={"name": "Unica", "city": "La Paz"}, headers=headers
    )
    assert first.status_code == 201, first.text

    second = client.post(
        "/api/branches/", json={"name": "Excedida", "city": "La Paz"}, headers=headers
    )
    assert second.status_code == 409

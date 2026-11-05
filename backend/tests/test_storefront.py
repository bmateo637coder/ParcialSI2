"""El escaparate público muestra una tienda sin habilitar acceso empresarial."""
from datetime import date, timedelta

import pytest

from conftest import subscribe_empresa
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.branch import Branch
from app.models.catalog import Category, Color, Product, ProductVariant, Provider, Size
from app.models.inventory import Inventory
from app.models.tenant import Empresa, Suscripcion
from app.models.user import Role, User


@pytest.fixture(scope="module")
def storefronts(client):
    with SessionLocal() as db:
        stores = [Empresa(razon_social=f"Escaparate {label}", nit=f"PUBLIC-{label}") for label in ("A", "B")]
        db.add_all(stores)
        db.flush()
        for store in stores:
            subscribe_empresa(db, store.id)
        size, color = Size(name="PUBLIC-M"), Color(name="PUBLIC-Azul")
        db.add_all([size, color])
        db.flush()
        result = []
        for i, store in enumerate(stores):
            category = Category(empresa_id=store.id, name=f"Prendas {i}")
            provider = Provider(empresa_id=store.id, name=f"Proveedor privado {i}", nit=f"PRIVATE-{i}")
            branch = Branch(empresa_id=store.id, name=f"Local {i}", city="La Paz")
            db.add_all([category, provider, branch])
            db.flush()
            product = Product(empresa_id=store.id, name=f"Prenda pública {i}", base_price=100, category_id=category.id, provider_id=provider.id)
            hidden = Product(empresa_id=store.id, name=f"Prenda retirada {i}", base_price=200, category_id=category.id, is_active=False)
            db.add_all([product, hidden])
            db.flush()
            variant = ProductVariant(product_id=product.id, size_id=size.id, color_id=color.id, sku=f"PUBLIC-{i}")
            db.add(variant)
            db.flush()
            db.add(Inventory(variant_id=variant.id, branch_id=branch.id, available=7 + i))
            result.append(dict(id=store.id, product=product.id, hidden=hidden.id, category=category.id, branch=branch.id, variant=variant.id))
        role = db.query(Role).filter_by(name="Administrador").first()
        db.add(User(empresa_id=stores[0].id, email="storefront-admin@test.example", first_name="Admin", last_name="A", hashed_password=hash_password("storefront123"), role_id=role.id))
        db.commit()
    login = client.post("/api/auth/login", json={"email": "storefront-admin@test.example", "password": "storefront123"})
    assert login.status_code == 200
    return result, {"Authorization": "Bearer " + login.json()["access_token"]}


def test_public_catalog_requires_explicit_store(client, storefronts):
    stores, _ = storefronts
    products = {row["id"] for row in client.get("/api/products/").json()}
    branches = {row["id"] for row in client.get("/api/branches/").json()}
    for store in stores:
        assert store["product"] not in products
        assert store["branch"] not in branches


def test_public_catalog_and_stock_belong_to_selected_store(client, storefronts):
    stores, _ = storefronts
    for i, store in enumerate(stores):
        params = {"empresa_id": store["id"], "include_inactive": "true"}
        products = client.get("/api/products/", params=params).json()
        assert [row["id"] for row in products] == [store["product"]]
        assert products[0]["provider"] is None
        assert products[0]["provider_id"] is None
        categories = client.get("/api/products/metadata/categories", params=params).json()
        assert [(row["id"], row["products_count"]) for row in categories] == [(store["category"], 1)]
        branches = client.get("/api/branches/", params=params).json()
        assert [row["id"] for row in branches] == [store["branch"]]
        variants = client.get(f"/api/products/{store['product']}/variants", params=params).json()
        assert [(row["id"], row["stock"]) for row in variants] == [(store["variant"], 7 + i)]
        availability = client.get("/api/inventory/availability", params=params).json()
        assert [(row["product_id"], row["branch_id"], row["available"]) for row in availability] == [(store["product"], store["branch"], 7 + i)]


def test_public_details_cannot_mix_stores_or_show_retired_products(client, storefronts):
    stores, _ = storefronts
    a, b = stores
    for path in (f"/api/products/{b['product']}", f"/api/products/{b['product']}/variants", f"/api/branches/{b['branch']}", f"/api/products/{a['hidden']}", f"/api/products/{a['hidden']}/variants"):
        response = client.get(path, params={"empresa_id": a["id"], "include_inactive": "true"})
        assert response.status_code == 404, response.text
    response = client.get(f"/api/products/{a['product']}", params={"empresa_id": a["id"]})
    assert response.status_code == 200
    assert response.json()["provider"] is None


def test_logged_in_user_cannot_override_company_with_public_parameter(client, storefronts):
    stores, headers = storefronts
    for path in ("/api/products/", "/api/branches/", "/api/products/metadata/categories", "/api/inventory/availability"):
        assert client.get(path, params={"empresa_id": stores[1]["id"]}, headers=headers).status_code == 404
    rows = client.get("/api/products/", headers=headers).json()
    assert stores[0]["product"] in {row["id"] for row in rows}
    assert stores[1]["product"] not in {row["id"] for row in rows}


def test_public_selection_does_not_authorize_writes(client, storefronts):
    stores, _ = storefronts
    response = client.post("/api/products/", params={"empresa_id": stores[0]["id"]}, json={"name": "No autorizado", "base_price": 1})
    assert response.status_code == 401
    assert client.get("/api/inventory/", params={"empresa_id": stores[0]["id"]}).status_code == 401


def test_expired_store_is_not_available(client, storefronts):
    stores, _ = storefronts
    store_id = stores[0]["id"]
    with SessionLocal() as db:
        subscription = db.query(Suscripcion).filter_by(empresa_id=store_id).one()
        original = subscription.fecha_vencimiento
        subscription.fecha_vencimiento = date.today() - timedelta(days=1)
        db.commit()
    try:
        assert client.get("/api/products/", params={"empresa_id": store_id}).status_code == 404
        assert store_id not in {row["id"] for row in client.get("/api/plataforma/tiendas").json()}
    finally:
        with SessionLocal() as db:
            db.query(Suscripcion).filter_by(empresa_id=store_id).one().fecha_vencimiento = original
            db.commit()

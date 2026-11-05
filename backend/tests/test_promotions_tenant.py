import uuid
from conftest import subscribe_empresa

from app.core.database import SessionLocal
from app.core.security import create_access_token, hash_password
from app.models.catalog import Category, Color, Product, ProductVariant, Size
from app.models.tenant import Empresa
from app.models.user import Role, User
from app.services.promotions import promotion_discount_for_variant


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _tenant_admin(db, uid, suffix):
    empresa = Empresa(
        razon_social=f"Empresa {suffix} {uid}",
        nit=f"{suffix}-{uid}",
        is_active=True,
    )
    db.add(empresa)
    db.flush()
    subscribe_empresa(db, empresa.id)
    role = db.query(Role).filter(Role.name == "Administrador").first()
    admin = User(
        first_name="Admin",
        last_name=suffix,
        email=f"admin_{suffix}_{uid}@test.com",
        hashed_password=hash_password("admin123"),
        is_active=True,
        role_id=role.id,
        empresa_id=empresa.id,
    )
    db.add(admin)
    db.flush()
    token = create_access_token(subject=admin.email, role="Administrador")
    return empresa, admin, token


def test_promotions_are_isolated_per_tenant(client):
    uid = uuid.uuid4().hex[:8]
    with SessionLocal() as db:
        empresa_a, _, token_a = _tenant_admin(db, uid, "a")
        empresa_b, _, token_b = _tenant_admin(db, uid, "b")

        category_a = Category(name=f"Categoria A {uid}", empresa_id=empresa_a.id)
        db.add(category_a)
        db.flush()
        product_a = Product(name=f"Producto A {uid}", base_price=100.0,
                            category_id=category_a.id, is_active=True)

        category_b = Category(name=f"Categoria B {uid}", empresa_id=empresa_b.id)
        db.add(category_b)
        db.flush()
        product_b = Product(name=f"Producto B {uid}", base_price=100.0,
                            category_id=category_b.id, is_active=True)
        db.add_all([product_a, product_b])
        db.commit()
        empresa_a_id = empresa_a.id
        product_a_id = product_a.id
        category_b_id = category_b.id
        product_b_id = product_b.id

    promo_a = client.post(
        "/api/promotions/",
        json={"name": "Promo A", "discount_type": "PERCENTAGE", "value": 10,
              "target_type": "GLOBAL", "is_active": True},
        headers=_headers(token_a),
    )
    assert promo_a.status_code == 201, promo_a.text
    assert promo_a.json()["empresa_id"] == empresa_a_id

    promo_b = client.post(
        "/api/promotions/",
        json={"name": "Promo B", "discount_type": "PERCENTAGE", "value": 25,
              "target_type": "GLOBAL", "is_active": True},
        headers=_headers(token_b),
    )
    assert promo_b.status_code == 201, promo_b.text

    list_a = client.get("/api/promotions/", headers=_headers(token_a))
    assert list_a.status_code == 200, list_a.text
    ids_a = {p["id"] for p in list_a.json()}
    assert promo_a.json()["id"] in ids_a
    assert promo_b.json()["id"] not in ids_a

    cross = client.patch(
        f"/api/promotions/{promo_b.json()['id']}",
        json={"value": 50},
        headers=_headers(token_a),
    )
    assert cross.status_code == 404

    cross_product = client.post(
        "/api/promotions/",
        json={"name": "Promo cruzada", "discount_type": "PERCENTAGE", "value": 10,
              "target_type": "PRODUCT", "target_id": product_b_id, "is_active": True},
        headers=_headers(token_a),
    )
    assert cross_product.status_code == 404

    cross_category = client.post(
        "/api/promotions/",
        json={"name": "Promo categoría cruzada", "discount_type": "PERCENTAGE",
              "value": 10, "target_type": "CATEGORY", "target_id": category_b_id,
              "is_active": True},
        headers=_headers(token_a),
    )
    assert cross_category.status_code == 404

    with SessionLocal() as db:
        size = Size(name=f"Talla {uid}")
        color = Color(name=f"Color {uid}")
        db.add_all([size, color])
        db.flush()
        variant = ProductVariant(
            product_id=product_a_id,
            size_id=size.id,
            color_id=color.id,
            sku=f"TENANT-{uid}",
            price=100.0,
            is_active=True,
        )
        db.add(variant)
        db.commit()
        db.refresh(variant)
        promo_id, discount = promotion_discount_for_variant(db, variant)
        assert promo_id == promo_a.json()["id"]
        assert discount == 10.0

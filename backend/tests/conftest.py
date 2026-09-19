"""Configuración de tests: base de datos temporal aislada."""

import os
import tempfile

_TEST_DB = os.path.join(tempfile.gettempdir(), "fashionstore_test.db")
if os.path.exists(_TEST_DB):
    os.remove(_TEST_DB)

os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB}"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["BACKEND_CORS_ORIGINS"] = '["http://localhost:4200"]'

import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.models.user import Role, User
from main import app


def _seed_users(db):
    roles = {
        "Administrador": "Test",
        "Cliente": "Test",
        "Cajero": "Test",
        "Encargado de Sucursal": "Test",
        "Proveedor": "Test",
    }
    objs = []
    for name, desc in roles.items():
        objs.append(Role(name=name, description=desc))
    db.add_all(objs)
    db.flush()
    role = {r.name: r.id for r in objs}

    db.add(User(first_name="Admin", last_name="Test", email="admin@test.com",
                hashed_password=hash_password("admin123"), is_active=True, role_id=role["Administrador"]))
    db.add(User(first_name="Juan", last_name="Perez", email="cliente@test.com",
                hashed_password=hash_password("cliente123"), is_active=True, role_id=role["Cliente"]))
    db.add(User(first_name="Ana", last_name="Cajera", email="cajero@test.com",
                hashed_password=hash_password("cajero123"), is_active=True, role_id=role["Cajero"]))
    db.add(User(first_name="Luis", last_name="Encargado", email="encargado@test.com",
                hashed_password=hash_password("encargado123"), is_active=True, role_id=role["Encargado de Sucursal"]))
    db.add(User(first_name="Pedro", last_name="Proveedor", email="proveedor@test.com",
                hashed_password=hash_password("proveedor123"), is_active=True, role_id=role["Proveedor"]))
    db.commit()


@pytest.fixture(scope="session")
def client():
    from app.core.database import SessionLocal

    with SessionLocal() as db:
        _seed_users(db)

    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def admin_token(client):
    res = client.post("/api/auth/login", json={"email": "admin@test.com", "password": "admin123"})
    assert res.status_code == 200
    return res.json()["access_token"]


@pytest.fixture(scope="session")
def client_token(client):
    res = client.post("/api/auth/login", json={"email": "cliente@test.com", "password": "cliente123"})
    assert res.status_code == 200
    return res.json()["access_token"]


@pytest.fixture(scope="session")
def cajero_token(client):
    res = client.post("/api/auth/login", json={"email": "cajero@test.com", "password": "cajero123"})
    assert res.status_code == 200
    return res.json()["access_token"]


@pytest.fixture(scope="session")
def encargado_token(client):
    res = client.post("/api/auth/login", json={"email": "encargado@test.com", "password": "encargado123"})
    assert res.status_code == 200
    return res.json()["access_token"]


@pytest.fixture(scope="session")
def provider_token(client):
    res = client.post("/api/auth/login", json={"email": "proveedor@test.com", "password": "proveedor123"})
    assert res.status_code == 200
    return res.json()["access_token"]


@pytest.fixture()
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture()
def cajero_headers(cajero_token):
    return {"Authorization": f"Bearer {cajero_token}"}


@pytest.fixture()
def encargado_headers(encargado_token):
    return {"Authorization": f"Bearer {encargado_token}"}


@pytest.fixture()
def catalog(client):
    """Catálogo mínimo con inventario para ejercitar CU11/CU13/CU16 en la BD de prueba.
    Datos maestros reutilizados, producto/sucursal únicos por test para mantener aislamiento."""
    import uuid

    from app.core.database import SessionLocal
    from app.models.branch import Branch
    from app.models.catalog import Category, Color, Product, ProductVariant, Season, Size
    from app.models.inventory import Inventory, InventoryMovement
    from app.models.user import User

    uid = uuid.uuid4().hex[:8]

    with SessionLocal() as db:
        season = db.query(Season).filter(Season.name == "Test 2026").first()
        if season is None:
            season = Season(name="Test 2026", year=2026)
            db.add(season)
            db.flush()
        category = db.query(Category).filter(Category.name == "Prueba").first()
        if category is None:
            category = Category(name="Prueba")
            db.add(category)
            db.flush()
        size = db.query(Size).filter(Size.name == "M").first()
        if size is None:
            size = Size(name="M")
            db.add(size)
            db.flush()
        color = db.query(Color).filter(Color.name == "Negro").first()
        if color is None:
            color = Color(name="Negro")
            db.add(color)
            db.flush()

        branch = Branch(name=f"Sucursal Test {uid}", city="Prueba City",
                        address="Calle 1", phone="+591 0000 0000", is_active=True)
        db.add(branch)
        db.flush()

        product = Product(name=f"Prenda Test {uid}", description="Para pruebas", base_price=100.0,
                          category_id=category.id, season_id=season.id)
        db.add(product)
        db.flush()

        variant = ProductVariant(product_id=product.id, size_id=size.id, color_id=color.id,
                                 sku=f"TEST-{uid}", price=120.0, is_active=True)
        db.add(variant)
        db.flush()

        inv = Inventory(variant_id=variant.id, branch_id=branch.id, available=10)
        db.add(inv)
        db.flush()
        admin = db.query(User).filter(User.email == "admin@test.com").first()
        db.add(InventoryMovement(inventory_id=inv.id, movement_type="INGRESO",
                                 quantity=10, reason="Stock inicial", user_id=admin.id))
        db.commit()

        return {
            "variant_id": variant.id,
            "product_id": product.id,
            "branch_id": branch.id,
            "category_id": product.category_id or category.id,
            "stock": 10,
        }
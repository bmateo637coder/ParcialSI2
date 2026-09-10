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
    admin_role = Role(name="Administrador", description="Test")
    client_role = Role(name="Cliente", description="Test")
    db.add_all([admin_role, client_role])
    db.flush()

    db.add(User(first_name="Admin", last_name="Test", email="admin@test.com",
               hashed_password=hash_password("admin123"), is_active=True, role_id=admin_role.id))
    db.add(User(first_name="Juan", last_name="Perez", email="cliente@test.com",
               hashed_password=hash_password("cliente123"), is_active=True, role_id=client_role.id))
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


@pytest.fixture()
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}
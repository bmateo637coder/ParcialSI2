def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_register_and_login(client):
    payload = {
        "first_name": "Ana",
        "last_name": "Torres",
        "email": "ana@test.com",
        "password": "secreta123",
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 201
    body = res.json()
    assert body["email"] == "ana@test.com"
    assert body["role_name"] == "Cliente"
    assert "password" not in body

    res = client.post("/api/auth/login", json={"email": "ana@test.com", "password": "secreta123"})
    assert res.status_code == 200
    assert res.json()["role"] == "Cliente"
    assert res.json()["token_type"] == "bearer"


def test_register_duplicate_conflict(client):
    payload = {
        "first_name": "Ana",
        "last_name": "Torres",
        "email": "ana@test.com",
        "password": "secreta123",
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 409


def test_register_invalid_email(client):
    res = client.post(
        "/api/auth/register",
        json={"first_name": "X", "last_name": "Y", "email": "no-es-correo", "password": "123456"},
    )
    assert res.status_code == 422


def test_login_wrong_password(client):
    res = client.post(
        "/api/auth/login", json={"email": "admin@test.com", "password": "incorrecta"}
    )
    assert res.status_code == 401


def test_me_requires_token(client):
    res = client.get("/api/auth/me")
    assert res.status_code == 401


def test_me_returns_profile(client, auth_headers):
    res = client.get("/api/auth/me", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["email"] == "admin@test.com"
    assert body["role_name"] == "Administrador"


def test_me_update_profile(client, auth_headers):
    res = client.patch("/api/auth/me", json={"first_name": "Administradora"}, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["first_name"] == "Administradora"
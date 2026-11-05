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


def test_password_reset_token_is_single_use_and_cannot_access_api(client):
    import uuid
    email = f"reset-{uuid.uuid4().hex}@test.com"
    assert client.post('/api/auth/register', json={
        'first_name': 'Reset', 'last_name': 'Test', 'email': email,
        'password': 'before123',
    }).status_code == 201
    response = client.post('/api/auth/forgot-password', json={'email': email})
    assert response.status_code == 200
    token = response.json()['reset_token']
    assert client.get('/api/auth/me', headers={'Authorization': f'Bearer {token}'}).status_code == 401
    payload = {'token': token, 'new_password': 'after123'}
    assert client.post('/api/auth/reset-password', json=payload).status_code == 200
    assert client.post('/api/auth/reset-password', json=payload).status_code == 400
    assert client.post('/api/auth/login', json={'email': email, 'password': 'after123'}).status_code == 200


def test_reset_without_email_configuration_does_not_expose_token(client, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, 'ALLOW_DEMO_PASSWORD_RESET', False)
    monkeypatch.setattr(settings, 'SMTP_HOST', '')
    response = client.post('/api/auth/forgot-password', json={'email': 'admin@test.com'})
    assert response.status_code == 503
    assert 'reset_token' not in response.json()

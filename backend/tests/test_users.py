"""Tests de administración de usuarios y roles (CU4)."""


def test_list_roles_requires_admin(client, client_token):
    headers = {"Authorization": f"Bearer {client_token}"}
    res = client.get("/api/users/roles", headers=headers)
    assert res.status_code == 403


def test_list_roles(client, auth_headers):
    res = client.get("/api/users/roles", headers=auth_headers)
    assert res.status_code == 200
    names = {r["name"] for r in res.json()}
    assert {"Administrador", "Cliente", "Cajero", "Encargado de Sucursal"} <= names


def test_list_users_filters(client, auth_headers):
    res = client.get("/api/users/?q=Juan", headers=auth_headers)
    assert res.status_code == 200
    assert any(u["email"] == "cliente@test.com" for u in res.json())


def test_list_users_role_filter(client, auth_headers):
    roles = client.get("/api/users/roles", headers=auth_headers).json()
    cliente_role = next(r for r in roles if r["name"] == "Cliente")
    res = client.get(f"/api/users/?role_id={cliente_role['id']}", headers=auth_headers)
    assert res.status_code == 200
    assert all(u["role_id"] == cliente_role["id"] for u in res.json())


def test_create_user(client, auth_headers):
    roles = client.get("/api/users/roles", headers=auth_headers).json()
    cajero_role = next(r for r in roles if r["name"] == "Cajero")

    res = client.post(
        "/api/users/",
        json={
            "first_name": "Nuevo",
            "last_name": "Cajero",
            "email": "nuevo@test.com",
            "password": "segura123",
            "phone": "+591 700 000 100",
            "role_id": cajero_role["id"],
        },
        headers=auth_headers,
    )
    assert res.status_code == 201
    assert res.json()["phone"] == "+591 700 000 100"
    assert res.json()["role_id"] == cajero_role["id"]
    assert "hashed_password" not in res.json()


def test_create_user_duplicate(client, auth_headers):
    roles = client.get("/api/users/roles", headers=auth_headers).json()
    cliente_role = next(r for r in roles if r["name"] == "Cliente")
    res = client.post(
        "/api/users/",
        json={"first_name": "X", "last_name": "Y", "email": "cliente@test.com",
              "password": "cliente123", "role_id": cliente_role["id"]},
        headers=auth_headers,
    )
    assert res.status_code == 409


def test_create_user_invalid_role(client, auth_headers):
    res = client.post(
        "/api/users/",
        json={"first_name": "X", "last_name": "Y", "email": "x@test.com",
              "password": "cliente123", "role_id": 99999},
        headers=auth_headers,
    )
    assert res.status_code == 400


def test_update_user_fields(client, auth_headers):
    user = client.get("/api/users/?q=cliente@test.com", headers=auth_headers).json()[0]
    res = client.patch(
        f"/api/users/{user['id']}",
        json={"phone": "+591 777 888 999", "last_name": "Actualizado"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    assert res.json()["phone"] == "+591 777 888 999"
    assert res.json()["last_name"] == "Actualizado"


def test_update_user_requires_admin(client, client_token, auth_headers):
    user = client.get("/api/users/?q=cliente@test.com", headers=auth_headers).json()[0]
    headers = {"Authorization": f"Bearer {client_token}"}
    res = client.patch(f"/api/users/{user['id']}", json={"phone": "x"}, headers=headers)
    assert res.status_code == 403


def test_deactivate_user_soft_delete(client, auth_headers):
    roles = client.get("/api/users/roles", headers=auth_headers).json()
    cliente_role = next(r for r in roles if r["name"] == "Cliente")
    created = client.post(
        "/api/users/",
        json={"first_name": "Tmp", "last_name": "User", "email": "tmp@test.com",
              "password": "tmp123", "role_id": cliente_role["id"]},
        headers=auth_headers,
    ).json()

    res = client.delete(f"/api/users/{created['id']}", headers=auth_headers)
    assert res.status_code == 204

    detail = client.get(f"/api/users/{created['id']}", headers=auth_headers).json()
    assert detail["is_active"] is False


def test_admin_cannot_deactivate_self(client, auth_headers, admin_token):
    admin = client.get("/api/users/?q=admin@test.com", headers=auth_headers).json()[0]
    res = client.delete(f"/api/users/{admin['id']}", headers=auth_headers)
    assert res.status_code == 400


def test_get_missing_user_404(client, auth_headers):
    assert client.get("/api/users/999999", headers=auth_headers).status_code == 404


def test_admin_cannot_change_own_role(client, auth_headers, admin_token):
    admin = client.get("/api/auth/me", headers=auth_headers).json()
    roles = client.get("/api/users/roles", headers=auth_headers).json()
    cliente_role = next(r for r in roles if r["name"] == "Cliente")

    res = client.patch(f"/api/users/{admin['id']}", json={"role_id": cliente_role["id"]}, headers=auth_headers)
    assert res.status_code == 400


def test_admin_cannot_deactivate_self_via_patch(client, auth_headers, admin_token):
    admin = client.get("/api/auth/me", headers=auth_headers).json()
    res = client.patch(f"/api/users/{admin['id']}", json={"is_active": False}, headers=auth_headers)
    assert res.status_code == 400


def test_admin_can_update_own_last_name(client, auth_headers):
    admin = client.get("/api/auth/me", headers=auth_headers).json()
    res = client.patch(f"/api/users/{admin['id']}", json={"last_name": "AdminActualizado"}, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["last_name"] == "AdminActualizado"
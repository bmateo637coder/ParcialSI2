"""Tests del portal Proveedor (API).

Cubre el inicio de sesión del usuario con rol Proveedor, la consulta del
perfil/empresa, la gestión de la disponibilidad de sus productos, el envío de
propuestas de producto y el flujo de aprobación/rechazo por parte del administrador.

Los tests crean los datos (usuarios, empresas, productos) exclusivamente a
través de la API existente, sin importar los modelos nuevos.
"""

import pytest


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _admin_setup(client, admin_token: str, tag: str) -> dict:
    roles = client.get("/api/users/roles", headers=_h(admin_token)).json()
    prov_role_id = next(r["id"] for r in roles if r["name"] == "Proveedor")

    res = client.post("/api/products/catalog/providers",
                      json={"name": f"Empresa {tag}", "nit": f"9000-{tag}"},
                      headers=_h(admin_token))
    assert res.status_code == 201, res.text
    provider = res.json()

    email = f"prov.{tag}@test.com"
    res2 = client.post("/api/users/", json={
        "first_name": "Prov", "last_name": tag, "email": email,
        "password": "proveedor123", "role_id": prov_role_id,
    }, headers=_h(admin_token))
    assert res2.status_code == 201, res2.text
    user = res2.json()

    res3 = client.post("/api/providers/accounts", json={
        "user_id": user["id"], "provider_id": provider["id"],
    }, headers=_h(admin_token))
    assert res3.status_code == 201, res3.text

    login = client.post("/api/auth/login",
                        json={"email": email, "password": "proveedor123"})
    assert login.status_code == 200
    return {
        "provider_id": provider["id"],
        "user_id": user["id"],
        "token": login.json()["access_token"],
    }


def _create_product(client, admin_token: str, provider_id: int, tag: str) -> int:
    res = client.post("/api/products/", json={
        "name": f"Telar {tag}", "base_price": 300.0, "provider_id": provider_id,
    }, headers=_h(admin_token))
    assert res.status_code == 201, res.text
    return res.json()["id"]


# ======================================================================
# ACCESO Y PERFIL
# ======================================================================


def test_provider_me_returns_company(client, admin_token, client_token):
    prov = _admin_setup(client, admin_token, tag="me")
    res = client.get("/api/providers/me", headers=_h(prov["token"]))
    assert res.status_code == 200
    body = res.json()
    assert body["provider"]["id"] == prov["provider_id"]
    assert body["user"]["email"] == f"prov.me@test.com"
    assert body["role"] == "Proveedor"


def test_client_cannot_access_provider_portal(client, client_token):
    res = client.get("/api/providers/me", headers=_h(client_token))
    assert res.status_code == 403


def test_account_linking_requires_admin(client, admin_token):
    prov = _admin_setup(client, admin_token, tag="link")
    res = client.post("/api/providers/accounts",
                      json={"user_id": prov["user_id"], "provider_id": prov["provider_id"]},
                      headers=_h(prov["token"]))
    assert res.status_code == 403


# ======================================================================
# PRODUCTOS: SOLO LOS PROPIOS, SOLO SU DISPONIBILIDAD
# ======================================================================


def test_provider_sees_only_own_products(client, admin_token):
    p1 = _admin_setup(client, admin_token, tag="soloA")
    p2 = _admin_setup(client, admin_token, tag="soloB")
    own = _create_product(client, admin_token, p1["provider_id"], "soloA")
    _create_product(client, admin_token, p2["provider_id"], "soloB")

    res = client.get("/api/providers/products", headers=_h(p1["token"]))
    assert res.status_code == 200
    assert any(p["id"] == own for p in res.json())
    assert all(p["provider_id"] == p1["provider_id"] for p in res.json())


def test_provider_cannot_toggle_other_provider_product(client, admin_token):
    p1 = _admin_setup(client, admin_token, tag="togA")
    p2 = _admin_setup(client, admin_token, tag="togB")
    other = _create_product(client, admin_token, p2["provider_id"], "togB")

    res = client.patch(f"/api/providers/products/{other}",
                       json={"is_active": False}, headers=_h(p1["token"]))
    assert res.status_code == 403


def test_provider_updates_own_product_availability(client, admin_token):
    prov = _admin_setup(client, admin_token, tag="disp")
    product = _create_product(client, admin_token, prov["provider_id"], "disp")

    res = client.patch(f"/api/providers/products/{product}",
                       json={"is_active": False}, headers=_h(prov["token"]))
    assert res.status_code == 200
    assert res.json()["is_active"] is False

    mine = client.get("/api/providers/products", headers=_h(prov["token"])).json()
    assert any(p["id"] == product and p["is_active"] is False for p in mine)


# ======================================================================
# PROPUESTAS DE PRODUCTO Y APROBACIÓN ADMIN
# ======================================================================


def test_provider_submits_and_sees_own_proposals(client, admin_token):
    prov = _admin_setup(client, admin_token, tag="prop")
    res = client.post("/api/providers/products", json={
        "name": "Sillón Propuesto", "description": "Propuesta",
        "base_price": 1200.0,
    }, headers=_h(prov["token"]))
    assert res.status_code == 201, res.text
    proposal = res.json()
    assert proposal["status"] == "PENDIENTE"

    mine = client.get("/api/providers/proposals", headers=_h(prov["token"])).json()
    assert any(x["id"] == proposal["id"] for x in mine)


def test_admin_approves_proposal_and_product_is_created(client, admin_token):
    prov = _admin_setup(client, admin_token, tag="aprob")
    proposal = client.post("/api/providers/products", json={
        "name": "Vaso Aprobado", "description": "Aprobado", "base_price": 55.0,
    }, headers=_h(prov["token"])).json()

    all_props = client.get("/api/providers/proposals", headers=_h(admin_token)).json()
    assert any(p["id"] == proposal["id"] for p in all_props)

    res = client.patch(f"/api/providers/proposals/{proposal['id']}/approve",
                       json={"admin_comment": "OK"}, headers=_h(admin_token))
    assert res.status_code == 200
    assert res.json()["status"] == "APROBADA"

    products = client.get(f"/api/products?provider_id={prov['provider_id']}",
                          headers=_h(admin_token)).json()
    assert any(p["name"] == "Vaso Aprobado" for p in products)


def test_admin_rejects_proposal_and_no_product_is_created(client, admin_token):
    prov = _admin_setup(client, admin_token, tag="recha")
    proposal = client.post("/api/providers/products", json={
        "name": "Plato Rechazado", "description": "Rechazado", "base_price": 10.0,
    }, headers=_h(prov["token"])).json()

    res = client.patch(f"/api/providers/proposals/{proposal['id']}/reject",
                       json={"admin_comment": "Mala calidad"}, headers=_h(admin_token))
    assert res.status_code == 200
    assert res.json()["status"] == "RECHAZADA"

    products = client.get(f"/api/products?provider_id={prov['provider_id']}",
                          headers=_h(admin_token)).json()
    assert not any(p["name"] == "Plato Rechazado" for p in products)


def test_provider_cannot_approve_own_proposal(client, admin_token):
    prov = _admin_setup(client, admin_token, tag="noaprob")
    proposal = client.post("/api/providers/products", json={
        "name": "Autoaprobación", "description": "No", "base_price": 5.0,
    }, headers=_h(prov["token"])).json()

    res = client.patch(f"/api/providers/proposals/{proposal['id']}/approve",
                       json={}, headers=_h(prov["token"]))
    assert res.status_code == 403
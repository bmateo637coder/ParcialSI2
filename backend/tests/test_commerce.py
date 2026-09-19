"""Tests de carrito (CU16), reservas (CU13-15), pedidos y notificaciones."""

import pytest


@pytest.fixture(autouse=True)
def clean_client_cart(client, client_token):
    """El carrito del cliente persiste entre tests; se limpia antes de cada uno."""
    yield
    client.delete("/api/cart", headers=_client_headers(client_token))


# ======================================================================
# CARRITO (CU16)
# ======================================================================


def _client_headers(client_token):
    return {"Authorization": f"Bearer {client_token}"}


def test_cart_add_and_summary(client, client_token, catalog):
    headers = _client_headers(client_token)
    res = client.post("/api/cart", json={"variant_id": catalog["variant_id"], "quantity": 2}, headers=headers)
    assert res.status_code == 201
    body = res.json()
    assert body["total_items"] == 2
    assert body["total_amount"] == 240.0
    assert body["items"][0]["variant_id"] == catalog["variant_id"]


def test_cart_accumulates_same_variant(client, client_token, catalog):
    headers = _client_headers(client_token)
    client.post("/api/cart", json={"variant_id": catalog["variant_id"], "quantity": 2}, headers=headers)
    res = client.post("/api/cart", json={"variant_id": catalog["variant_id"], "quantity": 3}, headers=headers)
    assert res.json()["total_items"] == 5


def test_cart_update_and_remove(client, client_token, catalog):
    headers = _client_headers(client_token)
    item = client.post("/api/cart", json={"variant_id": catalog["variant_id"], "quantity": 1}, headers=headers).json()["items"][0]

    res = client.patch(f"/api/cart/{item['id']}", json={"quantity": 4}, headers=headers)
    assert res.json()["total_items"] == 4

    res = client.delete(f"/api/cart/{item['id']}", headers=headers)
    assert res.json()["total_items"] == 0


def test_cart_clear(client, client_token, catalog):
    headers = _client_headers(client_token)
    client.post("/api/cart", json={"variant_id": catalog["variant_id"], "quantity": 1}, headers=headers)
    res = client.delete("/api/cart", headers=headers)
    assert res.json()["total_items"] == 0
    assert res.json()["items"] == []


def test_cart_requires_auth(client):
    assert client.get("/api/cart").status_code == 401


def test_cart_invalid_variant(client, client_token):
    headers = _client_headers(client_token)
    res = client.post("/api/cart", json={"variant_id": 999999, "quantity": 1}, headers=headers)
    assert res.status_code == 404


def test_cart_isolation_between_clients(client, client_token, admin_token, catalog):
    client.post("/api/cart", json={"variant_id": catalog["variant_id"], "quantity": 1},
                headers=_client_headers(client_token))
    mine = client.get("/api/cart", headers=_client_headers(client_token)).json()
    other = client.get("/api/cart", headers=_client_headers(admin_token)).json()
    assert mine["total_items"] == 1
    assert other["total_items"] == 0


# ======================================================================
# RESERVAS (CU13, CU14, CU15)
# ======================================================================


def test_create_reservation_and_reduce_stock(client, client_token, catalog):
    headers = _client_headers(client_token)
    res = client.post(
        "/api/reservations",
        json={"branch_id": catalog["branch_id"], "items": [{"variant_id": catalog["variant_id"], "quantity": 2}]},
        headers=headers,
    )
    assert res.status_code == 201
    r = res.json()
    assert r["status"] == "PENDIENTE"
    assert r["total"] == 240.0
    assert r["item_count"] == 2
    assert r["code"].startswith("RSV-")

    availability = client.get(f"/api/inventory/availability?branch_id={catalog['branch_id']}").json()
    row = next(x for x in availability if x["variant_id"] == catalog["variant_id"])
    assert row["available"] == 8


def test_create_reservation_insufficient_stock(client, client_token, catalog):
    headers = _client_headers(client_token)
    res = client.post(
        "/api/reservations",
        json={"branch_id": catalog["branch_id"], "items": [{"variant_id": catalog["variant_id"], "quantity": 999}]},
        headers=headers,
    )
    assert res.status_code == 409


def test_list_own_reservations(client, client_token, catalog):
    headers = _client_headers(client_token)
    client.post(
        "/api/reservations",
        json={"branch_id": catalog["branch_id"], "items": [{"variant_id": catalog["variant_id"], "quantity": 1}]},
        headers=headers,
    )
    res = client.get("/api/reservations", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_staff_can_list_all_reservations(client, encargado_token, client_token, catalog):
    client.post(
        "/api/reservations",
        json={"branch_id": catalog["branch_id"], "items": [{"variant_id": catalog["variant_id"], "quantity": 1}]},
        headers=_client_headers(client_token),
    )
    total = client.get("/api/reservations", headers=_client_headers(client_token)).json()
    all_rows = client.get("/api/reservations?all_reservations=true",
                          headers=_client_headers(encargado_token)).json()
    assert len(all_rows) >= len(total)


def test_attend_reservation_direct(client, client_token, encargado_token, cajero_token, catalog):
    res = client.post(
        "/api/reservations",
        json={"branch_id": catalog["branch_id"], "items": [{"variant_id": catalog["variant_id"], "quantity": 1}]},
        headers=_client_headers(client_token),
    ).json()
    res_id = res["id"]

    attended = client.patch(f"/api/reservations/{res_id}/attend", headers=_client_headers(cajero_token)).json()
    assert attended["status"] == "ATENDIDA"
    assert attended["attend_date"] is not None


def test_cancel_reservation_releases_stock(client, client_token, catalog):
    headers = _client_headers(client_token)
    r = client.post(
        "/api/reservations",
        json={"branch_id": catalog["branch_id"], "items": [{"variant_id": catalog["variant_id"], "quantity": 3}]},
        headers=headers,
    ).json()

    cancelled = client.patch(f"/api/reservations/{r['id']}/cancel", headers=headers).json()
    assert cancelled["status"] == "CANCELADA"

    availability = client.get(f"/api/inventory/availability?branch_id={catalog['branch_id']}").json()
    row = next(x for x in availability if x["variant_id"] == catalog["variant_id"])
    assert row["available"] == 10


def test_attend_then_cancel_rejected(client, client_token, encargado_token, catalog):
    r = client.post(
        "/api/reservations",
        json={"branch_id": catalog["branch_id"], "items": [{"variant_id": catalog["variant_id"], "quantity": 1}]},
        headers=_client_headers(client_token),
    ).json()
    client.patch(f"/api/reservations/{r['id']}/attend", headers=_client_headers(encargado_token))

    res = client.patch(f"/api/reservations/{r['id']}/cancel", headers=_client_headers(client_token))
    assert res.status_code == 400


def test_client_cannot_attend_reservation(client, client_token, catalog):
    r = client.post(
        "/api/reservations",
        json={"branch_id": catalog["branch_id"], "items": [{"variant_id": catalog["variant_id"], "quantity": 1}]},
        headers=_client_headers(client_token),
    ).json()
    res = client.patch(f"/api/reservations/{r['id']}/attend", headers=_client_headers(client_token))
    assert res.status_code == 403


def test_attend_expired_reservation_rejected(client, client_token, encargado_token, catalog):
    from datetime import datetime, timedelta

    from app.core.database import SessionLocal
    from app.models.commerce import Reservation

    r = client.post(
        "/api/reservations",
        json={"branch_id": catalog["branch_id"], "items": [{"variant_id": catalog["variant_id"], "quantity": 1}]},
        headers=_client_headers(client_token),
    ).json()

    with SessionLocal() as db:
        row = db.get(Reservation, r["id"])
        row.expiration_date = datetime.now() - timedelta(hours=1)
        db.commit()

    res = client.patch(f"/api/reservations/{r['id']}/attend", headers=_client_headers(encargado_token))
    assert res.status_code == 400
    assert "venció" in res.json()["detail"]

    detail = client.get(f"/api/reservations/{r['id']}", headers=_client_headers(client_token)).json()
    assert detail["status"] == "VENCIDA"

    availability = client.get(f"/api/inventory/availability?branch_id={catalog['branch_id']}").json()
    inv_row = next(x for x in availability if x["variant_id"] == catalog["variant_id"])
    assert inv_row["available"] == 10  # stock liberado al vencer


# ======================================================================
# PEDIDOS Y NOTIFICACIONES (CU16)
# ======================================================================


def test_checkout_from_cart(client, client_token, catalog):
    headers = _client_headers(client_token)
    client.post("/api/cart", json={"variant_id": catalog["variant_id"], "quantity": 2}, headers=headers)

    res = client.post(
        "/api/orders/checkout",
        json={"order_type": "DIGITAL", "branch_id": catalog["branch_id"], "payment_method": "TARJETA"},
        headers=headers,
    )
    assert res.status_code == 201
    order = res.json()
    assert order["status"] == "PAGADO"
    assert order["total"] == 240.0
    assert order["payment"]["status"] == "COMPLETADO"

    cart = client.get("/api/cart", headers=headers).json()
    assert cart["total_items"] == 0  # carrito vaciado tras el pedido


def test_checkout_requires_inventory(client, client_token, catalog):
    headers = _client_headers(client_token)
    client.post("/api/cart", json={"variant_id": catalog["variant_id"], "quantity": 999}, headers=headers)
    res = client.post(
        "/api/orders/checkout",
        json={"order_type": "DIGITAL", "branch_id": catalog["branch_id"], "payment_method": "TARJETA"},
        headers=headers,
    )
    assert res.status_code == 409


def test_checkout_empty_cart(client, client_token):
    headers = _client_headers(client_token)
    res = client.post("/api/orders/checkout", json={"order_type": "DIGITAL", "payment_method": "TARJETA"}, headers=headers)
    assert res.status_code == 400


def test_pos_presencial_requires_staff(client, client_token, catalog):
    res = client.post(
        "/api/orders/checkout",
        json={"order_type": "PRESENCIAL", "branch_id": catalog["branch_id"],
              "items": [{"variant_id": catalog["variant_id"], "quantity": 1}], "payment_method": "EFECTIVO"},
        headers=_client_headers(client_token),
    )
    assert res.status_code == 403


def test_list_orders_staff_sees_all(client, client_token, encargado_token, catalog):
    client.post(
        "/api/cart", json={"variant_id": catalog["variant_id"], "quantity": 1}, headers=_client_headers(client_token))
    client.post("/api/orders/checkout", json={"order_type": "DIGITAL", "branch_id": catalog["branch_id"],
                                              "payment_method": "TARJETA"}, headers=_client_headers(client_token))

    mine = client.get("/api/orders", headers=_client_headers(client_token)).json()
    all_orders = client.get("/api/orders", headers=_client_headers(encargado_token)).json()
    assert len(all_orders) >= len(mine)


def test_notifications_created_and_read(client, client_token, catalog):
    headers = _client_headers(client_token)
    client.post(
        "/api/reservations",
        json={"branch_id": catalog["branch_id"], "items": [{"variant_id": catalog["variant_id"], "quantity": 1}]},
        headers=headers,
    )
    notes = client.get("/api/notifications", headers=headers).json()
    assert len(notes) >= 1
    assert any("Reserva" in n["title"] for n in notes)

    first = next(n for n in notes if not n["is_read"])
    res = client.patch(f"/api/notifications/{first['id']}/read", headers=headers)
    assert res.status_code == 200
    assert res.json()["is_read"] is True


def test_unread_notification_requires_owner(client, client_token, cajero_token):
    notes = client.get("/api/notifications", headers=_client_headers(client_token)).json()
    if notes:
        res = client.patch(f"/api/notifications/{notes[0]['id']}/read", headers=_client_headers(cajero_token))
        assert res.status_code == 404


def test_expire_stale_reservations(client, cajero_token, client_token, catalog):
    from datetime import datetime, timedelta

    from app.core.database import SessionLocal
    from app.models.commerce import Reservation

    headers = _client_headers(client_token)
    r = client.post(
        "/api/reservations",
        json={"branch_id": catalog["branch_id"], "items": [{"variant_id": catalog["variant_id"], "quantity": 2}]},
        headers=headers,
    ).json()

    with SessionLocal() as db:
        row = db.get(Reservation, r["id"])
        row.expiration_date = datetime.now() - timedelta(hours=1)
        db.commit()

    res = client.post("/api/reservations/expire-stale", headers=_client_headers(cajero_token))
    assert res.status_code == 200
    assert res.json()["expired"] >= 1

    detail = client.get(f"/api/reservations/{r['id']}", headers=headers).json()
    assert detail["status"] == "VENCIDA"

    availability = client.get(f"/api/inventory/availability?branch_id={catalog['branch_id']}").json()
    inv_row = next(x for x in availability if x["variant_id"] == catalog["variant_id"])
    assert inv_row["available"] == 10  # stock liberado


def test_order_valid_transitions_and_terminal_reject(client, client_token, encargado_token, catalog):
    headers = _client_headers(client_token)
    client.post("/api/cart", json={"variant_id": catalog["variant_id"], "quantity": 1}, headers=headers)
    order = client.post(
        "/api/orders/checkout",
        json={"order_type": "DIGITAL", "branch_id": catalog["branch_id"], "payment_method": "TARJETA"},
        headers=headers,
    ).json()
    oid = order["id"]
    staff = _client_headers(encargado_token)

    assert client.patch(f"/api/orders/{oid}/status", json={"status": "ENVIADO"}, headers=staff).json()["status"] == "ENVIADO"
    assert client.patch(f"/api/orders/{oid}/status", json={"status": "ENTREGADO"}, headers=staff).json()["status"] == "ENTREGADO"

    res = client.patch(f"/api/orders/{oid}/status", json={"status": "CANCELADO"}, headers=staff)
    assert res.status_code == 400


def test_order_cancel_restores_stock(client, client_token, encargado_token, catalog):
    headers = _client_headers(client_token)
    client.post("/api/cart", json={"variant_id": catalog["variant_id"], "quantity": 2}, headers=headers)
    order = client.post(
        "/api/orders/checkout",
        json={"order_type": "DIGITAL", "branch_id": catalog["branch_id"], "payment_method": "TARJETA"},
        headers=headers,
    ).json()

    res = client.patch(f"/api/orders/{order['id']}/status", json={"status": "CANCELADO"},
                       headers=_client_headers(encargado_token))
    assert res.status_code == 200
    assert res.json()["status"] == "CANCELADO"

    availability = client.get(f"/api/inventory/availability?branch_id={catalog['branch_id']}").json()
    inv_row = next(x for x in availability if x["variant_id"] == catalog["variant_id"])
    assert inv_row["available"] == 10  # stock restaurado al cancelar
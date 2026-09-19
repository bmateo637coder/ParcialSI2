"""Tests Ciclo 4:

CU24 — Generar reporte por comando de voz (extensión)
CU25 — Consultar reportes y dashboards (indicadores: ventas, inventario, reservas)
CU26 — Consultar historial de compras
"""

from datetime import datetime, timezone

import pytest


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _add_to_cart(client, token: str, variant_id: int, qty: int = 1) -> None:
    client.post("/api/cart", json={"variant_id": variant_id, "quantity": qty}, headers=_h(token))


def _make_paid_order(client, token: str, catalog: dict, qty: int = 1, order_type: str = "DIGITAL") -> int:
    """Crea un pedido PAGADO: checkout TRANSFERENCIA (cliente) o venta POS EFECTIVO (staff)."""
    if order_type == "PRESENCIAL":
        res = client.post(
            "/api/pos/sale",
            json={"branch_id": catalog["branch_id"],
                  "items": [{"variant_id": catalog["variant_id"], "quantity": qty}],
                  "payment_method": "EFECTIVO"},
            headers=_h(token),
        )
        assert res.status_code == 201, res.text
        return res.json()["id"]
    _add_to_cart(client, token, catalog["variant_id"], qty)
    res = client.post("/api/orders/checkout",
                      json={"order_type": "DIGITAL", "payment_method": "TRANSFERENCIA"},
                      headers=_h(token))
    assert res.status_code == 201, res.text
    return res.json()["id"]


def _make_reservation(client, token: str, catalog: dict, qty: int = 1) -> int:
    res = client.post(
        "/api/reservations",
        json={"branch_id": catalog["branch_id"], "items": [{"variant_id": catalog["variant_id"], "quantity": qty}]},
        headers=_h(token),
    )
    assert res.status_code == 201
    return res.json()["id"]


@pytest.fixture(autouse=True)
def _clean_cart(client, client_token):
    yield
    client.delete("/api/cart", headers=_h(client_token))


# ======================================================================
# CU25 — CONSULTAR REPORTES Y DASHBOARDS
# ======================================================================


def test_dashboard_admin_returns_indicators(client, admin_token, cajero_token, client_token, catalog):
    # Los tests comparten la BD de la sesión: se mide la línea base y se valida el delta.
    base = client.get("/api/reports/dashboard", headers=_h(admin_token)).json()["kpis"]
    _make_paid_order(client, client_token, catalog, qty=2, order_type="DIGITAL")
    _make_reservation(client, client_token, catalog, qty=1)

    res = client.get("/api/reports/dashboard", headers=_h(admin_token))
    assert res.status_code == 200
    body = res.json()
    assert body["empty"] is False
    kpis = body["kpis"]
    assert kpis["total_orders"] == base["total_orders"] + 1
    assert kpis["total_sales"] == round(base["total_sales"] + 240.0, 2)
    assert kpis["reservations"] == base["reservations"] + 1
    assert kpis["total_units_available"] >= 0
    assert kpis["low_stock_variants"] >= 0
    assert len(body["sales_series"]) >= 1
    assert any(c["category_name"] for c in body["by_category"])
    assert body["top_products"]
    assert all(tp["product_id"] is not None and tp["units"] >= 0 for tp in body["top_products"])


def test_dashboard_accessible_by_encargado_not_client(client, encargado_token, client_token):
    res_enc = client.get("/api/reports/dashboard", headers=_h(encargado_token))
    assert res_enc.status_code == 200
    res_cli = client.get("/api/reports/dashboard", headers=_h(client_token))
    assert res_cli.status_code == 403


def test_dashboard_filters_by_branch(client, admin_token, cajero_token, catalog):
    _make_paid_order(client, cajero_token, catalog, qty=1, order_type="PRESENCIAL")

    res = client.get(f"/api/reports/dashboard?branch_id={catalog['branch_id']}", headers=_h(admin_token))
    assert res.json()["kpis"]["total_orders"] == 1

    other = client.get("/api/reports/dashboard?branch_id=999999", headers=_h(admin_token))
    assert other.json()["kpis"]["total_orders"] == 0


def test_dashboard_insufficient_data_marks_empty(client, admin_token):
    res = client.get(
        "/api/reports/dashboard?desde=2000-01-01&hasta=2000-01-31",
        headers=_h(admin_token),
    )
    assert res.status_code == 200
    body = res.json()
    assert body["empty"] is True
    assert body["kpis"]["total_orders"] == 0
    assert body["kpis"]["reservations"] == 0


def test_dashboard_category_filter(client, admin_token, client_token, catalog):
    _make_paid_order(client, client_token, catalog, qty=3, order_type="DIGITAL")

    res = client.get(f"/api/reports/dashboard?category_id={catalog['category_id']}", headers=_h(admin_token))
    assert res.status_code == 200
    # Los tests comparten la BD de la sesión; puede haber pedidos previos de la misma categoría.
    assert res.json()["kpis"]["total_orders"] >= 1
    assert any(c["category_id"] == catalog["category_id"] for c in res.json()["by_category"])

    miss = client.get("/api/reports/dashboard?category_id=999999", headers=_h(admin_token))
    assert miss.json()["kpis"]["total_orders"] == 0


def test_dashboard_invalid_date_rejected(client, admin_token):
    res = client.get("/api/reports/dashboard?desde=not-a-date", headers=_h(admin_token))
    assert res.status_code == 422


# ======================================================================
# CU24 — GENERAR REPORTE POR COMANDO DE VOZ
# ======================================================================


def test_voice_command_ventas_recognized_and_returns_data(client, admin_token, client_token, catalog):
    _make_paid_order(client, client_token, catalog, qty=1, order_type="DIGITAL")

    res = client.post("/api/reports/voice", json={"command": "generar reporte de ventas"}, headers=_h(admin_token))
    assert res.status_code == 200
    body = res.json()
    assert body["recognized"] is True
    assert body["intent"]["report_type"] == "VENTAS"
    assert body["data"] is not None
    assert body["data"]["kpis"]["total_orders"] >= 1
    assert body["data"]["sales_series"]


def test_voice_command_inventario_detects_branch(client, admin_token, catalog):
    branches = client.get("/api/branches/", headers=_h(admin_token)).json()
    branch = next(b for b in branches if b["id"] == catalog["branch_id"])

    res = client.post(
        "/api/reports/voice",
        json={"command": f"quiero el reporte de inventario de la {branch['name']}"},
        headers=_h(admin_token),
    )
    assert res.status_code == 200
    body = res.json()
    assert body["recognized"] is True
    assert body["intent"]["report_type"] == "INVENTARIO"
    assert body["intent"]["branch_id"] == catalog["branch_id"]
    assert body["data"]["kpis"]["total_units_available"] >= 0


def test_voice_command_reservas_semana_sets_period(client, admin_token):
    res = client.post("/api/reports/voice", json={"command": "muéstrame las reservas de la semana"}, headers=_h(admin_token))
    assert res.status_code == 200
    intent = res.json()["intent"]
    assert intent["report_type"] == "RESERVAS"
    assert intent["date_from"] is not None
    assert intent["date_to"] is not None


def test_voice_command_hoy_sets_single_day(client, admin_token):
    res = client.post("/api/reports/voice", json={"command": "ventas de hoy"}, headers=_h(admin_token))
    intent = res.json()["intent"]
    assert intent["report_type"] == "VENTAS"
    utc_today = datetime.now(timezone.utc).date().isoformat()
    assert intent["date_from"] == intent["date_to"] == utc_today


def test_voice_command_unrecognized_returns_helpful_error(client, admin_token):
    res = client.post("/api/reports/voice", json={"command": "hola buenos días"}, headers=_h(admin_token))
    assert res.status_code == 200
    body = res.json()
    assert body["recognized"] is False
    assert body["data"] is None
    assert "repetir" in body["message"].lower() or "panel" in body["message"].lower()


def test_voice_command_requires_staff(client, client_token):
    res = client.post("/api/reports/voice", json={"command": "reporte de ventas"}, headers=_h(client_token))
    assert res.status_code == 403


# ======================================================================
# CU26 — CONSULTAR HISTORIAL DE COMPRAS
# ======================================================================


def test_history_lists_own_orders_with_item_detail(client, client_token, cajero_token, catalog):
    order_id = _make_paid_order(client, client_token, catalog, qty=2, order_type="DIGITAL")
    # La venta presencial de caja queda registrada a nombre de un cliente "mostrador":
    # jamás debe filtrarse al historial de este cliente.
    client.post(
        "/api/pos/sale",
        json={"branch_id": catalog["branch_id"], "items": [{"variant_id": catalog["variant_id"], "quantity": 1}],
              "payment_method": "EFECTIVO"},
        headers=_h(cajero_token),
    )

    res = client.get("/api/orders", headers=_h(client_token))
    assert res.status_code == 200
    orders = res.json()
    digi = [o for o in orders if o["order_type"] == "DIGITAL"]
    # Los tests comparten la BD de la sesión: solo interesa validar que el pedido creado
    # aquí se lista con su detalle y que ninguna venta POS de "mostrador" se filtra.
    assert any(o["id"] == order_id for o in digi)
    assert not any(o["client_name"] == "Cliente Mostrador" for o in orders)
    order = next(o for o in digi if o["id"] == order_id)
    assert order["total"] > 0
    assert order["created_at"] is not None
    assert order["items"]
    item = order["items"][0]
    assert item["product_id"] == catalog["product_id"]
    assert item["unit_price"] is not None
    assert item["subtotal"] is not None
    # La venta presencial del mostrador no aparece en el historial del cliente
    assert all(o["order_type"] != "PRESENCIAL" for o in orders)


def test_history_does_not_leak_other_clients_orders(client, client_token, cajero_token, catalog):
    # Un segundo cliente sin actividad no debe ver los pedidos del primero
    res = client.post("/api/auth/register", json={
        "first_name": "Nuevo", "last_name": "Cliente", "email": "nuevo.cliente.ci4@test.com",
        "password": "cliente123",
    })
    assert res.status_code == 201
    login = client.post("/api/auth/login", json={"email": "nuevo.cliente.ci4@test.com", "password": "cliente123"})
    token = login.json()["access_token"]

    _make_paid_order(client, client_token, catalog, qty=1, order_type="DIGITAL")

    res2 = client.get("/api/orders", headers=_h(token))
    assert res2.status_code == 200
    assert res2.json() == []


def test_history_empty_state_for_new_client(client):
    res = client.post("/api/auth/register", json={
        "first_name": "Vacío", "last_name": "Cliente", "email": "vacio.cliente.ci4@test.com",
        "password": "cliente123",
    })
    assert res.status_code == 201
    login = client.post("/api/auth/login", json={"email": "vacio.cliente.ci4@test.com", "password": "cliente123"})
    token = login.json()["access_token"]

    res = client.get("/api/orders", headers=_h(token))
    assert res.status_code == 200
    assert res.json() == []
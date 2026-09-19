"""Tests de los reportes por voz GENERATIVOS (narrativa natural en español).

El endpoint de voz debe devolver, además de los datos, una narrativa en texto
natural que resuma la situación del negocio; el dashboard GET no la incluye.
"""

import pytest


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _make_order(client, token: str, catalog: dict) -> int:
    client.post("/api/cart", json={"variant_id": catalog["variant_id"], "quantity": 1},
                headers=_h(token))
    res = client.post("/api/orders/checkout",
                      json={"order_type": "DIGITAL", "payment_method": "TRANSFERENCIA"},
                      headers=_h(token))
    assert res.status_code == 201, res.text
    return res.json()["id"]


@pytest.fixture(autouse=True)
def _clean_cart(client, client_token):
    yield
    client.delete("/api/cart", headers=_h(client_token))


def test_voice_report_returns_natural_language_narrative(client, admin_token, client_token, catalog):
    _make_order(client, client_token, catalog)

    res = client.post("/api/reports/voice", json={"command": "generar reporte de ventas"},
                      headers=_h(admin_token))
    assert res.status_code == 200
    body = res.json()
    assert body["recognized"] is True

    narrative = body["data"]["narrative"]
    assert narrative and isinstance(narrative, str)
    assert any(word in narrative for word in ("pedidos", "Bs", "venta", "bolivianos"))


def test_voice_inventory_report_narrative_mentions_units(client, admin_token, catalog):
    res = client.post("/api/reports/voice", json={"command": "reporte de inventario"},
                      headers=_h(admin_token))
    assert res.status_code == 200
    narrative = res.json()["data"]["narrative"]
    assert any(word in narrative for word in ("unidades", "stock", "disponible"))


def test_voice_report_kpis_still_machine_readable(client, admin_token, client_token, catalog):
    _make_order(client, client_token, catalog)
    res = client.post("/api/reports/voice", json={"command": "generar reporte de ventas"},
                      headers=_h(admin_token))
    body = res.json()
    assert isinstance(body["data"]["kpis"]["total_sales"], (int, float))
    assert isinstance(body["data"]["kpis"]["total_orders"], (int, float))


def test_dashboard_endpoint_includes_no_narrative_by_default(client, admin_token):
    res = client.get("/api/reports/dashboard", headers=_h(admin_token))
    assert res.status_code == 200
    assert res.json().get("narrative") is None
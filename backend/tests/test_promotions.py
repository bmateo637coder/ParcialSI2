"""Tests de Promociones (gerencia Admin).

Cubre el CRUD de promociones (porcentaje/fijo, alcance global/categoría/producto),
la aplicación del mejor descuento al carrito, al checkout digital y al POS,
las reglas de vigencia (fechas y activación), el control de acceso y el reflejo
en los KPI del dashboard (active_promotions, discount_amount).

Aislamiento: cada test crea su propio producto (y variante/inventario) vía API,
de modo que las promociones PRODUCT de un test nunca afectan los totales exactos
de otro test. Las promociones GLOBAL se eliminan en try/finally.
"""

from datetime import datetime, timedelta, timezone

import pytest


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _create_promo(client, token: str, payload: dict) -> int:
    res = client.post("/api/promotions", json=payload, headers=_h(token))
    assert res.status_code == 201, res.text
    return res.json()["id"]


def _make_product(client, admin_token: str, tag: str) -> dict:
    """Crea un producto aislado con una variante y stock en la sucursal del fixture."""
    sizes = client.get("/api/products/metadata/sizes").json()
    colors = client.get("/api/products/metadata/colors").json()
    assert sizes and colors, "El catálogo de tallas/colores debe tener datos"

    res = client.post("/api/products/", json={
        "name": f"Prenda Promo {tag}", "base_price": 120.0, "is_active": True,
    }, headers=_h(admin_token))
    assert res.status_code == 201, res.text
    product = res.json()

    variant = client.post(f"/api/products/{product['id']}/variants", json={
        "size_id": sizes[0]["id"], "color_id": colors[0]["id"],
        "sku": f"PROMO-{tag}-{product['id']}", "stock": 5, "is_active": True,
    }, headers=_h(admin_token))
    assert variant.status_code == 201, variant.text
    variant_id = variant.json()["id"]

    return {"product_id": product["id"], "variant_id": variant_id}


def _as_catalog(branch_id: int, variant_id: int) -> dict:
    """Adapta a la forma del fixture catalog para helpers de pedidos."""
    return {"branch_id": branch_id, "variant_id": variant_id, "product_id": None}


def _make_paid_order(client, token: str, item: dict, qty: int = 1, order_type: str = "DIGITAL"):
    if order_type == "PRESENCIAL":
        res = client.post(
            "/api/pos/sale",
            json={"branch_id": item["branch_id"],
                  "items": [{"variant_id": item["variant_id"], "quantity": qty}],
                  "payment_method": "EFECTIVO"},
            headers=_h(token),
        )
        assert res.status_code == 201, res.text
        return res.json()
    client.post("/api/cart", json={"variant_id": item["variant_id"], "quantity": qty}, headers=_h(token))
    res = client.post("/api/orders/checkout",
                      json={"order_type": "DIGITAL", "payment_method": "TRANSFERENCIA"},
                      headers=_h(token))
    assert res.status_code == 201, res.text
    return res.json()


@pytest.fixture(autouse=True)
def _clean_cart(client, client_token):
    yield
    client.delete("/api/cart", headers=_h(client_token))


# ======================================================================
# CRUD Y ACCESO
# ======================================================================


def test_admin_creates_and_lists_promotion(client, admin_token, catalog):
    pid = _create_promo(client, admin_token, {
        "name": "Semana de la Moda", "discount_type": "PERCENTAGE", "value": 15,
        "target_type": "PRODUCT", "target_id": catalog["product_id"], "is_active": True,
    })
    res = client.get("/api/promotions", headers=_h(admin_token))
    assert res.status_code == 200
    assert any(p["id"] == pid and p["discount_type"] == "PERCENTAGE" for p in res.json())


def test_non_admin_cannot_create_promotion(client, client_token):
    res = client.post("/api/promotions", json={
        "name": "Hack", "discount_type": "PERCENTAGE", "value": 10,
        "target_type": "GLOBAL", "is_active": True,
    }, headers=_h(client_token))
    assert res.status_code == 403


def test_clients_see_only_active_promotions(client, admin_token, client_token, catalog):
    pid = _create_promo(client, admin_token, {
        "name": "Promo Visible", "discount_type": "PERCENTAGE", "value": 5,
        "target_type": "PRODUCT", "target_id": catalog["product_id"], "is_active": True,
    })
    res_admin = client.get("/api/promotions", headers=_h(admin_token))
    assert any(p["id"] == pid for p in res_admin.json())

    client.delete(f"/api/promotions/{pid}", headers=_h(admin_token))

    res_cli = client.get("/api/promotions", headers=_h(client_token))
    assert res_cli.status_code == 200
    assert not any(p["id"] == pid for p in res_cli.json())


def test_admin_can_update_and_deactivate_promotion(client, admin_token):
    pid = _create_promo(client, admin_token, {
        "name": "Editable", "discount_type": "PERCENTAGE", "value": 10,
        "target_type": "GLOBAL", "is_active": True,
    })
    try:
        res = client.patch(f"/api/promotions/{pid}", json={"value": 15}, headers=_h(admin_token))
        assert res.status_code == 200
        assert res.json()["value"] == 15

        deleted = client.delete(f"/api/promotions/{pid}", headers=_h(admin_token))
        assert deleted.status_code == 200
        res2 = client.get("/api/promotions?include_inactive=true", headers=_h(admin_token))
        assert any(p["id"] == pid and p["is_active"] is False for p in res2.json())
    finally:
        client.delete(f"/api/promotions/{pid}", headers=_h(admin_token))


def test_promotion_validation_rejects_bad_input(client, admin_token):
    bad_percentage = client.post("/api/promotions", json={
        "name": "Inv", "discount_type": "PERCENTAGE", "value": 150, "target_type": "GLOBAL",
    }, headers=_h(admin_token))
    assert bad_percentage.status_code == 422

    bad_fixed = client.post("/api/promotions", json={
        "name": "Inv", "discount_type": "FIXED", "value": 0, "target_type": "GLOBAL",
    }, headers=_h(admin_token))
    assert bad_fixed.status_code == 422

    missing_target = client.post("/api/promotions", json={
        "name": "Inv", "discount_type": "PERCENTAGE", "value": 10, "target_type": "CATEGORY",
    }, headers=_h(admin_token))
    assert missing_target.status_code == 422

    bad_dates = client.post("/api/promotions", json={
        "name": "Inv", "discount_type": "PERCENTAGE", "value": 10, "target_type": "GLOBAL",
        "start_date": "2026-12-01", "end_date": "2026-01-01",
    }, headers=_h(admin_token))
    assert bad_dates.status_code == 422

    stub = client.post("/api/promotions", json={
        "name": "Inv", "discount_type": "PERCENTAGE", "value": 10,
        "target_type": "PRODUCT", "target_id": 99999999,
    }, headers=_h(admin_token))
    assert stub.status_code == 404


# ======================================================================
# APLICACIÓN DEL DESCUENTO (viva = el mejor descuento vigente aplicable)
# ======================================================================


def test_checkout_applies_percentage_promotion_and_cart_shows_discount(client, admin_token, client_token, catalog):
    item = _make_product(client, admin_token, tag="cart")
    _create_promo(client, admin_token, {
        "name": "Liquidación Prenda", "discount_type": "PERCENTAGE", "value": 10,
        "target_type": "PRODUCT", "target_id": item["product_id"], "is_active": True,
    })

    client.post("/api/cart", json={"variant_id": item["variant_id"], "quantity": 2}, headers=_h(client_token))
    cart = client.get("/api/cart", headers=_h(client_token)).json()
    row = cart["items"][0]
    assert row["unit_price"] == 120.0
    assert row["discount"] == 24.0                 # 10% de 120 por 2 unidades
    assert row["subtotal"] == 216.0                # unit_price*qty - discount
    assert round(cart["total_amount"], 2) == 216.0
    assert round(cart["total_discount"], 2) == 24.0

    order = client.post("/api/orders/checkout",
                        json={"order_type": "DIGITAL", "payment_method": "TRANSFERENCIA"},
                        headers=_h(client_token)).json()
    assert round(order["total"], 2) == 216.0
    assert order["items"][0]["unit_price"] == 120.0
    assert order["items"][0]["discount"] == 24.0
    assert order["items"][0]["subtotal"] == 216.0


def test_checkout_applies_global_fixed_promotion(client, admin_token, client_token, catalog):
    pid = _create_promo(client, admin_token, {
        "name": "Descuento Fijo Global", "discount_type": "FIXED", "value": 20,
        "target_type": "GLOBAL", "is_active": True,
    })
    try:
        order = _make_paid_order(client, client_token, _as_catalog(catalog["branch_id"], catalog["variant_id"]), qty=1)
        assert round(order["total"], 2) == 100.0   # 120 - 20
        assert order["items"][0]["discount"] == 20.0
    finally:
        client.delete(f"/api/promotions/{pid}", headers=_h(admin_token))


def test_pos_sale_applies_product_promotion(client, admin_token, cajero_token, catalog):
    item = _make_product(client, admin_token, tag="pos")
    _create_promo(client, admin_token, {
        "name": "Oferta Caja", "discount_type": "PERCENTAGE", "value": 25,
        "target_type": "PRODUCT", "target_id": item["product_id"], "is_active": True,
    })
    # Inventario en la sucursal para la venta presencial.
    res = client.post("/api/inventory/", json={
        "variant_id": item["variant_id"], "branch_id": catalog["branch_id"], "available": 5,
    }, headers=_h(admin_token))
    assert res.status_code == 201, res.text

    order = _make_paid_order(client, cajero_token, _as_catalog(catalog["branch_id"], item["variant_id"]),
                             qty=1, order_type="PRESENCIAL")
    assert round(order["total"], 2) == 90.0        # 120 * 0.75
    assert order["items"][0]["discount"] == 30.0


def test_expired_and_future_promotions_are_not_applied(client, admin_token, client_token, catalog):
    yesterday = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
    tomorrow = (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat()
    item = _make_product(client, admin_token, tag="vigencia")
    _create_promo(client, admin_token, {
        "name": "Caducada", "discount_type": "PERCENTAGE", "value": 10,
        "target_type": "PRODUCT", "target_id": item["product_id"],
        "start_date": "2020-01-01", "end_date": yesterday, "is_active": True,
    })
    _create_promo(client, admin_token, {
        "name": "Futura", "discount_type": "PERCENTAGE", "value": 10,
        "target_type": "PRODUCT", "target_id": item["product_id"],
        "start_date": tomorrow, "end_date": "2099-01-01", "is_active": True,
    })

    order = _make_paid_order(client, client_token, _as_catalog(catalog["branch_id"], item["variant_id"]), qty=2)
    assert round(order["total"], 2) == 240.0       # sin descuento
    assert order["items"][0]["discount"] == 0.0


def test_inactive_promotion_is_not_applied(client, admin_token, client_token, catalog):
    item = _make_product(client, admin_token, tag="pausada")
    _create_promo(client, admin_token, {
        "name": "Pausada", "discount_type": "PERCENTAGE", "value": 10,
        "target_type": "PRODUCT", "target_id": item["product_id"], "is_active": False,
    })

    order = _make_paid_order(client, client_token, _as_catalog(catalog["branch_id"], item["variant_id"]), qty=1)
    assert round(order["total"], 2) == 120.0
    assert order["items"][0]["discount"] == 0.0


def test_dashboard_reports_discount_amount_and_active_promotions(client, admin_token, client_token, catalog):
    base = client.get("/api/reports/dashboard", headers=_h(admin_token)).json()["kpis"]
    item = _make_product(client, admin_token, tag="kpi")
    _create_promo(client, admin_token, {
        "name": "KPI Promo", "discount_type": "PERCENTAGE", "value": 10,
        "target_type": "PRODUCT", "target_id": item["product_id"], "is_active": True,
    })

    _make_paid_order(client, client_token, _as_catalog(catalog["branch_id"], item["variant_id"]), qty=1)

    kpis = client.get("/api/reports/dashboard", headers=_h(admin_token)).json()["kpis"]
    assert kpis["active_promotions"] >= base["active_promotions"] + 1
    assert round(kpis["discount_amount"], 2) == round(base["discount_amount"] + 12.0, 2)
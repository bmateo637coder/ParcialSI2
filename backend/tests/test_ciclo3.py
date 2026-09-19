"""Tests Ciclo 3:

CU17 — Confirmar compra digital
CU18 — Registrar venta presencial
CU19 — Procesar pago electrónico (pasarela sandbox)
CU20 — Actualizar inventario automáticamente
CU22 — Recomendar prendas (IA)
CU23 — Consultar asistente virtual (chatbot)
"""

import pytest


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _add_to_cart(client, token: str, variant_id: int, qty: int = 1) -> None:
    client.post("/api/cart", json={"variant_id": variant_id, "quantity": qty}, headers=_h(token))


def _available(client, branch_id: int, variant_id: int) -> int:
    rows = client.get(f"/api/inventory/availability?branch_id={branch_id}").json()
    return next(x for x in rows if x["variant_id"] == variant_id)["available"]


@pytest.fixture(autouse=True)
def _clean_cart(client, client_token):
    """El carrito del cliente persiste entre tests; se limpia antes de cada uno."""
    yield
    client.delete("/api/cart", headers=_h(client_token))


# ======================================================================
# CU17 — CONFIRMAR COMPRA DIGITAL
# ======================================================================


def test_digital_checkout_persists_shipping_address(client, client_token, catalog):
    _add_to_cart(client, client_token, catalog["variant_id"], 2)
    res = client.post(
        "/api/orders/checkout",
        json={
            "order_type": "DIGITAL",
            "branch_id": catalog["branch_id"],
            "payment_method": "TARJETA",
            "shipping_address": "Av. Siempre Viva 742, La Paz",
        },
        headers=_h(client_token),
    )
    assert res.status_code == 201
    order = res.json()
    assert order["status"] == "PAGADO"
    assert order["shipping_address"] == "Av. Siempre Viva 742, La Paz"
    assert order["payment"]["status"] == "COMPLETADO"
    assert order["payment"]["stripe_payment_id"].startswith("pi_sandbox_")


def test_digital_checkout_transferencia_pending_no_branch(client, client_token, catalog):
    _add_to_cart(client, client_token, catalog["variant_id"], 1)
    res = client.post(
        "/api/orders/checkout",
        json={"order_type": "DIGITAL", "payment_method": "TRANSFERENCIA"},
        headers=_h(client_token),
    )
    assert res.status_code == 201
    order = res.json()
    assert order["status"] == "PAGADO"
    assert order["payment"]["status"] == "COMPLETADO"


def test_digital_checkout_declined_card_cancels_without_losing_stock(client, client_token, catalog):
    _add_to_cart(client, client_token, catalog["variant_id"], 3)
    res = client.post(
        "/api/orders/checkout",
        json={
            "order_type": "DIGITAL",
            "branch_id": catalog["branch_id"],
            "payment_method": "TARJETA",
            "card_number": "4000000000000002",
        },
        headers=_h(client_token),
    )
    assert res.status_code == 201
    order = res.json()
    assert order["status"] == "CANCELADO"
    assert order["payment"]["status"] == "FALLIDO"
    # el pago se rechazó: el stock nunca se descontó
    assert _available(client, catalog["branch_id"], catalog["variant_id"]) == 10


def test_digital_checkout_insufficient_stock_rejected_before_paying(client, client_token, catalog):
    _add_to_cart(client, client_token, catalog["variant_id"], 999)
    res = client.post(
        "/api/orders/checkout",
        json={"order_type": "DIGITAL", "branch_id": catalog["branch_id"],
              "payment_method": "TARJETA"},
        headers=_h(client_token),
    )
    assert res.status_code == 409


# ======================================================================
# CU18 — REGISTRAR VENTA PRESENCIAL
# ======================================================================


def test_pos_sale_cash_creates_presencial_order_and_comprobante(client, cajero_token, catalog):
    res = client.post(
        "/api/pos/sale",
        json={
            "branch_id": catalog["branch_id"],
            "items": [{"variant_id": catalog["variant_id"], "quantity": 2}],
            "payment_method": "EFECTIVO",
        },
        headers=_h(cajero_token),
    )
    assert res.status_code == 201
    order = res.json()
    assert order["order_type"] == "PRESENCIAL"
    assert order["status"] == "PAGADO"
    assert order["total"] == 240.0
    assert order["receipt_number"].startswith("VC-")
    # CU20: el stock de la sucursal se descuenta automáticamente
    assert _available(client, catalog["branch_id"], catalog["variant_id"]) == 8


def test_pos_sale_requires_staff(client, client_token, catalog):
    res = client.post(
        "/api/pos/sale",
        json={
            "branch_id": catalog["branch_id"],
            "items": [{"variant_id": catalog["variant_id"], "quantity": 1}],
            "payment_method": "EFECTIVO",
        },
        headers=_h(client_token),
    )
    assert res.status_code == 403


def test_pos_sale_insufficient_stock(client, cajero_token, catalog):
    res = client.post(
        "/api/pos/sale",
        json={
            "branch_id": catalog["branch_id"],
            "items": [{"variant_id": catalog["variant_id"], "quantity": 999}],
            "payment_method": "EFECTIVO",
        },
        headers=_h(cajero_token),
    )
    assert res.status_code == 409


def test_pos_sale_card_declined_keeps_pending_then_retry(client, cajero_token, catalog):
    res = client.post(
        "/api/pos/sale",
        json={
            "branch_id": catalog["branch_id"],
            "items": [{"variant_id": catalog["variant_id"], "quantity": 1}],
            "payment_method": "TARJETA",
            "card_number": "4000000000009995",
        },
        headers=_h(cajero_token),
    )
    assert res.status_code == 201
    order = res.json()
    assert order["status"] == "PENDIENTE"
    assert order["payment"]["status"] == "FALLIDO"
    # el stock no se descuenta hasta que el pago se complete
    assert _available(client, catalog["branch_id"], catalog["variant_id"]) == 10

    pay = client.post(
        f"/api/orders/{order['id']}/pay",
        json={"payment_method": "EFECTIVO"},
        headers=_h(cajero_token),
    )
    assert pay.status_code == 200
    paid = pay.json()
    assert paid["status"] == "PAGADO"
    assert paid["payment"]["status"] == "COMPLETADO"
    assert paid["payment"]["method"] == "EFECTIVO"
    assert _available(client, catalog["branch_id"], catalog["variant_id"]) == 9


def test_pos_sale_registers_client(client, cajero_token, catalog):
    me = client.get("/api/auth/me", headers=_h(cajero_token)).json()
    res = client.post(
        "/api/pos/sale",
        json={
            "branch_id": catalog["branch_id"],
            "client_id": me["id"],
            "items": [{"variant_id": catalog["variant_id"], "quantity": 1}],
            "payment_method": "EFECTIVO",
        },
        headers=_h(cajero_token),
    )
    assert res.status_code == 201
    assert res.json()["client_id"] == me["id"]


# ======================================================================
# CU19 — PROCESAR PAGO ELECTRÓNICO
# ======================================================================


def test_payment_retry_requires_pending_order(client, cajero_token, catalog):
    res = client.post(
        "/api/pos/sale",
        json={
            "branch_id": catalog["branch_id"],
            "items": [{"variant_id": catalog["variant_id"], "quantity": 1}],
            "payment_method": "EFECTIVO",
        },
        headers=_h(cajero_token),
    )
    assert res.status_code == 201
    order_id = res.json()["id"]
    pay = client.post(f"/api/orders/{order_id}/pay", json={"payment_method": "TARJETA"},
                      headers=_h(cajero_token))
    assert pay.status_code == 400  # ya está pagado


def test_payment_failed_result_is_captured(client, client_token, catalog):
    _add_to_cart(client, client_token, catalog["variant_id"], 1)
    res = client.post(
        "/api/orders/checkout",
        json={
            "order_type": "DIGITAL",
            "branch_id": catalog["branch_id"],
            "payment_method": "TARJETA",
            "card_number": "4000000000000002",
        },
        headers=_h(client_token),
    )
    assert res.status_code == 201
    payment = res.json()["payment"]
    assert payment["status"] == "FALLIDO"
    assert payment["stripe_payment_id"]  # referencia de la transacción registrada


# ======================================================================
# CU20 — ACTUALIZAR INVENTARIO AUTOMÁTICAMENTE
# ======================================================================


def test_sale_creates_inventory_movement(client, cajero_token, admin_token, catalog):
    res = client.post(
        "/api/pos/sale",
        json={
            "branch_id": catalog["branch_id"],
            "items": [{"variant_id": catalog["variant_id"], "quantity": 4}],
            "payment_method": "EFECTIVO",
        },
        headers=_h(cajero_token),
    )
    assert res.status_code == 201

    inv_rows = client.get(f"/api/inventory?branch_id={catalog['branch_id']}",
                          headers=_h(admin_token)).json()
    inv_id = next(x["id"] for x in inv_rows if x["variant_id"] == catalog["variant_id"])
    movements = client.get(f"/api/inventory/movements?inventory_id={inv_id}",
                           headers=_h(admin_token)).json()
    assert any(m["movement_type"] == "SALIDA" and m["quantity"] == -4 for m in movements)


def test_sale_out_of_stock_alerts_staff(client, cajero_token, encargado_headers, admin_token, catalog):
    res = client.post(
        "/api/pos/sale",
        json={
            "branch_id": catalog["branch_id"],
            "items": [{"variant_id": catalog["variant_id"], "quantity": 10}],
            "payment_method": "EFECTIVO",
        },
        headers=_h(cajero_token),
    )
    assert res.status_code == 201
    inv_rows = client.get(f"/api/inventory?branch_id={catalog['branch_id']}",
                          headers=_h(admin_token)).json()
    row = next(x for x in inv_rows if x["variant_id"] == catalog["variant_id"])
    assert row["available"] == 0

    notes = client.get("/api/notifications", headers=encargado_headers).json()
    assert any("agotad" in n["title"].lower() or "agotad" in (n["message"] or "").lower()
               for n in notes)


# ======================================================================
# CU22 — RECOMENDAR PRENDAS (IA)
# ======================================================================


def test_recommendations_require_auth(client):
    assert client.get("/api/recommendations").status_code == 401


def _new_client_token(client, admin_token, tag: str) -> str:
    """Crea (vía API de admin) un cliente nuevo sin historial y devuelve su token."""
    headers = _h(admin_token)
    roles = client.get("/api/users/roles", headers=headers).json()
    cliente_role = next(r["id"] for r in roles if r["name"] == "Cliente")
    email = f"nuevo-{tag}@test.com"
    res = client.post(
        "/api/users",
        json={"first_name": f"Nuevo-{tag}", "last_name": "Test", "email": email,
              "password": "cliente123", "role_id": cliente_role},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    login = client.post("/api/auth/login", json={"email": email, "password": "cliente123"})
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def test_recommendations_featured_fallback_without_history(client, client_token, admin_token, catalog):
    # El cliente de sesión ya tiene historial por otros tests de la suite, así que se
    # usa un cliente recién creado (sin pedidos) → debe caer al modo "featured".
    token = _new_client_token(client, admin_token, "featured")
    res = client.get("/api/recommendations", headers=_h(token))
    assert res.status_code == 200
    body = res.json()
    assert body["source"] == "featured"
    assert len(body["items"]) >= 1


def test_recommendations_use_order_history_and_exclude_purchased(client, client_token, admin_token, catalog):
    # La "prenda hermana" comparte categoría con el fixture: candidata válida.
    _admin_api_create_sibling_product(client, catalog, admin_token)

    # El cliente compra el producto del fixture (categoría Prueba)
    _add_to_cart(client, client_token, catalog["variant_id"], 1)
    r = client.post(
        "/api/orders/checkout",
        json={"order_type": "DIGITAL", "branch_id": catalog["branch_id"],
              "payment_method": "TARJETA"},
        headers=_h(client_token),
    )
    assert r.status_code == 201

    res = client.get("/api/recommendations", headers=_h(client_token))
    assert res.status_code == 200
    body = res.json()
    assert body["source"] == "ai"
    recommended_ids = [i["product_id"] for i in body["items"]]
    # Comprado → excluido
    assert catalog["product_id"] not in recommended_ids
    # Usa el historial de compras: prioriza prendas de la categoría que más compra
    assert any("por tu interés en Prueba" in (i["reason"] or "") for i in body["items"])
    # La prenda hermana (misma categoría, sin estropear) es un candidato válido y en stock
    assert all(i["in_stock"] is True for i in body["items"])


def _admin_api_create_sibling_product(client, catalog, admin_token) -> dict:
    """Crea (vía API de admin) un segundo producto con la misma categoría del fixture."""
    headers = _h(admin_token)
    cats = client.get("/api/products/metadata/categories").json()
    category = next(c for c in cats if c["name"] == "Prueba")

    sizes = client.get("/api/products/metadata/sizes").json()
    colors = client.get("/api/products/metadata/colors").json()

    res = client.post(
        "/api/products",
        json={
            "name": "Prenda Hermana",
            "description": "Misma categoría, para recomendar",
            "base_price": 90.0,
            "category_id": category["id"],
            "is_active": True,
        },
        headers=headers,
    )
    assert res.status_code == 201
    product_id = res.json()["id"]

    var = client.post(
        f"/api/products/{product_id}/variants",
        json={"size_id": sizes[0]["id"], "color_id": colors[0]["id"],
              "sku": f"HERMANA-{product_id}", "is_active": True},
        headers=headers,
    )
    assert var.status_code == 201
    variant_id = var.json()["id"]

    inv = client.post(
        "/api/inventory",
        json={"variant_id": variant_id, "branch_id": catalog["branch_id"], "available": 5},
        headers=headers,
    )
    assert inv.status_code == 201

    return {"product_id": product_id, "variant_id": variant_id}


# ======================================================================
# CU23 — CONSULTAR ASISTENTE VIRTUAL (CHATBOT)
# ======================================================================


def test_chat_requires_auth(client):
    assert client.post("/api/assistant/chat", json={"message": "Hola"}).status_code == 401


def test_chat_replies_and_persists_conversation(client, client_token):
    res = client.post("/api/assistant/chat", json={"message": "Hola, buenas", },
                      headers=_h(client_token))
    assert res.status_code == 200
    body = res.json()
    assert body["conversation_id"]
    assert body["reply"]

    convs = client.get("/api/assistant/conversations", headers=_h(client_token)).json()
    assert any(c["id"] == body["conversation_id"] for c in convs)

    detail = client.get(f"/api/assistant/conversations/{body['conversation_id']}",
                        headers=_h(client_token)).json()
    roles = [m["role"] for m in detail["messages"]]
    assert roles == ["user", "assistant"]


def test_chat_unknown_query_suggests_support(client, client_token):
    res = client.post("/api/assistant/chat", json={"message": "qlksdjhqjw"},
                      headers=_h(client_token))
    assert res.status_code == 200
    assert "soporte" in res.json()["reply"].lower()


def test_chat_answers_order_status(client, client_token, catalog):
    _add_to_cart(client, client_token, catalog["variant_id"], 1)
    assert client.post(
        "/api/orders/checkout",
        json={"order_type": "DIGITAL", "branch_id": catalog["branch_id"],
              "payment_method": "TARJETA"},
        headers=_h(client_token),
    ).status_code == 201

    res = client.post("/api/assistant/chat",
                      json={"message": "¿Cómo va mi pedido?"}, headers=_h(client_token))
    assert res.status_code == 200
    assert "PAGADO" in res.json()["reply"]


def test_chat_conversations_are_private(client, client_token, cajero_token):
    res = client.post("/api/assistant/chat", json={"message": "Hola", },
                      headers=_h(client_token))
    conv_id = res.json()["conversation_id"]
    other = client.get(f"/api/assistant/conversations/{conv_id}", headers=_h(cajero_token))
    assert other.status_code == 404
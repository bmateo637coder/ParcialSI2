"""Tests de inventario por sucursal (CU11) y movimientos (CU21)."""


def test_availability_public_endpoint(client, catalog):
    res = client.get("/api/inventory/availability")
    assert res.status_code == 200
    rows = [r for r in res.json() if r["variant_id"] == catalog["variant_id"]]
    assert rows, "La variante sembrada debe aparecer en disponibilidad"
    assert rows[0]["available"] == 10
    assert rows[0]["branch_id"] == catalog["branch_id"]
    assert rows[0]["product_name"].startswith("Prenda Test")


def test_availability_filter_by_product(client, catalog):
    res = client.get(f"/api/inventory/availability?product_id={catalog['product_id']}")
    assert res.status_code == 200
    assert all(r["product_id"] == catalog["product_id"] for r in res.json())


def test_availability_filter_by_branch(client, catalog):
    res = client.get(f"/api/inventory/availability?branch_id={catalog['branch_id']}")
    assert res.status_code == 200
    assert all(r["branch_id"] == catalog["branch_id"] for r in res.json())


def test_availability_filter_by_query(client, catalog):
    res = client.get("/api/inventory/availability?q=Prenda+Test")
    assert res.status_code == 200
    assert all("Prenda Test" in r["product_name"] for r in res.json())


def test_list_inventory_requires_admin(client, client_token, catalog):
    headers = {"Authorization": f"Bearer {client_token}"}
    res = client.get("/api/inventory/", headers=headers)
    assert res.status_code == 403


def test_list_inventory_admin(client, auth_headers, catalog):
    res = client.get("/api/inventory/", headers=auth_headers)
    assert res.status_code == 200
    rows = [r for r in res.json() if r["variant_id"] == catalog["variant_id"]]
    assert rows and rows[0]["available"] == 10


def test_list_inventory_low_stock_filter(client, auth_headers, catalog):
    from app.core.database import SessionLocal
    from app.models.inventory import Inventory

    with SessionLocal() as db:
        inv = db.query(Inventory).filter(Inventory.variant_id == catalog["variant_id"]).first()
        inv.available = 2
        db.commit()

    res = client.get("/api/inventory/?low_stock_only=true", headers=auth_headers)
    assert res.status_code == 200
    assert any(r["variant_id"] == catalog["variant_id"] for r in res.json())


def test_create_inventory_duplicate_conflict(client, auth_headers, catalog):
    res = client.post(
        "/api/inventory/",
        json={"variant_id": catalog["variant_id"], "branch_id": catalog["branch_id"], "available": 5},
        headers=auth_headers,
    )
    assert res.status_code == 409


def test_create_inventory_invalid_variant(client, auth_headers, catalog):
    res = client.post(
        "/api/inventory/",
        json={"variant_id": 999999, "branch_id": catalog["branch_id"], "available": 5},
        headers=auth_headers,
    )
    assert res.status_code == 400


def test_create_movement_decrements_and_records(client, auth_headers, catalog):
    from app.core.database import SessionLocal
    from app.models.inventory import Inventory

    with SessionLocal() as db:
        inv_id = db.query(Inventory).filter(Inventory.variant_id == catalog["variant_id"]).first().id

    res = client.post(
        "/api/inventory/movements",
        json={"inventory_id": inv_id, "movement_type": "SALIDA", "quantity": -3, "reason": "Prueba"},
        headers=auth_headers,
    )
    assert res.status_code == 201
    assert res.json()["quantity"] == -3

    with SessionLocal() as db:
        available = db.query(Inventory).filter(Inventory.variant_id == catalog["variant_id"]).first().available
    assert available == 7

    movements = client.get(f"/api/inventory/movements?inventory_id={inv_id}&movement_type=SALIDA", headers=auth_headers)
    assert movements.status_code == 200
    assert any(m["quantity"] == -3 for m in movements.json())


def test_create_ingreso_requires_positive_delta(client, auth_headers, catalog):
    from app.core.database import SessionLocal
    from app.models.inventory import Inventory

    with SessionLocal() as db:
        inv_id = db.query(Inventory).filter(Inventory.variant_id == catalog["variant_id"]).first().id

    res = client.post(
        "/api/inventory/movements",
        json={"inventory_id": inv_id, "movement_type": "INGRESO", "quantity": -5},
        headers=auth_headers,
    )
    assert res.status_code == 400


def test_create_movement_insufficient_stock(client, auth_headers, catalog):
    from app.core.database import SessionLocal
    from app.models.inventory import Inventory

    with SessionLocal() as db:
        inv_id = db.query(Inventory).filter(Inventory.variant_id == catalog["variant_id"]).first().id

    res = client.post(
        "/api/inventory/movements",
        json={"inventory_id": inv_id, "movement_type": "SALIDA", "quantity": -999},
        headers=auth_headers,
    )
    assert res.status_code == 409


def test_movements_denied_for_client(client, client_token, catalog):
    headers = {"Authorization": f"Bearer {client_token}"}
    res = client.post(
        "/api/inventory/movements",
        json={"inventory_id": 1, "movement_type": "AJUSTE", "quantity": 1},
        headers=headers,
    )
    assert res.status_code == 403


def test_update_inventory_absolute_patch(client, auth_headers, catalog):
    from app.core.database import SessionLocal
    from app.models.inventory import Inventory

    with SessionLocal() as db:
        inv = db.query(Inventory).filter(Inventory.variant_id == catalog["variant_id"]).first()
        inv_id = inv.id

    res = client.patch(
        f"/api/inventory/{inv_id}",
        json={"available": 15},
        headers=auth_headers,
    )
    assert res.status_code == 200
    assert res.json()["available"] == 15

    with SessionLocal() as db:
        available = db.query(Inventory).filter(Inventory.variant_id == catalog["variant_id"]).first().available
    assert available == 15


def test_create_salida_requires_negative_delta(client, auth_headers, catalog):
    from app.core.database import SessionLocal
    from app.models.inventory import Inventory

    with SessionLocal() as db:
        inv_id = db.query(Inventory).filter(Inventory.variant_id == catalog["variant_id"]).first().id

    res = client.post(
        "/api/inventory/movements",
        json={"inventory_id": inv_id, "movement_type": "SALIDA", "quantity": 5},
        headers=auth_headers,
    )
    assert res.status_code == 400


def test_create_devolucion_requires_positive_delta(client, auth_headers, catalog):
    from app.core.database import SessionLocal
    from app.models.inventory import Inventory

    with SessionLocal() as db:
        inv_id = db.query(Inventory).filter(Inventory.variant_id == catalog["variant_id"]).first().id

    res = client.post(
        "/api/inventory/movements",
        json={"inventory_id": inv_id, "movement_type": "DEVOLUCION", "quantity": -5},
        headers=auth_headers,
    )
    assert res.status_code == 400


def test_list_inventory_filters_by_branch_and_product(client, auth_headers, catalog):
    res = client.get(
        f"/api/inventory/?branch_id={catalog['branch_id']}&product_id={catalog['product_id']}",
        headers=auth_headers,
    )
    assert res.status_code == 200
    rows = [r for r in res.json() if r["variant_id"] == catalog["variant_id"]]
    assert rows and all(r["branch_id"] == catalog["branch_id"] and r["product_id"] == catalog["product_id"] for r in rows)


def test_update_inventory_denied_for_client(client, client_token, catalog):
    headers = {"Authorization": f"Bearer {client_token}"}
    res = client.patch("/api/inventory/1", json={"available": 5}, headers=headers)
    assert res.status_code == 403


def test_movements_denied_for_client_GET(client, client_token):
    headers = {"Authorization": f"Bearer {client_token}"}
    res = client.get("/api/inventory/movements", headers=headers)
    assert res.status_code == 403
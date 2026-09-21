def _product_payload():
    return {
        "name": "Pantalón Cargo",
        "description": "Pantalón de carga con bolsillos amplios.",
        "base_price": 320.0,
        "image_url": "https://example.com/pantalon.jpg",
    }


def test_list_products_empty(client):
    res = client.get("/api/products/")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_create_product_requires_admin(client, client_token):
    res = client.post("/api/products/", json=_product_payload())
    assert res.status_code == 401

    res = client.post(
        "/api/products/",
        json=_product_payload(),
        headers={"Authorization": f"Bearer {client_token}"},
    )
    assert res.status_code == 403


def test_create_and_fetch_product(client, auth_headers):
    res = client.post("/api/products/", json=_product_payload(), headers=auth_headers)
    assert res.status_code == 201
    product_id = res.json()["id"]

    res = client.get(f"/api/products/{product_id}")
    assert res.status_code == 200
    assert res.json()["name"] == "Pantalón Cargo"

    assert client.delete(f"/api/products/{product_id}", headers=auth_headers).status_code == 204


def test_search_products(client, auth_headers):
    client.post("/api/products/", json=_product_payload(), headers=auth_headers)
    res = client.get("/api/products/?q=cargo")
    assert res.status_code == 200
    assert any("cargo" in p["name"].lower() for p in res.json())


def test_product_validation(client, auth_headers):
    res = client.post(
        "/api/products/",
        json={"name": "", "base_price": 250},
        headers=auth_headers,
    )
    assert res.status_code == 422

    res = client.post(
        "/api/products/",
        json={"name": "Test", "base_price": -5},
        headers=auth_headers,
    )
    assert res.status_code == 422


def test_product_404(client):
    res = client.get("/api/products/999999")
    assert res.status_code == 404


def test_categories_metadata(client):
    res = client.get("/api/products/metadata/categories")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_variant_flow(client, auth_headers):
    product = client.post(
        "/api/products/",
        json={"name": "Camiseta Naranja", "base_price": 120},
        headers=auth_headers,
    ).json()

    size = client.post(
        "/api/products/catalog/sizes",
        json={"name": "XXG"},
        headers=auth_headers,
    ).json()
    color = client.post(
        "/api/products/catalog/colors",
        json={"name": "Naranja"},
        headers=auth_headers,
    ).json()

    variant = client.post(
        f"/api/products/{product['id']}/variants",
        json={"size_id": size["id"], "color_id": color["id"], "sku": "CAM-XXG-NR", "stock": 7},
        headers=auth_headers,
    )
    assert variant.status_code == 201
    body = variant.json()
    assert body["stock"] == 7
    assert body["size_name"] == "XXG"
    assert body["color_name"] == "Naranja"

    client.delete(f"/api/products/variants/{body['id']}", headers=auth_headers)
    assert variant.status_code == 201


def test_variant_stock_mirrors_real_inventory(client, auth_headers):
    """El stock de las variantes visibles en el catálogo debe sumar el
    inventario real por sucursal, no una columna que nunca se llena."""
    product = client.post(
        "/api/products/",
        json={"name": "Camiseta Stock", "base_price": 150},
        headers=auth_headers,
    ).json()

    size = client.post(
        "/api/products/catalog/sizes",
        json={"name": "LG"},
        headers=auth_headers,
    ).json()
    color = client.post(
        "/api/products/catalog/colors",
        json={"name": "Azul"},
        headers=auth_headers,
    ).json()

    variant = client.post(
        f"/api/products/{product['id']}/variants",
        json={"size_id": size["id"], "color_id": color["id"], "sku": "STK-LG-AZ", "stock": 0},
        headers=auth_headers,
    ).json()

    b1 = client.post(
        "/api/branches/",
        json={"name": "Stock LP", "city": "La Paz", "address": "Av. 1"},
        headers=auth_headers,
    ).json()
    b2 = client.post(
        "/api/branches/",
        json={"name": "Stock SC", "city": "Santa Cruz", "address": "Av. 2"},
        headers=auth_headers,
    ).json()

    for branch_id, available in ((b1["id"], 12), (b2["id"], 3)):
        client.post(
            "/api/inventory/",
            json={"variant_id": variant["id"], "branch_id": branch_id, "available": available},
            headers=auth_headers,
        )

    data = client.get(f"/api/products/{product['id']}/variants").json()
    assert len(data) == 1
    assert data[0]["id"] == variant["id"]
    assert data[0]["stock"] == 15

    well = client.post(
        "/api/branches/",
        json={"name": "Stock CB", "city": "Cochabamba", "address": "Av. 3"},
        headers=auth_headers,
    ).json()
    client.post(
        "/api/inventory/",
        json={"variant_id": variant["id"], "branch_id": well["id"], "available": 10},
        headers=auth_headers,
    )

    data = client.get(f"/api/products/{product['id']}/variants").json()
    assert data[0]["stock"] == 25


# ======================================================================
# Colecciones (CU8 ampliado)
# ======================================================================


def test_metadata_collections_public(client):
    res = client.get("/api/products/metadata/collections")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_create_and_list_collection(client, auth_headers):
    season = client.post(
        "/api/products/catalog/seasons",
        json={"name": "Verano Test", "year": 2026, "is_active": True},
        headers=auth_headers,
    ).json()

    res = client.post(
        "/api/products/catalog/collections",
        json={"name": "Colección Test", "season_id": season["id"]},
        headers=auth_headers,
    )
    assert res.status_code == 201
    assert res.json()["season_id"] == season["id"]

    meta = client.get("/api/products/metadata/collections").json()
    assert any(c["name"] == "Colección Test" for c in meta)


def test_create_collection_invalid_season(client, auth_headers):
    res = client.post(
        "/api/products/catalog/collections",
        json={"name": "Bad", "season_id": 999999},
        headers=auth_headers,
    )
    assert res.status_code == 400


def test_update_and_deactivate_collection(client, auth_headers):
    collection = client.post(
        "/api/products/catalog/collections",
        json={"name": "Colección Edit", "is_active": True},
        headers=auth_headers,
    ).json()

    res = client.patch(
        f"/api/products/catalog/collections/{collection['id']}",
        json={"name": "Colección Renombrada"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    assert res.json()["name"] == "Colección Renombrada"

    assert client.delete(
        f"/api/products/catalog/collections/{collection['id']}", headers=auth_headers
    ).status_code == 204


def test_update_collection_invalid_season(client, auth_headers):
    collection = client.post(
        "/api/products/catalog/collections",
        json={"name": "Colección Bad Season"},
        headers=auth_headers,
    ).json()
    res = client.patch(
        f"/api/products/catalog/collections/{collection['id']}",
        json={"season_id": 999999},
        headers=auth_headers,
    )
    assert res.status_code == 400


# ======================================================================
# Proveedores (CU9 completado)
# ======================================================================


def test_provider_create_update_delete(client, auth_headers):
    provider = client.post(
        "/api/products/catalog/providers",
        json={"name": "Proveedor Test", "contact_email": "p@test.com", "nit": "8888888",
              "phone": "+591 111", "address": "Calle 99"},
        headers=auth_headers,
    ).json()
    assert provider["nit"] == "8888888"

    updated = client.patch(
        f"/api/products/catalog/providers/{provider['id']}",
        json={"phone": "+591 222"},
        headers=auth_headers,
    ).json()
    assert updated["phone"] == "+591 222"

    assert client.delete(
        f"/api/products/catalog/providers/{provider['id']}", headers=auth_headers
    ).status_code == 204


def test_provider_update_404(client, auth_headers):
    res = client.patch("/api/products/catalog/providers/999999", json={"phone": "x"}, headers=auth_headers)
    assert res.status_code == 404


# ======================================================================
# Temporadas (CU8)
# ======================================================================


def test_season_update_and_deactivate(client, auth_headers):
    season = client.post(
        "/api/products/catalog/seasons",
        json={"name": "Temporada Test", "year": 2026, "description": "x", "is_active": True},
        headers=auth_headers,
    ).json()

    res = client.patch(
        f"/api/products/catalog/seasons/{season['id']}",
        json={"description": "Actualizado"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    assert res.json()["description"] == "Actualizado"

    assert client.delete(
        f"/api/products/catalog/seasons/{season['id']}", headers=auth_headers
    ).status_code == 204


def test_season_update_404(client, auth_headers):
    res = client.patch("/api/products/catalog/seasons/999999", json={"description": "x"}, headers=auth_headers)
    assert res.status_code == 404


# ======================================================================
# Filtros y visibilidad (is_active)
# ======================================================================


def test_product_filters_by_collection_and_provider(client, auth_headers):
    season = client.post(
        "/api/products/catalog/seasons",
        json={"name": "Filtro Season", "year": 2026},
        headers=auth_headers,
    ).json()
    collection = client.post(
        "/api/products/catalog/collections",
        json={"name": "Filtro Colección", "season_id": season["id"]},
        headers=auth_headers,
    ).json()
    provider = client.post(
        "/api/products/catalog/providers",
        json={"name": "Filtro Proveedor"},
        headers=auth_headers,
    ).json()

    product = client.post(
        "/api/products/",
        json={"name": "Producto Filtro", "base_price": 150,
              "season_id": season["id"], "collection_id": collection["id"], "provider_id": provider["id"]},
        headers=auth_headers,
    ).json()

    data = client.get(f"/api/products/?collection_id={collection['id']}").json()
    assert any(p["id"] == product["id"] for p in data)

    data = client.get(f"/api/products/?provider_id={provider['id']}").json()
    assert any(p["id"] == product["id"] for p in data)


def test_product_soft_delete_hidden_by_default(client, auth_headers):
    product = client.post("/api/products/", json={"name": "Temporal Oculto", "base_price": 1},
                          headers=auth_headers).json()
    client.delete(f"/api/products/{product['id']}", headers=auth_headers)

    assert not any(p["id"] == product["id"] for p in client.get("/api/products/").json())


def test_include_inactive_products(client, auth_headers):
    product = client.post("/api/products/", json={"name": "Inactivo Visible", "base_price": 2},
                          headers=auth_headers).json()
    client.delete(f"/api/products/{product['id']}", headers=auth_headers)

    data = client.get("/api/products/?include_inactive=true").json()
    assert any(p["id"] == product["id"] for p in data)
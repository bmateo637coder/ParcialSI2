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
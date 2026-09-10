def test_list_branches(client):
    res = client.get("/api/branches/")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_filter_branches_by_city(client, auth_headers):
    client.post(
        "/api/branches/",
        json={"name": "Sucursal Norte", "city": "Oruro"},
        headers=auth_headers,
    )
    res = client.get("/api/branches/?city=oruro")
    assert res.status_code == 200
    assert all(b["city"] == "Oruro" for b in res.json())


def test_create_branches_requires_admin(client):
    res = client.post(
        "/api/branches/",
        json={"name": "Sin Auth", "city": "X"},
    )
    assert res.status_code == 401


def test_update_and_soft_delete_branch(client, auth_headers):
    branch = client.post(
        "/api/branches/",
        json={"name": "Sucursal Sur", "city": "Sucre", "address": "Calle 1"},
        headers=auth_headers,
    ).json()

    res = client.patch(
        f"/api/branches/{branch['id']}",
        json={"phone": "+591 70000000"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    assert res.json()["phone"] == "+591 70000000"

    assert client.delete(f"/api/branches/{branch['id']}", headers=auth_headers).status_code == 204
    assert client.get(f"/api/branches/{branch['id']}").status_code == 404


def test_update_missing_branch_404(client, auth_headers):
    res = client.patch("/api/branches/999999", json={"name": "X"}, headers=auth_headers)
    assert res.status_code == 404


def test_branch_validation(client, auth_headers):
    res = client.post(
        "/api/branches/",
        json={"name": "", "city": "X"},
        headers=auth_headers,
    )
    assert res.status_code == 422
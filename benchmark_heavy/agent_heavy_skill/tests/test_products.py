"""Product endpoint testleri — mevcut desen örneği."""


def test_create_and_get_product(client):
    r = client.post("/products", json={
        "name": "Widget", "sku": "W1", "price_cents": 500,
        "stock": 10, "category": "tools"})
    assert r.status_code == 201
    pid = r.json()["id"]
    assert client.get(f"/products/{pid}").json()["sku"] == "W1"


def test_duplicate_sku_409(client):
    body = {"name": "A", "sku": "DUP", "price_cents": 1, "stock": 1, "category": "c"}
    assert client.post("/products", json=body).status_code == 201
    assert client.post("/products", json=body).status_code == 409


def test_negative_price_422(client):
    r = client.post("/products", json={
        "name": "A", "sku": "N1", "price_cents": -1, "stock": 1, "category": "c"})
    assert r.status_code == 422


def test_list_pagination(client):
    for i in range(3):
        client.post("/products", json={
            "name": "P", "sku": f"PAG{i}", "price_cents": 1,
            "stock": 1, "category": "pag"})
    assert len(client.get("/products?category=pag&limit=2&offset=0").json()) == 2
    assert client.get("/products?category=pag&limit=2&offset=99").json() == []

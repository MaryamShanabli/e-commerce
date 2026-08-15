import pytest

from app.categories.models import Category
from app.products.models import Product


@pytest.fixture()
def admin_headers(client, create_user, auth_headers):
    admin = create_user(is_admin=True)
    return auth_headers(admin)


@pytest.fixture()
def category_id(db_session):
    db_session.add(Category(name="Electronics"))
    db_session.commit()
    return 1


def _create_product(client, headers, category_id, **overrides):
    payload = {
        "name": "iPhone 15",
        "price": 999.99,
        "description": "Flagship phone",
        "quantity": 50,
        "category_id": category_id,
    }
    payload.update(overrides)
    return client.post("/api/product", json=payload, headers=headers)


def test_admin_create_product_succeeds(client, admin_headers, category_id):
    response = _create_product(client, admin_headers, category_id)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "iPhone 15"
    assert body["price"] == "999.99"
    assert body["quantity"] == 50
    assert body["category_id"] == category_id
    assert body["category_name"] == "Electronics"
    assert body["description"] == "Flagship phone"


def test_non_admin_create_product_forbidden(client, create_user, auth_headers, category_id):
    user = create_user(is_admin=False)
    response = _create_product(client, auth_headers(user), category_id)
    assert response.status_code == 403
    assert response.json()["error_type"] == "ForbiddenException"


def test_create_product_zero_price_validation_400(client, admin_headers, category_id):
    response = _create_product(client, admin_headers, category_id, price=0)
    assert response.status_code == 400
    assert response.json()["error_type"] == "ValidationError"


def test_create_product_negative_quantity_validation_400(client, admin_headers, category_id):
    response = _create_product(client, admin_headers, category_id, quantity=-1)
    assert response.status_code == 400
    assert response.json()["error_type"] == "ValidationError"


def test_create_product_unknown_category_not_found(client, admin_headers):
    response = _create_product(client, admin_headers, 999)
    assert response.status_code == 404
    assert response.json()["error_type"] == "NotFoundException"


def test_get_product_list_and_detail_public(client, admin_headers, category_id):
    _create_product(client, admin_headers, category_id)
    response = client.get("/api/product")
    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["name"] == "iPhone 15"
    assert body["items"][0]["description"] == "Flagship phone"

    response = client.get("/api/product/1")
    assert response.status_code == 200
    assert response.json()["name"] == "iPhone 15"
    assert response.json()["description"] == "Flagship phone"


def test_get_product_not_found(client):
    response = client.get("/api/product/999")
    assert response.status_code == 404


def test_update_product_admin_succeeds(client, admin_headers, category_id):
    _create_product(client, admin_headers, category_id)
    response = client.put(
        "/api/product/1",
        json={
            "name": "iPhone 16",
            "price": 1099.99,
            "description": "Updated description",
            "quantity": 40,
            "category_id": category_id,
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "iPhone 16"
    assert body["price"] == "1099.99"
    assert body["description"] == "Updated description"


def test_update_product_not_found(client, admin_headers, category_id):
    response = client.put(
        "/api/product/999",
        json={
            "name": "X",
            "price": 1,
            "quantity": 1,
            "category_id": category_id,
        },
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_delete_product_soft_delete_and_disappears_from_public_reads(
    client, admin_headers, category_id
):
    _create_product(client, admin_headers, category_id)
    response = client.delete("/api/product/1", headers=admin_headers)
    assert response.status_code == 204

    assert client.get("/api/product/1").status_code == 404
    assert client.get("/api/product").json()["total_count"] == 0


def test_delete_already_inactive_product_not_found(client, admin_headers, category_id):
    _create_product(client, admin_headers, category_id)
    client.delete("/api/product/1", headers=admin_headers)
    response = client.delete("/api/product/1", headers=admin_headers)
    assert response.status_code == 404


def test_pagination_defaults(client, admin_headers, category_id):
    for i in range(3):
        _create_product(client, admin_headers, category_id, name=f"Product {i}")
    response = client.get("/api/product")
    body = response.json()
    assert body["page_number"] == 1
    assert body["page_size"] == 10
    assert body["total_count"] == 3


def test_pagination_size_clamped_at_100(client, admin_headers, category_id):
    for i in range(3):
        _create_product(client, admin_headers, category_id, name=f"Product {i}")
    response = client.get("/api/product?size=500")
    assert response.json()["page_size"] == 100


def test_pagination_flags_on_first_middle_and_last_page(client, admin_headers, category_id):
    for i in range(25):
        _create_product(client, admin_headers, category_id, name=f"Product {i}")

    first = client.get("/api/product?page=1&size=10").json()
    assert first["page_number"] == 1
    assert first["page_size"] == 10
    assert first["total_count"] == 25
    assert first["total_pages"] == 3
    assert first["has_previous_page"] is False
    assert first["has_next_page"] is True
    assert len(first["items"]) == 10

    middle = client.get("/api/product?page=2&size=10").json()
    assert middle["page_number"] == 2
    assert middle["has_previous_page"] is True
    assert middle["has_next_page"] is True
    assert len(middle["items"]) == 10

    last = client.get("/api/product?page=3&size=10").json()
    assert last["page_number"] == 3
    assert last["has_previous_page"] is True
    assert last["has_next_page"] is False
    assert len(last["items"]) == 5

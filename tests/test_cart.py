import pytest

from app.cart.models import Cart
from app.categories.models import Category
from app.products.models import Product


@pytest.fixture()
def setup_store(db_session):
    category = Category(name="Store")
    db_session.add(category)
    db_session.flush()
    product = Product(name="Widget", price=10.00, quantity=5, category_id=category.id)
    db_session.add(product)
    db_session.commit()
    return product.id


def _add(client, headers, user_id, product_id, quantity):
    return client.post(
        f"/api/cart/add?userID={user_id}",
        json={"product_id": product_id, "quantity": quantity},
        headers=headers,
    )


def test_get_cart_returns_empty_cart_with_totals(client, create_user, auth_headers):
    user = create_user()
    response = client.get(f"/api/cart/{user.id}", headers=auth_headers(user))
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == user.id
    assert body["total_price"] == "0"
    assert body["items"] == []


def test_add_to_cart_returns_item_with_product_details(client, create_user, auth_headers, setup_store):
    user = create_user()
    response = _add(client, auth_headers(user), user.id, setup_store, 2)
    assert response.status_code == 200
    body = response.json()
    assert body["total_price"] == "20.00"
    assert body["items"][0]["product_id"] == setup_store
    assert body["items"][0]["product_name"] == "Widget"
    assert body["items"][0]["product_price"] == "10.00"
    assert body["items"][0]["quantity"] == 2
    assert body["items"][0]["subtotal"] == "20.00"


def test_add_same_product_twice_increments_not_duplicates(
    client, create_user, auth_headers, setup_store
):
    user = create_user()
    headers = auth_headers(user)
    _add(client, headers, user.id, setup_store, 2)
    response = _add(client, headers, user.id, setup_store, 3)
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["quantity"] == 5
    assert items[0]["subtotal"] == "50.00"


def test_add_more_than_available_stock_conflict(client, create_user, auth_headers, setup_store):
    user = create_user()
    response = _add(client, auth_headers(user), user.id, setup_store, 6)
    assert response.status_code == 409
    assert response.json()["error_type"] == "ConflictException"


def test_add_inactive_product_not_found(client, create_user, auth_headers, db_session):
    category = Category(name="C")
    db_session.add(category)
    db_session.flush()
    product = Product(name="Gone", price=1, quantity=5, category_id=category.id, is_active=False)
    db_session.add(product)
    db_session.commit()

    user = create_user()
    response = _add(client, auth_headers(user), user.id, product.id, 1)
    assert response.status_code == 404


def test_add_to_other_users_cart_forbidden(client, create_user, auth_headers, setup_store):
    user_a = create_user()
    user_b = create_user()
    response = _add(client, auth_headers(user_a), user_b.id, setup_store, 1)
    assert response.status_code == 403
    assert response.json()["error_type"] == "ForbiddenException"


def test_admin_can_add_to_any_users_cart(client, create_user, auth_headers, setup_store):
    admin = create_user(is_admin=True)
    user = create_user()
    response = _add(client, auth_headers(admin), user.id, setup_store, 1)
    assert response.status_code == 200
    assert response.json()["items"][0]["quantity"] == 1


def test_get_other_users_cart_forbidden(client, create_user, auth_headers):
    user_a = create_user()
    user_b = create_user()
    response = client.get(f"/api/cart/{user_b.id}", headers=auth_headers(user_a))
    assert response.status_code == 403


def test_update_quantity_increments_value(client, create_user, auth_headers, setup_store):
    user = create_user()
    headers = auth_headers(user)
    item_id = _add(client, headers, user.id, setup_store, 2).json()["items"][0]["id"]

    response = client.put(
        "/api/cart/quantity", json={"cart_item_id": item_id, "quantity_required": 4}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["items"][0]["quantity"] == 4
    assert response.json()["total_price"] == "40.00"


def test_update_quantity_zero_removes_item(client, create_user, auth_headers, setup_store):
    user = create_user()
    headers = auth_headers(user)
    item_id = _add(client, headers, user.id, setup_store, 2).json()["items"][0]["id"]

    response = client.put(
        "/api/cart/quantity", json={"cart_item_id": item_id, "quantity_required": 0}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total_price"] == "0"


def test_update_quantity_beyond_stock_conflict(client, create_user, auth_headers, setup_store):
    user = create_user()
    headers = auth_headers(user)
    item_id = _add(client, headers, user.id, setup_store, 2).json()["items"][0]["id"]

    response = client.put(
        "/api/cart/quantity", json={"cart_item_id": item_id, "quantity_required": 6}, headers=headers
    )
    assert response.status_code == 409
    assert response.json()["error_type"] == "ConflictException"


def test_update_quantity_missing_item_not_found(client, create_user, auth_headers):
    user = create_user()
    response = client.put(
        "/api/cart/quantity",
        json={"cart_item_id": 999, "quantity_required": 1},
        headers=auth_headers(user),
    )
    assert response.status_code == 404


def test_update_quantity_other_users_item_forbidden(client, create_user, auth_headers, setup_store):
    user_a = create_user()
    user_b = create_user()
    item_id = _add(client, auth_headers(user_a), user_a.id, setup_store, 1).json()["items"][0]["id"]

    response = client.put(
        "/api/cart/quantity",
        json={"cart_item_id": item_id, "quantity_required": 2},
        headers=auth_headers(user_b),
    )
    assert response.status_code == 403


def test_cart_route_without_token_unauthorized(client):
    response = client.get("/api/cart/1")
    assert response.status_code == 401
    response = client.post("/api/cart/add?userID=1", json={"product_id": 1, "quantity": 1})
    assert response.status_code == 401

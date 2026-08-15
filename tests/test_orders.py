import pytest

from app.cart.models import Cart, CartItem
from app.categories.models import Category
from app.orders.models import Order
from app.products.models import Product


@pytest.fixture()
def store(db_session):
    category = Category(name="Store")
    db_session.add(category)
    db_session.flush()
    product_a = Product(name="A", price=10.00, quantity=5, category_id=category.id)
    product_b = Product(name="B", price=20.00, quantity=3, category_id=category.id)
    db_session.add_all([product_a, product_b])
    db_session.commit()
    return product_a.id, product_b.id


def _checkout(client, headers, user_id, **overrides):
    payload = {
        "user_id": user_id,
        "payment_method": "Credit Card",
        "shipping_address": "123 Main St",
    }
    payload.update(overrides)
    return client.post("/api/cart/checkout", json=payload, headers=headers)


def _add(client, headers, user_id, product_id, quantity):
    return client.post(
        f"/api/cart/add?userID={user_id}",
        json={"product_id": product_id, "quantity": quantity},
        headers=headers,
    )


def test_successful_checkout_full_flow(client, create_user, auth_headers, store, db_session):
    product_a_id, product_b_id = store
    user = create_user()
    headers = auth_headers(user)
    _add(client, headers, user.id, product_a_id, 2)
    _add(client, headers, user.id, product_b_id, 1)

    response = _checkout(client, headers, user.id)
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == user.id
    assert body["status"] == "Pending"
    assert body["price"] == "40.00"
    assert body["shipping_address"] == "123 Main St"
    assert body["payment_method"] == "Credit Card"
    assert len(body["items"]) == 2
    by_id = {item["product_id"]: item for item in body["items"]}
    assert by_id[product_a_id]["product_name"] == "A"
    assert by_id[product_a_id]["unit_price"] == "10.00"
    assert by_id[product_a_id]["subtotal"] == "20.00"
    assert by_id[product_b_id]["unit_price"] == "20.00"
    assert by_id[product_b_id]["subtotal"] == "20.00"

    stock_a = db_session.get(Product, product_a_id).quantity
    stock_b = db_session.get(Product, product_b_id).quantity
    assert stock_a == 3
    assert stock_b == 2

    cart = db_session.query(Cart).filter(Cart.user_id == user.id).first()
    assert cart is not None
    assert db_session.query(CartItem).filter(CartItem.cart_id == cart.id).count() == 0


def test_checkout_empty_cart_bad_request(client, create_user, auth_headers, db_session):
    user = create_user()
    response = _checkout(client, auth_headers(user), user.id)
    assert response.status_code == 400
    assert response.json()["error_type"] == "BadRequestException"
    assert db_session.query(Order).count() == 0


def test_checkout_body_user_id_mismatch_forbidden(client, create_user, auth_headers, store):
    product_a_id, _ = store
    user = create_user()
    other = create_user()
    headers = auth_headers(user)
    _add(client, headers, user.id, product_a_id, 1)

    response = _checkout(client, headers, other.id)
    assert response.status_code == 403
    assert response.json()["error_type"] == "ForbiddenException"


def test_checkout_with_out_of_stock_item_rolls_back_everything(
    client, create_user, auth_headers, store, db_session
):
    product_a_id, product_b_id = store
    user = create_user()
    headers = auth_headers(user)
    _add(client, headers, user.id, product_a_id, 2)
    _add(client, headers, user.id, product_b_id, 1)

    product_b = db_session.get(Product, product_b_id)
    product_b.quantity = 0
    db_session.commit()

    response = _checkout(client, headers, user.id)
    assert response.status_code == 409
    assert "Insufficient stock" in response.json()["message"]

    assert db_session.query(Order).count() == 0
    assert db_session.get(Product, product_a_id).quantity == 5


def test_two_checkouts_racing_for_last_unit_exactly_one_succeeds(
    client, create_user, auth_headers, db_session
):
    category = Category(name="Race")
    db_session.add(category)
    db_session.flush()
    product = Product(name="LastUnit", price=5.00, quantity=1, category_id=category.id)
    db_session.add(product)
    db_session.commit()

    user_a = create_user()
    user_b = create_user()
    headers_a = auth_headers(user_a)
    headers_b = auth_headers(user_b)
    _add(client, headers_a, user_a.id, product.id, 1)
    _add(client, headers_b, user_b.id, product.id, 1)

    first = _checkout(client, headers_a, user_a.id)
    second = _checkout(client, headers_b, user_b.id)
    statuses = sorted([first.status_code, second.status_code])
    assert statuses == [200, 409]

    assert db_session.get(Product, product.id).quantity == 0
    assert db_session.query(Order).count() == 1


def test_order_items_snapshot_name_and_price(client, create_user, auth_headers, store, db_session):
    product_a_id, product_b_id = store
    user = create_user()
    headers = auth_headers(user)
    _add(client, headers, user.id, product_a_id, 1)

    order_id = _checkout(client, headers, user.id).json()["id"]

    product_a = db_session.get(Product, product_a_id)
    product_a.name = "A renamed"
    product_a.price = 99.99
    db_session.commit()

    body = client.get(f"/api/order/{order_id}", headers=headers).json()
    assert body["items"][0]["product_name"] == "A"
    assert body["items"][0]["unit_price"] == "10.00"
    assert body["items"][0]["subtotal"] == "10.00"


def test_list_orders_only_shows_current_users_orders(
    client, create_user, auth_headers, store
):
    product_a_id, _ = store
    user_a = create_user()
    user_b = create_user()
    _add(client, auth_headers(user_a), user_a.id, product_a_id, 1)
    _checkout(client, auth_headers(user_a), user_a.id)

    response = client.get("/api/order", headers=auth_headers(user_b))
    assert response.status_code == 200
    assert response.json() == []

    response = client.get("/api/order", headers=auth_headers(user_a))
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["user_id"] == user_a.id


def test_get_other_users_order_forbidden(client, create_user, auth_headers, store):
    product_a_id, _ = store
    user_a = create_user()
    user_b = create_user()
    _add(client, auth_headers(user_a), user_a.id, product_a_id, 1)
    order_id = _checkout(client, auth_headers(user_a), user_a.id).json()["id"]

    response = client.get(f"/api/order/{order_id}", headers=auth_headers(user_b))
    assert response.status_code == 403
    assert response.json()["error_type"] == "ForbiddenException"


def test_admin_can_read_any_orders(client, create_user, auth_headers, store):
    product_a_id, _ = store
    user_a = create_user()
    admin = create_user(is_admin=True)
    _add(client, auth_headers(user_a), user_a.id, product_a_id, 1)
    order_id = _checkout(client, auth_headers(user_a), user_a.id).json()["id"]

    response = client.get(f"/api/order/{order_id}", headers=auth_headers(admin))
    assert response.status_code == 200

    response = client.get("/api/order", headers=auth_headers(admin))
    assert response.status_code == 200


def test_get_order_not_found(client, create_user, auth_headers):
    user = create_user()
    response = client.get("/api/order/999", headers=auth_headers(user))
    assert response.status_code == 404
    assert response.json()["error_type"] == "NotFoundException"

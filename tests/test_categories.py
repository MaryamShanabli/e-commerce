def test_list_categories_public(client, create_user, auth_headers, db_session):
    from app.categories.models import Category

    admin = create_user(is_admin=True)
    headers = auth_headers(admin)
    db_session.add_all([Category(name="A"), Category(name="B")])
    db_session.commit()

    response = client.get("/api/category")
    assert response.status_code == 200
    names = [c["name"] for c in response.json()]
    assert names == ["A", "B"]

    response = client.get("/api/category", headers=headers)
    assert response.status_code == 200


def test_get_category_by_id_public_and_not_found(client, create_user, auth_headers, db_session):
    from app.categories.models import Category

    db_session.add(Category(name="Only"))
    db_session.commit()

    response = client.get("/api/category/1")
    assert response.status_code == 200
    assert response.json() == {"id": 1, "name": "Only"}

    response = client.get("/api/category/999")
    assert response.status_code == 404
    assert response.json()["error_type"] == "NotFoundException"


def test_create_category_admin_succeeds(client, create_user, auth_headers):
    admin = create_user(is_admin=True)
    response = client.post(
        "/api/category", json={"name": "Electronics"}, headers=auth_headers(admin)
    )
    assert response.status_code == 201
    assert response.json() == {"id": 1, "name": "Electronics"}


def test_create_category_duplicate_name_conflict(client, create_user, auth_headers):
    admin = create_user(is_admin=True)
    headers = auth_headers(admin)
    assert client.post("/api/category", json={"name": "Dup"}, headers=headers).status_code == 201
    response = client.post("/api/category", json={"name": "Dup"}, headers=headers)
    assert response.status_code == 409
    assert response.json()["error_type"] == "ConflictException"


def test_create_category_empty_name_validation_400(client, create_user, auth_headers):
    admin = create_user(is_admin=True)
    headers = auth_headers(admin)

    response = client.post("/api/category", json={"name": ""}, headers=headers)
    assert response.status_code == 400
    assert response.json()["error_type"] == "ValidationError"

    response = client.post("/api/category", json={"name": "   "}, headers=headers)
    assert response.status_code == 400
    assert response.json()["error_type"] == "ValidationError"


def test_non_admin_create_category_forbidden(client, create_user, auth_headers):
    user = create_user(is_admin=False)
    response = client.post(
        "/api/category", json={"name": "Nope"}, headers=auth_headers(user)
    )
    assert response.status_code == 403
    assert response.json()["error_type"] == "ForbiddenException"


def test_update_category_renames_with_body_id(client, create_user, auth_headers):
    admin = create_user(is_admin=True)
    headers = auth_headers(admin)
    assert client.post("/api/category", json={"name": "Old"}, headers=headers).status_code == 201

    response = client.put("/api/category", json={"id": 1, "name": "New"}, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"id": 1, "name": "New"}

    response = client.get("/api/category/1")
    assert response.json()["name"] == "New"


def test_update_category_not_found(client, create_user, auth_headers):
    admin = create_user(is_admin=True)
    response = client.put(
        "/api/category", json={"id": 999, "name": "Ghost"}, headers=auth_headers(admin)
    )
    assert response.status_code == 404


def test_update_category_duplicate_name_on_other_category_conflict(client, create_user, auth_headers):
    admin = create_user(is_admin=True)
    headers = auth_headers(admin)
    assert client.post("/api/category", json={"name": "Keep"}, headers=headers).status_code == 201
    assert client.post("/api/category", json={"name": "Rename"}, headers=headers).status_code == 201

    response = client.put("/api/category", json={"id": 2, "name": "Keep"}, headers=headers)
    assert response.status_code == 409


def test_delete_category_with_products_conflict(client, create_user, auth_headers, db_session):
    from app.categories.models import Category
    from app.products.models import Product

    admin = create_user(is_admin=True)
    headers = auth_headers(admin)
    category = Category(name="InUse")
    db_session.add(category)
    db_session.flush()
    db_session.add(
        Product(name="P", price=1, quantity=1, category_id=category.id)
    )
    db_session.commit()

    response = client.delete("/api/category/1", headers=headers)
    assert response.status_code == 409
    assert response.json()["error_type"] == "ConflictException"


def test_delete_category_without_products_succeeds_and_non_admin_forbidden(
    client, create_user, auth_headers
):
    admin = create_user(is_admin=True)
    user = create_user(is_admin=False)
    headers = auth_headers(admin)
    assert client.post("/api/category", json={"name": "Empty"}, headers=headers).status_code == 201

    response = client.delete("/api/category/1", headers=auth_headers(user))
    assert response.status_code == 403

    response = client.delete("/api/category/1", headers=headers)
    assert response.status_code == 204

    response = client.get("/api/category/1")
    assert response.status_code == 404


def test_delete_category_not_found(client, create_user, auth_headers):
    admin = create_user(is_admin=True)
    response = client.delete("/api/category/999", headers=auth_headers(admin))
    assert response.status_code == 404

def _assert_contract_shape(body: dict) -> None:
    assert set(body.keys()) == {"message", "status_code", "error_type", "timestamp"}
    assert isinstance(body["message"], str)
    assert isinstance(body["status_code"], int)
    assert isinstance(body["error_type"], str)
    assert isinstance(body["timestamp"], str)


def test_404_error_contract(client):
    response = client.get("/api/product/999")
    assert response.status_code == 404
    _assert_contract_shape(response.json())


def test_400_error_contract(client):
    response = client.post(
        "/api/auth/sign-up",
        json={"name": "John Doe", "password": "SecurePass123!"},
    )
    assert response.status_code == 400
    body = response.json()
    _assert_contract_shape(body)
    assert body["error_type"] == "ValidationError"


def test_409_error_contract(client):
    client.post(
        "/api/auth/sign-up",
        json={"name": "John Doe", "email": "dup@example.com", "password": "SecurePass123!"},
    )
    response = client.post(
        "/api/auth/sign-up",
        json={"name": "John Doe", "email": "dup@example.com", "password": "SecurePass123!"},
    )
    assert response.status_code == 409
    _assert_contract_shape(response.json())


def test_401_error_contract(client):
    response = client.get("/api/cart/1")
    assert response.status_code == 401
    body = response.json()
    _assert_contract_shape(body)
    assert body["error_type"] == "UnauthorizedException"


def test_403_error_contract(client, create_user, auth_headers):
    user = create_user()
    response = client.post(
        "/api/category", json={"name": "Nope"}, headers=auth_headers(user)
    )
    assert response.status_code == 403
    body = response.json()
    _assert_contract_shape(body)
    assert body["error_type"] == "ForbiddenException"

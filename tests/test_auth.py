from app.core.security import create_access_token


def test_signup_succeeds_returns_user_response_shape(client):
    response = client.post(
        "/api/auth/sign-up",
        json={"name": "John Doe", "email": "john@example.com", "password": "SecurePass123!"},
    )
    assert response.status_code == 201
    body = response.json()
    assert set(body.keys()) == {"id", "name", "email"}
    assert body["name"] == "John Doe"
    assert body["email"] == "john@example.com"


def test_signup_duplicate_email_conflict(client):
    payload = {"name": "John Doe", "email": "dup@example.com", "password": "SecurePass123!"}
    assert client.post("/api/auth/sign-up", json=payload).status_code == 201
    response = client.post("/api/auth/sign-up", json=payload)
    assert response.status_code == 409
    assert response.json()["error_type"] == "ConflictException"


def test_login_with_correct_credentials_returns_token(client):
    client.post(
        "/api/auth/sign-up",
        json={"name": "John Doe", "email": "login@example.com", "password": "SecurePass123!"},
    )
    response = client.post(
        "/api/auth/login",
        json={"email": "login@example.com", "password": "SecurePass123!"},
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"access_token", "token_type", "expires_in", "email"}
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 1440
    assert body["email"] == "login@example.com"
    assert body["access_token"]


def test_login_with_wrong_password_unauthorized(client):
    client.post(
        "/api/auth/sign-up",
        json={"name": "John Doe", "email": "wrong@example.com", "password": "SecurePass123!"},
    )
    response = client.post(
        "/api/auth/login",
        json={"email": "wrong@example.com", "password": "WrongPass123!"},
    )
    assert response.status_code == 401
    assert response.json()["error_type"] == "UnauthorizedException"


def test_login_with_nonexistent_email_same_message(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "ghost@example.com", "password": "Whatever123!"},
    )
    assert response.status_code == 401
    assert response.json()["message"] == "Invalid email or password"


def test_protected_route_without_token_unauthorized(client):
    response = client.get("/api/cart/1")
    assert response.status_code == 401
    assert response.json()["error_type"] == "UnauthorizedException"


def test_protected_route_with_expired_token_unauthorized(client, create_user):
    user = create_user()
    token = create_access_token(user.id, user.email, user.is_admin, expires_minutes=-1)
    response = client.get(
        "/api/cart/1", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    assert response.json()["error_type"] == "UnauthorizedException"


def test_protected_route_with_garbage_token_unauthorized(client):
    response = client.get(
        "/api/cart/1", headers={"Authorization": "Bearer not.a.valid.jwt"}
    )
    assert response.status_code == 401
    assert response.json()["error_type"] == "UnauthorizedException"


def test_signup_missing_email_returns_400_not_422(client):
    response = client.post(
        "/api/auth/sign-up",
        json={"name": "John Doe", "password": "SecurePass123!"},
    )
    assert response.status_code == 400
    body = response.json()
    assert set(body.keys()) == {"message", "status_code", "error_type", "timestamp"}
    assert body["error_type"] == "ValidationError"

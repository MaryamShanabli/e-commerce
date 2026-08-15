import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.models import User
from app.cart.models import Cart
from app.core.db import Base, get_db
from app.core.security import create_access_token, hash_password
from app.main import app

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        except Exception:
            db_session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def create_user(db_session):
    counter = {"n": 0}

    def _create_user(is_admin: bool = False, email: str | None = None) -> User:
        counter["n"] += 1
        user = User(
            name=f"User {counter['n']}",
            email=email or f"user{counter['n']}@example.com",
            password_hash=hash_password("pass123"),
            is_admin=is_admin,
        )
        db_session.add(user)
        db_session.flush()
        db_session.add(Cart(user_id=user.id))
        db_session.commit()
        return user

    return _create_user


@pytest.fixture()
def auth_headers():
    def _auth_headers(user: User) -> dict:
        token = create_access_token(
            user_id=user.id, email=user.email, is_admin=user.is_admin, expires_minutes=1440
        )
        return {"Authorization": f"Bearer {token}"}

    return _auth_headers

from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.schemas import LoginRequest, LoginResponse, RegisterRequest, UserResponse
from app.cart.models import Cart
from app.core.config import get_settings
from app.core.exceptions import ConflictException, UnauthorizedException
from app.core.security import create_access_token, hash_password, verify_password


def register_user(db: Session, payload: RegisterRequest) -> UserResponse:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing is not None:
        raise ConflictException("Email already registered")
    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        is_admin=False,
    )
    db.add(user)
    db.flush()
    db.add(Cart(user_id=user.id))
    db.commit()
    db.refresh(user)
    return UserResponse(id=user.id, name=user.name, email=user.email)


def login_user(db: Session, payload: LoginRequest) -> LoginResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise UnauthorizedException("Invalid email or password")
    settings = get_settings()
    token = create_access_token(
        user_id=user.id,
        email=user.email,
        is_admin=user.is_admin,
        expires_minutes=settings.JWT_EXPIRE_MINUTES,
    )
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRE_MINUTES,
        email=user.email,
    )

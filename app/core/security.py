from datetime import datetime, timedelta, timezone

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.config import get_settings
from app.core.db import get_db
from app.core.exceptions import ForbiddenException, UnauthorizedException

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int, email: str, is_admin: bool, expires_minutes: int) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "is_admin": is_admin,
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise UnauthorizedException("Invalid or expired token") from exc


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise UnauthorizedException("Invalid or expired token")
    payload = decode_access_token(credentials.credentials)
    sub = payload.get("sub")
    if sub is None:
        raise UnauthorizedException("Invalid or expired token")
    try:
        user_id = int(sub)
    except (TypeError, ValueError) as exc:
        raise UnauthorizedException("Invalid or expired token") from exc
    user = db.get(User, user_id)
    if user is None:
        raise UnauthorizedException("Invalid or expired token")
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise ForbiddenException("Admin privileges required")
    return current_user


def require_owner_or_admin(resource_user_id: int, current_user: User = Depends(get_current_user)) -> None:
    if current_user.id != resource_user_id and not current_user.is_admin:
        raise ForbiddenException("You do not have access to this resource")

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.schemas import LoginRequest, LoginResponse, RegisterRequest, UserResponse
from app.auth.service import login_user, register_user
from app.core.db import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/sign-up", response_model=UserResponse, status_code=201)
def sign_up(payload: RegisterRequest, db: Session = Depends(get_db)) -> UserResponse:
    return register_user(db, payload)


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    return login_user(db, payload)

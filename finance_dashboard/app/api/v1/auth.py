"""
Authentication routes.
Paper applied: arXiv OAuth Token Security 2025
- Login returns both access + refresh tokens
- Refresh endpoint validates token type before issuing new access token
- Edge cases: wrong password, inactive account, invalid refresh token
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from app.api.deps import get_db
from app.security.password import verify_password
from app.security.jwt_handler import create_access_token, create_refresh_token, decode_token
from app.infrastructure.repositories.user_repo_impl import UserRepository

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


@router.post("/login", summary="Login and receive access + refresh tokens")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = UserRepository(db).get_by_email(payload.email)

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if user.status == "inactive":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive — contact an administrator",
        )

    token_data = {"sub": user.id, "role": user.role}
    return {
        "access_token":  create_access_token(token_data),
        "refresh_token": create_refresh_token(token_data),
        "token_type":    "bearer",
        "user": {
            "id":        user.id,
            "email":     user.email,
            "full_name": user.full_name,
            "role":      user.role,
        },
    }


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh", summary="Exchange a refresh token for a new access token")
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    token_payload = decode_token(payload.refresh_token)

    if token_payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Provided token is not a refresh token",
        )

    user = UserRepository(db).get_by_id(token_payload.get("sub"))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User no longer exists",
        )

    return {
        "access_token": create_access_token({"sub": user.id, "role": user.role}),
        "token_type":   "bearer",
    }

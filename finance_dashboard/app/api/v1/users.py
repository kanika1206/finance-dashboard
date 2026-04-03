"""
User management routes — admin only.
Paper applied: CHI 2025 API usability + IEEE Clean Architecture 2022
- Route guards use require_permission — business logic never lives in routes
- Duplicate email check before creation (edge case coverage)
- Admin cannot deactivate their own account (prevents lockout)
- PATCH used for partial updates, not PUT (AIP-aligned design)
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.api.deps import get_db
from app.security.rbac import Permission
from app.security.dependencies import require_permission
from app.security.password import hash_password
from app.infrastructure.repositories.user_repo_impl import UserRepository

router = APIRouter(prefix="/users", tags=["Users"])


class UserCreate(BaseModel):
    email:     EmailStr
    full_name: str
    password:  str
    role:      str = "viewer"


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role:      Optional[str] = None


@router.get("/", summary="List all users (admin only)")
def list_users(
    page:  int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(require_permission(Permission.USER_READ)),
    db: Session = Depends(get_db),
):
    return UserRepository(db).get_all(page=page, limit=limit)


@router.post("/", status_code=201, summary="Create a new user (admin only)")
def create_user(
    payload: UserCreate,
    user=Depends(require_permission(Permission.USER_MANAGE)),
    db: Session = Depends(get_db),
):
    repo = UserRepository(db)

    # Edge case: duplicate email
    if repo.email_exists(payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with email '{payload.email}' already exists",
        )

    valid_roles = {"viewer", "analyst", "admin"}
    if payload.role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid role '{payload.role}'. Must be one of: {valid_roles}",
        )

    new_user = repo.create({
        "email":           payload.email,
        "full_name":       payload.full_name,
        "hashed_password": hash_password(payload.password),
        "role":            payload.role,
    })
    return {
        "id":        new_user.id,
        "email":     new_user.email,
        "full_name": new_user.full_name,
        "role":      new_user.role,
        "status":    new_user.status,
    }


@router.patch("/{user_id}", summary="Update user details (admin only)")
def update_user(
    user_id: str,
    payload: UserUpdate,
    current_user=Depends(require_permission(Permission.USER_MANAGE)),
    db: Session = Depends(get_db),
):
    repo = UserRepository(db)
    update_data = payload.model_dump(exclude_none=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No fields provided for update",
        )

    if "role" in update_data and update_data["role"] not in {"viewer", "analyst", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid role value",
        )

    updated = repo.update(user_id, update_data)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return updated


@router.patch("/{user_id}/status", summary="Toggle user active/inactive (admin only)")
def toggle_status(
    user_id: str,
    current_user=Depends(require_permission(Permission.USER_MANAGE)),
    db: Session = Depends(get_db),
):
    # Edge case: admin cannot deactivate themselves
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own account status",
        )

    user = UserRepository(db).toggle_status(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return {"id": user.id, "email": user.email, "status": user.status}

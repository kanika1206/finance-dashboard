"""
FastAPI dependency guards for authentication and authorization.
Paper applied: IEEE Clean Architecture 2022 — cross-cutting concerns in one place
- get_current_user: validates JWT, checks user exists and is active
- require_permission: factory that returns a dependency guard for a specific permission
- Edge cases covered: expired token, wrong token type, inactive user, deleted user
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.security.jwt_handler import decode_token
from app.security.rbac import Permission, has_permission, Role
from app.infrastructure.database import SessionLocal
from app.infrastructure.repositories.user_repo_impl import UserRepository

bearer_scheme = HTTPBearer()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    payload = decode_token(credentials.credentials)

    # Ensure this is an access token, not a refresh token
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type — use access token",
        )

    user = UserRepository(db).get_by_id(payload.get("sub"))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User no longer exists",
        )
    if user.status == "inactive":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive — contact an administrator",
        )
    return user


def require_permission(permission: Permission):
    """
    Factory function — returns a FastAPI dependency that checks a specific permission.
    Usage: user = Depends(require_permission(Permission.RECORD_CREATE))
    """
    def guard(current_user=Depends(get_current_user)):
        if not has_permission(Role(current_user.role), permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied — your role does not have permission: {permission}",
            )
        return current_user
    return guard

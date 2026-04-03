"""
Role-Based Access Control — permission matrix.
Paper applied: JERR 2024 (RBAC best practices) + ACM MECC 2025 (contextual authorization)
- Permissions are associated with roles, never directly with users (JERR 2024)
- Fine-grained permission strings (resource:action) allow minimal privilege (arXiv 2025)
- ROLE_PERMISSIONS is the single source of truth — no scattered if/else checks
"""
from enum import Enum
from typing import Set


class Role(str, Enum):
    VIEWER  = "viewer"
    ANALYST = "analyst"
    ADMIN   = "admin"


class Permission(str, Enum):
    # Financial records
    RECORD_READ   = "record:read"
    RECORD_CREATE = "record:create"
    RECORD_UPDATE = "record:update"
    RECORD_DELETE = "record:delete"
    # Dashboard
    DASHBOARD_VIEW     = "dashboard:view"
    DASHBOARD_INSIGHTS = "dashboard:insights"
    # Users
    USER_READ   = "user:read"
    USER_MANAGE = "user:manage"


ROLE_PERMISSIONS: dict[Role, Set[Permission]] = {
    Role.VIEWER: {
        Permission.RECORD_READ,
        Permission.DASHBOARD_VIEW,
    },
    Role.ANALYST: {
        Permission.RECORD_READ,
        Permission.DASHBOARD_VIEW,
        Permission.DASHBOARD_INSIGHTS,
    },
    Role.ADMIN: set(Permission),  # full access
}


def has_permission(role: Role, permission: Permission) -> bool:
    """Check if a role has the required permission."""
    return permission in ROLE_PERMISSIONS.get(role, set())

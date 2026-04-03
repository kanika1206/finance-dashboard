"""
Unit tests for RBAC permission matrix.
Paper applied: IEEE Clean Architecture 2022 — testability as a design quality metric
Tests cover: role boundaries, permission grants, denial cases, admin completeness
"""
import pytest
from app.security.rbac import Role, Permission, has_permission


class TestViewerPermissions:
    def test_viewer_can_read_records(self):
        assert has_permission(Role.VIEWER, Permission.RECORD_READ)

    def test_viewer_can_view_dashboard(self):
        assert has_permission(Role.VIEWER, Permission.DASHBOARD_VIEW)

    def test_viewer_cannot_create_records(self):
        assert not has_permission(Role.VIEWER, Permission.RECORD_CREATE)

    def test_viewer_cannot_update_records(self):
        assert not has_permission(Role.VIEWER, Permission.RECORD_UPDATE)

    def test_viewer_cannot_delete_records(self):
        assert not has_permission(Role.VIEWER, Permission.RECORD_DELETE)

    def test_viewer_cannot_manage_users(self):
        assert not has_permission(Role.VIEWER, Permission.USER_MANAGE)

    def test_viewer_cannot_access_insights(self):
        assert not has_permission(Role.VIEWER, Permission.DASHBOARD_INSIGHTS)


class TestAnalystPermissions:
    def test_analyst_can_read_records(self):
        assert has_permission(Role.ANALYST, Permission.RECORD_READ)

    def test_analyst_can_view_dashboard(self):
        assert has_permission(Role.ANALYST, Permission.DASHBOARD_VIEW)

    def test_analyst_can_access_insights(self):
        assert has_permission(Role.ANALYST, Permission.DASHBOARD_INSIGHTS)

    def test_analyst_cannot_create_records(self):
        assert not has_permission(Role.ANALYST, Permission.RECORD_CREATE)

    def test_analyst_cannot_delete_records(self):
        assert not has_permission(Role.ANALYST, Permission.RECORD_DELETE)

    def test_analyst_cannot_manage_users(self):
        assert not has_permission(Role.ANALYST, Permission.USER_MANAGE)


class TestAdminPermissions:
    def test_admin_has_all_permissions(self):
        for perm in Permission:
            assert has_permission(Role.ADMIN, perm), f"Admin missing: {perm}"

    def test_admin_can_manage_users(self):
        assert has_permission(Role.ADMIN, Permission.USER_MANAGE)

    def test_admin_can_delete_records(self):
        assert has_permission(Role.ADMIN, Permission.RECORD_DELETE)


class TestUnknownRole:
    def test_unknown_role_has_no_permissions(self):
        # has_permission should return False for any unrecognised role string
        result = has_permission("hacker", Permission.RECORD_READ)  # type: ignore
        assert not result

"""
Integration tests — auth, records, and access control enforcement.
Paper applied: CHI 2025 API usability — tests verify the contract from a consumer perspective
Uses FastAPI TestClient with an in-memory SQLite database (isolated per test session).
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.infrastructure.database import Base
from app.api.deps import get_db
from app.security.password import hash_password
from app.infrastructure.models.user_model import UserModel
from app.infrastructure.models.record_model import FinancialRecordModel  # noqa

# --- Test database setup (in-memory SQLite) ---
TEST_DATABASE_URL = "sqlite:///./test.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    # Seed test users
    db = TestingSession()
    users = [
        UserModel(
            email="admin@test.com", full_name="Test Admin",
            hashed_password=hash_password("adminpass"), role="admin", status="active"
        ),
        UserModel(
            email="analyst@test.com", full_name="Test Analyst",
            hashed_password=hash_password("analystpass"), role="analyst", status="active"
        ),
        UserModel(
            email="viewer@test.com", full_name="Test Viewer",
            hashed_password=hash_password("viewerpass"), role="viewer", status="active"
        ),
        UserModel(
            email="inactive@test.com", full_name="Inactive User",
            hashed_password=hash_password("pass"), role="viewer", status="inactive"
        ),
    ]
    db.add_all(users)
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=test_engine)


client = TestClient(app, raise_server_exceptions=False)


def get_token(email: str, password: str) -> str:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


# --- Auth tests ---
class TestAuth:
    def test_login_success(self):
        resp = client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": "adminpass"})
        assert resp.status_code == 200
        assert "access_token" in resp.json()
        assert "refresh_token" in resp.json()

    def test_login_wrong_password(self):
        resp = client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": "wrong"})
        assert resp.status_code == 401

    def test_login_nonexistent_user(self):
        resp = client.post("/api/v1/auth/login", json={"email": "nobody@test.com", "password": "pass"})
        assert resp.status_code == 401

    def test_login_inactive_user(self):
        resp = client.post("/api/v1/auth/login", json={"email": "inactive@test.com", "password": "pass"})
        assert resp.status_code == 403

    def test_refresh_token(self):
        login = client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": "adminpass"})
        refresh_token = login.json()["refresh_token"]
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_access_token_rejected_as_refresh(self):
        access_token = get_token("admin@test.com", "adminpass")
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
        assert resp.status_code == 401


# --- Records tests ---
class TestRecords:
    def test_admin_can_create_record(self):
        token = get_token("admin@test.com", "adminpass")
        resp = client.post(
            "/api/v1/records/",
            json={"amount": 5000, "type": "income", "category": "salary", "record_date": "2024-01-15"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201

    def test_viewer_cannot_create_record(self):
        token = get_token("viewer@test.com", "viewerpass")
        resp = client.post(
            "/api/v1/records/",
            json={"amount": 100, "type": "expense", "category": "food", "record_date": "2024-01-15"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_viewer_can_read_records(self):
        token = get_token("viewer@test.com", "viewerpass")
        resp = client.get("/api/v1/records/", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert "data" in resp.json()

    def test_record_not_found_returns_404(self):
        token = get_token("viewer@test.com", "viewerpass")
        resp = client.get("/api/v1/records/nonexistent-id", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 404

    def test_negative_amount_rejected(self):
        token = get_token("admin@test.com", "adminpass")
        resp = client.post(
            "/api/v1/records/",
            json={"amount": -100, "type": "income", "category": "salary", "record_date": "2024-01-15"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    def test_invalid_date_range_rejected(self):
        token = get_token("viewer@test.com", "viewerpass")
        resp = client.get(
            "/api/v1/records/?date_from=2024-12-01&date_to=2024-01-01",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    def test_soft_delete_removes_from_listing(self):
        token = get_token("admin@test.com", "adminpass")
        # Create
        create_resp = client.post(
            "/api/v1/records/",
            json={"amount": 200, "type": "expense", "category": "utilities", "record_date": "2024-02-01"},
            headers={"Authorization": f"Bearer {token}"},
        )
        record_id = create_resp.json()["id"]
        # Delete
        client.delete(f"/api/v1/records/{record_id}", headers={"Authorization": f"Bearer {token}"})
        # Fetch — should 404
        get_resp = client.get(f"/api/v1/records/{record_id}", headers={"Authorization": f"Bearer {token}"})
        assert get_resp.status_code == 404

    def test_unauthenticated_request_rejected(self):
        resp = client.get("/api/v1/records/")
        assert resp.status_code == 403


# --- Dashboard tests ---
class TestDashboard:
    def test_viewer_can_see_summary(self):
        token = get_token("viewer@test.com", "viewerpass")
        resp = client.get("/api/v1/dashboard/summary", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "total_income" in data
        assert "total_expenses" in data
        assert "net_balance" in data

    def test_viewer_cannot_see_insights(self):
        token = get_token("viewer@test.com", "viewerpass")
        resp = client.get("/api/v1/dashboard/by-category", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_analyst_can_see_insights(self):
        token = get_token("analyst@test.com", "analystpass")
        resp = client.get("/api/v1/dashboard/by-category", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_trends_monthly(self):
        token = get_token("analyst@test.com", "analystpass")
        resp = client.get("/api/v1/dashboard/trends?period=monthly", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_trends_invalid_period(self):
        token = get_token("analyst@test.com", "analystpass")
        resp = client.get("/api/v1/dashboard/trends?period=yearly", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 422


# --- Health ---
class TestHealth:
    def test_health_check(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

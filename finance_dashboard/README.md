# Finance Dashboard API

A role-based financial records management backend built with **FastAPI + SQLAlchemy + SQLite**.

Designed according to Clean Architecture principles (IEEE ICoICT 2022), Domain-Driven Design patterns (arXiv DDD SLR 2025), AIP-aligned REST API design (CHI 2025), and OAuth/JWT security best practices (arXiv 2025).

---

## Quick Start

```bash
# 1. Clone and enter the project
cd finance_dashboard

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env .env.local              # Edit SECRET_KEY and ADMIN_PASSWORD as needed

# 5. Run the server
uvicorn app.main:app --reload

# 6. Open API docs
# http://localhost:8000/docs      ← Swagger UI
# http://localhost:8000/redoc     ← ReDoc
```

A default admin account is seeded automatically on first run:

| Field    | Value               |
|----------|---------------------|
| Email    | admin@finance.com   |
| Password | admin123            |

Change `ADMIN_EMAIL` and `ADMIN_PASSWORD` in `.env` before deployment.

---

## Architecture

The project follows **Clean Architecture** (IEEE ICoICT 2022) — business rules are isolated from frameworks, databases, and HTTP concerns.

```
Request
  │
  ▼
┌─────────────────────────────────┐
│  API Layer  (app/api/)          │  Routes only — no business logic
│  FastAPI routers, Pydantic I/O  │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│  Security Layer (app/security/) │  JWT, RBAC, permission guards
│  jwt_handler, rbac, deps        │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│  Infrastructure (app/infra/)    │  SQLAlchemy ORM, repositories
│  Models, concrete repos, DB     │
└─────────────────────────────────┘
```

**Key design principle:** Routes call repositories. Repositories call the DB. Business rules (validation, access control, aggregation logic) never cross layer boundaries.

---

## Role Model

| Permission            | Viewer | Analyst | Admin |
|-----------------------|:------:|:-------:|:-----:|
| View records          | ✅     | ✅      | ✅    |
| View dashboard        | ✅     | ✅      | ✅    |
| Dashboard insights    | ❌     | ✅      | ✅    |
| Create records        | ❌     | ❌      | ✅    |
| Update records        | ❌     | ❌      | ✅    |
| Delete records        | ❌     | ❌      | ✅    |
| Read users            | ❌     | ❌      | ✅    |
| Manage users          | ❌     | ❌      | ✅    |

Permissions are attached to **roles**, never directly to users (JERR 2024 RBAC best practice).

---

## API Reference

### Authentication
| Method | Endpoint              | Description                        |
|--------|-----------------------|------------------------------------|
| POST   | `/api/v1/auth/login`  | Login — returns access + refresh tokens |
| POST   | `/api/v1/auth/refresh`| Exchange refresh token for new access token |

### Users _(Admin only)_
| Method | Endpoint                      | Description              |
|--------|-------------------------------|--------------------------|
| GET    | `/api/v1/users/`              | List all users (paginated) |
| POST   | `/api/v1/users/`              | Create a new user         |
| PATCH  | `/api/v1/users/{id}`          | Update name or role       |
| PATCH  | `/api/v1/users/{id}/status`   | Toggle active / inactive  |

### Financial Records
| Method | Endpoint                  | Description                              |
|--------|---------------------------|------------------------------------------|
| GET    | `/api/v1/records/`        | List records (filter + search + paginate) |
| POST   | `/api/v1/records/`        | Create a record _(admin only)_           |
| GET    | `/api/v1/records/{id}`    | Get record by ID                         |
| PATCH  | `/api/v1/records/{id}`    | Update a record _(admin only)_           |
| DELETE | `/api/v1/records/{id}`    | Soft-delete a record _(admin only)_      |

**Record list query parameters:**

| Param      | Type   | Description                          |
|------------|--------|--------------------------------------|
| `type`     | string | `income` or `expense`                |
| `category` | string | Filter by exact category             |
| `date_from`| date   | Records on or after this date        |
| `date_to`  | date   | Records on or before this date       |
| `search`   | string | Search across category and notes     |
| `page`     | int    | Page number (default: 1)             |
| `limit`    | int    | Results per page (default: 20, max: 100) |

### Dashboard
| Method | Endpoint                       | Access         | Description                        |
|--------|--------------------------------|----------------|------------------------------------|
| GET    | `/api/v1/dashboard/summary`    | All roles      | Total income, expenses, net balance |
| GET    | `/api/v1/dashboard/by-category`| Analyst, Admin | Totals grouped by category          |
| GET    | `/api/v1/dashboard/trends`     | Analyst, Admin | Monthly or weekly trends (`?period=monthly\|weekly`) |
| GET    | `/api/v1/dashboard/recent`     | All roles      | Most recent records (`?limit=10`)   |

---

## Data Model

### users
| Column           | Type    | Notes                          |
|------------------|---------|--------------------------------|
| id               | UUID    | Primary key                    |
| email            | string  | Unique, indexed                |
| full_name        | string  |                                |
| hashed_password  | string  | bcrypt                         |
| role             | enum    | viewer / analyst / admin       |
| status           | enum    | active / inactive              |
| created_at       | datetime| DB-managed                     |
| updated_at       | datetime| DB-managed                     |

### financial_records
| Column      | Type       | Notes                                      |
|-------------|------------|--------------------------------------------|
| id          | UUID       | Primary key                                |
| created_by  | FK → users |                                            |
| amount      | Decimal(12,2) | Never Float — avoids rounding errors    |
| type        | enum       | income / expense                           |
| category    | string     | Indexed, stored lowercase                  |
| record_date | date       | Indexed for range queries                  |
| notes       | string     | Optional                                   |
| is_deleted  | boolean    | Soft delete — records never removed        |
| created_at  | datetime   |                                            |
| updated_at  | datetime   |                                            |

---

## Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# With coverage
pip install pytest-cov
pytest --cov=app --cov-report=term-missing
```

---

## Project Structure

```
finance_dashboard/
├── app/
│   ├── api/v1/
│   │   ├── auth.py          # Login, token refresh
│   │   ├── users.py         # User CRUD + status management
│   │   ├── records.py       # Financial records CRUD + filtering
│   │   └── dashboard.py     # Aggregated analytics
│   ├── infrastructure/
│   │   ├── database.py      # SQLAlchemy engine + session
│   │   ├── models/          # ORM models
│   │   └── repositories/    # All DB queries
│   ├── security/
│   │   ├── jwt_handler.py   # Token creation + validation
│   │   ├── password.py      # bcrypt hashing
│   │   ├── rbac.py          # Role + permission matrix
│   │   └── dependencies.py  # FastAPI auth guards
│   ├── middleware/
│   │   └── rate_limiter.py  # Sliding window rate limiting
│   └── main.py              # App factory
├── tests/
│   ├── unit/                # RBAC + validator tests
│   └── integration/         # Full API endpoint tests
├── .env
├── requirements.txt
└── README.md
```

---

## Assumptions Made

1. **SQLite for persistence** — simple setup for assessment. Swap `DATABASE_URL` in `.env` to a PostgreSQL URI for production with no code changes.
2. **In-memory rate limiting** — sufficient for a single-server deployment. Redis would be used in a multi-instance setup.
3. **Soft delete only** — records are never permanently removed. This supports audit trails and is consistent with financial data best practices.
4. **Admin seeds on startup** — a default admin is created automatically if none exists, to avoid a bootstrapping problem.
5. **category normalized to lowercase** — ensures consistent grouping in dashboard aggregations regardless of how it was entered.
6. **Decimal(12,2) for amounts** — financial data should never use float due to IEEE 754 rounding errors.

---

## Tradeoffs

| Decision | Chosen | Alternative | Reason |
|----------|--------|-------------|--------|
| Database | SQLite | PostgreSQL | Simplicity for assessment |
| Auth | JWT stateless | Sessions | Stateless scales better |
| Delete | Soft | Hard | Preserves audit history |
| Rate limit | In-memory | Redis | Single instance sufficient |
| ORM | SQLAlchemy | Raw SQL | Safety + portability |
| Architecture | Clean/layered | MVC | Better separation, testability |

---

## Research Papers Applied

| Paper | Applied To |
|-------|------------|
| IEEE Clean Architecture (ICoICT 2022) | Folder structure, layer separation |
| DDD Systematic Literature Review (arXiv 2025) | Use case isolation, bounded contexts |
| CHI 2025 API Usability Study | Route design, AIP-aligned naming |
| arXiv OAuth Token Security (2025) | JWT implementation, CIA triad |
| JERR 2024 RBAC Best Practices | Permission matrix, role-not-user model |
| ACM MECC 2025 Contextual Authorization | Dependency-based permission guards |
| ACM Schema Design Survey (2024) | Data types, enum constraints, indexing |
| IJRPR MySQL Performance (2024) | Decimal vs float, index placement |
| Scalable REST APIs (Hegde, 2024) | Filtering, pagination, error responses |
| arXiv API Gateway Governance (2025) | Rate limiting as unified API concern |

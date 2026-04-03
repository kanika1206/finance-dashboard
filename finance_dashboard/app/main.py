"""
Application factory — wires everything together.
Paper applied: IEEE Clean Architecture 2022 + arXiv API Gateway Governance 2025
- All routers registered with versioned prefix /api/v1
- Rate limiting applied as ASGI middleware
- CORS configured (open for assessment; restrict origins in production)
- Global exception handler ensures consistent error response shape
- DB tables auto-created on startup (Alembic migrations recommended for production)
"""
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.infrastructure.database import Base, engine
from app.infrastructure.models import user_model, record_model  # noqa: F401 — ensure models registered
from app.api.v1 import auth, users, records, dashboard
from app.middleware.rate_limiter import rate_limit_middleware
from app.security.password import hash_password
from app.infrastructure.database import SessionLocal
from app.infrastructure.repositories.user_repo_impl import UserRepository

load_dotenv()

# Create tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Finance Dashboard API",
    description=(
        "Role-based financial records management system.\n\n"
        "**Roles:** viewer · analyst · admin\n\n"
        "**Auth:** Bearer JWT — login via `/api/v1/auth/login` to get your token."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Restrict to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(rate_limit_middleware)


# --- Global error handler ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred",
            "type":   type(exc).__name__,
        },
    )


# --- Routers ---
app.include_router(auth.router,      prefix="/api/v1")
app.include_router(users.router,     prefix="/api/v1")
app.include_router(records.router,   prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")


# --- Health check ---
@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "version": "1.0.0"}


# --- Seed default admin on first run ---
@app.on_event("startup")
def seed_admin():
    db = SessionLocal()
    try:
        repo = UserRepository(db)
        admin_email = os.getenv("ADMIN_EMAIL", "admin@finance.com")
        if not repo.email_exists(admin_email):
            repo.create({
                "email":           admin_email,
                "full_name":       "System Admin",
                "hashed_password": hash_password(os.getenv("ADMIN_PASSWORD", "admin123")),
                "role":            "admin",
                "status":          "active",
            })
            print(f"[seed] Default admin created: {admin_email}")
    finally:
        db.close()

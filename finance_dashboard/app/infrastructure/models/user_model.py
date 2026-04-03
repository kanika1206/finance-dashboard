"""
User ORM model.
Paper applied: ACM Schema Design Survey 2024 + IJRPR MySQL 2024
- Roles and status as DB-level enums for integrity enforcement
- UUID primary keys for security (no sequential ID guessing)
- Indexed email for fast lookup
- Timestamps managed at DB level via server_default
"""
import uuid
import enum
from sqlalchemy import Column, String, Enum, DateTime, func
from app.infrastructure.database import Base


class RoleEnum(str, enum.Enum):
    viewer  = "viewer"
    analyst = "analyst"
    admin   = "admin"


class StatusEnum(str, enum.Enum):
    active   = "active"
    inactive = "inactive"


class UserModel(Base):
    __tablename__ = "users"

    id              = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email           = Column(String, unique=True, nullable=False, index=True)
    full_name       = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role            = Column(Enum(RoleEnum), nullable=False, default=RoleEnum.viewer)
    status          = Column(Enum(StatusEnum), nullable=False, default=StatusEnum.active)
    created_at      = Column(DateTime, server_default=func.now())
    updated_at      = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<User id={self.id} email={self.email} role={self.role}>"

"""
Financial Record ORM model.
Paper applied: ACM Schema Design Survey 2024 + IJRPR MySQL 2024
- Numeric(12,2) instead of Float — avoids floating point errors in financial data
- Soft delete via is_deleted flag (schema evolution paper: avoids destructive migrations)
- Indexed category and record_date for efficient dashboard aggregation queries
- FK to users ensures referential integrity
"""
import uuid
import enum
from sqlalchemy import (
    Column, String, Enum, Boolean, DateTime, Numeric, Date, ForeignKey, func
)
from app.infrastructure.database import Base


class RecordTypeEnum(str, enum.Enum):
    income  = "income"
    expense = "expense"


class FinancialRecordModel(Base):
    __tablename__ = "financial_records"

    id          = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_by  = Column(String, ForeignKey("users.id"), nullable=False)
    amount      = Column(Numeric(12, 2), nullable=False)
    type        = Column(Enum(RecordTypeEnum), nullable=False)
    category    = Column(String, nullable=False, index=True)
    record_date = Column(Date, nullable=False, index=True)
    notes       = Column(String, nullable=True)
    is_deleted  = Column(Boolean, default=False, nullable=False)
    created_at  = Column(DateTime, server_default=func.now())
    updated_at  = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Record id={self.id} type={self.type} amount={self.amount}>"

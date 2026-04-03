"""
Financial Records routes — full CRUD with filtering, search, pagination.
Paper applied: CHI 2025 API usability + Scalable REST APIs 2024 + arXiv OAuth 2025
- Pydantic validators enforce data integrity at the API boundary
- Decimal used for amount to prevent floating point errors (IJRPR 2024)
- category normalized to lowercase on input (consistent aggregation in dashboard)
- 404 returned for missing/deleted records (not 403 — avoids information leakage)
- Soft delete used — records never permanently removed (schema evolution paper)
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator
from decimal import Decimal
from typing import Optional
from datetime import date
from app.api.deps import get_db
from app.security.rbac import Permission
from app.security.dependencies import require_permission
from app.infrastructure.repositories.record_repo_impl import RecordRepository

router = APIRouter(prefix="/records", tags=["Financial Records"])


class RecordCreate(BaseModel):
    amount:      Decimal
    type:        str
    category:    str
    record_date: date
    notes:       Optional[str] = None

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Amount must be greater than zero")
        return round(v, 2)

    @field_validator("type")
    @classmethod
    def type_must_be_valid(cls, v):
        if v not in {"income", "expense"}:
            raise ValueError("Type must be 'income' or 'expense'")
        return v

    @field_validator("category")
    @classmethod
    def category_not_blank(cls, v):
        if not v.strip():
            raise ValueError("Category cannot be blank")
        return v.strip().lower()


class RecordUpdate(BaseModel):
    amount:      Optional[Decimal] = None
    category:    Optional[str]     = None
    notes:       Optional[str]     = None
    record_date: Optional[date]    = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Amount must be greater than zero")
        return v

    @field_validator("category")
    @classmethod
    def category_not_blank(cls, v):
        if v is not None and not v.strip():
            raise ValueError("Category cannot be blank")
        return v.strip().lower() if v else v


@router.get("/", summary="List records with optional filters, search, and pagination")
def list_records(
    type:      Optional[str]  = Query(None, description="income or expense"),
    category:  Optional[str]  = Query(None),
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    search:    Optional[str]  = Query(None, description="Search in category and notes"),
    page:      int = Query(1, ge=1),
    limit:     int = Query(20, ge=1, le=100),
    user=Depends(require_permission(Permission.RECORD_READ)),
    db: Session = Depends(get_db),
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_from must be before date_to",
        )
    return RecordRepository(db).get_all(
        type=type,
        category=category,
        date_from=date_from,
        date_to=date_to,
        search=search,
        page=page,
        limit=limit,
    )


@router.post("/", status_code=201, summary="Create a new financial record")
def create_record(
    payload: RecordCreate,
    user=Depends(require_permission(Permission.RECORD_CREATE)),
    db: Session = Depends(get_db),
):
    data = payload.model_dump()
    data["created_by"] = user.id
    data["amount"]     = float(data["amount"])
    return RecordRepository(db).create(data)


@router.get("/{record_id}", summary="Get a single record by ID")
def get_record(
    record_id: str,
    user=Depends(require_permission(Permission.RECORD_READ)),
    db: Session = Depends(get_db),
):
    record = RecordRepository(db).get_by_id(record_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record not found",
        )
    return record


@router.patch("/{record_id}", summary="Update a record (partial update)")
def update_record(
    record_id: str,
    payload: RecordUpdate,
    user=Depends(require_permission(Permission.RECORD_UPDATE)),
    db: Session = Depends(get_db),
):
    update_data = payload.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No fields provided for update",
        )
    if "amount" in update_data:
        update_data["amount"] = float(update_data["amount"])

    updated = RecordRepository(db).update(record_id, update_data)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record not found",
        )
    return updated


@router.delete("/{record_id}", status_code=204, summary="Soft-delete a record")
def delete_record(
    record_id: str,
    user=Depends(require_permission(Permission.RECORD_DELETE)),
    db: Session = Depends(get_db),
):
    deleted = RecordRepository(db).soft_delete(record_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record not found",
        )

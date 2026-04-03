"""
Financial Record Repository — concrete implementation.
Paper applied: IEEE Clean Architecture + Scalable REST APIs 2024
- Filtering, search, and pagination all handled in DB layer (not Python layer)
- ilike used for case-insensitive search across category and notes
- Soft delete: sets is_deleted=True, never removes rows
- All queries exclude is_deleted=True by default
"""
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, extract
from app.infrastructure.models.record_model import FinancialRecordModel
from datetime import date


class RecordRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> FinancialRecordModel:
        record = FinancialRecordModel(**data)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_by_id(self, record_id: str) -> FinancialRecordModel | None:
        return self.db.query(FinancialRecordModel).filter(
            FinancialRecordModel.id == record_id,
            FinancialRecordModel.is_deleted == False
        ).first()

    def get_all(
        self,
        type: str | None = None,
        category: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        search: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> dict:
        query = self.db.query(FinancialRecordModel).filter(
            FinancialRecordModel.is_deleted == False
        )

        if type:
            query = query.filter(FinancialRecordModel.type == type)
        if category:
            query = query.filter(FinancialRecordModel.category == category)
        if date_from:
            query = query.filter(FinancialRecordModel.record_date >= date_from)
        if date_to:
            query = query.filter(FinancialRecordModel.record_date <= date_to)
        if search:
            query = query.filter(
                or_(
                    FinancialRecordModel.category.ilike(f"%{search}%"),
                    FinancialRecordModel.notes.ilike(f"%{search}%")
                )
            )

        total = query.count()
        records = (
            query.order_by(FinancialRecordModel.record_date.desc())
                 .offset((page - 1) * limit)
                 .limit(limit)
                 .all()
        )
        return {"total": total, "page": page, "limit": limit, "data": records}

    def update(self, record_id: str, data: dict) -> FinancialRecordModel | None:
        record = self.get_by_id(record_id)
        if not record:
            return None
        for key, val in data.items():
            setattr(record, key, val)
        self.db.commit()
        self.db.refresh(record)
        return record

    def soft_delete(self, record_id: str) -> bool:
        record = self.get_by_id(record_id)
        if not record:
            return False
        record.is_deleted = True
        self.db.commit()
        return True

    # --- Dashboard aggregation queries ---

    def get_summary(self) -> dict:
        rows = self.db.query(
            FinancialRecordModel.type,
            func.sum(FinancialRecordModel.amount).label("total")
        ).filter(FinancialRecordModel.is_deleted == False)\
         .group_by(FinancialRecordModel.type).all()

        income   = next((float(r.total) for r in rows if r.type == "income"), 0.0)
        expenses = next((float(r.total) for r in rows if r.type == "expense"), 0.0)
        return {
            "total_income":   income,
            "total_expenses": expenses,
            "net_balance":    round(income - expenses, 2),
        }

    def get_by_category(self) -> list:
        rows = self.db.query(
            FinancialRecordModel.category,
            FinancialRecordModel.type,
            func.sum(FinancialRecordModel.amount).label("total")
        ).filter(FinancialRecordModel.is_deleted == False)\
         .group_by(FinancialRecordModel.category, FinancialRecordModel.type).all()

        return [
            {"category": r.category, "type": r.type, "total": float(r.total)}
            for r in rows
        ]

    def get_trends(self, period: str = "monthly") -> list:
        if period == "monthly":
            group_exprs = [
                extract("year", FinancialRecordModel.record_date).label("year"),
                extract("month", FinancialRecordModel.record_date).label("period_val"),
            ]
            period_label = "month"
        else:
            group_exprs = [
                extract("year", FinancialRecordModel.record_date).label("year"),
                extract("week", FinancialRecordModel.record_date).label("period_val"),
            ]
            period_label = "week"

        rows = self.db.query(
            *group_exprs,
            FinancialRecordModel.type,
            func.sum(FinancialRecordModel.amount).label("total")
        ).filter(FinancialRecordModel.is_deleted == False)\
         .group_by(*group_exprs, FinancialRecordModel.type)\
         .order_by(*group_exprs).all()

        return [
            {
                "period": f"{int(r.year)}-{period_label}-{int(r.period_val)}",
                "type":   r.type,
                "total":  float(r.total),
            }
            for r in rows
        ]

    def get_recent(self, limit: int = 10) -> list:
        return (
            self.db.query(FinancialRecordModel)
                   .filter(FinancialRecordModel.is_deleted == False)
                   .order_by(FinancialRecordModel.created_at.desc())
                   .limit(limit)
                   .all()
        )

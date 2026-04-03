"""
Dashboard summary routes — aggregated analytics.
Paper applied: DDD SLR arXiv 2025 — use case isolation
- All aggregation logic lives in the repository layer (not in routes)
- Routes are thin — they only call the appropriate repository method
- Analyst and Admin can see insights; Viewer can only see basic summary + recent
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Literal
from app.api.deps import get_db
from app.security.rbac import Permission
from app.security.dependencies import require_permission
from app.infrastructure.repositories.record_repo_impl import RecordRepository

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", summary="Total income, expenses, and net balance")
def get_summary(
    user=Depends(require_permission(Permission.DASHBOARD_VIEW)),
    db: Session = Depends(get_db),
):
    return RecordRepository(db).get_summary()


@router.get("/by-category", summary="Totals grouped by category (analyst + admin)")
def get_by_category(
    user=Depends(require_permission(Permission.DASHBOARD_INSIGHTS)),
    db: Session = Depends(get_db),
):
    return RecordRepository(db).get_by_category()


@router.get("/trends", summary="Monthly or weekly trends (analyst + admin)")
def get_trends(
    period: Literal["monthly", "weekly"] = Query("monthly"),
    user=Depends(require_permission(Permission.DASHBOARD_INSIGHTS)),
    db: Session = Depends(get_db),
):
    return RecordRepository(db).get_trends(period=period)


@router.get("/recent", summary="Most recent financial activity")
def get_recent(
    limit: int = Query(10, ge=1, le=50),
    user=Depends(require_permission(Permission.DASHBOARD_VIEW)),
    db: Session = Depends(get_db),
):
    records = RecordRepository(db).get_recent(limit=limit)
    return {"count": len(records), "data": records}

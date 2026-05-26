from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...domain.schemas import DashboardStats, ModelUsageRow, PlatformUsageRow, UsageTrendPoint
from ...services.dashboard_service import DashboardService
from ..deps import get_current_user_id, get_session

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def stats(
    user_id: Annotated[int, Depends(get_current_user_id)],
    session: Annotated[Session, Depends(get_session)],
):
    return DashboardService(session).stats(user_id)


@router.get("/models", response_model=list[ModelUsageRow])
def models(
    user_id: Annotated[int, Depends(get_current_user_id)],
    session: Annotated[Session, Depends(get_session)],
):
    return DashboardService(session).model_usage(user_id)


@router.get("/platforms", response_model=list[PlatformUsageRow])
def platforms(
    user_id: Annotated[int, Depends(get_current_user_id)],
    session: Annotated[Session, Depends(get_session)],
):
    return DashboardService(session).platform_usage(user_id)


@router.get("/trend", response_model=list[UsageTrendPoint])
def trend(
    user_id: Annotated[int, Depends(get_current_user_id)],
    session: Annotated[Session, Depends(get_session)],
    days: int = 7,
):
    return DashboardService(session).usage_trend(user_id, days=min(max(days, 1), 90))

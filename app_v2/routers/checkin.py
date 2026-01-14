"""
FastAPI router for Check-in system endpoints.

Provides endpoints for check-in operations and analytics.
"""

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query

from app_v2.dependencies import (
    require_auth,
    get_checkin_service,
    get_checkin_analytics,
    get_insight_generator,
)
from app_v2.services.checkin.checkin_service import CheckInService
from app_v2.services.checkin.checkin_analytics import CheckInAnalytics
from app_v2.services.checkin.insight_generator import InsightGenerator
from app_v2.schemas.checkin import (
    CheckInRequest,
    CheckInResponse,
    SubmitCheckInResponse,
    TodayCheckInResponse,
    HistoryResponse,
    StreakResponse,
    TrendDataResponse,
)
from app_v2.pipelines import checkin as pipelines

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/checkin", tags=["checkin"])


@router.post("", response_model=SubmitCheckInResponse)
async def submit_checkin(
    body: CheckInRequest,
    user: Annotated[dict, Depends(require_auth)],
    checkin_service: Annotated[CheckInService, Depends(get_checkin_service)],
    checkin_analytics: Annotated[CheckInAnalytics, Depends(get_checkin_analytics)],
    insight_generator: Annotated[InsightGenerator, Depends(get_insight_generator)],
):
    """
    Submit a daily check-in.

    Creates or updates today's check-in and returns streak and AI insight.
    """
    metrics = {
        "mood": body.mood,
        "physicalEnergy": body.physicalEnergy,
        "mentalEnergy": body.mentalEnergy,
        "sleep": body.sleep,
        "stress": body.stress
    }

    result = await pipelines.submit_checkin_pipeline(
        checkin_service=checkin_service,
        checkin_analytics=checkin_analytics,
        insight_generator=insight_generator,
        user_id=str(user["_id"]),
        metrics=metrics,
        notes=body.notes
    )

    return SubmitCheckInResponse(**result)


@router.get("/today", response_model=TodayCheckInResponse)
async def get_today_checkin(
    user: Annotated[dict, Depends(require_auth)],
    checkin_service: Annotated[CheckInService, Depends(get_checkin_service)],
):
    """
    Get today's check-in status.

    Returns whether user has checked in today and the check-in data if exists.
    """
    result = await pipelines.get_today_checkin_pipeline(
        checkin_service=checkin_service,
        user_id=str(user["_id"])
    )

    checkin_response = None
    if result["checkin"]:
        checkin_response = CheckInResponse(**result["checkin"])

    return TodayCheckInResponse(
        hasCheckedInToday=result["hasCheckedInToday"],
        checkin=checkin_response
    )


@router.get("/history", response_model=HistoryResponse)
async def get_history(
    user: Annotated[dict, Depends(require_auth)],
    checkin_service: Annotated[CheckInService, Depends(get_checkin_service)],
    startDate: Optional[str] = Query(None, description="YYYY-MM-DD format"),
    endDate: Optional[str] = Query(None, description="YYYY-MM-DD format"),
    limit: int = Query(30, ge=1, le=90),
    offset: int = Query(0, ge=0),
):
    """
    Get check-in history with pagination.

    Optional date range filtering and pagination support.
    """
    result = await pipelines.get_history_pipeline(
        checkin_service=checkin_service,
        user_id=str(user["_id"]),
        start_date=startDate,
        end_date=endDate,
        limit=limit,
        offset=offset
    )

    return HistoryResponse(
        checkins=[CheckInResponse(**c) for c in result["checkins"]],
        total=result["total"],
        limit=result["limit"],
        offset=result["offset"],
        hasMore=result["hasMore"]
    )


@router.get("/streak", response_model=StreakResponse)
async def get_streak(
    user: Annotated[dict, Depends(require_auth)],
    checkin_analytics: Annotated[CheckInAnalytics, Depends(get_checkin_analytics)],
):
    """
    Get current streak count.

    Returns number of consecutive days user has checked in.
    """
    streak = await pipelines.get_streak_pipeline(
        checkin_analytics=checkin_analytics,
        user_id=str(user["_id"])
    )

    return StreakResponse(streak=streak)


@router.get("/trends", response_model=TrendDataResponse)
async def get_trends(
    user: Annotated[dict, Depends(require_auth)],
    checkin_analytics: Annotated[CheckInAnalytics, Depends(get_checkin_analytics)],
    period: int = Query(30, description="7, 30, or 90 days"),
):
    """
    Get trend data for graphs.

    Returns formatted data with values and percentage changes.
    """
    if period not in [7, 30, 90]:
        period = 30

    result = await pipelines.get_trends_pipeline(
        checkin_analytics=checkin_analytics,
        user_id=str(user["_id"]),
        period=period
    )

    return TrendDataResponse(**result)

"""
FastAPI router for Check-in system endpoints.

Provides endpoints for check-in operations and analytics.
"""

import logging
from typing import Annotated

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
from app_v2.schemas.checkin import CheckInRequest
from common.utils import success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/checkin", tags=["checkin"])


@router.post("")
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
    from app_v2.pipelines import checkin as pipelines

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
        notes=None
    )

    return success_response({
        "streak": result.get("streak", 0),
        "insight": result.get("insight", ""),
        "tip": result.get("tip", "")
    })


@router.get("/trends")
async def get_trends(
    user: Annotated[dict, Depends(require_auth)],
    checkin_analytics: Annotated[CheckInAnalytics, Depends(get_checkin_analytics)],
    period: int = Query(30, description="7, 30, or 90 days"),
):
    """
    Get trend data for graphs.

    Returns formatted data with values and percentage changes.
    """
    from app_v2.pipelines import checkin as pipelines

    if period not in [7, 30, 90]:
        period = 30

    result = await pipelines.get_trends_pipeline(
        checkin_analytics=checkin_analytics,
        user_id=str(user["_id"]),
        period=period
    )

    return success_response({
        "dataPoints": result.get("dataPoints", 0),
        "moodValues": result.get("moodValues", []),
        "moodChange": result.get("moodChange", 0),
        "energyValues": result.get("energyValues", []),
        "energyChange": result.get("energyChange", 0),
        "stressValues": result.get("stressValues", []),
        "stressChange": result.get("stressChange", 0)
    })

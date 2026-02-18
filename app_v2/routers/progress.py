"""
FastAPI router for Progress system endpoints.

Provides endpoints for stats and insights.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from app_v2.dependencies import (
    require_auth,
    get_stats_service,
    get_insight_service,
    get_insight_engine,
)
from app_v2.services.progress.stats_service import ProgressStatsService
from app_v2.services.progress.insight_service import InsightService
from app_v2.services.progress.insight_engine import InsightEngine
from common.utils import success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("/stats")
async def get_stats(
    user: Annotated[dict, Depends(require_auth)],
    stats_service: Annotated[ProgressStatsService, Depends(get_stats_service)],
):
    """
    Get aggregated user progress statistics.

    Returns streak, checkins, lessons, and sessions counts.
    """
    stats = await stats_service.get_stats(str(user["_id"]))

    return success_response({
        "streak": stats.get("streak", 0),
        "checkins": stats.get("checkins", 0),
        "lessons": stats.get("lessons", 0),
        "sessions": stats.get("sessions", 0),
    })


@router.get("/insights")
async def get_insights(
    user: Annotated[dict, Depends(require_auth)],
    insight_engine: Annotated[InsightEngine, Depends(get_insight_engine)],
    insight_service: Annotated[InsightService, Depends(get_insight_service)],
):
    """
    Get AI-generated insights based on user's check-in history.

    Returns list of insights with title and description.
    """
    await insight_engine.generate_insights(str(user["_id"]))

    insights = await insight_service.get_active_insights(str(user["_id"]))

    return success_response({
        "insights": [
            {
                "title": i.get("title", ""),
                "description": i.get("description", ""),
            }
            for i in insights
        ]
    })

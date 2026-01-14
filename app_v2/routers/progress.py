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
from app_v2.schemas.progress import (
    StatsResponse,
    InsightResponse,
    InsightsListResponse,
    UnreadCountResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    user: Annotated[dict, Depends(require_auth)],
    stats_service: Annotated[ProgressStatsService, Depends(get_stats_service)],
):
    """Get aggregated user progress statistics."""
    stats = await stats_service.get_stats(str(user["_id"]))
    return StatsResponse(**stats)


@router.get("/insights", response_model=InsightsListResponse)
async def get_insights(
    user: Annotated[dict, Depends(require_auth)],
    insight_engine: Annotated[InsightEngine, Depends(get_insight_engine)],
    insight_service: Annotated[InsightService, Depends(get_insight_service)],
):
    """Get insights, generating new ones if patterns are detected."""
    await insight_engine.generate_insights(str(user["_id"]))

    insights = await insight_service.get_active_insights(str(user["_id"]))

    return InsightsListResponse(
        insights=[InsightResponse(**i) for i in insights]
    )


@router.post("/insights/{insight_id}/read", response_model=InsightResponse)
async def mark_insight_read(
    insight_id: str,
    user: Annotated[dict, Depends(require_auth)],
    insight_service: Annotated[InsightService, Depends(get_insight_service)],
):
    """Mark an insight as read."""
    insight = await insight_service.mark_as_read(
        insight_id=insight_id,
        user_id=str(user["_id"])
    )
    return InsightResponse(**insight)


@router.get("/insights/count", response_model=UnreadCountResponse)
async def get_unread_count(
    user: Annotated[dict, Depends(require_auth)],
    insight_service: Annotated[InsightService, Depends(get_insight_service)],
):
    """Get count of unread insights."""
    count = await insight_service.get_unread_count(str(user["_id"]))
    return UnreadCountResponse(count=count)

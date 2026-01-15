"""
FastAPI router for Dashboard endpoint.

Provides a consolidated dashboard view for the frontend.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from app_v2.dependencies import (
    require_auth,
    get_checkin_service,
    get_checkin_analytics,
    get_insight_service,
)
from common.utils import success_response

logger = logging.getLogger(__name__)

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
async def get_dashboard(
    user: Annotated[dict, Depends(require_auth)],
):
    """
    Get dashboard data for the current user.

    Returns consolidated data including today's check-in, streak,
    insights count, and upcoming events.
    """
    from app_v2.dependencies import get_checkin_service, get_checkin_analytics, get_insight_service

    checkin_service = get_checkin_service()
    checkin_analytics = get_checkin_analytics()
    insight_service = get_insight_service()

    user_id = str(user["_id"])

    # Get today's check-in
    todays_checkin = await checkin_service.get_today_checkin(user_id)

    # Get streak
    streak = await checkin_analytics.get_streak(user_id)

    # Get insights count
    insights_count = await insight_service.get_unread_count(user_id)

    # Format today's checkin data
    checkin_data = None
    if todays_checkin:
        checkin_data = {
            "mood": todays_checkin.get("metrics", {}).get("mood"),
            "physicalEnergy": todays_checkin.get("metrics", {}).get("physicalEnergy"),
            "mentalEnergy": todays_checkin.get("metrics", {}).get("mentalEnergy"),
            "sleep": todays_checkin.get("metrics", {}).get("sleep"),
            "stress": todays_checkin.get("metrics", {}).get("stress"),
        }

    return success_response({
        "todaysCheckin": checkin_data,
        "streak": streak,
        "insightsCount": insights_count,
        "todaysFocus": None,  # Placeholder for learning module focus
        "nextCircle": None,   # Placeholder for next circle meeting
    })

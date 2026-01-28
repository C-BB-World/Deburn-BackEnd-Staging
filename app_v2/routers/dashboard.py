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
    get_learning_queue_service,
    get_hub_db,
)
from app_v2.pipelines.learning import get_todays_focus_pipeline
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
    checkin_service = get_checkin_service()
    checkin_analytics = get_checkin_analytics()
    insight_service = get_insight_service()
    learning_queue_service = get_learning_queue_service()

    user_id = str(user["_id"])

    # Get today's check-in
    todays_checkin = await checkin_service.get_today_checkin(user_id)

    # Get streak
    streak = await checkin_analytics.calculate_streak(user_id)

    # Get insights count
    insights_count = await insight_service.get_unread_count(user_id)

    # Get today's learning focus
    try:
        hub_db = get_hub_db()
        print(f"[DASHBOARD] Got hub_db, calling pipeline for user {user_id}")
        todays_focus = await get_todays_focus_pipeline(
            queue_service=learning_queue_service,
            hub_db=hub_db,
            user_id=user_id,
        )
        print(f"[DASHBOARD] Today's focus result: {todays_focus}")
    except RuntimeError as e:
        # Hub database not configured
        print(f"[DASHBOARD] RuntimeError: {e}")
        todays_focus = None
    except Exception as e:
        print(f"[DASHBOARD] Exception: {e}")
        import traceback
        traceback.print_exc()
        todays_focus = None

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
        "todaysFocus": todays_focus,
        "nextCircle": None,   # Placeholder for next circle meeting
    })

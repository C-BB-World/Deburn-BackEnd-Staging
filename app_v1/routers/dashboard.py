"""
Dashboard Router.

Provides aggregated dashboard data.
"""

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends

from common.utils import success_response

from app_v1.config import settings
from app_v1.models import User, CheckIn
from app_v1.dependencies import get_current_user

router = APIRouter()


# =============================================================================
# Helper Functions
# =============================================================================
async def calculate_streak(user_id: str) -> dict:
    """Calculate the user's current and longest streak."""
    checkins = await CheckIn.find(
        CheckIn.user_id == user_id
    ).sort(-CheckIn.date).to_list()

    if not checkins:
        return {"current": 0, "longest": 0}

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

    current_streak = 0
    longest_streak = 0
    temp_streak = 0
    previous_date = None

    for checkin in checkins:
        checkin_date = checkin.date

        if previous_date is None:
            if checkin_date == today or checkin_date == yesterday:
                current_streak = 1
            temp_streak = 1
        else:
            prev = datetime.strptime(previous_date, "%Y-%m-%d")
            curr = datetime.strptime(checkin_date, "%Y-%m-%d")
            diff_days = (prev - curr).days

            if diff_days == 1:
                temp_streak += 1
                if current_streak > 0:
                    current_streak += 1
            else:
                longest_streak = max(longest_streak, temp_streak)
                temp_streak = 1
                current_streak = 0

        previous_date = checkin_date

    longest_streak = max(longest_streak, temp_streak)
    return {"current": current_streak, "longest": longest_streak}


# =============================================================================
# GET /api/dashboard
# =============================================================================
@router.get("")
async def get_dashboard(
    user: User = Depends(get_current_user),
):
    """
    Get aggregated dashboard data.
    """
    user_id = str(user.id)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Get today's check-in
    today_checkin = await CheckIn.find_one(
        CheckIn.user_id == user_id,
        CheckIn.date == today,
    )

    # Get streak
    streak = await calculate_streak(user_id)

    # Get recent mood (from today's check-in or last check-in)
    recent_mood = None
    if today_checkin:
        recent_mood = today_checkin.metrics.mood
    else:
        last_checkin = await CheckIn.find_one(
            CheckIn.user_id == user_id
        )
        if last_checkin:
            recent_mood = last_checkin.metrics.mood

    # Calculate remaining coach exchanges
    daily_limit = settings.DAILY_EXCHANGE_LIMIT
    exchanges_today = user.coach_exchanges_count or 0

    # Reset if it's a new day
    last_reset = user.coach_exchanges_last_reset
    reset_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    if not last_reset or last_reset < reset_date:
        exchanges_today = 0

    exchanges_remaining = max(0, daily_limit - exchanges_today)

    # TODO: Get circle data (implement when circle models are added)
    active_groups = 0
    pending_invitations = 0

    return success_response({
        "user": {
            "firstName": user.profile.first_name if user.profile else None,
            "displayName": user.display_name,
        },
        "checkin": {
            "hasCheckedInToday": today_checkin is not None,
            "streak": streak,
            "recentMood": recent_mood,
        },
        "coach": {
            "exchangesRemaining": exchanges_remaining,
            "dailyLimit": daily_limit,
        },
        "circles": {
            "activeGroups": active_groups,
            "pendingInvitations": pending_invitations,
        },
    })

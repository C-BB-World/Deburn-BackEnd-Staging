"""
Progress Router.

Handles progress statistics and AI-generated insights.
"""

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query

from common.utils import success_response

from app.models import User, CheckIn
from app.dependencies import get_current_user

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


async def calculate_averages(user_id: str, days: int = 30) -> dict:
    """Calculate average metrics over a period."""
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    checkins = await CheckIn.find(
        CheckIn.user_id == user_id,
        CheckIn.date >= start_date,
    ).to_list()

    if not checkins:
        return {
            "mood": None,
            "physicalEnergy": None,
            "mentalEnergy": None,
            "sleep": None,
            "stress": None,
        }

    mood_sum = sum(c.metrics.mood for c in checkins)
    physical_sum = sum(c.metrics.physical_energy for c in checkins)
    mental_sum = sum(c.metrics.mental_energy for c in checkins)
    sleep_sum = sum(c.metrics.sleep for c in checkins)
    stress_sum = sum(c.metrics.stress for c in checkins)
    count = len(checkins)

    return {
        "mood": round(mood_sum / count, 1),
        "physicalEnergy": round(physical_sum / count, 1),
        "mentalEnergy": round(mental_sum / count, 1),
        "sleep": round(sleep_sum / count, 1),
        "stress": round(stress_sum / count, 1),
    }


# =============================================================================
# GET /api/progress/stats
# =============================================================================
@router.get("/stats")
async def get_stats(
    user: User = Depends(get_current_user),
):
    """
    Get progress statistics for the current user.
    """
    user_id = str(user.id)

    # Get streak
    streak = await calculate_streak(user_id)

    # Get total check-ins
    total_checkins = await CheckIn.find(CheckIn.user_id == user_id).count()

    # Get averages (last 30 days)
    averages = await calculate_averages(user_id, 30)

    # Calculate trends
    # Compare last 15 days to previous 15 days
    recent_avg = await calculate_averages(user_id, 15)
    older_checkins = await CheckIn.find(
        CheckIn.user_id == user_id,
        CheckIn.date >= (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d"),
        CheckIn.date < (datetime.now(timezone.utc) - timedelta(days=15)).strftime("%Y-%m-%d"),
    ).to_list()

    trends = {"mood": None, "energy": None, "stress": None}

    if older_checkins and recent_avg["mood"]:
        older_mood_avg = sum(c.metrics.mood for c in older_checkins) / len(older_checkins)
        if recent_avg["mood"] > older_mood_avg * 1.05:
            trends["mood"] = "improving"
        elif recent_avg["mood"] < older_mood_avg * 0.95:
            trends["mood"] = "declining"
        else:
            trends["mood"] = "stable"

        # Energy is average of physical and mental
        if recent_avg["physicalEnergy"] and recent_avg["mentalEnergy"]:
            recent_energy = (recent_avg["physicalEnergy"] + recent_avg["mentalEnergy"]) / 2
            older_energy = sum(
                (c.metrics.physical_energy + c.metrics.mental_energy) / 2
                for c in older_checkins
            ) / len(older_checkins)
            if recent_energy > older_energy * 1.05:
                trends["energy"] = "improving"
            elif recent_energy < older_energy * 0.95:
                trends["energy"] = "declining"
            else:
                trends["energy"] = "stable"

        # Stress (lower is better, so inverted)
        if recent_avg["stress"]:
            older_stress_avg = sum(c.metrics.stress for c in older_checkins) / len(older_checkins)
            if recent_avg["stress"] < older_stress_avg * 0.95:
                trends["stress"] = "improving"
            elif recent_avg["stress"] > older_stress_avg * 1.05:
                trends["stress"] = "declining"
            else:
                trends["stress"] = "stable"

    return success_response({
        "streak": streak,
        "totalCheckIns": total_checkins,
        "averages": averages,
        "trends": trends,
        "coachingStats": {
            "totalConversations": 0,  # TODO: Implement conversation tracking
            "topTopics": [],
        },
    })


# =============================================================================
# GET /api/progress/insights
# =============================================================================
@router.get("/insights")
async def get_insights(
    user: User = Depends(get_current_user),
    generate: bool = Query(True, description="Generate new insights if needed"),
    limit: int = Query(10, ge=1, le=20),
):
    """
    Get AI-generated insights based on user's data.
    """
    user_id = str(user.id)

    # TODO: Implement proper insight generation and storage
    # For now, return placeholder insights based on data patterns

    insights = []

    # Get recent check-ins for pattern detection
    checkins = await CheckIn.find(
        CheckIn.user_id == user_id
    ).sort(-CheckIn.date).limit(14).to_list()

    if len(checkins) >= 7:
        # Analyze sleep-energy correlation
        high_sleep_energy = []
        low_sleep_energy = []

        for c in checkins:
            if c.metrics.sleep >= 4:
                high_sleep_energy.append(
                    (c.metrics.physical_energy + c.metrics.mental_energy) / 2
                )
            else:
                low_sleep_energy.append(
                    (c.metrics.physical_energy + c.metrics.mental_energy) / 2
                )

        if high_sleep_energy and low_sleep_energy:
            high_avg = sum(high_sleep_energy) / len(high_sleep_energy)
            low_avg = sum(low_sleep_energy) / len(low_sleep_energy)

            if high_avg > low_avg * 1.2:
                insights.append({
                    "id": "sleep_energy_correlation",
                    "type": "pattern",
                    "trigger": "sleep_impact",
                    "title": "Sleep Affects Your Energy",
                    "body": f"We noticed that on days when you rate your sleep higher, your energy levels are about {int((high_avg/low_avg - 1) * 100)}% better. Consider prioritizing sleep this week.",
                    "isRead": False,
                    "createdAt": datetime.now(timezone.utc).isoformat(),
                })

        # Check for stress patterns
        recent_stress = [c.metrics.stress for c in checkins[:7]]
        if recent_stress:
            avg_stress = sum(recent_stress) / len(recent_stress)
            if avg_stress >= 7:
                insights.append({
                    "id": "high_stress_alert",
                    "type": "alert",
                    "trigger": "high_stress",
                    "title": "Elevated Stress Levels",
                    "body": "Your stress levels have been elevated this week. Consider taking some time for self-care or talking to Eve about stress management strategies.",
                    "isRead": False,
                    "createdAt": datetime.now(timezone.utc).isoformat(),
                })

    return success_response({
        "insights": insights[:limit],
        "unreadCount": len([i for i in insights if not i.get("isRead", True)]),
    })

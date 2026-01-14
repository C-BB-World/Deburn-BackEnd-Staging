"""
Check-in Router.

Handles daily wellness check-ins and trends.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from common.utils import success_response

from app.models import User, CheckIn, CheckInMetrics
from app.schemas.checkin import CheckInRequest
from app.dependencies import get_current_user

router = APIRouter()


# =============================================================================
# Helper Functions
# =============================================================================
def get_today_date() -> str:
    """Get today's date in YYYY-MM-DD format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def checkin_to_response(checkin: CheckIn) -> dict:
    """Convert CheckIn model to response dictionary."""
    return {
        "id": str(checkin.id),
        "date": checkin.date,
        "timestamp": checkin.timestamp.isoformat() if checkin.timestamp else None,
        "metrics": {
            "mood": checkin.metrics.mood,
            "physicalEnergy": checkin.metrics.physical_energy,
            "mentalEnergy": checkin.metrics.mental_energy,
            "sleep": checkin.metrics.sleep,
            "stress": checkin.metrics.stress,
        },
        "notes": checkin.notes,
    }


async def calculate_streak(user_id: str) -> dict:
    """
    Calculate the user's current and longest check-in streak.
    """
    # Get all check-ins sorted by date descending
    checkins = await CheckIn.find(
        CheckIn.user_id == user_id
    ).sort(-CheckIn.date).to_list()

    if not checkins:
        return {"current": 0, "longest": 0}

    today = get_today_date()
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

    current_streak = 0
    longest_streak = 0
    temp_streak = 0
    previous_date = None

    for checkin in checkins:
        checkin_date = checkin.date

        if previous_date is None:
            # First check-in
            if checkin_date == today or checkin_date == yesterday:
                current_streak = 1
            temp_streak = 1
        else:
            # Check if consecutive
            prev = datetime.strptime(previous_date, "%Y-%m-%d")
            curr = datetime.strptime(checkin_date, "%Y-%m-%d")
            diff_days = (prev - curr).days

            if diff_days == 1:
                # Consecutive day
                temp_streak += 1
                if current_streak > 0:
                    current_streak += 1
            else:
                # Streak broken
                longest_streak = max(longest_streak, temp_streak)
                temp_streak = 1
                current_streak = 0

        previous_date = checkin_date

    longest_streak = max(longest_streak, temp_streak)

    return {"current": current_streak, "longest": longest_streak}


from datetime import timedelta


# =============================================================================
# POST /api/checkin
# =============================================================================
@router.post("")
async def create_checkin(
    request: CheckInRequest,
    user: User = Depends(get_current_user),
):
    """
    Submit or update today's daily check-in.
    """
    today = get_today_date()
    user_id = str(user.id)

    # Check if user already checked in today
    existing = await CheckIn.find_one(
        CheckIn.user_id == user_id,
        CheckIn.date == today,
    )
    is_retake = existing is not None

    # Create metrics
    metrics = CheckInMetrics(
        mood=request.mood,
        physical_energy=request.physicalEnergy,
        mental_energy=request.mentalEnergy,
        sleep=request.sleep,
        stress=request.stress,
    )

    if existing:
        # Update existing check-in
        existing.metrics = metrics
        existing.notes = request.notes
        existing.timestamp = datetime.now(timezone.utc)
        await existing.save()
        checkin = existing
    else:
        # Create new check-in
        checkin = CheckIn(
            user_id=user_id,
            date=today,
            timestamp=datetime.now(timezone.utc),
            metrics=metrics,
            notes=request.notes,
        )
        await checkin.insert()

    # Calculate streak
    streak = await calculate_streak(user_id)

    return success_response(
        {
            "checkIn": checkin_to_response(checkin),
            "streak": streak,
            "isRetake": is_retake,
        },
        message="Check-in updated successfully" if is_retake else "Check-in saved successfully",
    )


# =============================================================================
# GET /api/checkin/trends
# =============================================================================
@router.get("/trends")
async def get_trends(
    user: User = Depends(get_current_user),
    period: int = Query(30, ge=7, le=90, description="Number of days"),
):
    """
    Get check-in trends over the specified period.
    """
    user_id = str(user.id)

    # Calculate start date
    start_date = (datetime.now(timezone.utc) - timedelta(days=period)).strftime("%Y-%m-%d")

    # Get check-ins in period
    checkins = await CheckIn.find(
        CheckIn.user_id == user_id,
        CheckIn.date >= start_date,
    ).sort(CheckIn.date).to_list()

    if not checkins:
        return success_response({
            "period": period,
            "dataPoints": 0,
            "mood": {"values": [], "average": None, "trend": None, "change": None},
            "physicalEnergy": {"values": [], "average": None, "trend": None, "change": None},
            "mentalEnergy": {"values": [], "average": None, "trend": None, "change": None},
            "sleep": {"values": [], "average": None, "trend": None, "change": None},
            "stress": {"values": [], "average": None, "trend": None, "change": None},
        })

    def calculate_metric_stats(values: list) -> dict:
        """Calculate stats for a metric."""
        if not values:
            return {"values": [], "average": None, "trend": None, "change": None}

        avg = sum(v["value"] for v in values) / len(values)

        # Calculate trend
        trend = None
        change = None
        if len(values) >= 4:
            midpoint = len(values) // 2
            first_half = values[:midpoint]
            second_half = values[midpoint:]
            first_avg = sum(v["value"] for v in first_half) / len(first_half)
            second_avg = sum(v["value"] for v in second_half) / len(second_half)

            if first_avg > 0:
                change = round((second_avg - first_avg) / first_avg * 100, 1)

            if second_avg > first_avg * 1.05:
                trend = "improving"
            elif second_avg < first_avg * 0.95:
                trend = "declining"
            else:
                trend = "stable"

        return {
            "values": values,
            "average": round(avg, 1),
            "trend": trend,
            "change": change,
        }

    # Extract metrics
    mood_values = [{"date": c.date, "value": c.metrics.mood} for c in checkins]
    physical_values = [{"date": c.date, "value": c.metrics.physical_energy} for c in checkins]
    mental_values = [{"date": c.date, "value": c.metrics.mental_energy} for c in checkins]
    sleep_values = [{"date": c.date, "value": c.metrics.sleep} for c in checkins]
    stress_values = [{"date": c.date, "value": c.metrics.stress} for c in checkins]

    return success_response({
        "period": period,
        "dataPoints": len(checkins),
        "mood": calculate_metric_stats(mood_values),
        "physicalEnergy": calculate_metric_stats(physical_values),
        "mentalEnergy": calculate_metric_stats(mental_values),
        "sleep": calculate_metric_stats(sleep_values),
        "stress": calculate_metric_stats(stress_values),
    })

"""
Check-in system pipeline functions.

Stateless orchestration logic for check-in operations.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta

from app_v2.services.checkin.checkin_service import CheckInService
from app_v2.services.checkin.checkin_analytics import CheckInAnalytics
from app_v2.services.checkin.insight_generator import InsightGenerator
from app_v2.services.progress.insight_service import InsightService

logger = logging.getLogger(__name__)


async def submit_checkin_pipeline(
    checkin_service: CheckInService,
    checkin_analytics: CheckInAnalytics,
    insight_generator: InsightGenerator,
    user_id: str,
    metrics: Dict[str, int],
    notes: Optional[str] = None,
    insight_service: Optional[InsightService] = None
) -> Dict[str, Any]:
    """
    Orchestrates the check-in submission flow.

    Args:
        checkin_service: For data persistence
        checkin_analytics: For streak calculation
        insight_generator: For AI-generated insights
        user_id: Current user's ID
        metrics: Check-in metrics from request
        notes: Optional notes
        insight_service: For persisting insights (optional)

    Returns:
        Response dict with streak, insight, tip
    """
    checkin = await checkin_service.submit_checkin(user_id, metrics, notes)

    streak = await checkin_analytics.calculate_streak(user_id)

    insight_data = await insight_generator.generate_insight(user_id, checkin)

    # Persist the generated insight so it shows on dashboard
    # Creates new insight or updates existing one on same-day retake
    if insight_service and insight_data.get("insight"):
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

            await insight_service.update_or_create_checkin_insight(
                user_id=user_id,
                title="Today's Check-in Insight",
                description=f"{insight_data['insight']}\n\nTip: {insight_data['tip']}",
                metrics={
                    "mood": metrics.get("mood"),
                    "physicalEnergy": metrics.get("physicalEnergy"),
                    "mentalEnergy": metrics.get("mentalEnergy"),
                    "sleep": metrics.get("sleep"),
                    "stress": metrics.get("stress"),
                },
                expires_at=expires_at
            )
        except Exception as e:
            # Don't fail check-in if insight persistence fails
            logger.warning(f"Failed to persist check-in insight: {e}")

    return {
        "streak": streak,
        "insight": insight_data["insight"],
        "tip": insight_data["tip"]
    }


async def get_today_checkin_pipeline(
    checkin_service: CheckInService,
    user_id: str
) -> Dict[str, Any]:
    """
    Get today's check-in status.

    Args:
        checkin_service: For data retrieval
        user_id: Current user's ID

    Returns:
        dict with hasCheckedInToday flag and checkin data
    """
    checkin = await checkin_service.get_today_checkin(user_id)

    return {
        "hasCheckedInToday": checkin is not None,
        "checkin": _format_checkin(checkin) if checkin else None
    }


async def get_history_pipeline(
    checkin_service: CheckInService,
    user_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 30,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Get check-in history with pagination.

    Args:
        checkin_service: For data retrieval
        user_id: Current user's ID
        start_date: Optional start date filter
        end_date: Optional end date filter
        limit: Max records to return
        offset: Records to skip

    Returns:
        dict with checkins list and pagination metadata
    """
    checkins = await checkin_service.get_history(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )

    total = await checkin_service.get_total_count(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date
    )

    return {
        "checkins": [_format_checkin(c) for c in checkins],
        "total": total,
        "limit": limit,
        "offset": offset,
        "hasMore": (offset + len(checkins)) < total
    }


async def get_streak_pipeline(
    checkin_analytics: CheckInAnalytics,
    user_id: str
) -> int:
    """
    Get current streak count.

    Args:
        checkin_analytics: For streak calculation
        user_id: Current user's ID

    Returns:
        Current streak count
    """
    return await checkin_analytics.calculate_streak(user_id)


async def get_trends_pipeline(
    checkin_analytics: CheckInAnalytics,
    user_id: str,
    period: int = 30
) -> Dict[str, Any]:
    """
    Get formatted trend data for graphs.

    Args:
        checkin_analytics: For trend calculation
        user_id: Current user's ID
        period: Number of days (7, 30, or 90)

    Returns:
        Trend data with values and changes
    """
    return await checkin_analytics.get_trends(user_id, period)


def _format_checkin(checkin: Dict[str, Any]) -> Dict[str, Any]:
    """Format check-in document for API response."""
    return {
        "id": str(checkin["_id"]),
        "date": checkin["date"],
        "timestamp": checkin["timestamp"],
        "metrics": checkin["metrics"],
        "notes": checkin.get("notes")
    }

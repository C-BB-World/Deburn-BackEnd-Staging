"""
Check-in analytics service.

Handles streak calculation and trend data formatting for graphs.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

from app_v2.services.checkin.checkin_service import CheckInService

logger = logging.getLogger(__name__)


class CheckInAnalytics:
    """
    Analytics and data formatting for check-ins.
    Handles streak calculation and trend data formatting for graphs.
    """

    def __init__(self, checkin_service: CheckInService):
        """
        Initialize CheckInAnalytics.

        Args:
            checkin_service: For fetching check-in data
        """
        self._checkin_service = checkin_service

    async def calculate_streak(self, user_id: str) -> int:
        """
        Calculate current streak for a user.

        Args:
            user_id: MongoDB user ID

        Returns:
            Current streak count (consecutive days from today/yesterday)

        Algorithm:
            1. Get all check-ins sorted by date descending
            2. If most recent is not today or yesterday, return 0
            3. Count consecutive days backward
        """
        checkins = await self._checkin_service.get_checkins_for_period(user_id, 365)

        if not checkins:
            return 0

        checkins_sorted = sorted(checkins, key=lambda x: x["date"], reverse=True)

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

        most_recent_date = checkins_sorted[0]["date"]

        if most_recent_date != today and most_recent_date != yesterday:
            return 0

        streak = 1
        current_date = most_recent_date

        for i in range(1, len(checkins_sorted)):
            checkin_date = checkins_sorted[i]["date"]
            if self._is_consecutive(checkin_date, current_date):
                streak += 1
                current_date = checkin_date
            else:
                break

        return streak

    async def get_trends(self, user_id: str, period: int = 30) -> Dict[str, Any]:
        """
        Get formatted trend data for graphs.

        Args:
            user_id: MongoDB user ID
            period: Number of days (7, 30, or 90)

        Returns:
            dict with keys:
                - dataPoints: int (number of check-ins in period)
                - moodValues: list[int] (flat array)
                - moodChange: int (percentage)
                - energyValues: list[float] (flat array, averaged)
                - energyChange: int (percentage)
                - stressValues: list[int] (flat array)
                - stressChange: int (percentage)
        """
        checkins = await self._checkin_service.get_checkins_for_period(user_id, period)

        if not checkins:
            return {
                "dataPoints": 0,
                "moodValues": [],
                "moodChange": None,
                "energyValues": [],
                "energyChange": None,
                "stressValues": [],
                "stressChange": None
            }

        mood_values = []
        energy_values = []
        stress_values = []

        for checkin in checkins:
            metrics = checkin.get("metrics", {})
            mood_values.append(metrics.get("mood", 0))
            energy_values.append(
                self._calculate_energy_average(
                    metrics.get("physicalEnergy", 0),
                    metrics.get("mentalEnergy", 0)
                )
            )
            stress_values.append(metrics.get("stress", 0))

        return {
            "dataPoints": len(checkins),
            "moodValues": mood_values,
            "moodChange": self._calculate_change_percentage(mood_values),
            "energyValues": energy_values,
            "energyChange": self._calculate_change_percentage(energy_values),
            "stressValues": stress_values,
            "stressChange": self._calculate_change_percentage(stress_values)
        }

    def _calculate_energy_average(self, physical: int, mental: int) -> float:
        """
        Calculate combined energy value.

        Args:
            physical: Physical energy (1-10)
            mental: Mental energy (1-10)

        Returns:
            Average of both values
        """
        return (physical + mental) / 2

    def _calculate_change_percentage(self, values: List[float]) -> Optional[int]:
        """
        Calculate percentage change between first and second half.

        Args:
            values: List of numeric values

        Returns:
            Percentage change as int, or None if < 4 data points
        """
        if len(values) < 4:
            return None

        mid = len(values) // 2
        first_half = values[:mid]
        second_half = values[mid:]

        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)

        if first_avg == 0:
            return None

        change = ((second_avg - first_avg) / first_avg) * 100
        return int(round(change))

    def _is_consecutive(self, date1: str, date2: str) -> bool:
        """
        Check if two dates are consecutive (1 day apart).

        Args:
            date1: Earlier date in YYYY-MM-DD format
            date2: Later date in YYYY-MM-DD format

        Returns:
            True if dates are exactly 1 day apart
        """
        d1 = datetime.strptime(date1, "%Y-%m-%d")
        d2 = datetime.strptime(date2, "%Y-%m-%d")

        diff = (d2 - d1).days
        return diff == 1

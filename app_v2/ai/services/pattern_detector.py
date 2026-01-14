"""
Pattern detection service.

Analyzes check-in data to detect behavioral patterns.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from collections import Counter
import statistics

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


@dataclass
class PatternResult:
    """Detected patterns from check-in data."""
    streak: Dict[str, int] = field(default_factory=lambda: {"current": 0})
    morning_checkins: int = 0
    stress_day_pattern: Optional[Dict[str, Any]] = None
    mood_change: Optional[int] = None
    stress_change: Optional[int] = None
    energy_change: Optional[int] = None
    low_energy_days: int = 0
    sleep_mood_correlation: float = 0.0


class PatternDetector:
    """
    Analyzes check-in data to detect behavioral patterns.
    """

    MINIMUM_CHECKINS = 5
    MORNING_HOUR_THRESHOLD = 9
    LOW_ENERGY_THRESHOLD = 5
    STRESS_PATTERN_MIN_COUNT = 3

    WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize PatternDetector.

        Args:
            db: MongoDB database connection
        """
        self._db = db
        self._checkins_collection = db["checkins"]

    async def detect(
        self,
        user_id: str,
        days: int = 30
    ) -> Optional[PatternResult]:
        """
        Detect patterns in user's check-in data.

        Args:
            user_id: User's ID
            days: Days of data to analyze

        Returns:
            PatternResult or None if insufficient data
        """
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        cursor = self._checkins_collection.find({
            "userId": ObjectId(user_id),
            "date": {"$gte": start_date}
        })
        cursor = cursor.sort("date", 1)

        checkins = await cursor.to_list(length=1000)

        if len(checkins) < self.MINIMUM_CHECKINS:
            return None

        result = PatternResult()

        result.streak = self._calculate_streak(checkins)
        result.morning_checkins = self._count_morning_checkins(checkins)
        result.stress_day_pattern = self._detect_stress_day_pattern(checkins)
        result.mood_change = self._calculate_metric_change(checkins, "mood")
        result.stress_change = self._calculate_metric_change(checkins, "stress")
        result.energy_change = self._calculate_metric_change(checkins, "energy")
        result.low_energy_days = self._count_low_energy_streak(checkins)
        result.sleep_mood_correlation = self._calculate_sleep_mood_correlation(checkins)

        return result

    def _calculate_streak(self, checkins: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate current check-in streak."""
        if not checkins:
            return {"current": 0}

        today = datetime.now(timezone.utc).date()
        streak = 0
        current_date = today

        dates = set()
        for checkin in checkins:
            checkin_date = checkin["date"]
            if isinstance(checkin_date, datetime):
                dates.add(checkin_date.date())

        for i in range(len(checkins)):
            if current_date in dates:
                streak += 1
                current_date -= timedelta(days=1)
            else:
                break

        return {"current": streak}

    def _count_morning_checkins(self, checkins: List[Dict[str, Any]]) -> int:
        """Count check-ins submitted before 9am."""
        count = 0
        for checkin in checkins:
            created_at = checkin.get("createdAt")
            if created_at and isinstance(created_at, datetime):
                if created_at.hour < self.MORNING_HOUR_THRESHOLD:
                    count += 1
        return count

    def _detect_stress_day_pattern(
        self,
        checkins: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Find day with highest stress frequency.
        Returns pattern if >= 3 occurrences.
        """
        high_stress_days = []

        for checkin in checkins:
            stress = checkin.get("stress", 0)
            if stress >= 7:
                checkin_date = checkin.get("date")
                if isinstance(checkin_date, datetime):
                    weekday = checkin_date.weekday()
                    high_stress_days.append(weekday)

        if not high_stress_days:
            return None

        day_counts = Counter(high_stress_days)
        most_common = day_counts.most_common(1)[0]
        weekday, count = most_common

        if count >= self.STRESS_PATTERN_MIN_COUNT:
            return {
                "weekday": self.WEEKDAY_NAMES[weekday],
                "weekdayIndex": weekday,
                "count": count
            }

        return None

    def _calculate_metric_change(
        self,
        checkins: List[Dict[str, Any]],
        metric: str
    ) -> Optional[int]:
        """Calculate % change between first and second half."""
        if len(checkins) < 4:
            return None

        midpoint = len(checkins) // 2
        first_half = checkins[:midpoint]
        second_half = checkins[midpoint:]

        first_values = [c.get(metric, 0) for c in first_half if c.get(metric) is not None]
        second_values = [c.get(metric, 0) for c in second_half if c.get(metric) is not None]

        if not first_values or not second_values:
            return None

        first_avg = sum(first_values) / len(first_values)
        second_avg = sum(second_values) / len(second_values)

        if first_avg == 0:
            return None

        change = int(((second_avg - first_avg) / first_avg) * 100)
        return change

    def _count_low_energy_streak(self, checkins: List[Dict[str, Any]]) -> int:
        """Count consecutive recent days with avg energy < 5."""
        if not checkins:
            return 0

        recent_checkins = list(reversed(checkins[-14:]))
        streak = 0

        for checkin in recent_checkins:
            energy = checkin.get("energy", 5)
            if energy < self.LOW_ENERGY_THRESHOLD:
                streak += 1
            else:
                break

        return streak

    def _calculate_sleep_mood_correlation(
        self,
        checkins: List[Dict[str, Any]]
    ) -> float:
        """Calculate correlation between sleep and mood."""
        sleep_values = []
        mood_values = []

        for checkin in checkins:
            sleep = checkin.get("sleep")
            mood = checkin.get("mood")
            if sleep is not None and mood is not None:
                sleep_values.append(sleep)
                mood_values.append(mood)

        if len(sleep_values) < 5:
            return 0.0

        try:
            correlation = self._pearson_correlation(sleep_values, mood_values)
            return abs(round(correlation, 2))
        except Exception:
            return 0.0

    def _pearson_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient."""
        n = len(x)
        if n != len(y) or n == 0:
            return 0.0

        mean_x = sum(x) / n
        mean_y = sum(y) / n

        numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))

        sum_sq_x = sum((xi - mean_x) ** 2 for xi in x)
        sum_sq_y = sum((yi - mean_y) ** 2 for yi in y)

        denominator = (sum_sq_x * sum_sq_y) ** 0.5

        if denominator == 0:
            return 0.0

        return numerator / denominator

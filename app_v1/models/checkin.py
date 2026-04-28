"""
CheckIn model for BrainBank.

Matches the original Mongoose schema from models/CheckIn.js.
Stores daily wellness check-in data for users.
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import Field
from beanie import Indexed, PydanticObjectId

from common.database import BaseDocument


class CheckInMetrics(BaseDocument):
    """Embedded wellness metrics."""

    # Mood: 1=struggling, 2=low, 3=neutral, 4=good, 5=great
    mood: int = Field(..., ge=1, le=5)

    # Physical energy level (1-10 scale)
    physical_energy: int = Field(..., ge=1, le=10)

    # Mental energy level (1-10 scale)
    mental_energy: int = Field(..., ge=1, le=10)

    # Sleep quality: 1=poor, 2=fair, 3=ok, 4=good, 5=great
    sleep: int = Field(..., ge=1, le=5)

    # Stress level (1-10 scale, where 1=low stress, 10=high stress)
    stress: int = Field(..., ge=1, le=10)

    class Settings:
        name = "checkin_metrics"


class CheckIn(BaseDocument):
    """
    CheckIn document for BrainBank.

    Stores daily wellness check-in data for users.
    One check-in per user per day.
    """

    # User reference
    user_id: Indexed(PydanticObjectId)  # type: ignore

    # Date of check-in (YYYY-MM-DD format for daily uniqueness)
    date: Indexed(str)  # type: ignore

    # Timestamp of when check-in was submitted
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Wellness metrics
    metrics: CheckInMetrics

    # Optional notes from user
    notes: Optional[str] = Field(None, max_length=500)

    class Settings:
        name = "checkins"
        indexes = [
            [("user_id", 1), ("date", 1)],  # Compound unique index
            [("user_id", 1), ("timestamp", -1)],  # For efficient trend queries
        ]

    def to_public_dict(self) -> dict:
        """Convert to public JSON format."""
        return {
            "id": str(self.id),
            "date": self.date,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metrics": {
                "mood": self.metrics.mood,
                "physicalEnergy": self.metrics.physical_energy,
                "mentalEnergy": self.metrics.mental_energy,
                "sleep": self.metrics.sleep,
                "stress": self.metrics.stress,
            },
            "notes": self.notes,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    async def get_history(
        cls,
        user_id: PydanticObjectId,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 90,
        offset: int = 0,
    ) -> List["CheckIn"]:
        """Get check-ins for a user within a date range."""
        query: Dict[str, Any] = {"user_id": user_id}

        if start_date or end_date:
            query["date"] = {}
            if start_date:
                query["date"]["$gte"] = start_date
            if end_date:
                query["date"]["$lte"] = end_date

        return await cls.find(query).sort("-date").skip(offset).limit(limit).to_list()

    @classmethod
    async def calculate_streak(
        cls,
        user_id: PydanticObjectId,
    ) -> Dict[str, int]:
        """Calculate streak for a user."""
        check_ins = await cls.find(
            {"user_id": user_id}
        ).sort("-date").to_list()

        if not check_ins:
            return {"current": 0, "longest": 0}

        # Helper to get date strings
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        yesterday = (
            datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        )
        yesterday = (yesterday.timestamp() - 86400)
        yesterday = datetime.fromtimestamp(yesterday, tz=timezone.utc).strftime("%Y-%m-%d")

        current_streak = 0
        longest_streak = 0
        temp_streak = 0
        previous_date = None

        for check_in in check_ins:
            check_in_date = check_in.date

            if previous_date is None:
                # First check-in - start counting if it's today or yesterday
                if check_in_date in (today, yesterday):
                    current_streak = 1
                temp_streak = 1
            else:
                # Check if consecutive
                prev_date_obj = datetime.strptime(previous_date, "%Y-%m-%d")
                curr_date_obj = datetime.strptime(check_in_date, "%Y-%m-%d")
                diff_days = (prev_date_obj - curr_date_obj).days

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

            previous_date = check_in_date

        longest_streak = max(longest_streak, temp_streak)

        return {"current": current_streak, "longest": longest_streak}

    @classmethod
    async def get_trends(
        cls,
        user_id: PydanticObjectId,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get trend data for a period."""
        start_date = datetime.now(timezone.utc)
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = datetime.fromtimestamp(
            start_date.timestamp() - (days * 86400),
            tz=timezone.utc,
        )
        start_date_str = start_date.strftime("%Y-%m-%d")

        check_ins = await cls.find(
            {"user_id": user_id, "date": {"$gte": start_date_str}}
        ).sort("date").to_list()

        if not check_ins:
            return {
                "period": days,
                "dataPoints": 0,
                "mood": {"values": [], "average": None, "trend": None},
                "physicalEnergy": {"values": [], "average": None, "trend": None},
                "mentalEnergy": {"values": [], "average": None, "trend": None},
                "sleep": {"values": [], "average": None, "trend": None},
                "stress": {"values": [], "average": None, "trend": None},
            }

        # Extract metric arrays
        metrics = {
            "mood": [{"date": c.date, "value": c.metrics.mood} for c in check_ins],
            "physicalEnergy": [
                {"date": c.date, "value": c.metrics.physical_energy} for c in check_ins
            ],
            "mentalEnergy": [
                {"date": c.date, "value": c.metrics.mental_energy} for c in check_ins
            ],
            "sleep": [{"date": c.date, "value": c.metrics.sleep} for c in check_ins],
            "stress": [{"date": c.date, "value": c.metrics.stress} for c in check_ins],
        }

        def calculate_stats(data_points: List[Dict[str, Any]]) -> Dict[str, Any]:
            if not data_points:
                return {"values": [], "average": None, "trend": None, "change": None}

            values = [d["value"] for d in data_points]
            average = sum(values) / len(values)

            # Calculate trend (comparing first half to second half)
            trend = None
            change = None
            if len(values) >= 4:
                midpoint = len(values) // 2
                first_half = values[:midpoint]
                second_half = values[midpoint:]
                first_avg = sum(first_half) / len(first_half)
                second_avg = sum(second_half) / len(second_half)

                if first_avg > 0:
                    change = round((second_avg - first_avg) / first_avg * 100, 1)

                if second_avg > first_avg * 1.05:
                    trend = "improving"
                elif second_avg < first_avg * 0.95:
                    trend = "declining"
                else:
                    trend = "stable"

            return {
                "values": data_points,
                "average": round(average, 1),
                "trend": trend,
                "change": change,
            }

        return {
            "period": days,
            "dataPoints": len(check_ins),
            "mood": calculate_stats(metrics["mood"]),
            "physicalEnergy": calculate_stats(metrics["physicalEnergy"]),
            "mentalEnergy": calculate_stats(metrics["mentalEnergy"]),
            "sleep": calculate_stats(metrics["sleep"]),
            "stress": calculate_stats(metrics["stress"]),
        }

    @classmethod
    async def get_total_count(cls, user_id: PydanticObjectId) -> int:
        """Get total check-in count for user."""
        return await cls.find({"user_id": user_id}).count()

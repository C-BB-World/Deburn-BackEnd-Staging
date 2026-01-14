"""
Progress statistics aggregation service.

Aggregates user statistics from multiple data sources.
"""

import logging
from typing import Dict, Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class ProgressStatsService:
    """
    Aggregates user progress stats from multiple systems.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize ProgressStatsService.

        Args:
            db: MongoDB database connection
        """
        self._db = db
        self._users_collection = db["users"]
        self._checkins_collection = db["checkins"]
        self._progress_collection = db["userLearningProgress"]

    async def get_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Aggregate stats from all sources.

        Args:
            user_id: User ID

        Returns:
            dict with streak, checkins, lessons, sessions
        """
        streak = await self._calculate_streak(user_id)
        checkins = await self._get_checkins_count(user_id)
        lessons = await self._get_lessons_count(user_id)
        sessions = await self._get_sessions_count(user_id)

        return {
            "streak": streak,
            "checkins": checkins,
            "lessons": lessons,
            "sessions": sessions
        }

    async def _calculate_streak(self, user_id: str) -> int:
        """Calculate current check-in streak."""
        from datetime import datetime, timezone, timedelta

        cursor = self._checkins_collection.find(
            {"userId": ObjectId(user_id)},
            {"date": 1}
        )
        cursor = cursor.sort("date", -1)
        cursor = cursor.limit(60)

        checkins = await cursor.to_list(length=60)

        if not checkins:
            return 0

        today = datetime.now(timezone.utc).date()
        dates = set()

        for checkin in checkins:
            checkin_date = checkin.get("date")
            if isinstance(checkin_date, datetime):
                dates.add(checkin_date.date())

        streak = 0
        current_date = today

        for _ in range(60):
            if current_date in dates:
                streak += 1
                current_date -= timedelta(days=1)
            else:
                break

        return streak

    async def _get_checkins_count(self, user_id: str) -> int:
        """Get total check-in count."""
        count = await self._checkins_collection.count_documents(
            {"userId": ObjectId(user_id)}
        )
        return count

    async def _get_lessons_count(self, user_id: str) -> int:
        """Get completed lessons count."""
        count = await self._progress_collection.count_documents({
            "userId": ObjectId(user_id),
            "progress": 100
        })
        return count

    async def _get_sessions_count(self, user_id: str) -> int:
        """Get coach sessions count from user document."""
        user = await self._users_collection.find_one(
            {"_id": ObjectId(user_id)},
            {"coachExchanges": 1}
        )

        if not user:
            return 0

        exchanges = user.get("coachExchanges", {})
        return exchanges.get("count", 0)

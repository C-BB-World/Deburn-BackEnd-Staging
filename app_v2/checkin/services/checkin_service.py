"""
Check-in CRUD service.

Handles check-in storage and retrieval operations.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from common.utils.exceptions import ValidationException
from app_v2.checkin.services.metrics_validator import MetricsValidator

logger = logging.getLogger(__name__)


class CheckInService:
    """
    Handles check-in storage and retrieval.
    Pure CRUD - no analytics or business logic.
    """

    MAX_LIMIT = 90

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize CheckInService.

        Args:
            db: MongoDB database connection
        """
        self._db = db
        self._checkins_collection = db["checkIns"]

    async def submit_checkin(
        self,
        user_id: str,
        metrics: Dict[str, int],
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create or update today's check-in for a user.

        Args:
            user_id: MongoDB user ID
            metrics: dict with mood, physicalEnergy, mentalEnergy, sleep, stress
            notes: Optional text notes (max 500 chars)

        Returns:
            Saved check-in document

        Raises:
            ValidationError: Metrics out of valid ranges
        """
        is_valid, error = MetricsValidator.validate(metrics)
        if not is_valid:
            raise ValidationException(message=error, code="VALIDATION_ERROR")

        is_valid, error = MetricsValidator.validate_notes(notes)
        if not is_valid:
            raise ValidationException(message=error, code="VALIDATION_ERROR")

        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%d")

        checkin_data = {
            "userId": ObjectId(user_id),
            "date": today,
            "timestamp": now,
            "metrics": {
                "mood": metrics["mood"],
                "physicalEnergy": metrics["physicalEnergy"],
                "mentalEnergy": metrics["mentalEnergy"],
                "sleep": metrics["sleep"],
                "stress": metrics["stress"]
            },
            "notes": notes.strip() if notes else None,
            "updatedAt": now
        }

        result = await self._checkins_collection.find_one_and_update(
            {"userId": ObjectId(user_id), "date": today},
            {
                "$set": checkin_data,
                "$setOnInsert": {"createdAt": now}
            },
            upsert=True,
            return_document=True
        )

        logger.info(f"Check-in submitted for user {user_id} on {today}")
        return result

    async def get_today_checkin(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get today's check-in for a user if it exists.

        Args:
            user_id: MongoDB user ID

        Returns:
            Check-in dict or None
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        return await self._checkins_collection.find_one({
            "userId": ObjectId(user_id),
            "date": today
        })

    async def get_history(
        self,
        user_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get paginated check-in history.

        Args:
            user_id: MongoDB user ID
            start_date: Optional YYYY-MM-DD start filter
            end_date: Optional YYYY-MM-DD end filter
            limit: Max records to return (capped at 90)
            offset: Number of records to skip

        Returns:
            List of check-in dicts sorted by date descending
        """
        limit = min(limit, self.MAX_LIMIT)

        query: Dict[str, Any] = {"userId": ObjectId(user_id)}

        if start_date or end_date:
            query["date"] = {}
            if start_date:
                query["date"]["$gte"] = start_date
            if end_date:
                query["date"]["$lte"] = end_date

        cursor = self._checkins_collection.find(query)
        cursor = cursor.sort("date", -1)
        cursor = cursor.skip(offset)
        cursor = cursor.limit(limit)

        return await cursor.to_list(length=limit)

    async def get_total_count(
        self,
        user_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> int:
        """
        Get total number of check-ins for a user.

        Args:
            user_id: MongoDB user ID
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Total count
        """
        query: Dict[str, Any] = {"userId": ObjectId(user_id)}

        if start_date or end_date:
            query["date"] = {}
            if start_date:
                query["date"]["$gte"] = start_date
            if end_date:
                query["date"]["$lte"] = end_date

        return await self._checkins_collection.count_documents(query)

    async def get_checkins_for_period(
        self,
        user_id: str,
        days: int
    ) -> List[Dict[str, Any]]:
        """
        Get all check-ins for a user within the last N days.
        Used by CheckInAnalytics for trend calculation.

        Args:
            user_id: MongoDB user ID
            days: Number of days to look back

        Returns:
            List of check-in dicts sorted by date ascending
        """
        start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

        cursor = self._checkins_collection.find({
            "userId": ObjectId(user_id),
            "date": {"$gte": start_date}
        })
        cursor = cursor.sort("date", 1)

        return await cursor.to_list(length=days + 1)

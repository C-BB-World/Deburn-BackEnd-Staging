"""
Learning progress tracking service.

Tracks user completion of content items.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class LearningProgressService:
    """
    Tracks user progress through learning content.
    Stores completion data in MongoDB.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize LearningProgressService.

        Args:
            db: MongoDB database connection
        """
        self._db = db
        self._progress_collection = db["userLearningProgress"]

    async def get_user_progress(self, user_id: str) -> Dict[str, int]:
        """
        Get progress for all content items a user has interacted with.

        Args:
            user_id: User ID

        Returns:
            Dict mapping content_id to progress percentage
        """
        cursor = self._progress_collection.find(
            {"userId": ObjectId(user_id)},
            {"contentId": 1, "progress": 1}
        )
        items = await cursor.to_list(length=1000)

        return {item["contentId"]: item["progress"] for item in items}

    async def get_item_progress(self, user_id: str, content_id: str) -> int:
        """
        Get user's progress for a specific content item.

        Args:
            user_id: User ID
            content_id: Content item ID

        Returns:
            Progress percentage (0-100), 0 if not started
        """
        record = await self._progress_collection.find_one({
            "userId": ObjectId(user_id),
            "contentId": content_id
        })

        return record["progress"] if record else 0

    async def update_progress(
        self,
        user_id: str,
        content_id: str,
        progress: int,
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update user's progress for a content item.

        Args:
            user_id: User ID
            content_id: Content item ID
            progress: Progress percentage (0-100)
            content_type: Optional content type for stats

        Returns:
            Updated progress record
        """
        progress = max(0, min(100, progress))

        now = datetime.now(timezone.utc)
        completed_at = now if progress == 100 else None

        update_data = {
            "progress": progress,
            "lastAccessedAt": now,
            "updatedAt": now,
        }

        if content_type:
            update_data["contentType"] = content_type

        if completed_at:
            update_data["completedAt"] = completed_at

        result = await self._progress_collection.find_one_and_update(
            {
                "userId": ObjectId(user_id),
                "contentId": content_id
            },
            {
                "$set": update_data,
                "$setOnInsert": {
                    "userId": ObjectId(user_id),
                    "contentId": content_id,
                    "createdAt": now,
                }
            },
            upsert=True,
            return_document=True
        )

        logger.info(f"Progress updated for user {user_id}, content {content_id}: {progress}%")
        return self._format_record(result)

    async def mark_complete(
        self,
        user_id: str,
        content_id: str,
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Mark content as complete (100% progress).

        Args:
            user_id: User ID
            content_id: Content item ID
            content_type: Optional content type for stats

        Returns:
            Updated progress record
        """
        return await self.update_progress(user_id, content_id, 100, content_type)

    async def get_completion_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get user's overall learning statistics.

        Args:
            user_id: User ID

        Returns:
            dict with totalCompleted, byType, lastCompletedAt
        """
        pipeline = [
            {"$match": {"userId": ObjectId(user_id), "progress": 100}},
            {"$group": {
                "_id": "$contentType",
                "count": {"$sum": 1},
                "lastCompleted": {"$max": "$completedAt"}
            }}
        ]

        results = await self._progress_collection.aggregate(pipeline).to_list(length=100)

        total_completed = 0
        by_type = {}
        last_completed_at = None

        for result in results:
            content_type = result["_id"] or "unknown"
            count = result["count"]
            total_completed += count
            by_type[content_type] = count

            if result.get("lastCompleted"):
                if last_completed_at is None or result["lastCompleted"] > last_completed_at:
                    last_completed_at = result["lastCompleted"]

        return {
            "totalCompleted": total_completed,
            "byType": by_type,
            "lastCompletedAt": last_completed_at
        }

    async def get_completed_count(self, user_id: str) -> int:
        """
        Get count of completed content items.

        Args:
            user_id: User ID

        Returns:
            Number of items with 100% progress
        """
        count = await self._progress_collection.count_documents({
            "userId": ObjectId(user_id),
            "progress": 100
        })
        return count

    async def get_recent_progress(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get user's recently accessed content progress.

        Args:
            user_id: User ID
            limit: Maximum items to return

        Returns:
            List of recent progress records
        """
        cursor = self._progress_collection.find({"userId": ObjectId(user_id)})
        cursor = cursor.sort("lastAccessedAt", -1)
        cursor = cursor.limit(limit)

        items = await cursor.to_list(length=limit)
        return [self._format_record(item) for item in items]

    async def get_in_progress(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get content items that are started but not completed.

        Args:
            user_id: User ID

        Returns:
            List of in-progress records
        """
        cursor = self._progress_collection.find({
            "userId": ObjectId(user_id),
            "progress": {"$gt": 0, "$lt": 100}
        })
        cursor = cursor.sort("lastAccessedAt", -1)

        items = await cursor.to_list(length=100)
        return [self._format_record(item) for item in items]

    def _format_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Format progress record for response."""
        return {
            "id": str(record["_id"]),
            "userId": str(record["userId"]),
            "contentId": record["contentId"],
            "contentType": record.get("contentType"),
            "progress": record["progress"],
            "completedAt": record.get("completedAt"),
            "lastAccessedAt": record.get("lastAccessedAt"),
            "createdAt": record.get("createdAt"),
        }

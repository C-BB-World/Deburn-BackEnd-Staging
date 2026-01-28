"""
Learning Queue service.

Handles user learning queue operations for Today's Focus feature.
"""

import logging
import random
from datetime import datetime, timezone, date
from typing import Optional, Dict, Any, List

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class LearningQueueService:
    """
    Handles learning queue storage and retrieval.
    Manages shuffled playlists for users' daily learning focus.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize LearningQueueService.

        Args:
            db: MongoDB database connection (main db)
        """
        self._db = db
        self._queue_collection = db["userlearningqueues"]

    async def get_queue(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user's learning queue.

        Args:
            user_id: User's ID

        Returns:
            Queue document or None if not exists
        """
        return await self._queue_collection.find_one(
            {"userId": ObjectId(user_id)}
        )

    async def create_queue(
        self,
        user_id: str,
        content_ids: List[str],
    ) -> Dict[str, Any]:
        """
        Create a new shuffled queue for user.

        Args:
            user_id: User's ID
            content_ids: List of content item IDs to shuffle

        Returns:
            Created queue document
        """
        # Shuffle the content IDs
        shuffled = content_ids.copy()
        random.shuffle(shuffled)

        now = datetime.now(timezone.utc)
        today = date.today().isoformat()

        queue_doc = {
            "userId": ObjectId(user_id),
            "queue": shuffled,
            "currentIndex": 0,
            "lastAdvancedDate": today,
            "createdAt": now,
            "updatedAt": now,
        }

        result = await self._queue_collection.insert_one(queue_doc)
        queue_doc["_id"] = result.inserted_id

        logger.info(f"Created learning queue for user {user_id} with {len(shuffled)} items")
        return queue_doc

    async def reshuffle_queue(
        self,
        user_id: str,
        content_ids: List[str],
    ) -> Dict[str, Any]:
        """
        Reshuffle and reset queue for user (when cycle completed).

        Args:
            user_id: User's ID
            content_ids: List of content item IDs to shuffle

        Returns:
            Updated queue document
        """
        # Shuffle the content IDs
        shuffled = content_ids.copy()
        random.shuffle(shuffled)

        now = datetime.now(timezone.utc)
        today = date.today().isoformat()

        result = await self._queue_collection.find_one_and_update(
            {"userId": ObjectId(user_id)},
            {
                "$set": {
                    "queue": shuffled,
                    "currentIndex": 0,
                    "lastAdvancedDate": today,
                    "updatedAt": now,
                }
            },
            return_document=True,
        )

        logger.info(f"Reshuffled learning queue for user {user_id} with {len(shuffled)} items")
        return result

    async def advance_index(self, user_id: str) -> Dict[str, Any]:
        """
        Advance currentIndex by 1 and update lastAdvancedDate.

        Args:
            user_id: User's ID

        Returns:
            Updated queue document
        """
        now = datetime.now(timezone.utc)
        today = date.today().isoformat()

        result = await self._queue_collection.find_one_and_update(
            {"userId": ObjectId(user_id)},
            {
                "$inc": {"currentIndex": 1},
                "$set": {
                    "lastAdvancedDate": today,
                    "updatedAt": now,
                }
            },
            return_document=True,
        )

        logger.info(f"Advanced learning queue index for user {user_id} to {result['currentIndex']}")
        return result

    async def update_last_advanced_date(self, user_id: str) -> Dict[str, Any]:
        """
        Update lastAdvancedDate to today without advancing index.
        Used when queue is first accessed on a new day but already at correct position.

        Args:
            user_id: User's ID

        Returns:
            Updated queue document
        """
        now = datetime.now(timezone.utc)
        today = date.today().isoformat()

        result = await self._queue_collection.find_one_and_update(
            {"userId": ObjectId(user_id)},
            {
                "$set": {
                    "lastAdvancedDate": today,
                    "updatedAt": now,
                }
            },
            return_document=True,
        )

        return result

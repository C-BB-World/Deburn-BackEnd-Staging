"""
Content bookmark service.

Allows users to bookmark/save content items for later.
"""

import logging
from datetime import datetime, timezone
from typing import List

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class BookmarkService:
    """
    Manages user content bookmarks.
    Stores bookmark data in MongoDB.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        self._db = db
        self._collection = db["userBookmarks"]

    async def ensure_indexes(self):
        """Create unique compound index on userId + contentId."""
        await self._collection.create_index(
            [("userId", 1), ("contentId", 1)],
            unique=True,
        )

    async def add_bookmark(self, user_id: str, content_id: str) -> dict:
        """Add a bookmark for a user."""
        now = datetime.now(timezone.utc)

        result = await self._collection.find_one_and_update(
            {
                "userId": ObjectId(user_id),
                "contentId": content_id,
            },
            {
                "$set": {
                    "bookmarkedAt": now,
                    "updatedAt": now,
                },
                "$setOnInsert": {
                    "userId": ObjectId(user_id),
                    "contentId": content_id,
                    "createdAt": now,
                },
            },
            upsert=True,
            return_document=True,
        )

        logger.info(f"Bookmark added for user {user_id}, content {content_id}")
        return {"contentId": result["contentId"]}

    async def remove_bookmark(self, user_id: str, content_id: str) -> bool:
        """Remove a bookmark for a user. Returns True if deleted."""
        result = await self._collection.delete_one({
            "userId": ObjectId(user_id),
            "contentId": content_id,
        })
        logger.info(f"Bookmark removed for user {user_id}, content {content_id}")
        return result.deleted_count > 0

    async def get_bookmark_ids(self, user_id: str) -> List[str]:
        """Get list of bookmarked content IDs for a user."""
        cursor = self._collection.find(
            {"userId": ObjectId(user_id)},
            {"contentId": 1},
        )
        items = await cursor.to_list(length=1000)
        return [item["contentId"] for item in items]

    async def is_bookmarked(self, user_id: str, content_id: str) -> bool:
        """Check if a content item is bookmarked by a user."""
        doc = await self._collection.find_one({
            "userId": ObjectId(user_id),
            "contentId": content_id,
        })
        return doc is not None

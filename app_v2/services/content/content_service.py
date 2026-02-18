"""
Content service with dual-source support.

Handles content retrieval and management from file or database.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from common.utils.exceptions import NotFoundException, ValidationException

logger = logging.getLogger(__name__)


class ContentService:
    """
    Handles content retrieval and management.
    Supports loading from file (current) or database (future).
    """

    VALID_CONTENT_TYPES = [
        "text_article",
        "audio_article",
        "audio_exercise",
        "video_link",
        "exercise"
    ]

    VALID_CATEGORIES = [
        "featured",
        "leadership",
        "breath",
        "meditation",
        "burnout",
        "wellbeing",
        "other"
    ]

    VALID_STATUSES = ["draft", "in_review", "published", "archived"]

    def __init__(
        self,
        source_type: str = "file",
        filepath: Optional[str] = None,
        db: Optional[AsyncIOMotorDatabase] = None
    ):
        """
        Initialize ContentService.

        Args:
            source_type: 'file' or 'database'
            filepath: Path to content file if source_type is 'file'
            db: MongoDB connection if source_type is 'database'
        """
        self._source_type = source_type
        self._filepath = filepath
        self._db = db
        self._content_collection = db["contentitems"] if db else None
        self._cached_content: Optional[List[Dict[str, Any]]] = None

    def _is_database_mode(self) -> bool:
        """Check if service is in database mode."""
        return self._source_type == "database" and self._db is not None

    async def _load_from_file(self) -> List[Dict[str, Any]]:
        """Load content from filepath."""
        if self._cached_content is not None:
            return self._cached_content

        if not self._filepath:
            return []

        try:
            with open(self._filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._cached_content = data.get("content", [])
                return self._cached_content
        except FileNotFoundError:
            logger.warning(f"Content file not found: {self._filepath}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in content file: {e}")
            return []

    def invalidate_cache(self) -> None:
        """Invalidate the file cache to reload on next access."""
        self._cached_content = None

    async def get_all(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Get all content items with optional filters.

        Args:
            filters: Optional dict with contentType, status, category

        Returns:
            List of content items
        """
        if self._is_database_mode():
            query = self._build_query(filters)
            cursor = self._content_collection.find(query)
            cursor = cursor.sort([("category", 1), ("sortOrder", 1)])
            items = await cursor.to_list(length=1000)
            return [self._format_item(item) for item in items]
        else:
            items = await self._load_from_file()
            return self._filter_items(items, filters)

    async def get_published(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Get only published content items.

        Args:
            filters: Optional dict with contentType, category

        Returns:
            List of published content items
        """
        if filters is None:
            filters = {}
        filters["status"] = "published"
        return await self.get_all(filters)

    async def get_by_id(self, content_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single content item by ID.

        Args:
            content_id: Content item ID

        Returns:
            Content item dict or None
        """
        if self._is_database_mode():
            try:
                item = await self._content_collection.find_one({"_id": ObjectId(content_id)})
                return self._format_item(item) if item else None
            except Exception:
                return None
        else:
            items = await self._load_from_file()
            for item in items:
                if item.get("id") == content_id:
                    return item
            return None

    async def get_for_coach(
        self,
        topics: List[str],
        limit: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Get content recommendations for coach.

        Args:
            topics: List of topic strings to match
            limit: Max items to return

        Returns:
            List of matching content items sorted by priority
        """
        if self._is_database_mode():
            cursor = self._content_collection.find({
                "status": "published",
                "coachEnabled": True,
                "coachTopics": {"$in": topics}
            })
            cursor = cursor.sort("coachPriority", -1)
            cursor = cursor.limit(limit)
            items = await cursor.to_list(length=limit)
            return [self._format_item(item) for item in items]
        else:
            items = await self._load_from_file()
            matching = []
            for item in items:
                if item.get("status") != "published":
                    continue
                if not item.get("coachEnabled"):
                    continue
                item_topics = item.get("coachTopics", [])
                if any(topic in item_topics for topic in topics):
                    matching.append(item)

            matching.sort(key=lambda x: x.get("coachPriority", 0), reverse=True)
            return matching[:limit]

    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new content item.

        Args:
            data: Content item data

        Returns:
            Created content item

        Raises:
            ValidationException: If in file mode
        """
        if not self._is_database_mode():
            raise ValidationException(
                message="Content creation not supported in file mode",
                code="FILE_MODE_READ_ONLY"
            )

        self._validate_content_data(data)

        now = datetime.now(timezone.utc)
        doc = {
            **data,
            "sortOrder": data.get("sortOrder", 0),
            "coachTopics": data.get("coachTopics", []),
            "coachPriority": data.get("coachPriority", 0),
            "coachEnabled": data.get("coachEnabled", False),
            "createdAt": now,
            "updatedAt": now,
        }

        result = await self._content_collection.insert_one(doc)
        doc["_id"] = result.inserted_id

        logger.info(f"Content created: {result.inserted_id}")
        return self._format_item(doc)

    async def update(
        self,
        content_id: str,
        data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update a content item.

        Args:
            content_id: Content item ID
            data: Fields to update

        Returns:
            Updated content item or None if not found

        Raises:
            ValidationException: If in file mode
        """
        if not self._is_database_mode():
            raise ValidationException(
                message="Content update not supported in file mode",
                code="FILE_MODE_READ_ONLY"
            )

        data["updatedAt"] = datetime.now(timezone.utc)

        result = await self._content_collection.find_one_and_update(
            {"_id": ObjectId(content_id)},
            {"$set": data},
            return_document=True
        )

        if result:
            logger.info(f"Content updated: {content_id}")
            return self._format_item(result)
        return None

    async def delete(self, content_id: str) -> bool:
        """
        Delete a content item.

        Args:
            content_id: Content item ID

        Returns:
            True if deleted, False if not found

        Raises:
            ValidationException: If in file mode
        """
        if not self._is_database_mode():
            raise ValidationException(
                message="Content deletion not supported in file mode",
                code="FILE_MODE_READ_ONLY"
            )

        result = await self._content_collection.delete_one({"_id": ObjectId(content_id)})

        if result.deleted_count > 0:
            logger.info(f"Content deleted: {content_id}")
            return True
        return False

    def _build_query(self, filters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Build MongoDB query from filters."""
        query = {}
        if not filters:
            return query

        if "contentType" in filters:
            query["contentType"] = filters["contentType"]
        if "status" in filters:
            query["status"] = filters["status"]
        if "category" in filters:
            query["category"] = filters["category"]

        return query

    def _filter_items(
        self,
        items: List[Dict[str, Any]],
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Filter items in memory for file mode."""
        if not filters:
            return items

        result = []
        for item in items:
            matches = True
            if "contentType" in filters and item.get("contentType") != filters["contentType"]:
                matches = False
            if "status" in filters and item.get("status") != filters["status"]:
                matches = False
            if "category" in filters and item.get("category") != filters["category"]:
                matches = False
            if matches:
                result.append(item)

        return sorted(
            result,
            key=lambda x: (x.get("category", ""), x.get("sortOrder", 0))
        )

    def _format_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Format database item for response."""
        if "_id" in item:
            item["id"] = str(item.pop("_id"))

        # Add hasImage flags based on mime type presence (single field for both languages)
        has_image = bool(item.get("articleImageMimeType"))
        item["hasImageEn"] = has_image
        item["hasImageSv"] = has_image
        item["hasImage"] = has_image

        return item

    async def get_article_image(
        self,
        content_id: str,
        lang: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get article image binary data for a content item.

        Args:
            content_id: Content item ID
            lang: Language code ('en' or 'sv')

        Returns:
            Dict with 'data' (bytes) and 'mime_type' (str), or None if not found
        """
        if not self._is_database_mode():
            return None

        try:
            # Fetch both language images and the single mime type field
            item = await self._content_collection.find_one(
                {"_id": ObjectId(content_id)},
                {"articleImageEn": 1, "articleImageSv": 1, "articleImageMimeType": 1}
            )

            if not item:
                return None

            # Get image data for requested language, fallback to English
            if lang == "sv":
                image_data = item.get("articleImageSv") or item.get("articleImageEn")
            else:
                image_data = item.get("articleImageEn")

            mime_type = item.get("articleImageMimeType")

            if not image_data or not mime_type:
                return None

            return {
                "data": image_data,
                "mime_type": mime_type,
            }
        except Exception as e:
            logger.error(f"Error fetching article image: {e}")
            return None

    def _validate_content_data(self, data: Dict[str, Any]) -> None:
        """Validate content data."""
        if "contentType" not in data:
            raise ValidationException(
                message="contentType is required",
                code="VALIDATION_ERROR"
            )

        if data["contentType"] not in self.VALID_CONTENT_TYPES:
            raise ValidationException(
                message=f"Invalid contentType: {data['contentType']}",
                code="VALIDATION_ERROR"
            )

        if "titleEn" not in data:
            raise ValidationException(
                message="titleEn is required",
                code="VALIDATION_ERROR"
            )

        if "category" in data and data["category"] not in self.VALID_CATEGORIES:
            raise ValidationException(
                message=f"Invalid category: {data['category']}",
                code="VALIDATION_ERROR"
            )

        if "status" in data and data["status"] not in self.VALID_STATUSES:
            raise ValidationException(
                message=f"Invalid status: {data['status']}",
                code="VALIDATION_ERROR"
            )

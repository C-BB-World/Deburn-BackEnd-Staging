"""
Hub content service.

Manages content library items with i18n support.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from common.utils.exceptions import (
    NotFoundException,
    ValidationException,
)

logger = logging.getLogger(__name__)


CONTENT_TYPES = ["text_article", "audio_article", "audio_exercise", "video_link"]
CONTENT_STATUSES = ["draft", "in_review", "published", "archived"]
CONTENT_CATEGORIES = ["featured", "leadership", "breath", "meditation", "burnout", "wellbeing", "other"]
MAX_AUDIO_SIZE = 50 * 1024 * 1024  # 50MB


class HubContentService:
    """
    Manages content library items.
    Supports multiple content types with i18n.
    """

    def __init__(self, hub_db: AsyncIOMotorDatabase):
        """
        Initialize HubContentService.

        Args:
            hub_db: Hub MongoDB database connection
        """
        self._db = hub_db
        self._content_collection = hub_db["contentitems"]

    async def get_all(
        self,
        content_type: Optional[str] = None,
        status: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get content items with optional filters.

        Args:
            content_type: Filter by content type
            status: Filter by status
            category: Filter by category

        Returns:
            List of content items
        """
        query = {}

        if content_type:
            query["contentType"] = content_type
        if status:
            query["status"] = status
        if category:
            query["category"] = category

        # Exclude binary audio data to avoid MongoDB 32MB sort memory limit
        projection = {"audioDataEn": 0, "audioDataSv": 0}
        cursor = self._content_collection.find(query, projection)
        cursor = cursor.sort("sortOrder", 1)

        items = await cursor.to_list(length=500)
        return [self._format_content(i, include_audio_data=False) for i in items]

    async def get_by_id(self, content_id: str) -> Optional[Dict[str, Any]]:
        """
        Get single content item by ID.

        Args:
            content_id: Content item ID

        Returns:
            Content item or None
        """
        item = await self._content_collection.find_one({
            "_id": ObjectId(content_id)
        })

        return self._format_content(item, include_audio_data=False) if item else None

    async def get_published(self) -> List[Dict[str, Any]]:
        """
        Get all published content for users.

        Returns:
            List of published content items
        """
        # Exclude binary audio data to avoid MongoDB 32MB sort memory limit
        projection = {"audioDataEn": 0, "audioDataSv": 0}
        cursor = self._content_collection.find({"status": "published"}, projection)
        cursor = cursor.sort("sortOrder", 1)

        items = await cursor.to_list(length=500)
        return [self._format_content(i, include_audio_data=False) for i in items]

    async def get_for_coach(self, topics: List[str]) -> List[Dict[str, Any]]:
        """
        Get content matching coach topics.
        Sorted by coachPriority descending.
        Only returns coachEnabled=True items.

        Args:
            topics: List of coaching topics

        Returns:
            List of matching content items
        """
        query = {
            "status": "published",
            "coachEnabled": True,
            "coachTopics": {"$in": topics}
        }

        # Exclude binary audio data to avoid MongoDB 32MB sort memory limit
        projection = {"audioDataEn": 0, "audioDataSv": 0}
        cursor = self._content_collection.find(query, projection)
        cursor = cursor.sort("coachPriority", -1)

        items = await cursor.to_list(length=50)
        return [self._format_content(i, include_audio_data=False) for i in items]

    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create new content item.

        Args:
            data: Content item data

        Returns:
            Created content item
        """
        if data.get("contentType") not in CONTENT_TYPES:
            raise ValidationException(
                message=f"Invalid content type. Must be one of: {CONTENT_TYPES}",
                code="INVALID_CONTENT_TYPE"
            )

        now = datetime.now(timezone.utc)

        content_doc = {
            "contentType": data["contentType"],
            "status": data.get("status", "draft"),
            "titleEn": data.get("titleEn", ""),
            "titleSv": data.get("titleSv", ""),
            "textContentEn": data.get("textContentEn"),
            "textContentSv": data.get("textContentSv"),
            "videoUrl": data.get("videoUrl"),
            "videoEmbedCode": data.get("videoEmbedCode"),
            "videoAvailableInEn": data.get("videoAvailableInEn", True),
            "videoAvailableInSv": data.get("videoAvailableInSv", True),
            "lengthMinutes": data.get("lengthMinutes", 0),
            "purpose": data.get("purpose"),
            "outcome": data.get("outcome"),
            "relatedFramework": data.get("relatedFramework"),
            "category": data.get("category", "other"),
            "sortOrder": data.get("sortOrder", 0),
            "coachTopics": data.get("coachTopics", []),
            "coachPriority": data.get("coachPriority", 0),
            "coachEnabled": data.get("coachEnabled", True),
            "ttsSpeed": data.get("ttsSpeed", 1.0),
            "ttsVoice": data.get("ttsVoice", "Aria"),
            "voiceoverScriptEn": data.get("voiceoverScriptEn"),
            "voiceoverScriptSv": data.get("voiceoverScriptSv"),
            "backgroundMusicTrack": data.get("backgroundMusicTrack"),
            "productionNotes": data.get("productionNotes"),
            "createdAt": now,
            "updatedAt": now,
        }

        result = await self._content_collection.insert_one(content_doc)
        content_doc["_id"] = result.inserted_id

        logger.info(f"Created content item: {content_doc.get('titleEn', 'Untitled')}")
        return self._format_content(content_doc, include_audio_data=False)

    async def update(
        self,
        content_id: str,
        data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update existing content item.

        Args:
            content_id: Content item ID
            data: Fields to update

        Returns:
            Updated content item or None
        """
        allowed_fields = {
            "contentType", "status", "titleEn", "titleSv",
            "textContentEn", "textContentSv", "videoUrl", "videoEmbedCode",
            "videoAvailableInEn", "videoAvailableInSv", "lengthMinutes",
            "purpose", "outcome", "relatedFramework", "category", "sortOrder",
            "coachTopics", "coachPriority", "coachEnabled", "ttsSpeed", "ttsVoice",
            "voiceoverScriptEn", "voiceoverScriptSv", "backgroundMusicTrack",
            "productionNotes"
        }

        updates = {k: v for k, v in data.items() if k in allowed_fields}

        if not updates:
            return await self.get_by_id(content_id)

        if "contentType" in updates and updates["contentType"] not in CONTENT_TYPES:
            raise ValidationException(
                message=f"Invalid content type. Must be one of: {CONTENT_TYPES}",
                code="INVALID_CONTENT_TYPE"
            )

        if "status" in updates and updates["status"] not in CONTENT_STATUSES:
            raise ValidationException(
                message=f"Invalid status. Must be one of: {CONTENT_STATUSES}",
                code="INVALID_STATUS"
            )

        updates["updatedAt"] = datetime.now(timezone.utc)

        result = await self._content_collection.find_one_and_update(
            {"_id": ObjectId(content_id)},
            {"$set": updates},
            return_document=True
        )

        return self._format_content(result, include_audio_data=False) if result else None

    async def delete(self, content_id: str) -> bool:
        """
        Delete content item.

        Args:
            content_id: Content item ID

        Returns:
            True if deleted
        """
        result = await self._content_collection.delete_one({
            "_id": ObjectId(content_id)
        })

        if result.deleted_count > 0:
            logger.info(f"Deleted content item: {content_id}")
            return True

        return False

    async def upload_audio(
        self,
        content_id: str,
        language: str,
        audio_data: bytes,
        mime_type: str
    ) -> str:
        """
        Upload audio file for content item.

        Args:
            content_id: Content item ID
            language: 'en' or 'sv'
            audio_data: Audio binary data
            mime_type: MIME type (audio/mpeg, audio/wav, etc.)

        Returns:
            Streaming URL
        """
        if language not in ("en", "sv"):
            raise ValidationException(
                message="Language must be 'en' or 'sv'",
                code="INVALID_LANGUAGE"
            )

        if len(audio_data) > MAX_AUDIO_SIZE:
            raise ValidationException(
                message=f"Audio file too large. Maximum size is {MAX_AUDIO_SIZE // (1024*1024)}MB",
                code="FILE_TOO_LARGE"
            )

        lang_suffix = language.capitalize()
        data_field = f"audioData{lang_suffix}"
        mime_field = f"audioMimeType{lang_suffix}"
        file_field = f"audioFile{lang_suffix}"

        streaming_url = f"/api/v2/hub/content/{content_id}/audio/{language}"

        result = await self._content_collection.find_one_and_update(
            {"_id": ObjectId(content_id)},
            {
                "$set": {
                    data_field: audio_data,
                    mime_field: mime_type,
                    file_field: streaming_url,
                    "updatedAt": datetime.now(timezone.utc),
                }
            },
            return_document=True
        )

        if not result:
            raise NotFoundException(
                message="Content item not found",
                code="CONTENT_NOT_FOUND"
            )

        logger.info(f"Uploaded audio for content {content_id} ({language})")
        return streaming_url

    async def get_audio(
        self,
        content_id: str,
        language: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get audio data for streaming.

        Args:
            content_id: Content item ID
            language: 'en' or 'sv'

        Returns:
            Dict with audioData and mimeType or None
        """
        lang_suffix = language.capitalize()
        data_field = f"audioData{lang_suffix}"
        mime_field = f"audioMimeType{lang_suffix}"

        item = await self._content_collection.find_one(
            {"_id": ObjectId(content_id)},
            {data_field: 1, mime_field: 1}
        )

        if not item or not item.get(data_field):
            return None

        return {
            "audioData": item[data_field],
            "mimeType": item.get(mime_field, "audio/mpeg"),
        }

    async def remove_audio(
        self,
        content_id: str,
        language: str
    ) -> bool:
        """
        Remove audio file from content item.

        Args:
            content_id: Content item ID
            language: 'en' or 'sv'

        Returns:
            True if removed
        """
        if language not in ("en", "sv"):
            raise ValidationException(
                message="Language must be 'en' or 'sv'",
                code="INVALID_LANGUAGE"
            )

        lang_suffix = language.capitalize()
        data_field = f"audioData{lang_suffix}"
        mime_field = f"audioMimeType{lang_suffix}"
        file_field = f"audioFile{lang_suffix}"

        result = await self._content_collection.update_one(
            {"_id": ObjectId(content_id)},
            {
                "$unset": {
                    data_field: "",
                    mime_field: "",
                    file_field: "",
                },
                "$set": {"updatedAt": datetime.now(timezone.utc)}
            }
        )

        return result.modified_count > 0

    def _format_content(
        self,
        item: Dict[str, Any],
        include_audio_data: bool = False
    ) -> Dict[str, Any]:
        """Format content item for response."""
        result = {
            "id": str(item["_id"]),
            "contentType": item.get("contentType"),
            "status": item.get("status"),
            "titleEn": item.get("titleEn"),
            "titleSv": item.get("titleSv"),
            "textContentEn": item.get("textContentEn"),
            "textContentSv": item.get("textContentSv"),
            "audioFileEn": item.get("audioFileEn"),
            "audioFileSv": item.get("audioFileSv"),
            "videoUrl": item.get("videoUrl"),
            "videoEmbedCode": item.get("videoEmbedCode"),
            "videoAvailableInEn": item.get("videoAvailableInEn"),
            "videoAvailableInSv": item.get("videoAvailableInSv"),
            "lengthMinutes": item.get("lengthMinutes"),
            "purpose": item.get("purpose"),
            "outcome": item.get("outcome"),
            "relatedFramework": item.get("relatedFramework"),
            "category": item.get("category"),
            "sortOrder": item.get("sortOrder"),
            "coachTopics": item.get("coachTopics", []),
            "coachPriority": item.get("coachPriority"),
            "coachEnabled": item.get("coachEnabled"),
            "ttsSpeed": item.get("ttsSpeed"),
            "ttsVoice": item.get("ttsVoice"),
            "voiceoverScriptEn": item.get("voiceoverScriptEn"),
            "voiceoverScriptSv": item.get("voiceoverScriptSv"),
            "backgroundMusicTrack": item.get("backgroundMusicTrack"),
            "productionNotes": item.get("productionNotes"),
            "createdAt": item.get("createdAt"),
            "updatedAt": item.get("updatedAt"),
        }

        if include_audio_data:
            result["audioDataEn"] = item.get("audioDataEn")
            result["audioDataSv"] = item.get("audioDataSv")

        return result

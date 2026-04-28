"""
Circle group message service.

Handles storing and retrieving messages within Think Tank groups.
Messages are stored as an embedded array in one document per group
(collection: circlegroupmessages), with AES-256-CBC encryption on content.
"""

import logging
import secrets as py_secrets
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from common.utils.exceptions import ValidationException

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 500


class GroupMessageService:
    """Handles CRUD operations for group messages using embedded array pattern."""

    def __init__(self, db: AsyncIOMotorDatabase, encryption_service=None):
        self._db = db
        self._collection = db["circlemessages"]
        self._encryption_service = encryption_service

    async def create_message(
        self,
        group_id: str,
        user_id: str,
        user_name: str,
        content: str,
    ) -> Dict[str, Any]:
        """Create a new message in the group's embedded messages array."""
        content = content.strip() if content else ""

        if not content:
            raise ValidationException(
                message="Message content cannot be empty",
                code="EMPTY_MESSAGE",
            )

        if len(content) > MAX_MESSAGE_LENGTH:
            raise ValidationException(
                message=f"Message cannot exceed {MAX_MESSAGE_LENGTH} characters",
                code="MESSAGE_TOO_LONG",
            )

        now = datetime.now(timezone.utc)
        message_id = f"msg_{py_secrets.token_hex(8)}"

        # Encrypt content if encryption service is available
        stored_content = content
        encrypted = False
        if self._encryption_service:
            stored_content = self._encryption_service.encrypt(content)
            encrypted = True

        message_doc = {
            "messageId": message_id,
            "userId": ObjectId(user_id),
            "userName": user_name,
            "content": stored_content,
            "encrypted": encrypted,
            "createdAt": now,
        }

        # Upsert: create the group doc if it doesn't exist, push message
        await self._collection.update_one(
            {"groupId": ObjectId(group_id)},
            {
                "$push": {"messages": message_doc},
                "$set": {"updatedAt": now},
                "$setOnInsert": {
                    "groupId": ObjectId(group_id),
                    "createdAt": now,
                },
            },
            upsert=True,
        )

        logger.info(f"Message created in group {group_id} by user {user_id}")

        return {
            "id": message_id,
            "groupId": group_id,
            "userId": user_id,
            "userName": user_name,
            "content": content,  # Return plaintext to caller
            "createdAt": now.isoformat(),
        }

    async def get_messages(
        self,
        group_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get messages for a group, decrypting content."""
        doc = await self._collection.find_one(
            {"groupId": ObjectId(group_id)}
        )

        if not doc:
            return []

        messages = doc.get("messages", [])

        # Apply offset and limit
        sliced = messages[offset : offset + limit]

        return [self._format_message(msg, group_id) for msg in sliced]

    async def get_message_count(self, group_id: str) -> int:
        """Get total message count for a group."""
        doc = await self._collection.find_one(
            {"groupId": ObjectId(group_id)},
            {"messages": 1},
        )

        if not doc:
            return 0

        return len(doc.get("messages", []))

    def _format_message(self, msg: dict, group_id: str) -> Dict[str, Any]:
        """Format an embedded message for API response, decrypting if needed."""
        content = msg.get("content", "")

        if msg.get("encrypted") and self._encryption_service:
            decrypted = self._encryption_service.decrypt(content)
            if decrypted is not None:
                content = decrypted

        created_at = msg.get("createdAt")
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()

        return {
            "id": msg.get("messageId", ""),
            "groupId": group_id,
            "userId": str(msg.get("userId", "")),
            "userName": msg.get("userName", ""),
            "content": content,
            "createdAt": created_at,
        }

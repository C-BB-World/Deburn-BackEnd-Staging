"""
Conversation history management service.

Manages coaching conversation history and persistence.
"""

import logging
import secrets
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class ConversationService:
    """
    Manages coaching conversation history.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize ConversationService.

        Args:
            db: MongoDB database connection
        """
        self._db = db
        self._conversations_collection = db["conversations"]

    def _generate_conversation_id(self) -> str:
        """Generate a unique conversation ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        random_part = secrets.token_hex(4)
        return f"conv_{timestamp}_{random_part}"

    async def get_or_create(
        self,
        conversation_id: Optional[str],
        user_id: str,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get existing conversation or create new one.

        Args:
            conversation_id: Existing ID or None for new
            user_id: User's ID
            title: Optional title for new conversations

        Returns:
            Conversation document with messages history
        """
        if conversation_id:
            conversation = await self._conversations_collection.find_one({
                "conversationId": conversation_id,
                "userId": ObjectId(user_id)
            })
            if conversation:
                return self._format_conversation(conversation)

        now = datetime.now(timezone.utc)
        new_id = self._generate_conversation_id()

        conversation_doc = {
            "conversationId": new_id,
            "userId": ObjectId(user_id),
            "messages": [],
            "topics": [],
            "status": "active",
            "lastMessageAt": now,
            "createdAt": now,
            "updatedAt": now
        }

        if title is not None:
            conversation_doc["title"] = title

        result = await self._conversations_collection.insert_one(conversation_doc)
        conversation_doc["_id"] = result.inserted_id

        logger.info(f"Created new conversation {new_id} for user {user_id}")
        return self._format_conversation(conversation_doc)

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a message to conversation history.

        Args:
            conversation_id: Conversation ID
            role: 'user' or 'assistant'
            content: Message content
            metadata: Optional metadata
        """
        now = datetime.now(timezone.utc)

        message = {
            "role": role,
            "content": content,
            "timestamp": now,
            "metadata": metadata or {}
        }

        await self._conversations_collection.update_one(
            {"conversationId": conversation_id},
            {
                "$push": {"messages": message},
                "$set": {
                    "lastMessageAt": now,
                    "updatedAt": now
                }
            }
        )

    async def get_recent_conversations(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get user's recent conversations."""
        cursor = self._conversations_collection.find({
            "userId": ObjectId(user_id),
            "status": "active"
        })
        cursor = cursor.sort("lastMessageAt", -1)
        cursor = cursor.limit(limit)

        conversations = await cursor.to_list(length=limit)
        return [self._format_conversation(c) for c in conversations]

    async def get_conversation(
        self,
        conversation_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get single conversation by ID."""
        conversation = await self._conversations_collection.find_one({
            "conversationId": conversation_id
        })
        return self._format_conversation(conversation) if conversation else None

    async def update_topics(
        self,
        conversation_id: str,
        topics: List[str]
    ) -> None:
        """Update detected topics for conversation."""
        await self._conversations_collection.update_one(
            {"conversationId": conversation_id},
            {
                "$addToSet": {"topics": {"$each": topics}},
                "$set": {"updatedAt": datetime.now(timezone.utc)}
            }
        )

    async def archive_conversation(self, conversation_id: str) -> None:
        """Archive a conversation."""
        await self._conversations_collection.update_one(
            {"conversationId": conversation_id},
            {
                "$set": {
                    "status": "archived",
                    "updatedAt": datetime.now(timezone.utc)
                }
            }
        )

    async def delete_all_for_user(self, user_id: str) -> int:
        """
        Delete all conversations for a user.

        Args:
            user_id: User's ID

        Returns:
            Number of conversations deleted
        """
        result = await self._conversations_collection.delete_many({
            "userId": ObjectId(user_id)
        })
        deleted_count = result.deleted_count
        logger.info(f"Deleted {deleted_count} conversations for user {user_id}")
        return deleted_count

    async def find_conversations(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Find conversations for a user with pagination."""
        cursor = self._conversations_collection.find({
            "userId": ObjectId(user_id),
            "status": "active"
        })
        cursor = cursor.sort("lastMessageAt", -1)
        cursor = cursor.skip(skip)
        cursor = cursor.limit(limit)
        return await cursor.to_list(length=limit)

    async def count_conversations(self, user_id: str) -> int:
        """Count active conversations for a user."""
        return await self._conversations_collection.count_documents({
            "userId": ObjectId(user_id),
            "status": "active"
        })

    async def delete_conversation(
        self,
        conversation_id: str,
        user_id: str
    ) -> bool:
        """Delete a single conversation with ownership check."""
        result = await self._conversations_collection.delete_one({
            "conversationId": conversation_id,
            "userId": ObjectId(user_id)
        })
        if result.deleted_count > 0:
            logger.info(f"Deleted conversation {conversation_id} for user {user_id}")
            return True
        return False

    async def rename(
        self,
        conversation_id: str,
        user_id: str,
        title: str
    ) -> Optional[Dict[str, str]]:
        """Rename a conversation. Returns {id, title} or None if not found."""
        result = await self._conversations_collection.update_one(
            {
                "conversationId": conversation_id,
                "userId": ObjectId(user_id)
            },
            {
                "$set": {
                    "title": title,
                    "updatedAt": datetime.now(timezone.utc)
                }
            }
        )
        if result.matched_count > 0:
            return {"id": conversation_id, "title": title}
        return None

    def format_conversation_summary(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Format a raw MongoDB doc as a summary (no messages, no decryption)."""
        return {
            "id": str(doc["_id"]),
            "conversationId": doc["conversationId"],
            "title": doc.get("title"),
            "messageCount": len(doc.get("messages", [])),
            "topics": doc.get("topics", []),
            "status": doc.get("status", "active"),
            "lastMessageAt": doc.get("lastMessageAt"),
            "createdAt": doc.get("createdAt"),
        }

    def _format_conversation(self, conversation: Dict[str, Any]) -> Dict[str, Any]:
        """Format conversation for response."""
        return {
            "id": str(conversation["_id"]),
            "conversationId": conversation["conversationId"],
            "userId": str(conversation["userId"]),
            "messages": conversation.get("messages", []),
            "topics": conversation.get("topics", []),
            "status": conversation.get("status", "active"),
            "lastMessageAt": conversation.get("lastMessageAt"),
            "createdAt": conversation.get("createdAt"),
            "title": conversation.get("title"),
        }

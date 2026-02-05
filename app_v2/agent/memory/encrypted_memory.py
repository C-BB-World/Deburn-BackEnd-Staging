"""
Encrypted memory implementation.

MongoDB-backed memory with AES-256-CBC encryption for message content.
"""

import logging
import secrets
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app_v2.agent.memory.provider import MemoryProvider
from app_v2.agent.memory.encryption import MemoryEncryptionService
from app_v2.agent.types import Conversation, Message, ConversationSummary

logger = logging.getLogger(__name__)


class EncryptedMemory(MemoryProvider):
    """
    MongoDB-backed memory with AES-256-CBC encryption.

    Stores conversations in 'conversations' collection under deburn-hub.
    Message content is encrypted; metadata remains unencrypted for querying.
    """

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        encryption_service: MemoryEncryptionService
    ):
        """
        Initialize EncryptedMemory.

        Args:
            db: MongoDB database connection (deburn-hub)
            encryption_service: For content encryption/decryption
        """
        self._db = db
        self._collection = db["conversations"]
        self._encryption = encryption_service

    def _generate_conversation_id(self) -> str:
        """Generate a unique conversation ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        random_part = secrets.token_hex(4)
        return f"conv_{timestamp}_{random_part}"

    async def store_message(
        self,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Store a single message with encrypted content."""
        now = datetime.now(timezone.utc)

        encrypted_content = self._encryption.encrypt(content)
        content_hash = self._encryption.hash_for_search(content)

        message = {
            "role": role,
            "content": encrypted_content,
            "contentHash": content_hash,
            "timestamp": now,
            "metadata": metadata or {}
        }

        await self._collection.update_one(
            {"conversationId": conversation_id},
            {
                "$push": {"messages": message},
                "$inc": {"messageCount": 1},
                "$set": {
                    "lastMessageAt": now,
                    "updatedAt": now
                }
            }
        )

        logger.debug(f"Stored encrypted message in conversation {conversation_id}")

    async def get_conversation(
        self,
        conversation_id: str,
        user_id: str
    ) -> Optional[Conversation]:
        """Retrieve full conversation with decrypted messages."""
        doc = await self._collection.find_one({
            "conversationId": conversation_id,
            "userId": ObjectId(user_id)
        })

        if not doc:
            return None

        return self._doc_to_conversation(doc)

    async def get_recent_messages(
        self,
        conversation_id: str,
        user_id: str,
        limit: int = 10
    ) -> List[Message]:
        """Get recent messages for context window."""
        doc = await self._collection.find_one(
            {
                "conversationId": conversation_id,
                "userId": ObjectId(user_id)
            },
            {"messages": {"$slice": -limit}}
        )

        if not doc:
            return []

        messages = []
        for msg in doc.get("messages", []):
            decrypted = self._encryption.decrypt(msg["content"])
            if decrypted is not None:
                messages.append(Message(
                    role=msg["role"],
                    content=decrypted,
                    timestamp=msg["timestamp"],
                    metadata=msg.get("metadata", {})
                ))

        return messages

    async def create_conversation(
        self,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create new conversation."""
        now = datetime.now(timezone.utc)
        conversation_id = self._generate_conversation_id()

        doc = {
            "conversationId": conversation_id,
            "userId": ObjectId(user_id),
            "messages": [],
            "topics": [],
            "status": "active",
            "messageCount": 0,
            "lastMessageAt": now,
            "createdAt": now,
            "updatedAt": now,
            "metadata": metadata or {}
        }

        await self._collection.insert_one(doc)
        logger.info(f"Created new conversation {conversation_id} for user {user_id}")

        return conversation_id

    async def get_or_create_conversation(
        self,
        conversation_id: Optional[str],
        user_id: str
    ) -> Conversation:
        """Get existing conversation or create new one."""
        if conversation_id:
            conversation = await self.get_conversation(conversation_id, user_id)
            if conversation:
                return conversation

        new_id = await self.create_conversation(user_id)
        now = datetime.now(timezone.utc)

        return Conversation(
            id="",
            conversation_id=new_id,
            user_id=user_id,
            messages=[],
            topics=[],
            status="active",
            message_count=0,
            last_message_at=now,
            created_at=now
        )

    async def update_topics(
        self,
        conversation_id: str,
        topics: List[str]
    ) -> None:
        """Update detected topics for conversation."""
        await self._collection.update_one(
            {"conversationId": conversation_id},
            {
                "$addToSet": {"topics": {"$each": topics}},
                "$set": {"updatedAt": datetime.now(timezone.utc)}
            }
        )

    async def get_recent_conversations(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Conversation]:
        """Get user's recent conversations."""
        cursor = self._collection.find({
            "userId": ObjectId(user_id),
            "status": "active"
        })
        cursor = cursor.sort("lastMessageAt", -1)
        cursor = cursor.limit(limit)

        conversations = []
        async for doc in cursor:
            conversations.append(self._doc_to_conversation(doc))

        return conversations

    async def archive_conversation(
        self,
        conversation_id: str
    ) -> None:
        """Archive a conversation."""
        await self._collection.update_one(
            {"conversationId": conversation_id},
            {
                "$set": {
                    "status": "archived",
                    "updatedAt": datetime.now(timezone.utc)
                }
            }
        )
        logger.info(f"Archived conversation {conversation_id}")

    async def search_conversations(
        self,
        user_id: str,
        query: str,
        limit: int = 5
    ) -> List[ConversationSummary]:
        """
        Search past conversations.

        Note: Currently returns empty list.
        Future RAG implementation will use contentHash and embeddings.
        """
        return []

    async def clear_all_memory(
        self,
        user_id: str
    ) -> int:
        """
        Permanently delete all conversations for a user.

        This operation is irreversible.

        Args:
            user_id: User's ID

        Returns:
            Number of conversations deleted
        """
        result = await self._collection.delete_many({
            "userId": ObjectId(user_id)
        })

        deleted_count = result.deleted_count
        logger.info(f"Deleted {deleted_count} conversations for user {user_id}")

        return deleted_count

    def _doc_to_conversation(self, doc: Dict[str, Any]) -> Conversation:
        """Convert MongoDB document to Conversation object."""
        messages = []
        for msg in doc.get("messages", []):
            decrypted = self._encryption.decrypt(msg["content"])
            if decrypted is not None:
                messages.append(Message(
                    role=msg["role"],
                    content=decrypted,
                    timestamp=msg["timestamp"],
                    metadata=msg.get("metadata", {})
                ))

        return Conversation(
            id=str(doc["_id"]),
            conversation_id=doc["conversationId"],
            user_id=str(doc["userId"]),
            messages=messages,
            topics=doc.get("topics", []),
            status=doc.get("status", "active"),
            message_count=doc.get("messageCount", len(messages)),
            last_message_at=doc.get("lastMessageAt"),
            created_at=doc.get("createdAt")
        )

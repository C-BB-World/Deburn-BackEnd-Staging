"""
Conversation persistence pipeline.

Handles encrypted storage and retrieval of coach conversations.
Stateless orchestration logic with dependency injection.
"""

import logging
import secrets
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app_v2.agent.memory.encryption import MemoryEncryptionService

logger = logging.getLogger(__name__)


def _generate_conversation_id() -> str:
    """Generate a unique conversation ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    random_part = secrets.token_hex(4)
    return f"conv_{timestamp}_{random_part}"


async def get_or_create_conversation(
    db: AsyncIOMotorDatabase,
    encryption_service: MemoryEncryptionService,
    conversation_id: Optional[str],
    user_id: str
) -> Dict[str, Any]:
    """
    Get existing conversation or create a new one.

    Args:
        db: Hub database connection
        encryption_service: For decrypting messages
        conversation_id: Existing conversation ID or None
        user_id: User's ID

    Returns:
        Conversation dict with decrypted messages
    """
    collection = db["conversations"]

    if conversation_id:
        conversation = await collection.find_one({
            "conversationId": conversation_id,
            "userId": ObjectId(user_id)
        })
        if conversation:
            return _format_conversation(conversation, encryption_service)

    # Create new conversation
    now = datetime.now(timezone.utc)
    new_id = _generate_conversation_id()

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

    result = await collection.insert_one(conversation_doc)
    conversation_doc["_id"] = result.inserted_id

    logger.info(f"Created new conversation {new_id} for user {user_id}")
    return _format_conversation(conversation_doc, encryption_service)


async def save_message(
    db: AsyncIOMotorDatabase,
    encryption_service: MemoryEncryptionService,
    conversation_id: str,
    role: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
    language: str = "en"
) -> None:
    """
    Save an encrypted message to the conversation.

    Args:
        db: Hub database connection
        encryption_service: For encrypting message content
        conversation_id: Conversation ID
        role: 'user' or 'assistant'
        content: Message content (will be encrypted)
        metadata: Optional metadata (not encrypted)
        language: Language code of the message ('en' or 'sv')
    """
    collection = db["conversations"]
    now = datetime.now(timezone.utc)

    # Encrypt the message content
    encrypted_content = encryption_service.encrypt(content)

    message = {
        "role": role,
        "content": encrypted_content,
        "encrypted": True,
        "language": language,
        "timestamp": now,
        "metadata": metadata or {},
        "translations": {}
    }

    await collection.update_one(
        {"conversationId": conversation_id},
        {
            "$push": {"messages": message},
            "$set": {
                "lastMessageAt": now,
                "updatedAt": now
            }
        }
    )

    logger.debug(f"Saved encrypted {role} message to conversation {conversation_id}")


async def update_topics(
    db: AsyncIOMotorDatabase,
    conversation_id: str,
    topics: List[str]
) -> None:
    """
    Update detected topics for a conversation.

    Args:
        db: Hub database connection
        conversation_id: Conversation ID
        topics: List of topic strings
    """
    collection = db["conversations"]

    await collection.update_one(
        {"conversationId": conversation_id},
        {
            "$addToSet": {"topics": {"$each": topics}},
            "$set": {"updatedAt": datetime.now(timezone.utc)}
        }
    )


async def get_recent_conversations(
    db: AsyncIOMotorDatabase,
    encryption_service: MemoryEncryptionService,
    user_id: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get user's recent conversations with decrypted messages.

    Args:
        db: Hub database connection
        encryption_service: For decrypting messages
        user_id: User's ID
        limit: Maximum conversations to return

    Returns:
        List of conversation dicts with decrypted messages
    """
    collection = db["conversations"]

    cursor = collection.find({
        "userId": ObjectId(user_id),
        "status": "active"
    })
    cursor = cursor.sort("lastMessageAt", -1)
    cursor = cursor.limit(limit)

    conversations = await cursor.to_list(length=limit)
    return [_format_conversation(c, encryption_service) for c in conversations]


async def get_conversation(
    db: AsyncIOMotorDatabase,
    encryption_service: MemoryEncryptionService,
    conversation_id: str,
    user_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get a specific conversation with decrypted messages.

    Args:
        db: Hub database connection
        encryption_service: For decrypting messages
        conversation_id: Conversation ID
        user_id: User's ID (for authorization)

    Returns:
        Conversation dict or None
    """
    collection = db["conversations"]

    conversation = await collection.find_one({
        "conversationId": conversation_id,
        "userId": ObjectId(user_id)
    })

    if not conversation:
        return None

    return _format_conversation(conversation, encryption_service)


async def delete_all_for_user(
    db: AsyncIOMotorDatabase,
    user_id: str
) -> int:
    """
    Delete all conversations for a user.

    Args:
        db: Hub database connection
        user_id: User's ID

    Returns:
        Number of conversations deleted
    """
    collection = db["conversations"]

    result = await collection.delete_many({
        "userId": ObjectId(user_id)
    })

    deleted_count = result.deleted_count
    logger.info(f"Deleted {deleted_count} conversations for user {user_id}")
    return deleted_count


async def archive_conversation(
    db: AsyncIOMotorDatabase,
    conversation_id: str
) -> None:
    """
    Archive a conversation.

    Args:
        db: Hub database connection
        conversation_id: Conversation ID
    """
    collection = db["conversations"]

    await collection.update_one(
        {"conversationId": conversation_id},
        {
            "$set": {
                "status": "archived",
                "updatedAt": datetime.now(timezone.utc)
            }
        }
    )
    logger.info(f"Archived conversation {conversation_id}")


def _format_conversation(
    conversation: Dict[str, Any],
    encryption_service: MemoryEncryptionService
) -> Dict[str, Any]:
    """
    Format conversation document with decrypted messages.

    Args:
        conversation: Raw MongoDB document
        encryption_service: For decrypting messages

    Returns:
        Formatted conversation dict
    """
    messages = []
    for msg in conversation.get("messages", []):
        content = msg.get("content", "")

        # Decrypt if encrypted
        if msg.get("encrypted", False):
            decrypted = encryption_service.decrypt(content)
            if decrypted is not None:
                content = decrypted
            else:
                logger.warning(f"Failed to decrypt message in conversation {conversation.get('conversationId')}")
                content = "[Decryption failed]"

        messages.append({
            "role": msg["role"],
            "content": content,
            "timestamp": msg.get("timestamp"),
            "metadata": msg.get("metadata", {})
        })

    return {
        "id": str(conversation["_id"]),
        "conversationId": conversation["conversationId"],
        "userId": str(conversation["userId"]),
        "messages": messages,
        "topics": conversation.get("topics", []),
        "status": conversation.get("status", "active"),
        "lastMessageAt": conversation.get("lastMessageAt"),
        "createdAt": conversation.get("createdAt"),
    }

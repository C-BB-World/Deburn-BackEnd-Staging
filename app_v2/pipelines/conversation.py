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
    user_id: str,
    first_message: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get existing conversation or create a new one.

    Args:
        db: Hub database connection
        encryption_service: For decrypting messages
        conversation_id: Existing conversation ID or None
        user_id: User's ID
        first_message: First user message (used to auto-generate title for new conversations)

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

    if first_message is not None:
        conversation_doc["title"] = first_message[:50].strip()

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
        "title": conversation.get("title"),
    }


def _format_conversation_summary(doc: Dict[str, Any]) -> Dict[str, Any]:
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


async def list_conversation_summaries(
    db: AsyncIOMotorDatabase,
    user_id: str,
    skip: int = 0,
    limit: int = 20
) -> Dict[str, Any]:
    """
    List conversation summaries (no messages, no decryption).

    Args:
        db: Hub database connection
        user_id: User's ID
        skip: Pagination offset
        limit: Page size

    Returns:
        Dict with conversations list, total count, and hasMore flag
    """
    collection = db["conversations"]

    cursor = collection.find({
        "userId": ObjectId(user_id),
        "status": "active"
    })
    cursor = cursor.sort("lastMessageAt", -1)
    cursor = cursor.skip(skip)
    cursor = cursor.limit(limit)

    docs = await cursor.to_list(length=limit)
    total = await collection.count_documents({
        "userId": ObjectId(user_id),
        "status": "active"
    })

    conversations = [_format_conversation_summary(doc) for doc in docs]

    return {
        "conversations": conversations,
        "total": total,
        "hasMore": (skip + limit) < total,
    }


async def delete_conversation_by_id(
    db: AsyncIOMotorDatabase,
    conversation_id: str,
    user_id: str
) -> bool:
    """
    Delete a single conversation with ownership check.

    Args:
        db: Hub database connection
        conversation_id: Conversation ID to delete
        user_id: User's ID (ownership check)

    Returns:
        True if deleted, False if not found
    """
    collection = db["conversations"]

    result = await collection.delete_one({
        "conversationId": conversation_id,
        "userId": ObjectId(user_id)
    })

    if result.deleted_count > 0:
        logger.info(f"Deleted conversation {conversation_id} for user {user_id}")
        return True
    return False


async def rename_conversation(
    db: AsyncIOMotorDatabase,
    conversation_id: str,
    user_id: str,
    title: str
) -> Optional[Dict[str, str]]:
    """
    Rename a conversation.

    Args:
        db: Hub database connection
        conversation_id: Conversation ID to rename
        user_id: User's ID (ownership check)
        title: New title

    Returns:
        Dict with id and title, or None if not found
    """
    collection = db["conversations"]

    result = await collection.update_one(
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

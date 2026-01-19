"""
Conversations router.

Provides endpoints for conversation history management.
Uses the conversation pipeline for encrypted persistence.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app_v2.dependencies import (
    require_auth,
    get_hub_db,
    get_memory_encryption_service,
)
from app_v2.agent.memory.encryption import MemoryEncryptionService
from app_v2.pipelines import conversation as conversation_pipeline
from common.utils import success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("")
async def get_conversation_history(
    user: Annotated[dict, Depends(require_auth)],
    hub_db: Annotated[AsyncIOMotorDatabase, Depends(get_hub_db)],
    encryption_service: Annotated[MemoryEncryptionService, Depends(get_memory_encryption_service)],
):
    """
    Get user's conversation history.

    Returns the most recent conversation with decrypted messages.
    """
    user_id = str(user.get("_id", ""))

    conversations = await conversation_pipeline.get_recent_conversations(
        db=hub_db,
        encryption_service=encryption_service,
        user_id=user_id,
        limit=1
    )

    if not conversations:
        return success_response({
            "conversation": None,
            "messages": []
        })

    conversation = conversations[0]

    # Convert messages to serializable format
    messages = [
        {
            "role": msg.get("role"),
            "content": msg.get("content"),
            "timestamp": msg.get("timestamp").isoformat() if msg.get("timestamp") else None,
        }
        for msg in conversation.get("messages", [])
    ]

    return success_response({
        "conversation": {
            "id": conversation.get("conversationId"),
            "messageCount": len(conversation.get("messages", [])),
            "lastMessageAt": conversation.get("lastMessageAt").isoformat() if conversation.get("lastMessageAt") else None,
            "createdAt": conversation.get("createdAt").isoformat() if conversation.get("createdAt") else None,
        },
        "messages": messages
    })


@router.post("")
async def save_conversation(
    user: Annotated[dict, Depends(require_auth)],
):
    """
    Save/sync conversation.

    Note: Messages are stored automatically during chat via the pipeline.
    This endpoint is for explicit sync if needed.
    """
    return success_response({"synced": True})


@router.delete("")
async def delete_conversation_history(
    user: Annotated[dict, Depends(require_auth)],
    hub_db: Annotated[AsyncIOMotorDatabase, Depends(get_hub_db)],
):
    """
    Delete all conversation history for the user.

    This action is irreversible.
    """
    user_id = str(user.get("_id", ""))

    deleted_count = await conversation_pipeline.delete_all_for_user(
        db=hub_db,
        user_id=user_id
    )

    logger.info(f"Deleted {deleted_count} conversations for user {user_id}")

    return success_response({
        "deleted": True,
        "deletedCount": deleted_count
    })

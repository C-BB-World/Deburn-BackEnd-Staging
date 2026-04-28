"""
Translation pipeline functions.

Orchestrates translation of conversation messages with caching.
"""

import logging
from typing import Dict, Any, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app_v2.services.translation import TranslationService
from app_v2.agent import MemoryEncryptionService

logger = logging.getLogger(__name__)

# Maximum messages to translate in one request
MAX_BATCH_SIZE = 20
MAX_TOTAL_TRANSLATABLE = 100


async def translate_conversation_messages(
    db: AsyncIOMotorDatabase,
    translation_service: TranslationService,
    encryption_service: MemoryEncryptionService,
    conversation_id: str,
    user_id: str,
    target_language: str,
    start_index: Optional[int] = None,
    count: int = 20,
) -> Dict[str, Any]:
    """
    Translate messages in a conversation to target language.

    Args:
        db: Database connection
        translation_service: Translation service
        encryption_service: For encrypting/decrypting messages
        conversation_id: Conversation ID
        user_id: User ID (for encryption key)
        target_language: Target language code ('en' or 'sv')
        start_index: Starting message index (None = from end)
        count: Number of messages to translate (max 20)

    Returns:
        Dict with translated messages and metadata
    """
    # Limit count
    count = min(count, MAX_BATCH_SIZE)

    # Get conversation
    collection = db["conversations"]
    conversation = await collection.find_one({
        "conversationId": conversation_id,
        "userId": ObjectId(user_id),
    })

    if not conversation:
        return {"translatedMessages": [], "error": "Conversation not found"}

    messages = conversation.get("messages", [])
    total_messages = len(messages)

    if total_messages == 0:
        return {"translatedMessages": [], "totalMessages": 0}

    # Calculate range
    if start_index is None:
        start_index = max(0, total_messages - count)

    end_index = min(start_index + count, total_messages)
    start_index = max(0, min(start_index, total_messages - 1))

    # Get messages that need translation
    messages_to_translate = []
    already_translated = []

    for i in range(start_index, end_index):
        msg = messages[i]
        msg_language = msg.get("language", "en")
        translations = msg.get("translations", {})
        is_encrypted = msg.get("encrypted", False)

        # Skip if already in target language
        if msg_language == target_language:
            already_translated.append({
                "index": i,
                "content": _decrypt_content(msg.get("content", ""), encryption_service, is_encrypted),
                "alreadyInTargetLanguage": True,
            })
            continue

        # Check if translation exists (translations are also encrypted)
        if target_language in translations:
            already_translated.append({
                "index": i,
                "content": _decrypt_content(translations[target_language], encryption_service, is_encrypted),
                "fromCache": True,
            })
            continue

        # Need to translate this message
        decrypted_content = _decrypt_content(msg.get("content", ""), encryption_service, is_encrypted)
        messages_to_translate.append({
            "index": i,
            "content": decrypted_content,
            "sourceLanguage": msg_language,
        })

    # Translate messages that need it
    newly_translated = []
    if messages_to_translate:
        # Group by source language for better translation
        translated_results = await translation_service.translate_messages(
            messages=[{"index": m["index"], "content": m["content"]} for m in messages_to_translate],
            target_language=target_language,
        )

        # Cache translations in database
        for result in translated_results:
            idx = result["index"]
            translated_content = result["content"]

            # Encrypt the translation
            encrypted_translation = _encrypt_content(translated_content, encryption_service)

            # Update the message with translation
            await collection.update_one(
                {"conversationId": conversation_id},
                {"$set": {f"messages.{idx}.translations.{target_language}": encrypted_translation}}
            )

            newly_translated.append({
                "index": idx,
                "content": translated_content,
                "newlyTranslated": True,
            })

    # Combine all results
    all_translated = already_translated + newly_translated
    all_translated.sort(key=lambda x: x["index"])

    return {
        "translatedMessages": all_translated,
        "totalMessages": total_messages,
        "startIndex": start_index,
        "endIndex": end_index,
        "newlyTranslated": len(newly_translated),
        "fromCache": len([m for m in already_translated if m.get("fromCache")]),
    }


def _decrypt_content(content: str, encryption_service: MemoryEncryptionService, is_encrypted: bool = True) -> str:
    """Decrypt message content."""
    try:
        if content and is_encrypted:
            decrypted = encryption_service.decrypt(content)
            if decrypted is not None:
                return decrypted
        return content
    except Exception:
        return content


def _encrypt_content(content: str, encryption_service: MemoryEncryptionService) -> str:
    """Encrypt message content."""
    try:
        return encryption_service.encrypt(content)
    except Exception:
        return content


async def get_conversation_with_translations(
    db: AsyncIOMotorDatabase,
    encryption_service: MemoryEncryptionService,
    conversation_id: str,
    user_id: str,
    language: str,
    limit: int = 50,
) -> Dict[str, Any]:
    """
    Get conversation messages in requested language.

    Returns translated content if available, otherwise original.

    Args:
        db: Database connection
        encryption_service: For decryption
        conversation_id: Conversation ID
        user_id: User ID
        language: Preferred language
        limit: Max messages to return

    Returns:
        Conversation with messages in preferred language where available
    """
    collection = db["conversations"]
    conversation = await collection.find_one({
        "conversationId": conversation_id,
        "userId": ObjectId(user_id),
    })

    if not conversation:
        return None

    messages = conversation.get("messages", [])[-limit:]
    formatted_messages = []

    for i, msg in enumerate(messages):
        msg_language = msg.get("language", "en")
        translations = msg.get("translations", {})
        is_encrypted = msg.get("encrypted", False)

        # Determine which content to use
        if msg_language == language:
            content = msg.get("content", "")
        elif language in translations:
            content = translations[language]
        else:
            content = msg.get("content", "")

        # Decrypt
        decrypted = _decrypt_content(content, encryption_service, is_encrypted)

        formatted_messages.append({
            "role": msg.get("role"),
            "content": decrypted,
            "timestamp": msg.get("timestamp"),
            "language": msg_language,
            "hasTranslation": language in translations or msg_language == language,
        })

    return {
        "conversationId": str(conversation["_id"]),
        "messages": formatted_messages,
        "totalMessages": len(conversation.get("messages", [])),
    }

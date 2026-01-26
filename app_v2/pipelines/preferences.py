"""
Pipelines for user preferences management.

Handles coach preferences including voice settings.
Stores in separate 'userpreferences' collection.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app_v2.schemas.user import VALID_VOICES
from common.utils.exceptions import ValidationException

logger = logging.getLogger(__name__)

# Default preferences
DEFAULT_COACH_PREFERENCES = {
    "voice": "Alice"
}


async def get_preferences_pipeline(
    db: AsyncIOMotorDatabase,
    user_id: str
) -> Dict[str, Any]:
    """
    Get user's coach preferences from userpreferences collection.

    Args:
        db: MongoDB database connection
        user_id: User's MongoDB ObjectId as string

    Returns:
        Dict with coachPreferences
    """
    collection = db["userpreferences"]

    doc = await collection.find_one(
        {"userId": ObjectId(user_id)},
        {"coachPreferences": 1}
    )

    if not doc:
        # Return defaults if no preferences document exists
        return {"coachPreferences": DEFAULT_COACH_PREFERENCES.copy()}

    # Return stored preferences or defaults
    coach_prefs = doc.get("coachPreferences", {})

    # Merge with defaults for any missing fields
    result = DEFAULT_COACH_PREFERENCES.copy()
    result.update(coach_prefs)

    return {"coachPreferences": result}


async def update_preferences_pipeline(
    db: AsyncIOMotorDatabase,
    user_id: str,
    coach_preferences: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Update user's coach preferences in userpreferences collection.

    Args:
        db: MongoDB database connection
        user_id: User's MongoDB ObjectId as string
        coach_preferences: Dict with preference fields to update

    Returns:
        Dict with updated coachPreferences

    Raises:
        ValidationException: If voice is invalid
    """
    collection = db["userpreferences"]

    # Validate voice if provided
    if "voice" in coach_preferences:
        voice = coach_preferences["voice"]
        if voice not in VALID_VOICES:
            raise ValidationException(
                message=f"Invalid voice '{voice}'. Must be one of: {', '.join(VALID_VOICES)}",
                code="INVALID_VOICE"
            )

    now = datetime.now(timezone.utc)

    # Build update with dot notation for nested fields
    update_fields = {"updatedAt": now}
    for key, value in coach_preferences.items():
        update_fields[f"coachPreferences.{key}"] = value

    # Upsert the preferences document
    await collection.update_one(
        {"userId": ObjectId(user_id)},
        {
            "$set": update_fields,
            "$setOnInsert": {
                "userId": ObjectId(user_id),
                "createdAt": now
            }
        },
        upsert=True
    )

    logger.info(f"Updated coach preferences for user {user_id}: {list(coach_preferences.keys())}")

    # Return updated preferences
    return await get_preferences_pipeline(db, user_id)

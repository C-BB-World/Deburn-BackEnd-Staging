"""
Learning pipeline functions.

Stateless orchestration logic for learning operations.
"""

import logging
from datetime import date
from typing import Dict, Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app_v2.services.learning import LearningQueueService

logger = logging.getLogger(__name__)


async def get_todays_focus_pipeline(
    queue_service: LearningQueueService,
    hub_db: AsyncIOMotorDatabase,
    user_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Get today's learning focus for a user.

    Handles:
    - Creating queue for new users
    - Reshuffling when cycle is completed
    - Advancing index on new day

    Args:
        queue_service: For queue operations
        hub_db: Hub database for content items
        user_id: Current user's ID

    Returns:
        Dict with module info and progress, or None if no content available
    """
    # 1. Get all published content IDs
    all_content_ids = await _get_all_content_ids(hub_db)
    print(f"[TODAY'S FOCUS] Found {len(all_content_ids)} published content items for user {user_id}")

    if not all_content_ids:
        logger.warning("No learning content available in hub_db.contentitems with status='published'")
        return None

    # 2. Get user's queue
    queue_doc = await queue_service.get_queue(user_id)

    # 3. Create queue if doesn't exist (new user or existing user without queue)
    if not queue_doc:
        queue_doc = await queue_service.create_queue(user_id, all_content_ids)

    # 4. Check if cycle completed (currentIndex >= queue length)
    if queue_doc["currentIndex"] >= len(queue_doc["queue"]):
        queue_doc = await queue_service.reshuffle_queue(user_id, all_content_ids)

    # 5. Check if new day - advance index
    today = date.today().isoformat()
    if queue_doc["lastAdvancedDate"] < today:
        queue_doc = await queue_service.advance_index(user_id)

        # Check again if completed after advance
        if queue_doc["currentIndex"] >= len(queue_doc["queue"]):
            queue_doc = await queue_service.reshuffle_queue(user_id, all_content_ids)

    # 6. Get current module details
    current_index = queue_doc["currentIndex"]
    current_id = queue_doc["queue"][current_index]

    module = await _get_content_item(hub_db, current_id)

    if not module:
        # Content item was deleted, reshuffle to fix
        logger.warning(f"Content item {current_id} not found, reshuffling queue")
        queue_doc = await queue_service.reshuffle_queue(user_id, all_content_ids)
        current_index = 0
        current_id = queue_doc["queue"][current_index]
        module = await _get_content_item(hub_db, current_id)

        if not module:
            return None

    # 7. Calculate progress
    total_modules = len(queue_doc["queue"])
    progress = current_index / total_modules if total_modules > 0 else 0

    return {
        "module": {
            "id": module["id"],
            "contentType": module["contentType"],
            "category": module.get("category"),
            "titleEn": module.get("titleEn"),
            "titleSv": module.get("titleSv"),
            "lengthMinutes": module.get("lengthMinutes"),
        },
        "currentIndex": current_index,
        "totalModules": total_modules,
        "progress": progress,
    }


async def _get_all_content_ids(hub_db: AsyncIOMotorDatabase) -> list:
    """
    Get all published content item IDs.

    Args:
        hub_db: Hub database connection

    Returns:
        List of content ID strings
    """
    collection = hub_db["contentitems"]
    cursor = collection.find(
        {"status": "published"},
        {"_id": 1}
    )

    items = await cursor.to_list(length=500)
    return [str(item["_id"]) for item in items]


async def _get_content_item(
    hub_db: AsyncIOMotorDatabase,
    content_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Get a content item by ID.

    Args:
        hub_db: Hub database connection
        content_id: Content item ID

    Returns:
        Formatted content item or None
    """
    from bson import ObjectId

    collection = hub_db["contentitems"]

    try:
        item = await collection.find_one({"_id": ObjectId(content_id)})
    except Exception:
        return None

    if not item:
        return None

    return {
        "id": str(item["_id"]),
        "contentType": item.get("contentType"),
        "category": item.get("category"),
        "titleEn": item.get("titleEn"),
        "titleSv": item.get("titleSv"),
        "lengthMinutes": item.get("lengthMinutes"),
    }

"""
Reflection CRUD service.

Handles reflection prompt retrieval and storage.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

REFLECTION_PROMPT = "How was your day today?"


class ReflectionService:
    """
    Handles reflection prompt and storage.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        self._db = db
        self._collection = db["reflections"]

    def get_prompt(self) -> str:
        """Return the current reflection prompt (placeholder)."""
        return REFLECTION_PROMPT

    async def submit_reflection(
        self,
        user_id: str,
        reflection: str,
    ) -> Dict[str, Any]:
        """
        Store a user reflection.

        Args:
            user_id: User's ID
            reflection: The reflection text

        Returns:
            Created reflection document
        """
        now = datetime.now(timezone.utc)

        doc = {
            "userId": user_id,
            "reflection": reflection.strip(),
            "createdAt": now,
        }

        result = await self._collection.insert_one(doc)
        doc["_id"] = result.inserted_id

        logger.info(f"Reflection submitted: {result.inserted_id} for user {user_id}")
        return doc

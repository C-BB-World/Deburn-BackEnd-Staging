"""
Reflection CRUD service.

Handles reflection prompt retrieval and storage.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from bson import ObjectId
from fastapi import HTTPException
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

    # ─────────────────────────────────────────────────────────────────
    # Public: get_reflections
    # ─────────────────────────────────────────────────────────────────

    async def get_reflections(
        self,
        user_id: str,
        skip: int,
        limit: int,
    ) -> Dict[str, Any]:
        """Return a paginated list of reflections for a user."""
        filter_ = self._build_user_filter(user_id)
        docs = await self._fetch_page(filter_, skip, limit)
        total = await self._count(filter_)
        return self._build_paginated_response(docs, total, skip, limit)

    def _build_user_filter(self, user_id: str) -> Dict[str, Any]:
        return {"userId": user_id}

    async def _fetch_page(
        self,
        filter_: Dict[str, Any],
        skip: int,
        limit: int,
    ) -> List[Dict[str, Any]]:
        cursor = (
            self._collection.find(filter_)
            .sort("createdAt", -1)
            .skip(skip)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def _count(self, filter_: Dict[str, Any]) -> int:
        return await self._collection.count_documents(filter_)

    def _serialize(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "_id": str(doc["_id"]),
            "reflection": doc.get("reflection", ""),
            "createdAt": doc.get("createdAt"),
        }
        if "updatedAt" in doc:
            result["updatedAt"] = doc["updatedAt"]
        return result

    def _build_paginated_response(
        self,
        docs: List[Dict[str, Any]],
        total: int,
        skip: int,
        limit: int,
    ) -> Dict[str, Any]:
        return {
            "reflections": [self._serialize(d) for d in docs],
            "total": total,
            "hasMore": (skip + limit) < total,
        }

    # ─────────────────────────────────────────────────────────────────
    # Public: update_reflection
    # ─────────────────────────────────────────────────────────────────

    async def update_reflection(
        self,
        reflection_id: str,
        user_id: str,
        new_text: str,
    ) -> Dict[str, Any]:
        """Update a reflection's text (ownership enforced)."""
        query = self._build_ownership_query(reflection_id, user_id)
        update = self._build_update_doc(new_text)
        doc = await self._apply_update(query, update)
        if doc is None:
            raise HTTPException(status_code=404, detail="Reflection not found")
        return self._serialize(doc)

    def _build_ownership_query(
        self,
        reflection_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        return {"_id": ObjectId(reflection_id), "userId": user_id}

    def _build_update_doc(self, new_text: str) -> Dict[str, Any]:
        return {
            "$set": {
                "reflection": new_text.strip(),
                "updatedAt": datetime.now(timezone.utc),
            }
        }

    async def _apply_update(
        self,
        query: Dict[str, Any],
        update: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        from pymongo import ReturnDocument
        return await self._collection.find_one_and_update(
            query,
            update,
            return_document=ReturnDocument.AFTER,
        )

"""
Commitment tracking service.

Manages micro-commitments from coaching conversations.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from common.utils.exceptions import NotFoundException

logger = logging.getLogger(__name__)


@dataclass
class CommitmentData:
    """Extracted commitment data."""
    commitment: str
    reflection_question: Optional[str] = None
    psychological_trigger: Optional[str] = None
    circle_prompt: Optional[str] = None


@dataclass
class CommitmentStats:
    """Commitment statistics."""
    active: int
    completed: int
    expired: int
    dismissed: int
    total: int
    completion_rate: int


class CommitmentService:
    """
    Tracks micro-commitments from coaching conversations.
    Handles 14-day follow-up cycle.
    """

    DEFAULT_FOLLOWUP_DAYS = 14
    DEFAULT_EXPIRY_DAYS = 30
    MAX_ACTIVE_COMMITMENTS = 5

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize CommitmentService.

        Args:
            db: MongoDB database connection
        """
        self._db = db
        self._commitments_collection = db["coachCommitments"]

    async def create_commitment(
        self,
        user_id: str,
        conversation_id: str,
        commitment_data: CommitmentData,
        topic: str = "other"
    ) -> Dict[str, Any]:
        """
        Create a new commitment with 14-day follow-up.

        Args:
            user_id: User's ID
            conversation_id: Source conversation
            commitment_data: Extracted commitment data
            topic: Coaching topic

        Returns:
            Created commitment document
        """
        now = datetime.now(timezone.utc)
        follow_up_date = now + timedelta(days=self.DEFAULT_FOLLOWUP_DAYS)

        commitment_doc = {
            "userId": ObjectId(user_id),
            "conversationId": conversation_id,
            "commitment": commitment_data.commitment[:1000],
            "trigger": None,
            "reflectionQuestion": commitment_data.reflection_question[:500] if commitment_data.reflection_question else None,
            "psychologicalTrigger": commitment_data.psychological_trigger[:500] if commitment_data.psychological_trigger else None,
            "circlePrompt": commitment_data.circle_prompt[:500] if commitment_data.circle_prompt else None,
            "topic": topic,
            "status": "active",
            "followUpDate": follow_up_date,
            "completedAt": None,
            "reflectionNotes": None,
            "helpfulnessRating": None,
            "followUpCount": 0,
            "lastFollowUpAt": None,
            "createdAt": now,
            "updatedAt": now
        }

        result = await self._commitments_collection.insert_one(commitment_doc)
        commitment_doc["_id"] = result.inserted_id

        logger.info(f"Created commitment for user {user_id}: {commitment_data.commitment[:50]}...")
        return self._format_commitment(commitment_doc)

    async def get_due_followups(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get commitments due for follow-up.

        Args:
            user_id: User's ID

        Returns:
            Commitments where status='active' and followUpDate <= now
        """
        now = datetime.now(timezone.utc)

        cursor = self._commitments_collection.find({
            "userId": ObjectId(user_id),
            "status": "active",
            "followUpDate": {"$lte": now}
        })
        cursor = cursor.sort("followUpDate", 1)

        commitments = await cursor.to_list(length=10)
        return [self._format_commitment(c) for c in commitments]

    async def get_active_commitments(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all active commitments for user."""
        cursor = self._commitments_collection.find({
            "userId": ObjectId(user_id),
            "status": "active"
        })
        cursor = cursor.sort("createdAt", -1)

        commitments = await cursor.to_list(length=50)
        return [self._format_commitment(c) for c in commitments]

    async def complete_commitment(
        self,
        commitment_id: str,
        user_id: str,
        reflection_notes: Optional[str] = None,
        helpfulness_rating: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Mark commitment as completed.

        Args:
            commitment_id: Commitment ID
            user_id: User's ID (for validation)
            reflection_notes: User's reflection
            helpfulness_rating: 1-5 rating

        Returns:
            Updated commitment

        Raises:
            NotFoundException: If not found or wrong user
        """
        now = datetime.now(timezone.utc)

        result = await self._commitments_collection.find_one_and_update(
            {
                "_id": ObjectId(commitment_id),
                "userId": ObjectId(user_id),
                "status": "active"
            },
            {
                "$set": {
                    "status": "completed",
                    "completedAt": now,
                    "reflectionNotes": reflection_notes[:2000] if reflection_notes else None,
                    "helpfulnessRating": helpfulness_rating if helpfulness_rating and 1 <= helpfulness_rating <= 5 else None,
                    "updatedAt": now
                }
            },
            return_document=True
        )

        if not result:
            raise NotFoundException(message="Commitment not found", code="COMMITMENT_NOT_FOUND")

        logger.info(f"Commitment {commitment_id} completed by user {user_id}")
        return self._format_commitment(result)

    async def dismiss_commitment(
        self,
        commitment_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Mark commitment as dismissed."""
        now = datetime.now(timezone.utc)

        result = await self._commitments_collection.find_one_and_update(
            {
                "_id": ObjectId(commitment_id),
                "userId": ObjectId(user_id),
                "status": "active"
            },
            {
                "$set": {
                    "status": "dismissed",
                    "updatedAt": now
                }
            },
            return_document=True
        )

        if not result:
            raise NotFoundException(message="Commitment not found", code="COMMITMENT_NOT_FOUND")

        return self._format_commitment(result)

    async def get_stats(self, user_id: str) -> CommitmentStats:
        """Get commitment statistics."""
        pipeline = [
            {"$match": {"userId": ObjectId(user_id)}},
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }}
        ]

        results = await self._commitments_collection.aggregate(pipeline).to_list(length=10)

        stats = {"active": 0, "completed": 0, "expired": 0, "dismissed": 0}
        for result in results:
            status = result["_id"]
            if status in stats:
                stats[status] = result["count"]

        total = sum(stats.values())
        completion_rate = int((stats["completed"] / total) * 100) if total > 0 else 0

        return CommitmentStats(
            active=stats["active"],
            completed=stats["completed"],
            expired=stats["expired"],
            dismissed=stats["dismissed"],
            total=total,
            completion_rate=completion_rate
        )

    async def expire_old_commitments(self, days_old: int = 30) -> int:
        """
        Expire commitments older than threshold.

        Args:
            days_old: Days threshold

        Returns:
            Count of commitments expired
        """
        threshold = datetime.now(timezone.utc) - timedelta(days=days_old)

        result = await self._commitments_collection.update_many(
            {
                "status": "active",
                "createdAt": {"$lt": threshold}
            },
            {
                "$set": {
                    "status": "expired",
                    "updatedAt": datetime.now(timezone.utc)
                }
            }
        )

        if result.modified_count > 0:
            logger.info(f"Expired {result.modified_count} old commitments")

        return result.modified_count

    async def record_followup(self, commitment_id: str) -> None:
        """Record that a follow-up was shown."""
        now = datetime.now(timezone.utc)

        await self._commitments_collection.update_one(
            {"_id": ObjectId(commitment_id)},
            {
                "$inc": {"followUpCount": 1},
                "$set": {
                    "lastFollowUpAt": now,
                    "followUpDate": now + timedelta(days=7),
                    "updatedAt": now
                }
            }
        )

    def build_followup_context(
        self,
        commitments: List[Dict[str, Any]],
        language: str = "en"
    ) -> str:
        """
        Build context string for prompt injection.

        Args:
            commitments: Due commitments
            language: 'en' or 'sv'

        Returns:
            Formatted markdown string
        """
        if not commitments:
            return ""

        if language == "sv":
            header = "## Uppföljning av Tidigare Åtaganden\n\n"
            header += "Användaren har väntande mikro-åtaganden att följa upp:\n\n"
        else:
            header = "## Follow-Up on Previous Commitments\n\n"
            header += "The user has pending micro-commitments to follow up on:\n\n"

        parts = [header]

        for i, commitment in enumerate(commitments, 1):
            days_ago = (datetime.now(timezone.utc) - commitment.get("createdAt", datetime.now(timezone.utc))).days

            parts.append(f"**{i}. Commitment** ({days_ago} days ago):\n")
            parts.append(f'"{commitment.get("commitment", "")}"\n')

            if commitment.get("reflectionQuestion"):
                label = "Reflektionsfråga" if language == "sv" else "Reflection question"
                parts.append(f'{label}: "{commitment["reflectionQuestion"]}"\n')

            parts.append("\n")

        ask_text = "Fråga hur det gick och vad de lärde sig." if language == "sv" else "Ask how it went and what they learned."
        parts.append(ask_text)

        return "".join(parts)

    def _format_commitment(self, commitment: Dict[str, Any]) -> Dict[str, Any]:
        """Format commitment for response."""
        return {
            "id": str(commitment["_id"]),
            "userId": str(commitment["userId"]),
            "conversationId": commitment.get("conversationId"),
            "commitment": commitment.get("commitment"),
            "reflectionQuestion": commitment.get("reflectionQuestion"),
            "psychologicalTrigger": commitment.get("psychologicalTrigger"),
            "circlePrompt": commitment.get("circlePrompt"),
            "topic": commitment.get("topic"),
            "status": commitment.get("status"),
            "followUpDate": commitment.get("followUpDate"),
            "completedAt": commitment.get("completedAt"),
            "reflectionNotes": commitment.get("reflectionNotes"),
            "helpfulnessRating": commitment.get("helpfulnessRating"),
            "followUpCount": commitment.get("followUpCount", 0),
            "createdAt": commitment.get("createdAt"),
        }

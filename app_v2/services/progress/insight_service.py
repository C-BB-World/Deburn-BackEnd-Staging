"""
Insight document management service.

Handles insight document storage, retrieval, and trigger configuration.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from common.utils.exceptions import NotFoundException

logger = logging.getLogger(__name__)


class InsightService:
    """
    Handles insight document storage, retrieval, and trigger configuration.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize InsightService.

        Args:
            db: MongoDB database connection
        """
        self._db = db
        self._insights_collection = db["insights"]
        self._triggers_collection = db["insightTriggers"]

    async def create_insight(
        self,
        user_id: str,
        insight_type: str,
        trigger: str,
        title: str,
        description: str,
        metrics: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Create a new insight document.

        Args:
            user_id: User ID
            insight_type: Insight type ('streak', 'pattern', 'trend', 'recommendation')
            trigger: Trigger ID that created this insight
            title: Display title
            description: Display description
            metrics: Optional supporting data
            expires_at: Optional expiration datetime

        Returns:
            Created insight document
        """
        now = datetime.now(timezone.utc)

        insight_doc = {
            "userId": ObjectId(user_id),
            "type": insight_type,
            "trigger": trigger,
            "title": title[:100],
            "description": description[:500],
            "metrics": metrics or {},
            "isRead": False,
            "expiresAt": expires_at,
            "createdAt": now,
            "updatedAt": now
        }

        result = await self._insights_collection.insert_one(insight_doc)
        insight_doc["_id"] = result.inserted_id

        logger.info(f"Created insight for user {user_id}: {title}")
        return self._format_insight(insight_doc)

    async def get_active_insights(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get non-expired insights for a user.

        Args:
            user_id: User ID
            limit: Maximum insights to return

        Returns:
            List of insight dicts sorted by createdAt descending
        """
        now = datetime.now(timezone.utc)

        cursor = self._insights_collection.find({
            "userId": ObjectId(user_id),
            "$or": [
                {"expiresAt": None},
                {"expiresAt": {"$gt": now}}
            ]
        })
        cursor = cursor.sort("createdAt", -1)
        cursor = cursor.limit(limit)

        insights = await cursor.to_list(length=limit)
        return [self._format_insight(i) for i in insights]

    async def mark_as_read(
        self,
        insight_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Mark an insight as read.

        Args:
            insight_id: Insight document ID
            user_id: User ID (for ownership verification)

        Returns:
            Updated insight document

        Raises:
            NotFoundException: Insight not found or doesn't belong to user
        """
        result = await self._insights_collection.find_one_and_update(
            {
                "_id": ObjectId(insight_id),
                "userId": ObjectId(user_id)
            },
            {
                "$set": {
                    "isRead": True,
                    "updatedAt": datetime.now(timezone.utc)
                }
            },
            return_document=True
        )

        if not result:
            raise NotFoundException(message="Insight not found", code="INSIGHT_NOT_FOUND")

        return self._format_insight(result)

    async def get_unread_count(self, user_id: str) -> int:
        """Count unread, non-expired insights."""
        now = datetime.now(timezone.utc)

        count = await self._insights_collection.count_documents({
            "userId": ObjectId(user_id),
            "isRead": False,
            "$or": [
                {"expiresAt": None},
                {"expiresAt": {"$gt": now}}
            ]
        })

        return count

    async def has_recent_insight(
        self,
        user_id: str,
        trigger: str,
        days_back: int = 7
    ) -> bool:
        """Check if insight with trigger exists within time window."""
        threshold = datetime.now(timezone.utc) - timedelta(days=days_back)

        count = await self._insights_collection.count_documents({
            "userId": ObjectId(user_id),
            "trigger": trigger,
            "createdAt": {"$gte": threshold}
        })

        return count > 0

    async def get_all_triggers(self) -> List[Dict[str, Any]]:
        """
        Get all active insight triggers from database.

        Returns:
            List of trigger configurations
        """
        cursor = self._triggers_collection.find({"isActive": True})
        triggers = await cursor.to_list(length=100)
        return [self._format_trigger(t) for t in triggers]

    async def get_trigger_by_id(self, trigger_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific trigger by ID."""
        trigger = await self._triggers_collection.find_one({"triggerId": trigger_id})
        return self._format_trigger(trigger) if trigger else None

    async def seed_default_triggers(self) -> int:
        """
        Seed default triggers if none exist.

        Returns:
            Number of triggers created
        """
        count = await self._triggers_collection.count_documents({})
        if count > 0:
            return 0

        now = datetime.now(timezone.utc)
        triggers = [
            {
                "triggerId": "streak_milestone_7",
                "type": "streak",
                "condition": "streak.current == 7",
                "title": "One Week Strong!",
                "template": "You've checked in for 7 days straight. Consistency is building self-awareness.",
                "isActive": True,
                "duplicateWindowDays": 7,
                "useAiEnhancement": False,
                "createdAt": now,
                "updatedAt": now
            },
            {
                "triggerId": "streak_milestone_14",
                "type": "streak",
                "condition": "streak.current == 14",
                "title": "Two Weeks of Dedication",
                "template": "Two weeks of consistent check-ins! You're building a powerful habit.",
                "isActive": True,
                "duplicateWindowDays": 14,
                "useAiEnhancement": False,
                "createdAt": now,
                "updatedAt": now
            },
            {
                "triggerId": "streak_milestone_30",
                "type": "streak",
                "condition": "streak.current == 30",
                "title": "A Full Month!",
                "template": "30 days of self-reflection. This is real commitment to your growth.",
                "isActive": True,
                "duplicateWindowDays": 30,
                "useAiEnhancement": False,
                "createdAt": now,
                "updatedAt": now
            },
            {
                "triggerId": "mood_improvement",
                "type": "trend",
                "condition": "moodChange >= 15",
                "title": "Mood on the Rise",
                "template": "Your mood has improved by {{moodChange}}% over the past two weeks. Keep doing what's working!",
                "isActive": True,
                "duplicateWindowDays": 14,
                "useAiEnhancement": False,
                "createdAt": now,
                "updatedAt": now
            },
            {
                "triggerId": "stress_reduction",
                "type": "trend",
                "condition": "stressChange <= -15",
                "title": "Stress Decreasing",
                "template": "Your stress levels have dropped. The strategies you're using are making a difference.",
                "isActive": True,
                "duplicateWindowDays": 14,
                "useAiEnhancement": False,
                "createdAt": now,
                "updatedAt": now
            },
            {
                "triggerId": "energy_dip",
                "type": "recommendation",
                "condition": "lowEnergyDays >= 3",
                "title": "Energy Check-In",
                "template": "You've had {{lowEnergyDays}} consecutive days of low energy. Consider reviewing your sleep, exercise, and breaks.",
                "isActive": True,
                "duplicateWindowDays": 7,
                "useAiEnhancement": True,
                "createdAt": now,
                "updatedAt": now
            },
            {
                "triggerId": "sleep_correlation",
                "type": "pattern",
                "condition": "sleepMoodCorrelation >= 0.6",
                "title": "Sleep-Mood Connection",
                "template": "Your data shows a strong connection between sleep quality and mood. Prioritizing rest could boost your wellbeing.",
                "isActive": True,
                "duplicateWindowDays": 30,
                "useAiEnhancement": False,
                "createdAt": now,
                "updatedAt": now
            },
        ]

        await self._triggers_collection.insert_many(triggers)
        logger.info(f"Seeded {len(triggers)} default insight triggers")
        return len(triggers)

    def _format_insight(self, insight: Dict[str, Any]) -> Dict[str, Any]:
        """Format insight for response."""
        return {
            "id": str(insight["_id"]),
            "userId": str(insight["userId"]),
            "type": insight.get("type"),
            "trigger": insight.get("trigger"),
            "title": insight.get("title"),
            "description": insight.get("description"),
            "metrics": insight.get("metrics", {}),
            "isRead": insight.get("isRead", False),
            "expiresAt": insight.get("expiresAt"),
            "createdAt": insight.get("createdAt"),
        }

    def _format_trigger(self, trigger: Dict[str, Any]) -> Dict[str, Any]:
        """Format trigger for internal use."""
        return {
            "id": str(trigger["_id"]),
            "triggerId": trigger.get("triggerId"),
            "type": trigger.get("type"),
            "condition": trigger.get("condition"),
            "title": trigger.get("title"),
            "template": trigger.get("template"),
            "isActive": trigger.get("isActive", True),
            "duplicateWindowDays": trigger.get("duplicateWindowDays", 7),
            "useAiEnhancement": trigger.get("useAiEnhancement", False),
        }

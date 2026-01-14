"""
User availability management service.

Handles user availability for circle meetings.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class AvailabilityService:
    """
    Handles user availability for circle meetings.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize AvailabilityService.

        Args:
            db: MongoDB database connection
        """
        self._db = db
        self._availability_collection = db["userAvailability"]
        self._groups_collection = db["circleGroups"]

    async def get_availability(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's availability settings."""
        return await self._availability_collection.find_one(
            {"userId": ObjectId(user_id)}
        )

    async def update_availability(
        self,
        user_id: str,
        slots: List[Dict[str, int]],
        user_timezone: str = "UTC"
    ) -> Dict[str, Any]:
        """
        Update user's weekly availability.

        Args:
            user_id: User's ID
            slots: List of {day: 0-6, hour: 0-23}
            user_timezone: User's timezone

        Example slots:
            [
                {"day": 1, "hour": 9},   # Monday 9 AM
                {"day": 1, "hour": 10},  # Monday 10 AM
                {"day": 3, "hour": 14},  # Wednesday 2 PM
            ]
        """
        validated_slots = []
        for slot in slots:
            day = slot.get("day")
            hour = slot.get("hour")

            if day is None or hour is None:
                continue
            if not (0 <= day <= 6) or not (0 <= hour <= 23):
                continue

            validated_slots.append({"day": day, "hour": hour})

        now = datetime.now(timezone.utc)

        result = await self._availability_collection.find_one_and_update(
            {"userId": ObjectId(user_id)},
            {
                "$set": {
                    "slots": validated_slots,
                    "timezone": user_timezone,
                    "updatedAt": now
                },
                "$setOnInsert": {
                    "userId": ObjectId(user_id),
                    "createdAt": now
                }
            },
            upsert=True,
            return_document=True
        )

        logger.info(f"Updated availability for user {user_id}: {len(validated_slots)} slots")
        return result

    async def find_common_availability(
        self,
        user_ids: List[str]
    ) -> List[Dict[str, int]]:
        """
        Find time slots where ALL users are available.

        Args:
            user_ids: List of user IDs

        Returns:
            List of common slots [{day, hour}]
            Empty if not all users have set availability
        """
        if not user_ids:
            return []

        availabilities = await self._availability_collection.find({
            "userId": {"$in": [ObjectId(uid) for uid in user_ids]}
        }).to_list(length=len(user_ids))

        if len(availabilities) != len(user_ids):
            return []

        slot_sets = []
        for avail in availabilities:
            slots = avail.get("slots", [])
            slot_tuples = {(s["day"], s["hour"]) for s in slots}
            slot_sets.append(slot_tuples)

        if not slot_sets:
            return []

        common = slot_sets[0]
        for slot_set in slot_sets[1:]:
            common = common.intersection(slot_set)

        return [{"day": day, "hour": hour} for day, hour in sorted(common)]

    async def get_group_availability_status(
        self,
        group_id: str
    ) -> Dict[str, Any]:
        """
        Get availability status for a group.

        Returns:
            dict with commonSlots, member counts, and allMembersSet flag
        """
        group = await self._groups_collection.find_one({"_id": ObjectId(group_id)})

        if not group:
            return {
                "commonSlots": [],
                "totalMembers": 0,
                "membersWithAvailability": 0,
                "membersWithoutAvailability": 0,
                "allMembersSet": False
            }

        member_ids = [str(m) for m in group.get("members", [])]
        total_members = len(member_ids)

        availabilities = await self._availability_collection.find({
            "userId": {"$in": [ObjectId(uid) for uid in member_ids]}
        }).to_list(length=total_members)

        members_with_availability = len(availabilities)
        members_without_availability = total_members - members_with_availability
        all_members_set = members_with_availability == total_members

        common_slots = []
        if all_members_set:
            common_slots = await self.find_common_availability(member_ids)

        return {
            "commonSlots": common_slots,
            "totalMembers": total_members,
            "membersWithAvailability": members_with_availability,
            "membersWithoutAvailability": members_without_availability,
            "allMembersSet": all_members_set
        }

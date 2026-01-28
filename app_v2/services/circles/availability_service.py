"""
Group availability management service.

Handles user availability for circle meetings, stored per-group.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

DEFAULT_AVAILABILITY_COLLECTION = "useravailabilities"
DEFAULT_GROUPS_COLLECTION = "circlegroups"


class AvailabilityService:
    """
    Handles user availability for circle meetings.
    Availability is stored per-group.
    """

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        availability_collection: str = DEFAULT_AVAILABILITY_COLLECTION,
        groups_collection: str = DEFAULT_GROUPS_COLLECTION
    ):
        self._db = db
        self._availability_collection = db[availability_collection]
        self._groups_collection = db[groups_collection]

    async def get_availability(self, user_id: str, group_id: str) -> Optional[Dict[str, Any]]:
        """Get user's availability for a specific group."""
        doc = await self._availability_collection.find_one(
            {"groupId": ObjectId(group_id)}
        )
        if not doc:
            return None

        for member in doc.get("memberAvailability", []):
            if str(member.get("userId")) == user_id:
                return {
                    "userId": user_id,
                    "groupId": group_id,
                    "slots": member.get("slots", []),
                    "updatedAt": member.get("updatedAt")
                }
        return None

    async def get_group_availability(self, group_id: str) -> Optional[Dict[str, Any]]:
        """Get all members' availability for a group."""
        return await self._availability_collection.find_one(
            {"groupId": ObjectId(group_id)}
        )

    async def update_availability(
        self,
        user_id: str,
        group_id: str,
        slots: List[Dict[str, int]],
        user_timezone: str = "UTC"
    ) -> Dict[str, Any]:
        """
        Update user's weekly availability for a specific group.

        Args:
            user_id: User's ID
            group_id: Group's ID
            slots: List of {day: 0-6, hour: 0-23}
            user_timezone: User's timezone
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
        user_oid = ObjectId(user_id)
        group_oid = ObjectId(group_id)

        existing = await self._availability_collection.find_one({"groupId": group_oid})

        if existing:
            user_exists = any(
                str(m.get("userId")) == user_id
                for m in existing.get("memberAvailability", [])
            )

            if user_exists:
                result = await self._availability_collection.find_one_and_update(
                    {"groupId": group_oid, "memberAvailability.userId": user_oid},
                    {
                        "$set": {
                            "memberAvailability.$.slots": validated_slots,
                            "memberAvailability.$.timezone": user_timezone,
                            "memberAvailability.$.updatedAt": now,
                            "updatedAt": now
                        }
                    },
                    return_document=True
                )
            else:
                result = await self._availability_collection.find_one_and_update(
                    {"groupId": group_oid},
                    {
                        "$push": {
                            "memberAvailability": {
                                "userId": user_oid,
                                "slots": validated_slots,
                                "timezone": user_timezone,
                                "updatedAt": now
                            }
                        },
                        "$set": {"updatedAt": now}
                    },
                    return_document=True
                )
        else:
            new_doc = {
                "groupId": group_oid,
                "memberAvailability": [
                    {
                        "userId": user_oid,
                        "slots": validated_slots,
                        "timezone": user_timezone,
                        "updatedAt": now
                    }
                ],
                "createdAt": now,
                "updatedAt": now
            }
            await self._availability_collection.insert_one(new_doc)
            result = new_doc

        logger.info(f"Updated availability for user {user_id} in group {group_id}: {len(validated_slots)} slots")
        return result

    async def find_common_availability(
        self,
        group_id: str
    ) -> List[Dict[str, int]]:
        """
        Find time slots where ALL group members are available.

        Args:
            group_id: Group ID

        Returns:
            List of common slots [{day, hour}]
            Empty if not all members have set availability
        """
        group = await self._groups_collection.find_one({"_id": ObjectId(group_id)})
        if not group:
            return []

        member_ids = [str(m) for m in group.get("members", [])]
        if not member_ids:
            return []

        group_avail = await self._availability_collection.find_one(
            {"groupId": ObjectId(group_id)}
        )

        if not group_avail:
            return []

        member_availability = group_avail.get("memberAvailability", [])

        members_with_avail = {str(m.get("userId")) for m in member_availability}
        if not all(mid in members_with_avail for mid in member_ids):
            return []

        slot_sets = []
        for member in member_availability:
            if str(member.get("userId")) in member_ids:
                slots = member.get("slots", [])
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

        group_avail = await self._availability_collection.find_one(
            {"groupId": ObjectId(group_id)}
        )

        if not group_avail:
            return {
                "commonSlots": [],
                "totalMembers": total_members,
                "membersWithAvailability": 0,
                "membersWithoutAvailability": total_members,
                "allMembersSet": False
            }

        member_availability = group_avail.get("memberAvailability", [])
        members_with_avail = {str(m.get("userId")) for m in member_availability}

        members_with_availability = len([mid for mid in member_ids if mid in members_with_avail])
        members_without_availability = total_members - members_with_availability
        all_members_set = members_with_availability == total_members

        common_slots = []
        if all_members_set:
            common_slots = await self.find_common_availability(group_id)

        return {
            "commonSlots": common_slots,
            "totalMembers": total_members,
            "membersWithAvailability": members_with_availability,
            "membersWithoutAvailability": members_without_availability,
            "allMembersSet": all_members_set
        }

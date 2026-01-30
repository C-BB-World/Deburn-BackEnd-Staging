"""
Circle group management service.

Handles circle group formation, management, and member operations.
"""

import logging
import os
import random
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from common.utils.exceptions import (
    NotFoundException,
    ForbiddenException,
    ValidationException,
)

logger = logging.getLogger(__name__)


class GroupService:
    """
    Handles circle group formation, management, and member operations.
    """

    MIN_GROUP_SIZE = int(os.environ.get("MIN_GROUP_SIZE", "3"))
    MAX_GROUP_SIZE = int(os.environ.get("MAX_GROUP_SIZE", "6"))
    GROUP_NAMES = ["Circle A", "Circle B", "Circle C", "Circle D", "Circle E",
                   "Circle F", "Circle G", "Circle H", "Circle I", "Circle J"]

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize GroupService.

        Args:
            db: MongoDB database connection
        """
        self._db = db
        self._groups_collection = db["circlegroups"]
        self._pools_collection = db["circlepools"]
        self._invitations_collection = db["circleinvitations"]
        self._org_members_collection = db["organizationmembers"]
        self._users_collection = db["users"]

    async def assign_groups(self, pool_id: str, user_id: str) -> Dict[str, Any]:
        """
        Assign all accepted invitees to groups.

        Args:
            pool_id: Pool to assign
            user_id: Admin triggering assignment

        Returns:
            dict with groups and totalMembers
        """
        pool = await self._pools_collection.find_one({"_id": ObjectId(pool_id)})
        if not pool:
            raise NotFoundException(message="Pool not found", code="POOL_NOT_FOUND")

        is_admin = await self._is_org_admin(str(pool["organizationId"]), user_id)
        if not is_admin:
            raise ForbiddenException(message="Not authorized", code="NOT_ORG_ADMIN")

        accepted = await self._invitations_collection.find({
            "poolId": ObjectId(pool_id),
            "status": "accepted",
            "userId": {"$ne": None}
        }).to_list(length=500)

        existing_members = set()
        existing_groups = await self._groups_collection.find({
            "poolId": ObjectId(pool_id),
            "status": "active"
        }).to_list(length=100)

        for group in existing_groups:
            for member_id in group.get("members", []):
                existing_members.add(str(member_id))

        user_ids = [
            str(inv["userId"]) for inv in accepted
            if str(inv["userId"]) not in existing_members
        ]

        if len(user_ids) < self.MIN_GROUP_SIZE:
            raise ValidationException(
                message=f"Need at least {self.MIN_GROUP_SIZE} unassigned members to form groups",
                code="NOT_ENOUGH_MEMBERS"
            )

        target_size = pool.get("targetGroupSize", 4)
        group_assignments = self._divide_into_groups(
            user_ids, target_size, self.MIN_GROUP_SIZE, self.MAX_GROUP_SIZE
        )

        all_user_ids = [ObjectId(uid) for uid in user_ids]
        users_cursor = self._users_collection.find(
            {"_id": {"$in": all_user_ids}},
            {"_id": 1, "profile.firstName": 1, "profile.lastName": 1, "email": 1}
        )
        users_list = await users_cursor.to_list(length=len(all_user_ids))
        users_map = {str(u["_id"]): u for u in users_list}

        now = datetime.now(timezone.utc)
        existing_group_count = len(existing_groups)
        created_groups = []

        for i, member_ids in enumerate(group_assignments):
            group_index = existing_group_count + i
            group_name = self.GROUP_NAMES[group_index] if group_index < len(self.GROUP_NAMES) else f"Circle {group_index + 1}"

            members_with_names = []
            for uid in member_ids:
                user_data = users_map.get(uid, {})
                profile = user_data.get("profile", {})
                first_name = profile.get("firstName", "")
                last_name = profile.get("lastName", "")
                name = f"{first_name} {last_name}".strip() or user_data.get("email", "Member")
                members_with_names.append({
                    "userId": ObjectId(uid),
                    "name": name
                })

            group_doc = {
                "poolId": ObjectId(pool_id),
                "name": group_name,
                "members": members_with_names,
                "status": "active",
                "leaderId": None,
                "stats": {
                    "meetingsHeld": 0,
                    "totalMeetingMinutes": 0,
                    "lastMeetingAt": None
                },
                "createdAt": now,
                "updatedAt": now
            }

            result = await self._groups_collection.insert_one(group_doc)
            group_doc["_id"] = result.inserted_id
            created_groups.append(group_doc)

        await self._pools_collection.update_one(
            {"_id": ObjectId(pool_id)},
            {
                "$set": {
                    "status": "active",
                    "assignedAt": now,
                    "updatedAt": now
                },
                "$inc": {"stats.totalGroups": len(created_groups)}
            }
        )

        total_members = sum(len(g["members"]) for g in created_groups)
        logger.info(f"Created {len(created_groups)} groups with {total_members} members for pool {pool_id}")

        return {
            "groups": created_groups,
            "totalMembers": total_members
        }

    def _divide_into_groups(
        self,
        user_ids: List[str],
        target_size: int,
        min_size: int = 3,
        max_size: int = 6
    ) -> List[List[str]]:
        """
        Divide users into balanced groups.

        Algorithm:
            - Calculate optimal number of groups
            - Distribute extras evenly
            - No group smaller than min_size
        """
        random.shuffle(user_ids)

        n = len(user_ids)
        if n < min_size:
            return [user_ids]

        num_groups = max(1, n // target_size)
        base_size = n // num_groups
        extras = n % num_groups

        if base_size > max_size:
            num_groups += 1
            base_size = n // num_groups
            extras = n % num_groups

        groups = []
        index = 0

        for i in range(num_groups):
            size = base_size + (1 if i < extras else 0)
            groups.append(user_ids[index:index + size])
            index += size

        return groups

    async def get_group(self, group_id: str) -> Dict[str, Any]:
        """Get group by ID."""
        group = await self._groups_collection.find_one({"_id": ObjectId(group_id)})
        if not group:
            raise NotFoundException(message="Group not found", code="GROUP_NOT_FOUND")
        return group

    async def get_groups_for_pool(self, pool_id: str) -> List[Dict[str, Any]]:
        """Get all groups for a pool."""
        cursor = self._groups_collection.find({
            "poolId": ObjectId(pool_id),
            "status": "active"
        })
        return await cursor.to_list(length=100)

    async def get_groups_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's active groups across all pools."""
        cursor = self._groups_collection.find({
            "members.userId": ObjectId(user_id),
            "status": "active"
        })
        return await cursor.to_list(length=50)

    async def user_has_group_access(
        self,
        group_id: str,
        user_id: str
    ) -> bool:
        """Check if user can access group. True if member or org admin."""
        group = await self.get_group(group_id)

        member_ids = [m.get("userId") for m in group.get("members", []) if isinstance(m, dict)]
        if ObjectId(user_id) in member_ids:
            return True

        pool = await self._pools_collection.find_one({"_id": group["poolId"]})
        if pool:
            return await self._is_org_admin(str(pool["organizationId"]), user_id)

        return False

    async def move_member(
        self,
        member_id: str,
        from_group_id: str,
        to_group_id: str,
        admin_id: str
    ) -> None:
        """
        Move a member between groups (admin only).

        Raises:
            ValidationException: If target group is full
        """
        from_group = await self.get_group(from_group_id)
        to_group = await self.get_group(to_group_id)

        pool = await self._pools_collection.find_one({"_id": from_group["poolId"]})
        if not await self._is_org_admin(str(pool["organizationId"]), admin_id):
            raise ForbiddenException(message="Not authorized", code="NOT_ORG_ADMIN")

        if len(to_group["members"]) >= self.MAX_GROUP_SIZE:
            raise ValidationException(
                message="Target group is full",
                code="GROUP_FULL"
            )

        member_obj = None
        for m in from_group.get("members", []):
            if isinstance(m, dict) and m.get("userId") == ObjectId(member_id):
                member_obj = m
                break

        if not member_obj:
            raise ValidationException(
                message="Member not found in source group",
                code="MEMBER_NOT_FOUND"
            )

        now = datetime.now(timezone.utc)

        await self._groups_collection.update_one(
            {"_id": ObjectId(from_group_id)},
            {
                "$pull": {"members": {"userId": ObjectId(member_id)}},
                "$set": {"updatedAt": now}
            }
        )

        await self._groups_collection.update_one(
            {"_id": ObjectId(to_group_id)},
            {
                "$push": {"members": member_obj},
                "$set": {"updatedAt": now}
            }
        )

        logger.info(f"Member {member_id} moved from group {from_group_id} to {to_group_id}")

    async def set_leader(
        self,
        group_id: str,
        member_id: str,
        admin_id: str
    ) -> Dict[str, Any]:
        """Designate a group leader/facilitator."""
        group = await self.get_group(group_id)

        pool = await self._pools_collection.find_one({"_id": group["poolId"]})
        if not await self._is_org_admin(str(pool["organizationId"]), admin_id):
            raise ForbiddenException(message="Not authorized", code="NOT_ORG_ADMIN")

        member_ids = [m.get("userId") for m in group.get("members", []) if isinstance(m, dict)]
        if ObjectId(member_id) not in member_ids:
            raise ValidationException(
                message="User is not a member of this group",
                code="NOT_GROUP_MEMBER"
            )

        await self._groups_collection.update_one(
            {"_id": ObjectId(group_id)},
            {
                "$set": {
                    "leaderId": ObjectId(member_id),
                    "updatedAt": datetime.now(timezone.utc)
                }
            }
        )

        return await self.get_group(group_id)

    async def create_group(
        self,
        pool_id: str,
        name: str,
        admin_id: str
    ) -> Dict[str, Any]:
        """
        Create a new empty group in a pool (admin only).

        Args:
            pool_id: Pool to create group in
            name: Group name
            admin_id: Admin creating the group

        Returns:
            Created group document
        """
        pool = await self._pools_collection.find_one({"_id": ObjectId(pool_id)})
        if not pool:
            raise NotFoundException(message="Pool not found", code="POOL_NOT_FOUND")

        if not await self._is_org_admin(str(pool["organizationId"]), admin_id):
            raise ForbiddenException(message="Not authorized", code="NOT_ORG_ADMIN")

        # Check for duplicate name in pool
        existing = await self._groups_collection.find_one({
            "poolId": ObjectId(pool_id),
            "name": name,
            "status": "active"
        })
        if existing:
            raise ValidationException(
                message="A group with this name already exists",
                code="DUPLICATE_GROUP_NAME"
            )

        now = datetime.now(timezone.utc)
        group_doc = {
            "poolId": ObjectId(pool_id),
            "name": name,
            "members": [],
            "status": "active",
            "leaderId": None,
            "stats": {
                "meetingsHeld": 0,
                "totalMeetingMinutes": 0,
                "lastMeetingAt": None
            },
            "createdAt": now,
            "updatedAt": now
        }

        result = await self._groups_collection.insert_one(group_doc)
        group_doc["_id"] = result.inserted_id

        await self._pools_collection.update_one(
            {"_id": ObjectId(pool_id)},
            {"$inc": {"stats.totalGroups": 1}}
        )

        logger.info(f"Created empty group '{name}' in pool {pool_id}")
        return group_doc

    async def _is_org_admin(self, organization_id: str, user_id: str) -> bool:
        """Check if user is admin of organization."""
        member = await self._org_members_collection.find_one({
            "organizationId": ObjectId(organization_id),
            "userId": ObjectId(user_id),
            "role": "admin"
        })
        return member is not None

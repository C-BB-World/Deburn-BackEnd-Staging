"""
Circle pool management service.

Handles circle pool creation, updates, and lifecycle management.
"""

import logging
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


class PoolService:
    """
    Handles circle pool creation, updates, and lifecycle management.
    """

    VALID_STATUSES = ["draft", "inviting", "assigning", "active", "completed", "cancelled"]
    VALID_CADENCES = ["weekly", "biweekly"]

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize PoolService.

        Args:
            db: MongoDB database connection
        """
        self._db = db
        self._pools_collection = db["circlePools"]
        self._org_members_collection = db["organizationMembers"]

    async def create_pool(
        self,
        organization_id: str,
        name: str,
        created_by: str,
        topic: Optional[str] = None,
        description: Optional[str] = None,
        target_group_size: int = 4,
        cadence: str = "biweekly",
        invitation_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new circle pool.

        Args:
            organization_id: Organization this pool belongs to
            name: Pool name
            created_by: User ID of creator (must be org admin)
            topic: Discussion topic/theme
            description: Pool description
            target_group_size: Target members per group (3-6)
            cadence: Meeting frequency (weekly, biweekly)
            invitation_settings: Custom invite settings

        Returns:
            Created CirclePool

        Raises:
            ForbiddenException: If creator is not org admin
            ValidationException: If invalid parameters
        """
        is_admin = await self._is_org_admin(organization_id, created_by)
        if not is_admin:
            raise ForbiddenException(
                message="Only organization admins can create pools",
                code="NOT_ORG_ADMIN"
            )

        if target_group_size < 3 or target_group_size > 6:
            raise ValidationException(
                message="Target group size must be between 3 and 6",
                code="INVALID_GROUP_SIZE"
            )

        if cadence not in self.VALID_CADENCES:
            raise ValidationException(
                message=f"Cadence must be one of: {', '.join(self.VALID_CADENCES)}",
                code="INVALID_CADENCE"
            )

        now = datetime.now(timezone.utc)

        pool_doc = {
            "organizationId": ObjectId(organization_id),
            "name": name,
            "topic": topic,
            "description": description,
            "targetGroupSize": target_group_size,
            "cadence": cadence,
            "status": "draft",
            "invitationSettings": invitation_settings or {
                "expiryDays": 14,
                "customMessage": None
            },
            "stats": {
                "totalInvited": 0,
                "totalAccepted": 0,
                "totalDeclined": 0,
                "totalGroups": 0
            },
            "createdBy": ObjectId(created_by),
            "assignedAt": None,
            "createdAt": now,
            "updatedAt": now
        }

        result = await self._pools_collection.insert_one(pool_doc)
        pool_doc["_id"] = result.inserted_id

        logger.info(f"Pool created: {result.inserted_id}")
        return pool_doc

    async def get_pool(self, pool_id: str) -> Dict[str, Any]:
        """Get pool by ID."""
        pool = await self._pools_collection.find_one({"_id": ObjectId(pool_id)})
        if not pool:
            raise NotFoundException(message="Pool not found", code="POOL_NOT_FOUND")
        return pool

    async def update_pool(
        self,
        pool_id: str,
        user_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update pool settings.

        Note: targetGroupSize and cadence can only be updated in draft status
        """
        pool = await self.get_pool(pool_id)

        is_admin = await self._is_org_admin(str(pool["organizationId"]), user_id)
        if not is_admin:
            raise ForbiddenException(
                message="Only organization admins can update pools",
                code="NOT_ORG_ADMIN"
            )

        restricted_fields = ["targetGroupSize", "cadence"]
        if pool["status"] != "draft":
            for field in restricted_fields:
                if field in updates:
                    raise ValidationException(
                        message=f"{field} can only be updated in draft status",
                        code="FIELD_NOT_EDITABLE"
                    )

        allowed_updates = {}
        for key in ["name", "topic", "description", "targetGroupSize", "cadence", "invitationSettings"]:
            if key in updates:
                allowed_updates[key] = updates[key]

        if not allowed_updates:
            return pool

        allowed_updates["updatedAt"] = datetime.now(timezone.utc)

        await self._pools_collection.update_one(
            {"_id": ObjectId(pool_id)},
            {"$set": allowed_updates}
        )

        return await self.get_pool(pool_id)

    async def start_inviting(self, pool_id: str, user_id: str) -> Dict[str, Any]:
        """Transition pool from draft to inviting status."""
        pool = await self.get_pool(pool_id)

        is_admin = await self._is_org_admin(str(pool["organizationId"]), user_id)
        if not is_admin:
            raise ForbiddenException(message="Not authorized", code="NOT_ORG_ADMIN")

        if pool["status"] != "draft":
            raise ValidationException(
                message="Pool must be in draft status to start inviting",
                code="INVALID_STATUS"
            )

        await self._pools_collection.update_one(
            {"_id": ObjectId(pool_id)},
            {"$set": {"status": "inviting", "updatedAt": datetime.now(timezone.utc)}}
        )

        return await self.get_pool(pool_id)

    async def cancel_pool(self, pool_id: str, user_id: str) -> Dict[str, Any]:
        """Cancel pool and all pending invitations."""
        pool = await self.get_pool(pool_id)

        is_admin = await self._is_org_admin(str(pool["organizationId"]), user_id)
        if not is_admin:
            raise ForbiddenException(message="Not authorized", code="NOT_ORG_ADMIN")

        if pool["status"] in ["completed", "cancelled"]:
            raise ValidationException(
                message="Pool is already completed or cancelled",
                code="INVALID_STATUS"
            )

        now = datetime.now(timezone.utc)

        await self._pools_collection.update_one(
            {"_id": ObjectId(pool_id)},
            {"$set": {"status": "cancelled", "updatedAt": now}}
        )

        invitations_collection = self._db["circleInvitations"]
        await invitations_collection.update_many(
            {"poolId": ObjectId(pool_id), "status": "pending"},
            {"$set": {"status": "cancelled", "updatedAt": now}}
        )

        logger.info(f"Pool {pool_id} cancelled")
        return await self.get_pool(pool_id)

    async def get_pools_for_organization(
        self,
        organization_id: str,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all pools for an organization."""
        query: Dict[str, Any] = {"organizationId": ObjectId(organization_id)}

        if status:
            query["status"] = status

        cursor = self._pools_collection.find(query).sort("createdAt", -1)
        return await cursor.to_list(length=100)

    async def get_pool_stats(self, pool_id: str) -> Dict[str, Any]:
        """Get pool statistics."""
        pool = await self.get_pool(pool_id)

        invitations_collection = self._db["circleInvitations"]
        groups_collection = self._db["circleGroups"]

        pending = await invitations_collection.count_documents(
            {"poolId": ObjectId(pool_id), "status": "pending"}
        )
        accepted = await invitations_collection.count_documents(
            {"poolId": ObjectId(pool_id), "status": "accepted"}
        )
        declined = await invitations_collection.count_documents(
            {"poolId": ObjectId(pool_id), "status": "declined"}
        )
        groups = await groups_collection.count_documents(
            {"poolId": ObjectId(pool_id), "status": "active"}
        )

        min_group_size = 3
        can_assign = accepted >= min_group_size

        return {
            "pending": pending,
            "accepted": accepted,
            "declined": declined,
            "groups": groups,
            "canAssign": can_assign
        }

    async def _is_org_admin(self, organization_id: str, user_id: str) -> bool:
        """Check if user is admin of organization."""
        member = await self._org_members_collection.find_one({
            "organizationId": ObjectId(organization_id),
            "userId": ObjectId(user_id),
            "role": "admin"
        })
        return member is not None

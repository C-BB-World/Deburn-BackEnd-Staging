"""
Hub admin service.

Manages platform-level super admins.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from common.utils.exceptions import (
    NotFoundException,
    ValidationException,
    ConflictException,
)

logger = logging.getLogger(__name__)


class HubAdminService:
    """
    Manages platform-level super admins.
    Uses separate hub database connection.
    """

    def __init__(self, hub_db: AsyncIOMotorDatabase):
        """
        Initialize HubAdminService.

        Args:
            hub_db: Hub MongoDB database connection
        """
        self._db = hub_db
        self._admins_collection = hub_db["hubAdmins"]

    async def is_hub_admin(self, email: str) -> bool:
        """
        Check if email is an active hub admin.

        Args:
            email: User email

        Returns:
            True if active hub admin
        """
        admin = await self._admins_collection.find_one({
            "email": email.lower(),
            "status": "active"
        })

        return admin is not None

    async def get_active_admins(self) -> List[Dict[str, Any]]:
        """
        List all active hub admins.

        Returns:
            List of admin dicts
        """
        admins = await self._admins_collection.find({
            "status": "active"
        }).to_list(length=100)

        return [self._format_admin(a) for a in admins]

    async def add_admin(
        self,
        email: str,
        added_by: str
    ) -> Dict[str, Any]:
        """
        Add new hub admin or reactivate removed one.

        Args:
            email: Admin email
            added_by: Email of admin who added

        Returns:
            Admin dict
        """
        email = email.lower().strip()

        if not email or "@" not in email:
            raise ValidationException(
                message="Invalid email address",
                code="INVALID_EMAIL"
            )

        existing = await self._admins_collection.find_one({"email": email})

        if existing:
            if existing["status"] == "active":
                raise ConflictException(
                    message="Admin already exists and is active",
                    code="ALREADY_EXISTS"
                )

            result = await self._admins_collection.find_one_and_update(
                {"_id": existing["_id"]},
                {
                    "$set": {
                        "status": "active",
                        "addedBy": added_by,
                        "addedAt": datetime.now(timezone.utc),
                        "removedAt": None,
                        "removedBy": None,
                        "updatedAt": datetime.now(timezone.utc),
                    }
                },
                return_document=True
            )
            logger.info(f"Reactivated hub admin: {email}")
            return self._format_admin(result)

        now = datetime.now(timezone.utc)
        admin_doc = {
            "email": email,
            "addedBy": added_by,
            "addedAt": now,
            "status": "active",
            "removedAt": None,
            "removedBy": None,
            "createdAt": now,
            "updatedAt": now,
        }

        result = await self._admins_collection.insert_one(admin_doc)
        admin_doc["_id"] = result.inserted_id

        logger.info(f"Added hub admin: {email} by {added_by}")
        return self._format_admin(admin_doc)

    async def remove_admin(
        self,
        email: str,
        removed_by: str
    ) -> Dict[str, Any]:
        """
        Soft-delete hub admin.

        Args:
            email: Admin email to remove
            removed_by: Email of admin who removed

        Returns:
            Removed admin dict
        """
        email = email.lower().strip()

        if email == removed_by.lower():
            raise ValidationException(
                message="Cannot remove yourself",
                code="CANNOT_REMOVE_SELF"
            )

        admin = await self._admins_collection.find_one({
            "email": email,
            "status": "active"
        })

        if not admin:
            raise NotFoundException(
                message="Admin not found",
                code="ADMIN_NOT_FOUND"
            )

        now = datetime.now(timezone.utc)
        result = await self._admins_collection.find_one_and_update(
            {"_id": admin["_id"]},
            {
                "$set": {
                    "status": "removed",
                    "removedAt": now,
                    "removedBy": removed_by,
                    "updatedAt": now,
                }
            },
            return_document=True
        )

        logger.info(f"Removed hub admin: {email} by {removed_by}")
        return self._format_admin(result)

    async def seed_initial_admin(
        self,
        email: str = "aurora@brainbank.world"
    ) -> Optional[Dict[str, Any]]:
        """
        Create initial admin if none exist.

        Args:
            email: Initial admin email

        Returns:
            Created admin or None if admins exist
        """
        count = await self._admins_collection.count_documents({"status": "active"})

        if count > 0:
            return None

        now = datetime.now(timezone.utc)
        admin_doc = {
            "email": email.lower(),
            "addedBy": "system",
            "addedAt": now,
            "status": "active",
            "removedAt": None,
            "removedBy": None,
            "createdAt": now,
            "updatedAt": now,
        }

        result = await self._admins_collection.insert_one(admin_doc)
        admin_doc["_id"] = result.inserted_id

        logger.info(f"Seeded initial hub admin: {email}")
        return self._format_admin(admin_doc)

    def _format_admin(self, admin: Dict[str, Any]) -> Dict[str, Any]:
        """Format admin for response."""
        return {
            "id": str(admin["_id"]),
            "email": admin.get("email"),
            "addedBy": admin.get("addedBy"),
            "addedAt": admin.get("addedAt"),
            "status": admin.get("status"),
            "removedAt": admin.get("removedAt"),
            "removedBy": admin.get("removedBy"),
            "createdAt": admin.get("createdAt"),
            "updatedAt": admin.get("updatedAt"),
        }

"""
Organization service.

Manages organizations and their memberships.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from common.utils.exceptions import (
    NotFoundException,
    ValidationException,
    ForbiddenException,
    ConflictException,
)

logger = logging.getLogger(__name__)


DEFAULT_SETTINGS = {
    "defaultMeetingDuration": 60,
    "defaultGroupSize": 4,
    "allowMemberPoolCreation": False,
    "timezone": "Europe/Stockholm",
}


class OrganizationService:
    """
    Manages organizations and their memberships.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize OrganizationService.

        Args:
            db: MongoDB database connection
        """
        self._db = db
        self._orgs_collection = db["organizations"]
        self._members_collection = db["organizationMembers"]

    # ─────────────────────────────────────────────────────────────────
    # Organization CRUD
    # ─────────────────────────────────────────────────────────────────

    async def create_organization(
        self,
        name: str,
        created_by: str,
        domain: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new organization.
        Creator automatically becomes first admin.

        Args:
            name: Organization name (2-100 chars)
            created_by: User ID of creator
            domain: Optional email domain
            settings: Optional settings override

        Returns:
            Created organization dict
        """
        if not name or len(name) < 2 or len(name) > 100:
            raise ValidationException(
                message="Organization name must be 2-100 characters",
                code="VALIDATION_ERROR"
            )

        if domain:
            domain = domain.lower().strip()
            existing = await self._orgs_collection.find_one({
                "domain": domain,
                "status": {"$ne": "deleted"}
            })
            if existing:
                raise ConflictException(
                    message="Domain already in use by another organization",
                    code="DOMAIN_TAKEN"
                )

        now = datetime.now(timezone.utc)
        org_settings = {**DEFAULT_SETTINGS, **(settings or {})}

        org_doc = {
            "name": name.strip(),
            "domain": domain,
            "settings": org_settings,
            "status": "active",
            "createdBy": ObjectId(created_by),
            "createdAt": now,
            "updatedAt": now,
        }

        result = await self._orgs_collection.insert_one(org_doc)
        org_doc["_id"] = result.inserted_id

        member_doc = {
            "organizationId": result.inserted_id,
            "userId": ObjectId(created_by),
            "role": "admin",
            "status": "active",
            "joinedAt": now,
            "invitedBy": ObjectId(created_by),
            "createdAt": now,
            "updatedAt": now,
        }

        await self._members_collection.insert_one(member_doc)

        logger.info(f"Created organization {name} by user {created_by}")
        return self._format_organization(org_doc)

    async def get_organization(self, organization_id: str) -> Dict[str, Any]:
        """
        Get organization by ID.

        Args:
            organization_id: Organization ID

        Returns:
            Organization dict
        """
        org = await self._orgs_collection.find_one({
            "_id": ObjectId(organization_id),
            "status": {"$ne": "deleted"}
        })

        if not org:
            raise NotFoundException(
                message="Organization not found",
                code="ORGANIZATION_NOT_FOUND"
            )

        return self._format_organization(org)

    async def get_organization_with_stats(
        self,
        organization_id: str
    ) -> Dict[str, Any]:
        """
        Get organization with member counts.

        Args:
            organization_id: Organization ID

        Returns:
            Organization dict with memberCount, adminCount
        """
        org = await self.get_organization(organization_id)

        member_count = await self._members_collection.count_documents({
            "organizationId": ObjectId(organization_id),
            "status": "active"
        })

        admin_count = await self._members_collection.count_documents({
            "organizationId": ObjectId(organization_id),
            "status": "active",
            "role": "admin"
        })

        org["memberCount"] = member_count
        org["adminCount"] = admin_count

        return org

    async def update_organization(
        self,
        organization_id: str,
        updates: Dict[str, Any],
        updated_by: str
    ) -> Dict[str, Any]:
        """
        Update organization settings.

        Args:
            organization_id: Organization ID
            updates: Fields to update (name, domain, settings)
            updated_by: User making the update

        Returns:
            Updated organization dict
        """
        if not await self.is_admin(organization_id, updated_by):
            raise ForbiddenException(
                message="Only admins can update the organization",
                code="NOT_ADMIN"
            )

        allowed_fields = {"name", "domain", "settings"}
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}

        if not filtered_updates:
            return await self.get_organization(organization_id)

        if "name" in filtered_updates:
            name = filtered_updates["name"]
            if not name or len(name) < 2 or len(name) > 100:
                raise ValidationException(
                    message="Organization name must be 2-100 characters",
                    code="VALIDATION_ERROR"
                )
            filtered_updates["name"] = name.strip()

        if "domain" in filtered_updates and filtered_updates["domain"]:
            domain = filtered_updates["domain"].lower().strip()
            existing = await self._orgs_collection.find_one({
                "_id": {"$ne": ObjectId(organization_id)},
                "domain": domain,
                "status": {"$ne": "deleted"}
            })
            if existing:
                raise ConflictException(
                    message="Domain already in use by another organization",
                    code="DOMAIN_TAKEN"
                )
            filtered_updates["domain"] = domain

        if "settings" in filtered_updates:
            current_org = await self._orgs_collection.find_one({
                "_id": ObjectId(organization_id)
            })
            if current_org:
                new_settings = {**current_org.get("settings", {}), **filtered_updates["settings"]}
                if "defaultMeetingDuration" in new_settings:
                    duration = new_settings["defaultMeetingDuration"]
                    if duration < 15 or duration > 180:
                        raise ValidationException(
                            message="Meeting duration must be 15-180 minutes",
                            code="VALIDATION_ERROR"
                        )
                if "defaultGroupSize" in new_settings:
                    size = new_settings["defaultGroupSize"]
                    if size < 3 or size > 4:
                        raise ValidationException(
                            message="Group size must be 3-4",
                            code="VALIDATION_ERROR"
                        )
                filtered_updates["settings"] = new_settings

        filtered_updates["updatedAt"] = datetime.now(timezone.utc)

        result = await self._orgs_collection.find_one_and_update(
            {"_id": ObjectId(organization_id)},
            {"$set": filtered_updates},
            return_document=True
        )

        if not result:
            raise NotFoundException(
                message="Organization not found",
                code="ORGANIZATION_NOT_FOUND"
            )

        return self._format_organization(result)

    async def get_user_organizations(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all organizations a user belongs to.

        Args:
            user_id: User ID

        Returns:
            List of { organization, role, joinedAt }
        """
        memberships = await self._members_collection.find({
            "userId": ObjectId(user_id),
            "status": "active"
        }).to_list(length=100)

        results = []
        for membership in memberships:
            org = await self._orgs_collection.find_one({
                "_id": membership["organizationId"],
                "status": {"$ne": "deleted"}
            })

            if org:
                results.append({
                    "organization": self._format_organization(org),
                    "role": membership["role"],
                    "joinedAt": membership["joinedAt"],
                })

        return results

    # ─────────────────────────────────────────────────────────────────
    # Member Management
    # ─────────────────────────────────────────────────────────────────

    async def add_member(
        self,
        organization_id: str,
        user_id: str,
        role: str = "member",
        invited_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add a member to the organization.

        Args:
            organization_id: Organization ID
            user_id: User to add
            role: "admin" or "member"
            invited_by: Admin who added them

        Returns:
            Created membership dict
        """
        if invited_by and not await self.is_admin(organization_id, invited_by):
            raise ForbiddenException(
                message="Only admins can add members",
                code="NOT_ADMIN"
            )

        if role not in ("admin", "member"):
            raise ValidationException(
                message="Role must be 'admin' or 'member'",
                code="VALIDATION_ERROR"
            )

        existing = await self._members_collection.find_one({
            "organizationId": ObjectId(organization_id),
            "userId": ObjectId(user_id)
        })

        now = datetime.now(timezone.utc)

        if existing:
            if existing["status"] == "active":
                raise ConflictException(
                    message="User is already a member",
                    code="ALREADY_MEMBER"
                )

            result = await self._members_collection.find_one_and_update(
                {"_id": existing["_id"]},
                {
                    "$set": {
                        "status": "active",
                        "role": role,
                        "invitedBy": ObjectId(invited_by) if invited_by else None,
                        "joinedAt": now,
                        "updatedAt": now,
                    }
                },
                return_document=True
            )
            logger.info(f"Reactivated member {user_id} in org {organization_id}")
            return self._format_membership(result)

        member_doc = {
            "organizationId": ObjectId(organization_id),
            "userId": ObjectId(user_id),
            "role": role,
            "status": "active",
            "joinedAt": now,
            "invitedBy": ObjectId(invited_by) if invited_by else None,
            "createdAt": now,
            "updatedAt": now,
        }

        result = await self._members_collection.insert_one(member_doc)
        member_doc["_id"] = result.inserted_id

        logger.info(f"Added member {user_id} to org {organization_id}")
        return self._format_membership(member_doc)

    async def remove_member(
        self,
        organization_id: str,
        user_id: str,
        removed_by: str
    ) -> bool:
        """
        Remove a member from the organization.

        Args:
            organization_id: Organization ID
            user_id: User to remove
            removed_by: Admin performing removal

        Returns:
            True if removed
        """
        if not await self.is_admin(organization_id, removed_by):
            raise ForbiddenException(
                message="Only admins can remove members",
                code="NOT_ADMIN"
            )

        membership = await self._members_collection.find_one({
            "organizationId": ObjectId(organization_id),
            "userId": ObjectId(user_id),
            "status": "active"
        })

        if not membership:
            raise NotFoundException(
                message="Member not found",
                code="MEMBER_NOT_FOUND"
            )

        if membership["role"] == "admin":
            admin_count = await self.get_admin_count(organization_id)
            if admin_count <= 1:
                raise ForbiddenException(
                    message="Cannot remove the last admin",
                    code="LAST_ADMIN"
                )

        await self._members_collection.update_one(
            {"_id": membership["_id"]},
            {
                "$set": {
                    "status": "removed",
                    "updatedAt": datetime.now(timezone.utc)
                }
            }
        )

        logger.info(f"Removed member {user_id} from org {organization_id}")
        return True

    async def leave_organization(
        self,
        organization_id: str,
        user_id: str
    ) -> bool:
        """
        Member leaves the organization voluntarily.

        Args:
            organization_id: Organization ID
            user_id: User leaving

        Returns:
            True if left successfully
        """
        membership = await self._members_collection.find_one({
            "organizationId": ObjectId(organization_id),
            "userId": ObjectId(user_id),
            "status": "active"
        })

        if not membership:
            raise NotFoundException(
                message="You are not a member of this organization",
                code="NOT_MEMBER"
            )

        if membership["role"] == "admin":
            admin_count = await self.get_admin_count(organization_id)
            if admin_count <= 1:
                raise ForbiddenException(
                    message="Cannot leave as the last admin. Transfer ownership first.",
                    code="MUST_TRANSFER_OWNERSHIP"
                )

        await self._members_collection.update_one(
            {"_id": membership["_id"]},
            {
                "$set": {
                    "status": "removed",
                    "updatedAt": datetime.now(timezone.utc)
                }
            }
        )

        logger.info(f"User {user_id} left org {organization_id}")
        return True

    async def change_member_role(
        self,
        organization_id: str,
        user_id: str,
        new_role: str,
        changed_by: str
    ) -> Dict[str, Any]:
        """
        Change a member's role.

        Args:
            organization_id: Organization ID
            user_id: Member to update
            new_role: "admin" or "member"
            changed_by: Admin making the change

        Returns:
            Updated membership dict
        """
        if not await self.is_admin(organization_id, changed_by):
            raise ForbiddenException(
                message="Only admins can change roles",
                code="NOT_ADMIN"
            )

        if new_role not in ("admin", "member"):
            raise ValidationException(
                message="Role must be 'admin' or 'member'",
                code="VALIDATION_ERROR"
            )

        membership = await self._members_collection.find_one({
            "organizationId": ObjectId(organization_id),
            "userId": ObjectId(user_id),
            "status": "active"
        })

        if not membership:
            raise NotFoundException(
                message="Member not found",
                code="MEMBER_NOT_FOUND"
            )

        if membership["role"] == "admin" and new_role == "member":
            admin_count = await self.get_admin_count(organization_id)
            if admin_count <= 1:
                raise ForbiddenException(
                    message="Cannot demote the last admin",
                    code="LAST_ADMIN"
                )

        result = await self._members_collection.find_one_and_update(
            {"_id": membership["_id"]},
            {
                "$set": {
                    "role": new_role,
                    "updatedAt": datetime.now(timezone.utc)
                }
            },
            return_document=True
        )

        logger.info(f"Changed role of {user_id} to {new_role} in org {organization_id}")
        return self._format_membership(result)

    async def transfer_ownership(
        self,
        organization_id: str,
        new_owner_id: str,
        transferred_by: str
    ) -> Dict[str, Any]:
        """
        Transfer organization ownership to another member.

        Args:
            organization_id: Organization ID
            new_owner_id: User to become new owner
            transferred_by: Current admin transferring

        Returns:
            Updated organization dict
        """
        if not await self.is_admin(organization_id, transferred_by):
            raise ForbiddenException(
                message="Only admins can transfer ownership",
                code="NOT_ADMIN"
            )

        membership = await self._members_collection.find_one({
            "organizationId": ObjectId(organization_id),
            "userId": ObjectId(new_owner_id),
            "status": "active"
        })

        if not membership:
            raise NotFoundException(
                message="New owner must be an active member",
                code="NOT_MEMBER"
            )

        now = datetime.now(timezone.utc)

        if membership["role"] != "admin":
            await self._members_collection.update_one(
                {"_id": membership["_id"]},
                {
                    "$set": {
                        "role": "admin",
                        "updatedAt": now
                    }
                }
            )

        result = await self._orgs_collection.find_one_and_update(
            {"_id": ObjectId(organization_id)},
            {
                "$set": {
                    "createdBy": ObjectId(new_owner_id),
                    "updatedAt": now
                }
            },
            return_document=True
        )

        logger.info(f"Transferred ownership of org {organization_id} to {new_owner_id}")
        return self._format_organization(result)

    async def get_members(
        self,
        organization_id: str,
        role: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get organization members.

        Args:
            organization_id: Organization ID
            role: Optional filter by role

        Returns:
            List of member dicts with user details
        """
        query = {
            "organizationId": ObjectId(organization_id),
            "status": "active"
        }

        if role:
            query["role"] = role

        members = await self._members_collection.find(query).to_list(length=500)

        results = []
        for member in members:
            user = await self._db["users"].find_one({"_id": member["userId"]})

            results.append({
                "id": str(member["_id"]),
                "userId": str(member["userId"]),
                "organizationId": str(member["organizationId"]),
                "role": member["role"],
                "status": member["status"],
                "joinedAt": member["joinedAt"],
                "user": {
                    "id": str(user["_id"]) if user else None,
                    "email": user.get("email") if user else None,
                    "firstName": user.get("firstName") if user else None,
                    "lastName": user.get("lastName") if user else None,
                } if user else None
            })

        return results

    # ─────────────────────────────────────────────────────────────────
    # Access Checks
    # ─────────────────────────────────────────────────────────────────

    async def is_admin(self, organization_id: str, user_id: str) -> bool:
        """
        Check if user is an admin of the organization.

        Args:
            organization_id: Organization ID
            user_id: User ID

        Returns:
            True if user is active admin
        """
        membership = await self._members_collection.find_one({
            "organizationId": ObjectId(organization_id),
            "userId": ObjectId(user_id),
            "role": "admin",
            "status": "active"
        })

        return membership is not None

    async def is_member(self, organization_id: str, user_id: str) -> bool:
        """
        Check if user is a member of the organization.

        Args:
            organization_id: Organization ID
            user_id: User ID

        Returns:
            True if user is active member (any role)
        """
        membership = await self._members_collection.find_one({
            "organizationId": ObjectId(organization_id),
            "userId": ObjectId(user_id),
            "status": "active"
        })

        return membership is not None

    async def get_membership(
        self,
        organization_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get user's membership in an organization.

        Args:
            organization_id: Organization ID
            user_id: User ID

        Returns:
            Membership dict or None if not a member
        """
        membership = await self._members_collection.find_one({
            "organizationId": ObjectId(organization_id),
            "userId": ObjectId(user_id),
            "status": "active"
        })

        return self._format_membership(membership) if membership else None

    async def get_admin_count(self, organization_id: str) -> int:
        """
        Get count of active admins.

        Args:
            organization_id: Organization ID

        Returns:
            Number of active admins
        """
        return await self._members_collection.count_documents({
            "organizationId": ObjectId(organization_id),
            "role": "admin",
            "status": "active"
        })

    def _format_organization(self, org: Dict[str, Any]) -> Dict[str, Any]:
        """Format organization for response."""
        return {
            "id": str(org["_id"]),
            "name": org.get("name"),
            "domain": org.get("domain"),
            "settings": org.get("settings", {}),
            "status": org.get("status"),
            "createdBy": str(org["createdBy"]) if org.get("createdBy") else None,
            "createdAt": org.get("createdAt"),
            "updatedAt": org.get("updatedAt"),
        }

    def _format_membership(self, membership: Dict[str, Any]) -> Dict[str, Any]:
        """Format membership for response."""
        return {
            "id": str(membership["_id"]),
            "organizationId": str(membership["organizationId"]),
            "userId": str(membership["userId"]),
            "role": membership.get("role"),
            "status": membership.get("status"),
            "joinedAt": membership.get("joinedAt"),
            "invitedBy": str(membership["invitedBy"]) if membership.get("invitedBy") else None,
            "createdAt": membership.get("createdAt"),
            "updatedAt": membership.get("updatedAt"),
        }

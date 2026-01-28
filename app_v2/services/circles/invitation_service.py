"""
Circle invitation management service.

Manages circle pool invitations including sending, tracking, and acceptance.
"""

import csv
import io
import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from common.utils.exceptions import (
    NotFoundException,
    ValidationException,
)

logger = logging.getLogger(__name__)


class InvitationService:
    """
    Manages circle pool invitations.
    """

    TOKEN_LENGTH = 64

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize InvitationService.

        Args:
            db: MongoDB database connection
        """
        self._db = db
        self._invitations_collection = db["circleinvitations"]
        self._pools_collection = db["circlepools"]

    async def send_invitations(
        self,
        pool_id: str,
        invitees: List[Dict[str, str]],
        invited_by: str
    ) -> Dict[str, Any]:
        """
        Send invitations to a list of people.

        Args:
            pool_id: Pool to invite to
            invitees: List of {email, firstName?, lastName?}
            invited_by: User ID sending invitations

        Returns:
            dict with sent, failed, and duplicate counts
        """
        pool = await self._pools_collection.find_one({"_id": ObjectId(pool_id)})
        if not pool:
            raise NotFoundException(message="Pool not found", code="POOL_NOT_FOUND")

        expiry_days = pool.get("invitationSettings", {}).get("expiryDays", 14)

        sent = []
        failed = []
        duplicate = []

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=expiry_days)

        for invitee in invitees:
            email = invitee.get("email", "").lower().strip()

            if not email or "@" not in email:
                failed.append({"email": email, "reason": "Invalid email format"})
                continue

            existing = await self._invitations_collection.find_one({
                "poolId": ObjectId(pool_id),
                "email": email,
                "status": {"$in": ["pending", "accepted"]}
            })

            if existing:
                duplicate.append({"email": email})
                continue

            token = secrets.token_hex(self.TOKEN_LENGTH // 2)

            invitation_doc = {
                "poolId": ObjectId(pool_id),
                "email": email,
                "firstName": invitee.get("firstName"),
                "lastName": invitee.get("lastName"),
                "token": token,
                "status": "pending",
                "expiresAt": expires_at,
                "invitedBy": ObjectId(invited_by),
                "userId": None,
                "acceptedAt": None,
                "declinedAt": None,
                "emailSentAt": now,
                "emailSentCount": 1,
                "lastReminderAt": None,
                "reminderCount": 0,
                "createdAt": now,
                "updatedAt": now
            }

            await self._invitations_collection.insert_one(invitation_doc)

            # Send invitation email (non-blocking - invitation saved even if email fails)
            try:
                from app_v2.services.email.email_service import EmailService
                email_service = EmailService()
                await email_service.send_circle_invitation_email(
                    to_email=email,
                    token=token,
                    pool_name=pool.get("name", "Leadership Circle"),
                    topic=pool.get("topic"),
                    custom_message=pool.get("invitationSettings", {}).get("customMessage"),
                    first_name=invitee.get("firstName"),
                    expires_at=expires_at.strftime("%B %d, %Y"),
                )
            except Exception as email_error:
                logger.warning(f"Failed to send invitation email to {email}: {email_error}")

            sent.append({"email": email, "token": token})

        await self._pools_collection.update_one(
            {"_id": ObjectId(pool_id)},
            {
                "$inc": {"stats.totalInvited": len(sent)},
                "$set": {"updatedAt": now}
            }
        )

        if pool["status"] == "draft" and sent:
            await self._pools_collection.update_one(
                {"_id": ObjectId(pool_id)},
                {"$set": {"status": "inviting"}}
            )

        logger.info(f"Sent {len(sent)} invitations for pool {pool_id}")

        return {
            "sent": sent,
            "failed": failed,
            "duplicate": duplicate
        }

    def parse_invitation_csv(self, csv_content: str) -> Dict[str, Any]:
        """
        Parse CSV for bulk invitations.

        Args:
            csv_content: CSV string (email,first_name,last_name)

        Returns:
            dict with invitees and errors
        """
        invitees = []
        errors = []

        try:
            reader = csv.DictReader(io.StringIO(csv_content))

            for line_num, row in enumerate(reader, start=2):
                email = row.get("email", "").strip()

                if not email:
                    errors.append({"line": line_num, "error": "Missing email"})
                    continue

                invitees.append({
                    "email": email,
                    "firstName": row.get("first_name", row.get("firstName", "")),
                    "lastName": row.get("last_name", row.get("lastName", ""))
                })

        except Exception as e:
            errors.append({"line": 0, "error": f"CSV parse error: {str(e)}"})

        return {"invitees": invitees, "errors": errors}

    async def get_invitation_by_token(self, token: str) -> Dict[str, Any]:
        """Get invitation by its unique token."""
        invitation = await self._invitations_collection.find_one({"token": token})

        if not invitation:
            raise NotFoundException(
                message="Invitation not found",
                code="INVITATION_NOT_FOUND"
            )

        return invitation

    async def accept_invitation(
        self,
        token: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Accept an invitation.

        Args:
            token: Invitation token
            user_id: User accepting

        Returns:
            Updated invitation

        Raises:
            NotFoundException: If token not found
            ValidationException: If expired or already processed
        """
        invitation = await self.get_invitation_by_token(token)

        if invitation["status"] != "pending":
            raise ValidationException(
                message=f"Invitation already {invitation['status']}",
                code="INVITATION_ALREADY_PROCESSED"
            )

        now = datetime.now(timezone.utc)

        # Handle both timezone-aware and naive datetimes from MongoDB
        expires_at = invitation["expiresAt"]
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at < now:
            await self._invitations_collection.update_one(
                {"_id": invitation["_id"]},
                {"$set": {"status": "expired", "updatedAt": now}}
            )
            raise ValidationException(
                message="Invitation has expired",
                code="INVITATION_EXPIRED"
            )

        await self._invitations_collection.update_one(
            {"_id": invitation["_id"]},
            {
                "$set": {
                    "status": "accepted",
                    "userId": ObjectId(user_id),
                    "acceptedAt": now,
                    "updatedAt": now
                }
            }
        )

        await self._pools_collection.update_one(
            {"_id": invitation["poolId"]},
            {
                "$inc": {"stats.totalAccepted": 1},
                "$set": {"updatedAt": now}
            }
        )

        logger.info(f"Invitation {invitation['_id']} accepted by user {user_id}")

        return await self.get_invitation_by_token(token)

    async def decline_invitation(self, token: str) -> Dict[str, Any]:
        """Decline an invitation."""
        invitation = await self.get_invitation_by_token(token)

        if invitation["status"] != "pending":
            raise ValidationException(
                message=f"Invitation already {invitation['status']}",
                code="INVITATION_ALREADY_PROCESSED"
            )

        now = datetime.now(timezone.utc)

        await self._invitations_collection.update_one(
            {"_id": invitation["_id"]},
            {
                "$set": {
                    "status": "declined",
                    "declinedAt": now,
                    "updatedAt": now
                }
            }
        )

        await self._pools_collection.update_one(
            {"_id": invitation["poolId"]},
            {
                "$inc": {"stats.totalDeclined": 1},
                "$set": {"updatedAt": now}
            }
        )

        return await self.get_invitation_by_token(token)

    async def get_invitations_for_pool(
        self,
        pool_id: str,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get invitations for a pool with optional status filter."""
        query: Dict[str, Any] = {"poolId": ObjectId(pool_id)}

        if status:
            query["status"] = status

        cursor = self._invitations_collection.find(query).sort("createdAt", -1)
        return await cursor.to_list(length=500)

    async def cancel_invitation(self, invitation_id: str) -> Dict[str, Any]:
        """
        Delete an invitation and update pool stats.

        Args:
            invitation_id: ID of invitation to delete

        Returns:
            Dict with success message

        Raises:
            NotFoundException: If invitation not found
        """
        invitation = await self._invitations_collection.find_one({
            "_id": ObjectId(invitation_id)
        })

        if not invitation:
            raise NotFoundException(
                message="Invitation not found",
                code="INVITATION_NOT_FOUND"
            )

        pool_id = invitation["poolId"]
        status = invitation.get("status", "pending")
        now = datetime.now(timezone.utc)

        # Update pool stats based on invitation status
        stats_update = {"$set": {"updatedAt": now}}

        if status == "pending":
            stats_update["$inc"] = {"stats.totalInvited": -1}
        elif status == "accepted":
            stats_update["$inc"] = {"stats.totalInvited": -1, "stats.totalAccepted": -1}
        elif status == "declined":
            stats_update["$inc"] = {"stats.totalInvited": -1, "stats.totalDeclined": -1}

        # Update pool stats
        if "$inc" in stats_update:
            await self._pools_collection.update_one(
                {"_id": pool_id},
                stats_update
            )

        # Delete the invitation
        await self._invitations_collection.delete_one({
            "_id": ObjectId(invitation_id)
        })

        logger.info(f"Invitation {invitation_id} deleted (was {status})")

        return {"message": "Invitation deleted successfully"}

    async def get_invitation_by_id(self, invitation_id: str) -> Dict[str, Any]:
        """Get invitation by ID."""
        invitation = await self._invitations_collection.find_one({
            "_id": ObjectId(invitation_id)
        })

        if not invitation:
            raise NotFoundException(
                message="Invitation not found",
                code="INVITATION_NOT_FOUND"
            )

        return invitation

    async def get_pending_invitations_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get pending invitations for a user by their email."""
        # First get user's email from users collection
        users_collection = self._db["users"]
        user = await users_collection.find_one({"_id": ObjectId(user_id)})

        if not user:
            return []

        email = user.get("email", "").lower()

        # Find pending invitations for this email
        cursor = self._invitations_collection.find({
            "email": email,
            "status": "pending"
        }).sort("createdAt", -1)

        invitations = await cursor.to_list(length=100)

        # Populate pool details for each invitation
        result = []
        for inv in invitations:
            pool = await self._pools_collection.find_one({"_id": inv.get("poolId")})
            pool_name = pool.get("name", "") if pool else ""

            expires_at = inv.get("expiresAt")
            expires_at_str = None
            if expires_at:
                try:
                    expires_at_str = expires_at.isoformat() if hasattr(expires_at, 'isoformat') else str(expires_at)
                except Exception:
                    expires_at_str = str(expires_at)

            result.append({
                "id": str(inv["_id"]),
                "poolName": pool_name,
                "token": inv.get("token", ""),
                "expiresAt": expires_at_str,
                "status": inv.get("status", "pending"),
            })

        return result

    async def get_accepted_invitations_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get accepted invitations for a user."""
        cursor = self._invitations_collection.find({
            "userId": ObjectId(user_id),
            "status": "accepted"
        }).sort("acceptedAt", -1)

        invitations = await cursor.to_list(length=100)

        # Populate pool details for each invitation
        result = []
        for inv in invitations:
            pool = await self._pools_collection.find_one({"_id": inv.get("poolId")})
            pool_name = pool.get("name", "") if pool else ""

            accepted_at = inv.get("acceptedAt")
            accepted_at_str = None
            if accepted_at:
                try:
                    accepted_at_str = accepted_at.isoformat() if hasattr(accepted_at, 'isoformat') else str(accepted_at)
                except Exception:
                    accepted_at_str = str(accepted_at)

            result.append({
                "id": str(inv["_id"]),
                "poolName": pool_name,
                "token": inv.get("token", ""),
                "acceptedAt": accepted_at_str,
                "status": inv.get("status", "accepted"),
            })

        return result

    async def expire_old_invitations(self) -> int:
        """Mark expired pending invitations. Called by cron job."""
        now = datetime.now(timezone.utc)

        result = await self._invitations_collection.update_many(
            {
                "status": "pending",
                "expiresAt": {"$lt": now}
            },
            {
                "$set": {"status": "expired", "updatedAt": now}
            }
        )

        if result.modified_count > 0:
            logger.info(f"Expired {result.modified_count} invitations")

        return result.modified_count

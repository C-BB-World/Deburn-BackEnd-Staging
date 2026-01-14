"""
User service for user lifecycle management.

Handles user creation, retrieval, and deletion operations.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, TYPE_CHECKING

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from common.utils.exceptions import ConflictException, ValidationException, NotFoundException

if TYPE_CHECKING:
    from app_v2.user.services.consent_service import ConsentService

logger = logging.getLogger(__name__)


class UserService:
    """
    Manages user lifecycle and data.
    """

    DELETION_GRACE_PERIOD_DAYS = 30

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        consent_service: "ConsentService"
    ):
        """
        Initialize UserService.

        Args:
            db: MongoDB database connection
            consent_service: For consent validation
        """
        self._db = db
        self._consent_service = consent_service
        self._users_collection = db["users"]
        self._audit_logs_collection = db["auditLogs"]

    async def create_user(
        self,
        firebase_uid: str,
        email: str,
        organization: str,
        country: str,
        profile: dict,
        consents: List[dict]
    ) -> dict:
        """
        Create a new user record.

        Args:
            firebase_uid: Firebase user ID (from registration)
            email: User's email address
            organization: User's organization name
            country: User's country code (ISO 3166-1 alpha-2)
            profile: Initial profile data (firstName, lastName, timezone, etc.)
            consents: List of consents accepted at registration

        Returns:
            Created user document

        Raises:
            ConflictError: firebaseUid already exists
            ValidationError: Invalid profile or missing required consents
        """
        existing = await self._users_collection.find_one({"firebaseUid": firebase_uid})
        if existing:
            raise ConflictException(
                message="User already exists",
                code="USER_ALREADY_EXISTS"
            )

        self._validate_profile(profile)
        self._validate_country(country)
        self._consent_service.validate_registration_consents(consents)

        now = datetime.now(timezone.utc)

        consents_dict = {}
        for consent in consents:
            consent_type = consent.get("type")
            consents_dict[consent_type] = {
                "accepted": consent.get("accepted", False),
                "acceptedAt": now if consent.get("accepted") else None,
                "version": consent.get("version")
            }

        for consent_type in self._consent_service.CONSENT_VERSIONS:
            if consent_type not in consents_dict:
                consents_dict[consent_type] = {
                    "accepted": False,
                    "acceptedAt": None,
                    "version": None
                }

        user_doc = {
            "firebaseUid": firebase_uid,
            "email": email,
            "organization": organization,
            "country": country.upper(),
            "status": "active",
            "profile": {
                "firstName": profile.get("firstName"),
                "lastName": profile.get("lastName"),
                "jobTitle": profile.get("jobTitle"),
                "leadershipLevel": profile.get("leadershipLevel"),
                "timezone": profile.get("timezone", "UTC"),
                "preferredLanguage": profile.get("preferredLanguage", "en")
            },
            "consents": consents_dict,
            "coachExchanges": {
                "count": 0,
                "lastResetDate": now
            },
            "sessions": [],
            "lastLoginAt": None,
            "createdAt": now,
            "updatedAt": now
        }

        result = await self._users_collection.insert_one(user_doc)
        user_doc["_id"] = result.inserted_id

        await self._log_audit_event(
            user_id=result.inserted_id,
            action="user_created",
            metadata={"email": email}
        )

        logger.info(f"User created: {result.inserted_id}")
        return user_doc

    async def get_user_by_id(self, user_id: str) -> Optional[dict]:
        """
        Load user by MongoDB ID.

        Args:
            user_id: MongoDB ObjectId as string

        Returns:
            User document or None if not found
        """
        try:
            return await self._users_collection.find_one({"_id": ObjectId(user_id)})
        except Exception:
            return None

    async def get_user_by_firebase_uid(self, firebase_uid: str) -> Optional[dict]:
        """
        Load user by Firebase UID.

        Args:
            firebase_uid: Firebase user ID

        Returns:
            User document or None if not found
        """
        return await self._users_collection.find_one({"firebaseUid": firebase_uid})

    async def get_user_by_email(self, email: str) -> Optional[dict]:
        """
        Load user by email address.

        Args:
            email: User's email address

        Returns:
            User document or None if not found
        """
        return await self._users_collection.find_one({"email": email.lower()})

    async def update_last_login(self, user_id: str) -> None:
        """
        Update user's last login timestamp.

        Args:
            user_id: MongoDB user ID
        """
        now = datetime.now(timezone.utc)
        await self._users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"lastLoginAt": now, "updatedAt": now}}
        )

    async def request_deletion(
        self,
        user_id: str,
        reason: Optional[str] = None
    ) -> datetime:
        """
        Initiate account deletion with grace period.

        Args:
            user_id: MongoDB user ID
            reason: Optional reason for deletion

        Returns:
            scheduledFor datetime (30 days from now)

        Side Effects:
            - Sets deletion state on user
            - Updates status to pendingDeletion
            - Logs audit event
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            raise NotFoundException(
                message="User not found",
                code="USER_NOT_FOUND"
            )

        if user.get("status") == "pendingDeletion":
            raise ValidationException(
                message="Deletion already requested",
                code="DELETION_ALREADY_REQUESTED"
            )

        now = datetime.now(timezone.utc)
        scheduled_for = now + timedelta(days=self.DELETION_GRACE_PERIOD_DAYS)

        await self._users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "status": "pendingDeletion",
                    "deletion": {
                        "requestedAt": now,
                        "scheduledFor": scheduled_for,
                        "reason": reason
                    },
                    "updatedAt": now
                }
            }
        )

        await self._log_audit_event(
            user_id=ObjectId(user_id),
            action="deletion_requested",
            metadata={"reason": reason, "scheduledFor": scheduled_for.isoformat()}
        )

        logger.info(f"Deletion requested for user {user_id}, scheduled for {scheduled_for}")
        return scheduled_for

    async def cancel_deletion(self, user_id: str) -> None:
        """
        Cancel pending account deletion.

        Args:
            user_id: MongoDB user ID

        Side Effects:
            - Clears deletion state
            - Sets status back to active
            - Logs audit event
        """
        now = datetime.now(timezone.utc)

        await self._users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "status": "active",
                    "updatedAt": now
                },
                "$unset": {"deletion": ""}
            }
        )

        await self._log_audit_event(
            user_id=ObjectId(user_id),
            action="deletion_cancelled",
            metadata={}
        )

        logger.info(f"Deletion cancelled for user {user_id}")

    async def get_pending_deletions(self) -> List[dict]:
        """
        Find users ready for deletion.
        Used by background job.

        Returns:
            List of users where deletion.scheduledFor <= now
        """
        now = datetime.now(timezone.utc)

        cursor = self._users_collection.find({
            "status": "pendingDeletion",
            "deletion.scheduledFor": {"$lte": now}
        })

        return await cursor.to_list(length=None)

    async def execute_deletion(self, user_id: str) -> None:
        """
        Permanently delete a user account.
        Called by background job after grace period.

        Args:
            user_id: MongoDB user ID

        Side Effects:
            - Clears sessions array
            - Deletes user document
            - Logs final audit event
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            logger.warning(f"User {user_id} not found for deletion")
            return

        await self._users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"sessions": []}}
        )

        await self._users_collection.delete_one({"_id": ObjectId(user_id)})

        await self._log_audit_event(
            user_id=ObjectId(user_id),
            action="account_deleted",
            metadata={"email": "[deleted]"}
        )

        logger.info(f"User {user_id} permanently deleted")

    def _validate_profile(self, profile: dict) -> None:
        """Validate profile data."""
        if not profile.get("firstName"):
            raise ValidationException(
                message="First name is required",
                code="FIRST_NAME_REQUIRED"
            )

        if len(profile.get("firstName", "")) > 50:
            raise ValidationException(
                message="First name too long (max 50 characters)",
                code="FIRST_NAME_TOO_LONG"
            )

        if profile.get("lastName") and len(profile["lastName"]) > 50:
            raise ValidationException(
                message="Last name too long (max 50 characters)",
                code="LAST_NAME_TOO_LONG"
            )

        if profile.get("jobTitle") and len(profile["jobTitle"]) > 100:
            raise ValidationException(
                message="Job title too long (max 100 characters)",
                code="JOB_TITLE_TOO_LONG"
            )

        valid_leadership_levels = [
            "individual_contributor",
            "team_lead",
            "manager",
            "director",
            "executive"
        ]
        if profile.get("leadershipLevel") and profile["leadershipLevel"] not in valid_leadership_levels:
            raise ValidationException(
                message=f"Invalid leadership level. Must be one of: {', '.join(valid_leadership_levels)}",
                code="INVALID_LEADERSHIP_LEVEL"
            )

        valid_languages = ["en", "sv"]
        if profile.get("preferredLanguage") and profile["preferredLanguage"] not in valid_languages:
            raise ValidationException(
                message=f"Invalid language. Must be one of: {', '.join(valid_languages)}",
                code="INVALID_LANGUAGE"
            )

    def _validate_country(self, country: str) -> None:
        """Validate country code."""
        if not country or len(country) != 2:
            raise ValidationException(
                message="Country must be a valid ISO 3166-1 alpha-2 code",
                code="INVALID_COUNTRY"
            )

    async def _log_audit_event(
        self,
        user_id: ObjectId,
        action: str,
        metadata: dict
    ) -> None:
        """Log an audit event."""
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=90)

        await self._audit_logs_collection.insert_one({
            "userId": user_id,
            "action": action,
            "metadata": metadata,
            "timestamp": now,
            "expiresAt": expires_at
        })

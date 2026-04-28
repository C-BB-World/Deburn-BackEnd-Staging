"""
Profile service for user profile management.

Handles profile viewing and updates with validation and sanitization.
"""

import html
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from common.utils.exceptions import ValidationException, NotFoundException

logger = logging.getLogger(__name__)


class ProfileService:
    """
    Manages user profile data.
    """

    EDITABLE_FIELDS = {
        "firstName": {"max_length": 50, "required": True},
        "lastName": {"max_length": 50, "required": False},
        "jobTitle": {"max_length": 100, "required": False},
        "leadershipLevel": {"enum": [
            "individual_contributor",
            "team_lead",
            "manager",
            "director",
            "executive"
        ], "required": False},
        "timezone": {"type": "timezone", "required": False},
        "preferredLanguage": {"enum": ["en", "sv"], "required": False}
    }

    NON_EDITABLE_FIELDS = ["organization", "country"]

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize ProfileService.

        Args:
            db: MongoDB database connection
        """
        self._db = db
        self._users_collection = db["users"]
        self._audit_logs_collection = db["auditLogs"]

    async def get_profile(self, user_id: str) -> dict:
        """
        Get user's profile data.

        Args:
            user_id: MongoDB user ID

        Returns:
            dict with profile fields (firstName, lastName, timezone, etc.)
        """
        user = await self._users_collection.find_one(
            {"_id": ObjectId(user_id)},
            {
                "profile": 1,
                "email": 1,
                "organization": 1,
                "country": 1
            }
        )

        if not user:
            raise NotFoundException(
                message="User not found",
                code="USER_NOT_FOUND"
            )

        profile = user.get("profile", {})
        profile["email"] = user.get("email")
        profile["organization"] = user.get("organization")
        profile["country"] = user.get("country")

        return profile

    async def update_profile(
        self,
        user_id: str,
        updates: dict
    ) -> dict:
        """
        Update user's profile fields.

        Args:
            user_id: MongoDB user ID
            updates: Dict of fields to update (partial update)
                     Keys should be camelCase (firstName, lastName, etc.)

        Returns:
            Updated profile dict

        Raises:
            ValidationError: Invalid field value

        Side Effects:
            - Validates each field
            - Sanitizes string inputs
            - Updates user.profile in document
            - Logs audit event
        """
        for field in self.NON_EDITABLE_FIELDS:
            if field in updates:
                raise ValidationException(
                    message=f"Field '{field}' cannot be updated",
                    code="FIELD_NOT_EDITABLE"
                )

        sanitized_updates = {}
        for field, value in updates.items():
            if field not in self.EDITABLE_FIELDS:
                continue

            self.validate_profile_field(field, value)
            sanitized_value = self._sanitize_value(field, value)
            sanitized_updates[f"profile.{field}"] = sanitized_value

        if not sanitized_updates:
            return await self.get_profile(user_id)

        now = datetime.now(timezone.utc)
        sanitized_updates["updatedAt"] = now

        result = await self._users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": sanitized_updates}
        )

        if result.matched_count == 0:
            raise NotFoundException(
                message="User not found",
                code="USER_NOT_FOUND"
            )

        await self._log_audit_event(
            user_id=ObjectId(user_id),
            action="profile_updated",
            metadata={"updatedFields": list(updates.keys())}
        )

        logger.info(f"Profile updated for user {user_id}")
        return await self.get_profile(user_id)

    def validate_profile_field(self, field: str, value: Any) -> bool:
        """
        Validate a single profile field.

        Args:
            field: Field name (camelCase)
            value: Field value

        Returns:
            True if valid

        Raises:
            ValidationError: If invalid, with reason
        """
        if field not in self.EDITABLE_FIELDS:
            raise ValidationException(
                message=f"Unknown field: {field}",
                code="UNKNOWN_FIELD"
            )

        field_config = self.EDITABLE_FIELDS[field]

        if field_config.get("required") and not value:
            raise ValidationException(
                message=f"{field} is required",
                code=f"{self._to_snake_case(field).upper()}_REQUIRED"
            )

        if value is None:
            return True

        if "max_length" in field_config:
            if len(str(value)) > field_config["max_length"]:
                raise ValidationException(
                    message=f"{field} exceeds maximum length of {field_config['max_length']}",
                    code=f"{self._to_snake_case(field).upper()}_TOO_LONG"
                )

        if "enum" in field_config:
            if value not in field_config["enum"]:
                raise ValidationException(
                    message=f"Invalid {field}. Must be one of: {', '.join(field_config['enum'])}",
                    code=f"INVALID_{self._to_snake_case(field).upper()}"
                )

        if field_config.get("type") == "timezone":
            self._validate_timezone(value)

        return True

    def _validate_timezone(self, timezone_str: str) -> None:
        """Validate IANA timezone string."""
        try:
            import zoneinfo
            zoneinfo.ZoneInfo(timezone_str)
        except Exception:
            raise ValidationException(
                message=f"Invalid timezone: {timezone_str}",
                code="INVALID_TIMEZONE"
            )

    def _sanitize_value(self, field: str, value: Any) -> Any:
        """Sanitize a field value."""
        if value is None:
            return None

        if isinstance(value, str):
            value = value.strip()
            value = html.escape(value)

        return value

    def _to_snake_case(self, name: str) -> str:
        """Convert camelCase to snake_case."""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

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

"""
Consent service for GDPR compliance.

Tracks and manages user consents with version history.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from common.utils.exceptions import ValidationException

logger = logging.getLogger(__name__)


class ConsentService:
    """
    Tracks and manages user consents for GDPR compliance.
    """

    CONSENT_VERSIONS = {
        "termsOfService": "1.0",
        "privacyPolicy": "1.0",
        "dataProcessing": "1.0",
        "marketing": "1.0"
    }

    REQUIRED_CONSENTS = [
        "termsOfService",
        "privacyPolicy",
        "dataProcessing"
    ]

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize ConsentService.

        Args:
            db: MongoDB database connection
        """
        self._db = db
        self._users_collection = db["users"]
        self._audit_logs_collection = db["auditLogs"]

    async def get_consents(self, user_id: str) -> dict:
        """
        Get user's current consents with version check.

        Args:
            user_id: MongoDB user ID

        Returns:
            dict with:
                - consents: user's consent records
                - needsUpdate: bool (if any required consent outdated)
                - outdatedConsents: list of consent types needing update
        """
        user = await self._users_collection.find_one(
            {"_id": ObjectId(user_id)},
            {"consents": 1}
        )

        if not user:
            return {
                "consents": {},
                "needsUpdate": False,
                "outdatedConsents": []
            }

        consents = user.get("consents", {})
        outdated_consents = self._check_outdated_consents(consents)

        needs_update = any(
            consent_type in self.REQUIRED_CONSENTS
            for consent_type in outdated_consents
        )

        return {
            "consents": consents,
            "needsUpdate": needs_update,
            "outdatedConsents": outdated_consents
        }

    async def update_consent(
        self,
        user_id: str,
        consent_type: str,
        accepted: bool,
        version: str
    ) -> dict:
        """
        Update a user's consent.

        Args:
            user_id: MongoDB user ID
            consent_type: Type of consent (camelCase)
            accepted: Whether user accepts
            version: Version being accepted (must match current)

        Returns:
            Updated consent record

        Raises:
            ValidationError: Invalid consent type or version mismatch
        """
        if consent_type not in self.CONSENT_VERSIONS:
            raise ValidationException(
                message=f"Invalid consent type: {consent_type}",
                code="INVALID_CONSENT_TYPE"
            )

        current_version = self.CONSENT_VERSIONS[consent_type]
        if version != current_version:
            raise ValidationException(
                message=f"Version mismatch. Current version is {current_version}",
                code="CONSENT_VERSION_MISMATCH"
            )

        if not accepted and consent_type in self.REQUIRED_CONSENTS:
            raise ValidationException(
                message="Withdrawing required consent will trigger account deletion",
                code="WITHDRAWAL_TRIGGERS_DELETION"
            )

        now = datetime.now(timezone.utc)

        consent_record = {
            "accepted": accepted,
            "acceptedAt": now if accepted else None,
            "version": version
        }

        await self._users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    f"consents.{consent_type}": consent_record,
                    "updatedAt": now
                }
            }
        )

        await self._log_audit_event(
            user_id=ObjectId(user_id),
            action="consent_updated",
            metadata={
                "consentType": consent_type,
                "consentAccepted": accepted,
                "consentVersion": version
            }
        )

        logger.info(f"Consent {consent_type} updated for user {user_id}")
        return consent_record

    def validate_registration_consents(self, consents: List[dict]) -> bool:
        """
        Validate consents provided at registration.

        Args:
            consents: List of consents from registration

        Returns:
            True if all required consents present and accepted

        Raises:
            ValidationError: Missing or unaccepted required consent
        """
        consent_map = {c.get("type"): c for c in consents}

        for required in self.REQUIRED_CONSENTS:
            if required not in consent_map:
                raise ValidationException(
                    message=f"Missing required consent: {required}",
                    code="MISSING_REQUIRED_CONSENT"
                )

            consent = consent_map[required]
            if not consent.get("accepted"):
                raise ValidationException(
                    message=f"Required consent not accepted: {required}",
                    code="CONSENT_NOT_ACCEPTED"
                )

            current_version = self.CONSENT_VERSIONS[required]
            if consent.get("version") != current_version:
                raise ValidationException(
                    message=f"Consent version mismatch for {required}. Expected {current_version}",
                    code="CONSENT_VERSION_MISMATCH"
                )

        return True

    def check_consent_versions(self, consents: dict) -> List[str]:
        """
        Check which consents are outdated.

        Args:
            consents: User's consents dict

        Returns:
            List of consent types that need re-consent
        """
        return self._check_outdated_consents(consents)

    def _check_outdated_consents(self, consents: dict) -> List[str]:
        """Check which consents have outdated versions."""
        outdated = []

        for consent_type, current_version in self.CONSENT_VERSIONS.items():
            user_consent = consents.get(consent_type, {})

            if not user_consent.get("accepted"):
                if consent_type in self.REQUIRED_CONSENTS:
                    outdated.append(consent_type)
                continue

            user_version = user_consent.get("version")
            if user_version != current_version:
                outdated.append(consent_type)

        return outdated

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

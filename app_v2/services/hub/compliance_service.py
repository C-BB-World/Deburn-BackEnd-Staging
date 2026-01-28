"""
Compliance service.

GDPR compliance operations including data export, deletion, and session management.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from common.utils.exceptions import NotFoundException

logger = logging.getLogger(__name__)


class ComplianceService:
    """
    GDPR compliance operations.
    Handles data export, deletion, and session management.
    """

    def __init__(
        self,
        app_db: AsyncIOMotorDatabase,
        hub_db: AsyncIOMotorDatabase
    ):
        """
        Initialize ComplianceService.

        Args:
            app_db: Main application database connection
            hub_db: Hub database connection for settings
        """
        self._app_db = app_db
        self._hub_db = hub_db

        self._users_collection = app_db["users"]
        self._checkins_collection = app_db["checkIns"]
        self._conversations_collection = app_db["coachConversations"]
        self._commitments_collection = app_db["commitments"]
        self._insights_collection = app_db["insights"]
        self._audit_collection = app_db["auditLogs"]
        self._settings_collection = hub_db["hubSettings"]

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get compliance dashboard statistics.

        Returns:
            Dict with total_users, pending_deletions, audit_log_count, active_sessions
        """
        total_users = await self._users_collection.count_documents({"status": {"$ne": "deleted"}})

        pending_deletions = await self._users_collection.count_documents({
            "deletionRequestedAt": {"$exists": True, "$ne": None},
            "status": {"$ne": "deleted"}
        })

        audit_log_count = await self._audit_collection.count_documents({})

        now = datetime.now(timezone.utc)
        active_sessions = await self._users_collection.count_documents({
            "sessions": {
                "$elemMatch": {
                    "expiresAt": {"$gt": now}
                }
            }
        })

        return {
            "totalUsers": total_users,
            "pendingDeletions": pending_deletions,
            "auditLogCount": audit_log_count,
            "activeSessions": active_sessions,
        }

    async def get_user_compliance_data(
        self,
        email: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get user data for compliance review.

        Args:
            email: User email

        Returns:
            User compliance data or None
        """
        user = await self._users_collection.find_one({
            "email": email.lower()
        })

        if not user:
            return None

        user_id = user["_id"]

        checkin_count = await self._checkins_collection.count_documents({
            "userId": user_id
        })

        conversation_count = await self._conversations_collection.count_documents({
            "userId": user_id
        })

        return {
            "userId": str(user_id),
            "email": user.get("email"),
            "firstName": user.get("firstName"),
            "lastName": user.get("lastName"),
            "status": user.get("status"),
            "createdAt": user.get("createdAt"),
            "lastLogin": user.get("lastLogin"),
            "deletionRequestedAt": user.get("deletionRequestedAt"),
            "checkinCount": checkin_count,
            "conversationCount": conversation_count,
            "sessionCount": len(user.get("sessions", [])),
        }

    async def export_user_data(
        self,
        user_id: str,
        exported_by: str
    ) -> Dict[str, Any]:
        """
        Export all user data (GDPR Article 20).
        Includes: profile, check-ins, conversations, commitments.

        Args:
            user_id: User ID
            exported_by: Admin email who requested export

        Returns:
            Complete user data dict
        """
        user = await self._users_collection.find_one({"_id": ObjectId(user_id)})

        if not user:
            raise NotFoundException(
                message="User not found",
                code="USER_NOT_FOUND"
            )

        checkins = await self._checkins_collection.find({
            "userId": ObjectId(user_id)
        }).to_list(length=10000)

        conversations = await self._conversations_collection.find({
            "userId": ObjectId(user_id)
        }).to_list(length=1000)

        commitments = await self._commitments_collection.find({
            "userId": ObjectId(user_id)
        }).to_list(length=1000)

        insights = await self._insights_collection.find({
            "userId": ObjectId(user_id)
        }).to_list(length=1000)

        audit_logs = await self._audit_collection.find({
            "userId": ObjectId(user_id)
        }).to_list(length=10000)

        await self._audit_collection.insert_one({
            "userId": ObjectId(user_id),
            "action": "DATA_EXPORT",
            "performedBy": exported_by,
            "timestamp": datetime.now(timezone.utc),
            "details": {"exportedBy": exported_by}
        })

        logger.info(f"Exported user data for {user_id} by {exported_by}")

        return {
            "exportedAt": datetime.now(timezone.utc).isoformat(),
            "exportedBy": exported_by,
            "profile": self._serialize_doc(user, exclude=["passwordHash", "sessions"]),
            "checkIns": [self._serialize_doc(c) for c in checkins],
            "conversations": [self._serialize_doc(c) for c in conversations],
            "commitments": [self._serialize_doc(c) for c in commitments],
            "insights": [self._serialize_doc(i) for i in insights],
            "auditLogs": [self._serialize_doc(a) for a in audit_logs],
        }

    async def delete_user_account(
        self,
        user_id: str,
        deleted_by: str
    ) -> Dict[str, Any]:
        """
        Permanently delete user account (GDPR Article 17).
        - Deletes all check-ins
        - Deletes all conversations
        - Deletes all commitments
        - Anonymizes audit logs (removes PII, keeps entries)
        - Deletes user record

        Args:
            user_id: User ID
            deleted_by: Admin email who performed deletion

        Returns:
            Dict with counts of deleted/anonymized records
        """
        user = await self._users_collection.find_one({"_id": ObjectId(user_id)})

        if not user:
            raise NotFoundException(
                message="User not found",
                code="USER_NOT_FOUND"
            )

        checkins_result = await self._checkins_collection.delete_many({
            "userId": ObjectId(user_id)
        })

        conversations_result = await self._conversations_collection.delete_many({
            "userId": ObjectId(user_id)
        })

        commitments_result = await self._commitments_collection.delete_many({
            "userId": ObjectId(user_id)
        })

        insights_result = await self._insights_collection.delete_many({
            "userId": ObjectId(user_id)
        })

        audit_result = await self._audit_collection.update_many(
            {"userId": ObjectId(user_id)},
            {
                "$set": {
                    "userId": None,
                    "anonymizedAt": datetime.now(timezone.utc),
                    "anonymizedBy": deleted_by,
                },
                "$unset": {
                    "userEmail": "",
                    "userName": "",
                }
            }
        )

        await self._users_collection.delete_one({"_id": ObjectId(user_id)})

        await self._audit_collection.insert_one({
            "userId": None,
            "action": "ACCOUNT_DELETED",
            "performedBy": deleted_by,
            "timestamp": datetime.now(timezone.utc),
            "details": {
                "originalUserId": user_id,
                "deletedBy": deleted_by,
            }
        })

        logger.info(f"Deleted user account {user_id} by {deleted_by}")

        return {
            "success": True,
            "deletedCheckIns": checkins_result.deleted_count,
            "deletedConversations": conversations_result.deleted_count,
            "deletedCommitments": commitments_result.deleted_count,
            "deletedInsights": insights_result.deleted_count,
            "anonymizedAuditLogs": audit_result.modified_count,
            "deletedAt": datetime.now(timezone.utc).isoformat(),
        }

    async def get_pending_deletions(self) -> List[Dict[str, Any]]:
        """
        Get users with pending deletion requests.

        Returns:
            List of users pending deletion
        """
        settings = await self._settings_collection.find_one({"key": "coachSettings"})
        grace_period_days = settings.get("deletionGracePeriodDays", 30) if settings else 30

        users = await self._users_collection.find({
            "deletionRequestedAt": {"$exists": True, "$ne": None},
            "status": {"$ne": "deleted"}
        }).to_list(length=1000)

        now = datetime.now(timezone.utc)
        results = []

        for user in users:
            requested_at = user.get("deletionRequestedAt")
            if requested_at:
                scheduled_at = requested_at + timedelta(days=grace_period_days)
                days_remaining = (scheduled_at - now).days

                results.append({
                    "userId": str(user["_id"]),
                    "email": user.get("email"),
                    "firstName": user.get("firstName"),
                    "lastName": user.get("lastName"),
                    "deletionRequestedAt": requested_at,
                    "scheduledDeletionAt": scheduled_at,
                    "daysRemaining": max(0, days_remaining),
                    "canDeleteNow": days_remaining <= 0,
                })

        return results

    async def cleanup_expired_sessions(self) -> int:
        """
        Remove expired sessions from all users.

        Returns:
            Count of cleaned sessions
        """
        now = datetime.now(timezone.utc)

        result = await self._users_collection.update_many(
            {},
            {
                "$pull": {
                    "sessions": {
                        "expiresAt": {"$lt": now}
                    }
                }
            }
        )

        logger.info(f"Cleaned up expired sessions for {result.modified_count} users")
        return result.modified_count

    async def get_security_config(self) -> Dict[str, Any]:
        """
        Get current security configuration (read-only).

        Returns:
            Security configuration dict
        """
        import os

        return {
            "tokenExpiryHours": 24,
            "refreshTokenExpiryDays": 30,
            "maxSessionsPerUser": 5,
            "passwordMinLength": 8,
            "corsOrigins": os.getenv("CORS_ORIGINS", "").split(","),
            "dataRetentionDays": 365,
            "auditLogRetentionDays": 730,
        }

    async def get_deletion_grace_period(self) -> int:
        """
        Get configurable grace period in days.

        Returns:
            Grace period in days (default: 30)
        """
        settings = await self._settings_collection.find_one({"key": "coachSettings"})
        return settings.get("deletionGracePeriodDays", 30) if settings else 30

    async def set_deletion_grace_period(
        self,
        days: int,
        admin_email: str
    ) -> None:
        """
        Update deletion grace period.

        Args:
            days: New grace period in days
            admin_email: Admin making the change
        """
        from app_v2.services.hub.coach_config_service import CoachConfigService

        config_service = CoachConfigService(self._hub_db)
        await config_service.update_coach_settings(
            deletion_grace_period_days=days,
            admin_email=admin_email
        )

    def _serialize_doc(
        self,
        doc: Dict[str, Any],
        exclude: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Convert MongoDB document for JSON serialization."""
        exclude = exclude or []
        result = {}

        for key, value in doc.items():
            if key in exclude:
                continue

            if isinstance(value, ObjectId):
                result[key] = str(value)
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, bytes):
                result[key] = f"<binary data: {len(value)} bytes>"
            elif isinstance(value, list):
                result[key] = [
                    self._serialize_doc(v) if isinstance(v, dict) else
                    str(v) if isinstance(v, ObjectId) else
                    v.isoformat() if isinstance(v, datetime) else v
                    for v in value
                ]
            elif isinstance(value, dict):
                result[key] = self._serialize_doc(value)
            else:
                result[key] = value

        return result

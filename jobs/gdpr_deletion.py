"""
GDPR deletion background job.

Processes account deletion requests after the grace period expires.
This job should be run daily via CRON.

Usage:
    Run via CRON:
        0 2 * * * cd /path/to/project && python -m jobs.gdpr_deletion

    Or run directly:
        python -m jobs.gdpr_deletion
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class GDPRDeletionJob:
    """
    Processes pending account deletion requests.

    After a user requests account deletion, their account enters a grace period
    (default 30 days, configurable). This job processes deletions that have
    passed the grace period.

    Actions performed:
    1. Finds users with deletionRequestedAt older than grace period
    2. For each user:
       - Deletes all check-ins
       - Deletes all coach conversations
       - Deletes all commitments
       - Deletes all insights
       - Anonymizes audit logs (removes PII but keeps records)
       - Deletes user document
       - Logs the deletion action
    """

    def __init__(
        self,
        app_db_uri: str,
        hub_db_uri: str,
        app_db_name: str = "deburn",
        hub_db_name: str = "deburn_hub"
    ):
        """
        Initialize the GDPR deletion job.

        Args:
            app_db_uri: MongoDB URI for application database
            hub_db_uri: MongoDB URI for hub database
            app_db_name: Application database name
            hub_db_name: Hub database name
        """
        self._app_client = AsyncIOMotorClient(app_db_uri)
        self._hub_client = AsyncIOMotorClient(hub_db_uri)

        self._app_db = self._app_client[app_db_name]
        self._hub_db = self._hub_client[hub_db_name]

        self._users = self._app_db["users"]
        self._checkins = self._app_db["checkIns"]
        self._conversations = self._app_db["coachConversations"]
        self._commitments = self._app_db["commitments"]
        self._insights = self._app_db["insights"]
        self._audit_logs = self._app_db["auditLogs"]
        self._org_members = self._app_db["organizationMembers"]
        self._hub_settings = self._hub_db["hubSettings"]

    async def run(self) -> Dict[str, Any]:
        """
        Execute the GDPR deletion job.

        Returns:
            Dict with job results including counts and any errors
        """
        logger.info("Starting GDPR deletion job")
        start_time = datetime.now(timezone.utc)

        results = {
            "startTime": start_time.isoformat(),
            "usersProcessed": 0,
            "totalCheckInsDeleted": 0,
            "totalConversationsDeleted": 0,
            "totalCommitmentsDeleted": 0,
            "totalInsightsDeleted": 0,
            "totalAuditLogsAnonymized": 0,
            "errors": [],
        }

        try:
            grace_period_days = await self._get_grace_period()
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=grace_period_days)

            users_to_delete = await self._get_users_for_deletion(cutoff_date)

            logger.info(f"Found {len(users_to_delete)} users pending deletion")

            for user in users_to_delete:
                try:
                    deletion_result = await self._delete_user(user)
                    results["usersProcessed"] += 1
                    results["totalCheckInsDeleted"] += deletion_result["checkInsDeleted"]
                    results["totalConversationsDeleted"] += deletion_result["conversationsDeleted"]
                    results["totalCommitmentsDeleted"] += deletion_result["commitmentsDeleted"]
                    results["totalInsightsDeleted"] += deletion_result["insightsDeleted"]
                    results["totalAuditLogsAnonymized"] += deletion_result["auditLogsAnonymized"]

                except Exception as e:
                    error_msg = f"Failed to delete user {user['_id']}: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)

        except Exception as e:
            error_msg = f"Job failed: {str(e)}"
            logger.error(error_msg)
            results["errors"].append(error_msg)

        results["endTime"] = datetime.now(timezone.utc).isoformat()
        results["durationSeconds"] = (
            datetime.now(timezone.utc) - start_time
        ).total_seconds()

        logger.info(
            f"GDPR deletion job completed. "
            f"Processed: {results['usersProcessed']} users, "
            f"Errors: {len(results['errors'])}"
        )

        return results

    async def _get_grace_period(self) -> int:
        """Get the configured grace period in days."""
        settings = await self._hub_settings.find_one({"key": "coachSettings"})
        if settings and "deletionGracePeriodDays" in settings:
            return settings["deletionGracePeriodDays"]
        return 30  # Default 30 days

    async def _get_users_for_deletion(
        self,
        cutoff_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Get users whose deletion request has passed the grace period.

        Args:
            cutoff_date: Requests before this date are processed

        Returns:
            List of user documents to delete
        """
        cursor = self._users.find({
            "deletionRequestedAt": {
                "$exists": True,
                "$ne": None,
                "$lte": cutoff_date
            },
            "status": {"$ne": "deleted"}
        })

        return await cursor.to_list(length=1000)

    async def _delete_user(self, user: Dict[str, Any]) -> Dict[str, int]:
        """
        Delete a user and all associated data.

        Args:
            user: User document to delete

        Returns:
            Dict with counts of deleted/anonymized records
        """
        user_id = user["_id"]
        user_email = user.get("email", "unknown")

        logger.info(f"Processing deletion for user {user_id}")

        checkins_result = await self._checkins.delete_many({"userId": user_id})
        logger.debug(f"Deleted {checkins_result.deleted_count} check-ins")

        conversations_result = await self._conversations.delete_many({"userId": user_id})
        logger.debug(f"Deleted {conversations_result.deleted_count} conversations")

        commitments_result = await self._commitments.delete_many({"userId": user_id})
        logger.debug(f"Deleted {commitments_result.deleted_count} commitments")

        insights_result = await self._insights.delete_many({"userId": user_id})
        logger.debug(f"Deleted {insights_result.deleted_count} insights")

        await self._org_members.update_many(
            {"userId": user_id},
            {
                "$set": {
                    "status": "removed",
                    "updatedAt": datetime.now(timezone.utc)
                }
            }
        )

        audit_result = await self._audit_logs.update_many(
            {"userId": user_id},
            {
                "$set": {
                    "userId": None,
                    "anonymizedAt": datetime.now(timezone.utc),
                    "anonymizedReason": "GDPR_DELETION_JOB",
                },
                "$unset": {
                    "userEmail": "",
                    "userName": "",
                    "userDetails": "",
                }
            }
        )
        logger.debug(f"Anonymized {audit_result.modified_count} audit logs")

        await self._users.delete_one({"_id": user_id})
        logger.info(f"Deleted user document for {user_id}")

        await self._audit_logs.insert_one({
            "userId": None,
            "action": "GDPR_AUTO_DELETION",
            "performedBy": "SYSTEM_JOB",
            "timestamp": datetime.now(timezone.utc),
            "details": {
                "originalUserId": str(user_id),
                "originalEmail": user_email,
                "deletionRequestedAt": user.get("deletionRequestedAt"),
                "processedAt": datetime.now(timezone.utc),
            }
        })

        return {
            "checkInsDeleted": checkins_result.deleted_count,
            "conversationsDeleted": conversations_result.deleted_count,
            "commitmentsDeleted": commitments_result.deleted_count,
            "insightsDeleted": insights_result.deleted_count,
            "auditLogsAnonymized": audit_result.modified_count,
        }

    async def close(self):
        """Close database connections."""
        self._app_client.close()
        self._hub_client.close()


async def main():
    """Main entry point for the GDPR deletion job."""
    app_db_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    hub_db_uri = os.getenv("HUB_MONGODB_URI", app_db_uri)
    app_db_name = os.getenv("MONGODB_DB_NAME", "deburn")
    hub_db_name = os.getenv("HUB_MONGODB_DB_NAME", "deburn_hub")

    job = GDPRDeletionJob(
        app_db_uri=app_db_uri,
        hub_db_uri=hub_db_uri,
        app_db_name=app_db_name,
        hub_db_name=hub_db_name
    )

    try:
        results = await job.run()

        print("\n=== GDPR Deletion Job Results ===")
        print(f"Start Time: {results['startTime']}")
        print(f"End Time: {results['endTime']}")
        print(f"Duration: {results['durationSeconds']:.2f} seconds")
        print(f"Users Processed: {results['usersProcessed']}")
        print(f"Check-ins Deleted: {results['totalCheckInsDeleted']}")
        print(f"Conversations Deleted: {results['totalConversationsDeleted']}")
        print(f"Commitments Deleted: {results['totalCommitmentsDeleted']}")
        print(f"Insights Deleted: {results['totalInsightsDeleted']}")
        print(f"Audit Logs Anonymized: {results['totalAuditLogsAnonymized']}")

        if results["errors"]:
            print(f"\nErrors ({len(results['errors'])}):")
            for error in results["errors"]:
                print(f"  - {error}")

        exit_code = 1 if results["errors"] else 0
        sys.exit(exit_code)

    finally:
        await job.close()


if __name__ == "__main__":
    asyncio.run(main())

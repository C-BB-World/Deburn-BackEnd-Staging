"""
Daily reminder email job.

Sends a daily email to eligible users reminding them to do their
daily check-in and featuring today's micro-course from their learning queue.

Only users with marketing consent receive emails (GDPR compliant).
Supports EN/SV based on user's preferred language.

Usage:
    Run via Render Cron Jobs:
        0 9 * * *  python -m jobs.daily_reminder

    Or run directly:
        python -m jobs.daily_reminder
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any

from motor.motor_asyncio import AsyncIOMotorClient

from app_v2.services.email.email_service import EmailService
from app_v2.services.learning.learning_queue_service import LearningQueueService
from app_v2.pipelines.learning import get_todays_focus_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DailyReminderJob:
    """
    Sends daily reminder emails to eligible users.

    Eligible users:
    - status: "active"
    - consents.marketing.accepted: true

    Each email includes:
    - A check-in reminder
    - Today's micro-course title and duration (from the user's learning queue)
    """

    def __init__(
        self,
        app_db_uri: str,
        hub_db_uri: str,
        app_db_name: str = "deburn",
        hub_db_name: str = "deburn_hub",
    ):
        self._app_client = AsyncIOMotorClient(app_db_uri)
        self._hub_client = AsyncIOMotorClient(hub_db_uri)

        self._app_db = self._app_client[app_db_name]
        self._hub_db = self._hub_client[hub_db_name]

        self._users = self._app_db["users"]

        self._email_service = EmailService()
        self._queue_service = LearningQueueService(db=self._app_db)

    async def run(self) -> Dict[str, Any]:
        """
        Execute the daily reminder job.

        Returns:
            Dict with job results including counts and any errors
        """
        logger.info("Starting daily reminder job")
        start_time = datetime.now(timezone.utc)

        results = {
            "startTime": start_time.isoformat(),
            "eligibleUsers": 0,
            "emailsSent": 0,
            "errors": [],
        }

        try:
            # Query eligible users
            cursor = self._users.find(
                {
                    "status": "active",
                    "consents.marketing.accepted": True,
                },
                {
                    "_id": 1,
                    "email": 1,
                    "profile.firstName": 1,
                    "profile.preferredLanguage": 1,
                }
            )
            users = await cursor.to_list(length=10000)
            results["eligibleUsers"] = len(users)
            logger.info(f"Found {len(users)} eligible users")

            # Build recipients list with today's focus info
            recipients = []
            for user in users:
                user_id = str(user["_id"])
                email = user.get("email")
                if not email:
                    continue

                name = (user.get("profile") or {}).get("firstName") or None
                language = (user.get("profile") or {}).get("preferredLanguage", "en") or "en"

                # Get today's focus module
                module_title = None
                length_minutes = None
                try:
                    focus = await get_todays_focus_pipeline(
                        self._queue_service,
                        self._hub_db,
                        user_id,
                    )
                    if focus and focus.get("module"):
                        module = focus["module"]
                        # Pick localized title
                        if language == "sv":
                            module_title = module.get("titleSv") or module.get("titleEn")
                        else:
                            module_title = module.get("titleEn") or module.get("titleSv")
                        length_minutes = module.get("lengthMinutes")
                except Exception as e:
                    logger.warning(f"Failed to get today's focus for user {user_id}: {e}")

                recipients.append({
                    "email": email,
                    "name": name,
                    "language": language,
                    "module_title": module_title,
                    "length_minutes": length_minutes,
                })

            # Send batch emails
            if recipients:
                batch_result = await self._email_service.send_daily_reminder_emails_batch(recipients)
                results["emailsSent"] = batch_result.get("total_emails", 0)
                if not batch_result.get("success"):
                    results["errors"].append(f"Batch send reported failures")

        except Exception as e:
            error_msg = f"Job failed: {str(e)}"
            logger.error(error_msg)
            results["errors"].append(error_msg)

        results["endTime"] = datetime.now(timezone.utc).isoformat()
        results["durationSeconds"] = (
            datetime.now(timezone.utc) - start_time
        ).total_seconds()

        logger.info(
            f"Daily reminder job completed. "
            f"Eligible: {results['eligibleUsers']}, "
            f"Sent: {results['emailsSent']}, "
            f"Errors: {len(results['errors'])}"
        )

        return results

    async def close(self):
        """Close database connections."""
        self._app_client.close()
        self._hub_client.close()


async def main():
    """Main entry point for the daily reminder job."""
    app_db_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    hub_db_uri = os.getenv("HUB_MONGODB_URI", app_db_uri)
    app_db_name = os.getenv("MONGODB_DB_NAME", "deburn")
    hub_db_name = os.getenv("HUB_MONGODB_DB_NAME", "deburn_hub")

    job = DailyReminderJob(
        app_db_uri=app_db_uri,
        hub_db_uri=hub_db_uri,
        app_db_name=app_db_name,
        hub_db_name=hub_db_name,
    )

    try:
        results = await job.run()

        print("\n=== Daily Reminder Job Results ===")
        print(f"Start Time: {results['startTime']}")
        print(f"End Time: {results['endTime']}")
        print(f"Duration: {results['durationSeconds']:.2f} seconds")
        print(f"Eligible Users: {results['eligibleUsers']}")
        print(f"Emails Sent: {results['emailsSent']}")

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

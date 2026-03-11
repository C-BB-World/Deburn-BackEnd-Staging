"""
Daily reminder email job.

Reads due reminders from the deburn_hub.reminders collection and sends
personalised emails via Resend batch. Content is stored in the reminder
document itself (no locale files needed).

Reminder types:
  - one_time: status becomes "sent" after sending
  - recurring: nextRunAt bumps by intervalDays, stays "active"

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
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from motor.motor_asyncio import AsyncIOMotorClient

from app_v2.services.email.email_service import EmailService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DailyReminderJob:
    """
    Sends reminder emails driven by documents in deburn_hub.reminders.

    Queries reminders where status == "active" and nextRunAt <= now,
    builds personalised emails from the embedded content, and sends
    them via Resend batch.
    """

    def __init__(
        self,
        hub_db_uri: str,
        hub_db_name: str = "deburn_hub",
    ):
        self._hub_client = AsyncIOMotorClient(hub_db_uri)
        self._hub_db = self._hub_client[hub_db_name]
        self._reminders = self._hub_db["reminders"]
        self._email_service = EmailService()

    async def run(self) -> Dict[str, Any]:
        """
        Execute the reminder job.

        Returns:
            Dict with job results including counts and any errors.
        """
        logger.info("Starting daily reminder job")
        start_time = datetime.now(timezone.utc)
        now = start_time

        results = {
            "startTime": start_time.isoformat(),
            "remindersProcessed": 0,
            "emailsSent": 0,
            "errors": [],
        }

        try:
            cursor = self._reminders.find({
                "status": "active",
                "nextRunAt": {"$lte": now},
            })
            reminders = await cursor.to_list(length=1000)
            logger.info(f"Found {len(reminders)} due reminders")

            for reminder in reminders:
                reminder_id = reminder["_id"]
                reminder_name = reminder.get("name", str(reminder_id))
                try:
                    content = reminder.get("content", {})
                    recipients = reminder.get("recipients", [])

                    if not recipients:
                        logger.warning(f"Reminder '{reminder_name}' has no recipients, skipping")
                        continue

                    batch_result = await self._email_service.send_reminder_emails_batch(
                        content=content,
                        recipients=recipients,
                    )

                    sent_count = batch_result.get("total_emails", 0)
                    results["emailsSent"] += sent_count
                    results["remindersProcessed"] += 1

                    # Update reminder document
                    update: Dict[str, Any] = {
                        "$set": {
                            "lastSentAt": now,
                            "updatedAt": now,
                        },
                        "$inc": {"sendCount": 1},
                    }

                    if reminder.get("type") == "one_time":
                        update["$set"]["status"] = "sent"
                    elif reminder.get("type") == "recurring":
                        interval_days = reminder.get("intervalDays", 1)
                        next_run = now + timedelta(days=interval_days)
                        update["$set"]["nextRunAt"] = next_run

                    await self._reminders.update_one(
                        {"_id": reminder_id},
                        update,
                    )

                    logger.info(
                        f"Reminder '{reminder_name}' processed: "
                        f"{sent_count} emails sent"
                    )

                except Exception as e:
                    error_msg = f"Failed to process reminder '{reminder_name}': {e}"
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
            f"Daily reminder job completed. "
            f"Reminders: {results['remindersProcessed']}, "
            f"Sent: {results['emailsSent']}, "
            f"Errors: {len(results['errors'])}"
        )

        return results

    async def close(self):
        """Close database connections."""
        self._hub_client.close()


async def main():
    """Main entry point for the daily reminder job."""
    hub_db_uri = os.getenv("HUB_MONGODB_URI", os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
    hub_db_name = os.getenv("HUB_MONGODB_DB_NAME", "deburn_hub")

    job = DailyReminderJob(
        hub_db_uri=hub_db_uri,
        hub_db_name=hub_db_name,
    )

    try:
        results = await job.run()

        print("\n=== Daily Reminder Job Results ===")
        print(f"Start Time: {results['startTime']}")
        print(f"End Time: {results['endTime']}")
        print(f"Duration: {results['durationSeconds']:.2f} seconds")
        print(f"Reminders Processed: {results['remindersProcessed']}")
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

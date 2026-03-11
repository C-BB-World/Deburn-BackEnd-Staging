"""
Daily reminder email job.

Reads published reminders from the deburn_hub.reminders collection and sends
personalised emails via Resend batch. Content is stored in the reminder
document keyed by language (en/sv).

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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DailyReminderJob:
    """
    Sends reminder emails driven by documents in deburn_hub.reminders.

    Queries reminders where published == true, resolves per-recipient
    language content, and sends via Resend batch.
    """

    def __init__(
        self,
        hub_db_uri: str,
        hub_db_name: str = "deburn-hub",
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
                "published": True,
            })
            reminders = await cursor.to_list(length=1000)
            logger.info(f"Found {len(reminders)} published reminders")

            for reminder in reminders:
                reminder_id = reminder["_id"]
                reminder_name = reminder.get("name", str(reminder_id))
                try:
                    # Skip if already sent today (safety net against double-sends)
                    last_sent = reminder.get("lastSentAt")
                    if last_sent and last_sent.date() == now.date():
                        logger.info(f"Reminder '{reminder_name}' already sent today, skipping")
                        continue

                    content = reminder.get("content", {})
                    recipients = reminder.get("recipients", [])

                    if not recipients:
                        logger.warning(f"Reminder '{reminder_name}' has no recipients, skipping")
                        continue

                    # Group recipients by language so each group gets the right content
                    by_lang: Dict[str, list] = {}
                    for r in recipients:
                        lang = r.get("language", "sv")
                        by_lang.setdefault(lang, []).append(r)

                    total_sent = 0
                    for lang, lang_recipients in by_lang.items():
                        lang_content = content.get(lang) or content.get("sv") or content.get("en") or {}
                        batch_result = await self._email_service.send_reminder_emails_batch(
                            content=lang_content,
                            recipients=lang_recipients,
                        )
                        total_sent += batch_result.get("total_emails", 0)

                    results["emailsSent"] += total_sent
                    results["remindersProcessed"] += 1

                    # Update reminder document
                    update: Dict[str, Any] = {
                        "$set": {
                            "lastSentAt": now,
                            "updatedAt": now,
                        },
                        "$inc": {"sendCount": 1},
                    }

                    await self._reminders.update_one(
                        {"_id": reminder_id},
                        update,
                    )

                    logger.info(
                        f"Reminder '{reminder_name}' processed: "
                        f"{total_sent} emails sent"
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
    hub_db_name = os.getenv("HUB_MONGODB_DATABASE", "deburn-hub")

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

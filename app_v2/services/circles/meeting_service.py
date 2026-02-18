"""
Circle meeting management service.

Manages circle meetings with calendar integration and notifications.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from common.utils.exceptions import (
    NotFoundException,
    ForbiddenException,
    ValidationException,
)

logger = logging.getLogger(__name__)


class MeetingService:
    """
    Manages circle meetings with Google Calendar integration.
    """

    DEFAULT_DURATION = 60
    MIN_DURATION = 15
    MAX_DURATION = 180
    DEFAULT_TIMEZONE = "Europe/Stockholm"

    def __init__(self, db: AsyncIOMotorDatabase, calendar_service=None):
        """
        Initialize MeetingService.

        Args:
            db: MongoDB database connection
            calendar_service: Optional Google Calendar service
        """
        self._db = db
        self._calendar_service = calendar_service
        self._meetings_collection = db["circlemeetings"]
        self._groups_collection = db["circlegroups"]
        self._pools_collection = db["circlepools"]

    async def schedule_meeting(
        self,
        group_id: str,
        scheduled_by: str,
        title: Optional[str] = None,
        topic: Optional[str] = None,
        description: Optional[str] = None,
        scheduled_at: Optional[datetime] = None,
        duration: int = 60,
        meeting_link: Optional[str] = None,
        meeting_timezone: str = "Europe/Stockholm",
        create_calendar_events: bool = True,
        available_members: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Schedule a meeting for a group.

        Args:
            group_id: Group this meeting is for
            scheduled_by: User scheduling (must be member or admin)
            title: Meeting title
            topic: Discussion topic
            description: Additional description
            scheduled_at: When to meet
            duration: Duration in minutes (15-180)
            meeting_link: Video call link (Zoom, Meet, etc.)
            meeting_timezone: Timezone for the meeting
            create_calendar_events: Whether to create calendar events
            available_members: List of member names who are available for this slot

        Returns:
            Created CircleMeeting with meetingLink
        """
        group = await self._groups_collection.find_one({"_id": ObjectId(group_id)})
        if not group:
            raise NotFoundException(message="Group not found", code="GROUP_NOT_FOUND")

        if group["status"] != "active":
            raise ValidationException(
                message="Group is not active",
                code="GROUP_NOT_ACTIVE"
            )

        has_access = await self._user_has_access(group, scheduled_by)
        if not has_access:
            raise ForbiddenException(
                message="Not authorized to schedule meetings for this group",
                code="NOT_AUTHORIZED"
            )

        if duration < self.MIN_DURATION or duration > self.MAX_DURATION:
            raise ValidationException(
                message=f"Duration must be between {self.MIN_DURATION} and {self.MAX_DURATION} minutes",
                code="INVALID_DURATION"
            )

        now = datetime.now(timezone.utc)

        if scheduled_at:
            if isinstance(scheduled_at, str):
                scheduled_at = datetime.fromisoformat(scheduled_at.replace('Z', '+00:00'))
            if scheduled_at.tzinfo is None:
                scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
            if scheduled_at < now:
                raise ValidationException(
                    message="Cannot schedule meeting in the past",
                    code="INVALID_SCHEDULED_TIME"
                )

        if not title:
            title = f"{group['name']} Meeting"

        # Build attendance list with status based on availability
        # Use group member names (same source as availability endpoint) to avoid mismatches
        available_names_set = set(available_members) if available_members else None
        attendance = []

        for m in group["members"]:
            user_id = m.get("userId") if isinstance(m, dict) else m
            member_name = m.get("name", "") if isinstance(m, dict) else ""

            # Determine status: if we have available_members list, check if user is in it
            if available_names_set is not None:
                status = "pending" if member_name in available_names_set else "declined"
            else:
                status = "pending"

            attendance.append({
                "userId": user_id,
                "status": status,
                "respondedAt": now if status == "declined" else None
            })

        meeting_doc = {
            "groupId": ObjectId(group_id),
            "title": title,
            "description": description,
            "topic": topic,
            "scheduledAt": scheduled_at or (now + timedelta(days=7)),
            "duration": duration,
            "timezone": meeting_timezone,
            "meetingLink": meeting_link,
            "status": "scheduled",
            "scheduledBy": ObjectId(scheduled_by),
            "calendarEvents": [],
            "attendance": attendance,
            "notes": None,
            "reminder24hSent": False,
            "reminder1hSent": False,
            "cancelledAt": None,
            "cancelledBy": None,
            "cancellationReason": None,
            "createdAt": now,
            "updatedAt": now
        }

        result = await self._meetings_collection.insert_one(meeting_doc)
        meeting_doc["_id"] = result.inserted_id

        logger.info(f"Meeting scheduled: {result.inserted_id} for group {group_id}")

        return meeting_doc

    async def get_meeting(self, meeting_id: str) -> Dict[str, Any]:
        """Get meeting by ID."""
        meeting = await self._meetings_collection.find_one({"_id": ObjectId(meeting_id)})
        if not meeting:
            raise NotFoundException(message="Meeting not found", code="MEETING_NOT_FOUND")
        return meeting

    async def get_meetings_for_group(
        self,
        group_id: str,
        upcoming: bool = True,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get meetings for a group."""
        query: Dict[str, Any] = {"groupId": ObjectId(group_id)}

        if upcoming:
            query["scheduledAt"] = {"$gte": datetime.now(timezone.utc)}
            query["status"] = "scheduled"

        cursor = self._meetings_collection.find(query)
        cursor = cursor.sort("scheduledAt", 1 if upcoming else -1)
        cursor = cursor.limit(limit)

        return await cursor.to_list(length=limit)

    async def get_meetings_for_user(
        self,
        user_id: str,
        upcoming: bool = True,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get user's meetings across all groups."""
        groups = await self._groups_collection.find({
            "members": ObjectId(user_id),
            "status": "active"
        }).to_list(length=50)

        group_ids = [g["_id"] for g in groups]

        if not group_ids:
            return []

        query: Dict[str, Any] = {"groupId": {"$in": group_ids}}

        if upcoming:
            query["scheduledAt"] = {"$gte": datetime.now(timezone.utc)}
            query["status"] = "scheduled"

        cursor = self._meetings_collection.find(query)
        cursor = cursor.sort("scheduledAt", 1 if upcoming else -1)
        cursor = cursor.limit(limit)

        return await cursor.to_list(length=limit)

    async def get_next_meeting(self, group_id: str) -> Optional[Dict[str, Any]]:
        """Get next upcoming meeting for a group."""
        meetings = await self.get_meetings_for_group(group_id, upcoming=True, limit=1)
        return meetings[0] if meetings else None

    async def cancel_meeting(
        self,
        meeting_id: str,
        user_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cancel a meeting.

        Side Effects:
            - Updates meeting status
            - Could delete calendar events (if integrated)
        """
        meeting = await self.get_meeting(meeting_id)

        group = await self._groups_collection.find_one({"_id": meeting["groupId"]})
        has_access = await self._user_has_access(group, user_id)

        if not has_access:
            raise ForbiddenException(
                message="Not authorized to cancel this meeting",
                code="NOT_AUTHORIZED"
            )

        if meeting["status"] == "cancelled":
            raise ValidationException(
                message="Meeting is already cancelled",
                code="ALREADY_CANCELLED"
            )

        now = datetime.now(timezone.utc)

        await self._meetings_collection.update_one(
            {"_id": ObjectId(meeting_id)},
            {
                "$set": {
                    "status": "cancelled",
                    "cancelledAt": now,
                    "cancelledBy": ObjectId(user_id),
                    "cancellationReason": reason,
                    "updatedAt": now
                }
            }
        )

        logger.info(f"Meeting {meeting_id} cancelled by user {user_id}")

        return await self.get_meeting(meeting_id)

    async def update_attendance(
        self,
        meeting_id: str,
        user_id: str,
        status: str
    ) -> Dict[str, Any]:
        """
        Update user's attendance status.

        Args:
            status: "accepted" | "declined"
        """
        if status not in ["accepted", "declined"]:
            raise ValidationException(
                message="Status must be 'accepted' or 'declined'",
                code="INVALID_STATUS"
            )

        meeting = await self.get_meeting(meeting_id)

        now = datetime.now(timezone.utc)

        await self._meetings_collection.update_one(
            {
                "_id": ObjectId(meeting_id),
                "attendance.userId": ObjectId(user_id)
            },
            {
                "$set": {
                    "attendance.$.status": status,
                    "attendance.$.respondedAt": now,
                    "updatedAt": now
                }
            }
        )

        return await self.get_meeting(meeting_id)

    async def complete_meeting(
        self,
        meeting_id: str,
        user_id: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Mark meeting as completed with optional notes."""
        meeting = await self.get_meeting(meeting_id)

        group = await self._groups_collection.find_one({"_id": meeting["groupId"]})
        has_access = await self._user_has_access(group, user_id)

        if not has_access:
            raise ForbiddenException(
                message="Not authorized",
                code="NOT_AUTHORIZED"
            )

        now = datetime.now(timezone.utc)

        await self._meetings_collection.update_one(
            {"_id": ObjectId(meeting_id)},
            {
                "$set": {
                    "status": "completed",
                    "notes": notes,
                    "updatedAt": now
                }
            }
        )

        await self._groups_collection.update_one(
            {"_id": meeting["groupId"]},
            {
                "$inc": {
                    "stats.meetingsHeld": 1,
                    "stats.totalMeetingMinutes": meeting["duration"]
                },
                "$set": {
                    "stats.lastMeetingAt": meeting["scheduledAt"],
                    "updatedAt": now
                }
            }
        )

        return await self.get_meeting(meeting_id)

    async def send_reminders(self) -> Dict[str, int]:
        """
        Send meeting reminders (called by cron).

        Returns:
            dict with counts of 24h and 1h reminders sent
        """
        now = datetime.now(timezone.utc)

        reminder_24h_start = now + timedelta(hours=23)
        reminder_24h_end = now + timedelta(hours=24)

        meetings_24h = await self._meetings_collection.find({
            "status": "scheduled",
            "reminder24hSent": False,
            "scheduledAt": {
                "$gte": reminder_24h_start,
                "$lt": reminder_24h_end
            }
        }).to_list(length=100)

        for meeting in meetings_24h:
            await self._meetings_collection.update_one(
                {"_id": meeting["_id"]},
                {"$set": {"reminder24hSent": True}}
            )

        reminder_1h_start = now + timedelta(minutes=45)
        reminder_1h_end = now + timedelta(hours=1)

        meetings_1h = await self._meetings_collection.find({
            "status": "scheduled",
            "reminder1hSent": False,
            "scheduledAt": {
                "$gte": reminder_1h_start,
                "$lt": reminder_1h_end
            }
        }).to_list(length=100)

        for meeting in meetings_1h:
            await self._meetings_collection.update_one(
                {"_id": meeting["_id"]},
                {"$set": {"reminder1hSent": True}}
            )

        return {
            "reminder24h": len(meetings_24h),
            "reminder1h": len(meetings_1h)
        }

    async def _user_has_access(self, group: Dict[str, Any], user_id: str) -> bool:
        """Check if user has access to schedule/modify meetings."""
        member_ids = [m.get("userId") for m in group.get("members", []) if isinstance(m, dict)]
        if ObjectId(user_id) in member_ids:
            return True

        pool = await self._pools_collection.find_one({"_id": group["poolId"]})
        if pool:
            org_members = self._db["organizationmembers"]
            admin = await org_members.find_one({
                "organizationId": pool["organizationId"],
                "userId": ObjectId(user_id),
                "role": "admin"
            })
            return admin is not None

        return False

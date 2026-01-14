"""
Calendar availability calculation service.

Calculates user availability with timezone support and calendar integration.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
import pytz

from app_v2.calendar.services.google_calendar_service import GoogleCalendarService
from app_v2.calendar.services.connection_service import CalendarConnectionService

logger = logging.getLogger(__name__)


class CalendarAvailabilityService:
    """
    Calculates availability from calendars or manual slots.
    Handles cross-timezone calculations for groups.
    """

    DEFAULT_WORKING_START = 9
    DEFAULT_WORKING_END = 18
    DEFAULT_WORK_DAYS = [1, 2, 3, 4, 5]  # Monday-Friday
    DEFAULT_TIMEZONE = "Europe/Stockholm"
    MIN_SLOT_DURATION = 30
    MAX_SUGGESTED_SLOTS = 5
    LOOKAHEAD_DAYS = 14

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        google_calendar: GoogleCalendarService,
        connection_service: CalendarConnectionService
    ):
        """
        Initialize CalendarAvailabilityService.

        Args:
            db: MongoDB database connection
            google_calendar: Google Calendar client
            connection_service: Calendar connection service
        """
        self._db = db
        self._google_calendar = google_calendar
        self._connection_service = connection_service
        self._users_collection = db["users"]
        self._availability_collection = db["userAvailability"]
        self._groups_collection = db["circleGroups"]

    async def get_user_availability(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        min_duration: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Get availability for a single user.

        Args:
            user_id: User's ID
            start_date: Start of range
            end_date: End of range
            min_duration: Minimum slot duration in minutes

        Returns:
            List of free slots: [{ start, end, duration }]
        """
        working_hours = await self.get_user_working_hours(user_id)

        access_token = await self._connection_service.get_valid_access_token(user_id)

        if access_token:
            return await self._get_calendar_availability(
                user_id, access_token, start_date, end_date, working_hours, min_duration
            )
        else:
            return await self._get_manual_availability(
                user_id, start_date, end_date, working_hours, min_duration
            )

    async def get_user_working_hours(self, user_id: str) -> Dict[str, Any]:
        """
        Get user's configured working hours.

        Args:
            user_id: User's ID

        Returns:
            dict with startHour, endHour, workDays, timezone
        """
        user = await self._users_collection.find_one(
            {"_id": ObjectId(user_id)},
            {"settings.workingHours": 1, "profile.timezone": 1}
        )

        if not user:
            return self._default_working_hours()

        settings = user.get("settings", {})
        working_hours = settings.get("workingHours", {})

        return {
            "startHour": working_hours.get("startHour", self.DEFAULT_WORKING_START),
            "endHour": working_hours.get("endHour", self.DEFAULT_WORKING_END),
            "workDays": working_hours.get("workDays", self.DEFAULT_WORK_DAYS),
            "timezone": working_hours.get("timezone") or user.get("profile", {}).get("timezone", self.DEFAULT_TIMEZONE),
        }

    def _default_working_hours(self) -> Dict[str, Any]:
        """Get default working hours."""
        return {
            "startHour": self.DEFAULT_WORKING_START,
            "endHour": self.DEFAULT_WORKING_END,
            "workDays": self.DEFAULT_WORK_DAYS,
            "timezone": self.DEFAULT_TIMEZONE,
        }

    async def _get_calendar_availability(
        self,
        user_id: str,
        access_token: str,
        start_date: datetime,
        end_date: datetime,
        working_hours: Dict[str, Any],
        min_duration: int
    ) -> List[Dict[str, Any]]:
        """Get availability from connected calendar."""
        connection = await self._connection_service.get_connection(user_id)
        if not connection or not connection.get("calendarIds"):
            return []

        busy_slots = await self._google_calendar.get_free_busy(
            access_token=access_token,
            calendar_ids=connection["calendarIds"],
            time_min=start_date,
            time_max=end_date
        )

        return self._calculate_free_slots(
            start_date, end_date, busy_slots, working_hours, min_duration
        )

    async def _get_manual_availability(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        working_hours: Dict[str, Any],
        min_duration: int
    ) -> List[Dict[str, Any]]:
        """Get availability from manual weekly slots."""
        manual = await self._availability_collection.find_one({"userId": ObjectId(user_id)})

        if not manual or not manual.get("slots"):
            return self._calculate_free_slots(
                start_date, end_date, [], working_hours, min_duration
            )

        user_tz = pytz.timezone(working_hours["timezone"])
        free_slots = []

        current = start_date
        while current < end_date:
            local_time = current.astimezone(user_tz)
            day_of_week = local_time.weekday()

            for slot in manual["slots"]:
                if slot["day"] == day_of_week:
                    slot_start = local_time.replace(
                        hour=slot["hour"],
                        minute=0,
                        second=0,
                        microsecond=0
                    )
                    slot_end = slot_start + timedelta(hours=1)

                    if slot_start >= start_date and slot_end <= end_date:
                        free_slots.append({
                            "start": slot_start.astimezone(timezone.utc),
                            "end": slot_end.astimezone(timezone.utc),
                            "duration": 60,
                        })

            current += timedelta(days=1)

        return self._merge_adjacent_slots(free_slots, min_duration)

    def _calculate_free_slots(
        self,
        start_date: datetime,
        end_date: datetime,
        busy_slots: List[Dict[str, Any]],
        working_hours: Dict[str, Any],
        min_duration: int
    ) -> List[Dict[str, Any]]:
        """Calculate free slots from busy periods and working hours."""
        user_tz = pytz.timezone(working_hours["timezone"])
        free_slots = []

        current = start_date
        while current < end_date:
            local_time = current.astimezone(user_tz)
            day_of_week = local_time.weekday()

            if day_of_week not in working_hours["workDays"]:
                current += timedelta(days=1)
                current = current.replace(hour=0, minute=0, second=0, microsecond=0)
                continue

            day_start = local_time.replace(
                hour=working_hours["startHour"],
                minute=0,
                second=0,
                microsecond=0
            )
            day_end = local_time.replace(
                hour=working_hours["endHour"],
                minute=0,
                second=0,
                microsecond=0
            )

            day_start_utc = day_start.astimezone(timezone.utc)
            day_end_utc = day_end.astimezone(timezone.utc)

            if day_start_utc < start_date:
                day_start_utc = start_date
            if day_end_utc > end_date:
                day_end_utc = end_date

            day_busy = [
                s for s in busy_slots
                if s["end"] > day_start_utc and s["start"] < day_end_utc
            ]
            day_busy.sort(key=lambda x: x["start"])

            slot_start = day_start_utc
            for busy in day_busy:
                if busy["start"] > slot_start:
                    duration = int((busy["start"] - slot_start).total_seconds() / 60)
                    if duration >= min_duration:
                        free_slots.append({
                            "start": slot_start,
                            "end": busy["start"],
                            "duration": duration,
                        })
                slot_start = max(slot_start, busy["end"])

            if slot_start < day_end_utc:
                duration = int((day_end_utc - slot_start).total_seconds() / 60)
                if duration >= min_duration:
                    free_slots.append({
                        "start": slot_start,
                        "end": day_end_utc,
                        "duration": duration,
                    })

            current += timedelta(days=1)
            current = current.replace(hour=0, minute=0, second=0, microsecond=0)

        return free_slots

    def _merge_adjacent_slots(
        self,
        slots: List[Dict[str, Any]],
        min_duration: int
    ) -> List[Dict[str, Any]]:
        """Merge adjacent time slots."""
        if not slots:
            return []

        sorted_slots = sorted(slots, key=lambda x: x["start"])
        merged = [sorted_slots[0].copy()]

        for slot in sorted_slots[1:]:
            last = merged[-1]
            if slot["start"] <= last["end"]:
                last["end"] = max(last["end"], slot["end"])
                last["duration"] = int((last["end"] - last["start"]).total_seconds() / 60)
            else:
                merged.append(slot.copy())

        return [s for s in merged if s["duration"] >= min_duration]

    async def find_group_availability(
        self,
        group_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        min_duration: int = 60,
        max_slots: int = 5
    ) -> Dict[str, Any]:
        """
        Find common availability across group members.

        Args:
            group_id: Group ID
            start_date: Start of range (default: now)
            end_date: End of range (default: now + LOOKAHEAD_DAYS)
            min_duration: Minimum slot duration
            max_slots: Maximum slots to return

        Returns:
            dict with slots, stats
        """
        group = await self._groups_collection.find_one({"_id": ObjectId(group_id)})
        if not group:
            return {
                "slots": [],
                "totalFound": 0,
                "usersWithCalendar": 0,
                "usersWithManual": 0,
                "errors": [],
            }

        member_ids = [str(m) for m in group.get("members", [])]

        if not start_date:
            start_date = datetime.now(timezone.utc)
        if not end_date:
            end_date = start_date + timedelta(days=self.LOOKAHEAD_DAYS)

        all_availabilities = []
        users_with_calendar = 0
        users_with_manual = 0
        errors = []

        for user_id in member_ids:
            try:
                connection = await self._connection_service.get_connection(user_id)
                if connection and connection.get("status") == "active":
                    users_with_calendar += 1
                else:
                    users_with_manual += 1

                availability = await self.get_user_availability(
                    user_id, start_date, end_date, min_duration
                )
                all_availabilities.append(availability)

            except Exception as e:
                logger.error(f"Failed to get availability for user {user_id}: {e}")
                errors.append(user_id)
                all_availabilities.append([])

        if not all_availabilities or all(not a for a in all_availabilities):
            return {
                "slots": [],
                "totalFound": 0,
                "usersWithCalendar": users_with_calendar,
                "usersWithManual": users_with_manual,
                "errors": errors,
            }

        common_slots = all_availabilities[0]
        for availability in all_availabilities[1:]:
            if availability:
                common_slots = self.intersect_slots(common_slots, availability, min_duration)

        scored_slots = [(slot, self.score_slot(slot)) for slot in common_slots]
        scored_slots.sort(key=lambda x: -x[1])

        top_slots = [slot for slot, _ in scored_slots[:max_slots]]

        return {
            "slots": top_slots,
            "totalFound": len(common_slots),
            "usersWithCalendar": users_with_calendar,
            "usersWithManual": users_with_manual,
            "errors": errors,
        }

    def intersect_slots(
        self,
        slots_a: List[Dict[str, Any]],
        slots_b: List[Dict[str, Any]],
        min_duration: int
    ) -> List[Dict[str, Any]]:
        """
        Find intersection of two slot lists.

        Args:
            slots_a: First list of slots
            slots_b: Second list of slots
            min_duration: Minimum overlap required

        Returns:
            List of overlapping slots
        """
        if not slots_a or not slots_b:
            return []

        intersections = []

        for a in slots_a:
            for b in slots_b:
                start = max(a["start"], b["start"])
                end = min(a["end"], b["end"])

                if start < end:
                    duration = int((end - start).total_seconds() / 60)
                    if duration >= min_duration:
                        intersections.append({
                            "start": start,
                            "end": end,
                            "duration": duration,
                        })

        return intersections

    def convert_to_timezone(
        self,
        slots: List[Dict[str, Any]],
        target_tz: str
    ) -> List[Dict[str, Any]]:
        """
        Convert slots to a target timezone for display.

        Args:
            slots: Slots with start/end datetimes
            target_tz: Target timezone

        Returns:
            Slots with converted times
        """
        tz = pytz.timezone(target_tz)
        converted = []

        for slot in slots:
            converted.append({
                "start": slot["start"].astimezone(tz),
                "end": slot["end"].astimezone(tz),
                "duration": slot["duration"],
            })

        return converted

    def score_slot(self, slot: Dict[str, Any]) -> int:
        """
        Score a slot for sorting preference.

        Args:
            slot: Slot with start, end, duration

        Returns:
            Score (higher = better)
        """
        score = 0

        hour = slot["start"].hour
        if 10 <= hour <= 14:
            score += 100
        elif 9 <= hour <= 16:
            score += 50

        day = slot["start"].weekday()
        if day in (0, 1, 2):
            score += 30

        score += slot["duration"]

        return score

    async def check_slot_available(
        self,
        user_id: str,
        start: datetime,
        end: datetime
    ) -> bool:
        """
        Check if a specific slot is still available.

        Args:
            user_id: User's ID
            start: Slot start time
            end: Slot end time

        Returns:
            True if slot is free
        """
        duration = int((end - start).total_seconds() / 60)
        availability = await self.get_user_availability(user_id, start, end, duration)

        for slot in availability:
            if slot["start"] <= start and slot["end"] >= end:
                return True

        return False

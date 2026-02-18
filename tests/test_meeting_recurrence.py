"""Unit tests for recurring meeting logic in MeetingService."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
from bson import ObjectId

from app_v2.services.circles.meeting_service import MeetingService


# ─────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_meeting_db():
    db = MagicMock()
    meetings_col = AsyncMock()
    groups_col = AsyncMock()
    pools_col = AsyncMock()
    db.__getitem__ = MagicMock(side_effect=lambda key: {
        "circlemeetings": meetings_col,
        "circlegroups": groups_col,
        "circlepools": pools_col,
    }.get(key, AsyncMock()))
    return db, meetings_col, groups_col


@pytest.fixture
def meeting_service(mock_meeting_db):
    db, _, _ = mock_meeting_db
    return MeetingService(db)


@pytest.fixture
def recurring_meeting():
    """A weekly recurring meeting starting 3 weeks ago."""
    start = datetime.now(timezone.utc) - timedelta(weeks=3)
    # Normalize to the same hour
    start = start.replace(hour=14, minute=0, second=0, microsecond=0)
    return {
        "_id": ObjectId(),
        "groupId": ObjectId(),
        "title": "Weekly Standup",
        "scheduledAt": start,
        "duration": 60,
        "timezone": "Europe/Stockholm",
        "meetingLink": "https://meet.google.com/abc",
        "status": "scheduled",
        "recurrence": True,
        "frequency": "weekly",
        "skippedDates": [],
        "attendance": [],
    }


@pytest.fixture
def biweekly_meeting():
    """A biweekly recurring meeting starting 2 weeks ago."""
    start = datetime.now(timezone.utc) - timedelta(weeks=2)
    start = start.replace(hour=10, minute=0, second=0, microsecond=0)
    return {
        "_id": ObjectId(),
        "groupId": ObjectId(),
        "title": "Biweekly Review",
        "scheduledAt": start,
        "duration": 60,
        "timezone": "Europe/Stockholm",
        "meetingLink": "https://meet.google.com/xyz",
        "status": "scheduled",
        "recurrence": True,
        "frequency": "biweekly",
        "skippedDates": [],
        "attendance": [],
    }


@pytest.fixture
def non_recurring_meeting():
    """A standard one-off meeting."""
    return {
        "_id": ObjectId(),
        "groupId": ObjectId(),
        "title": "One-off Meeting",
        "scheduledAt": datetime.now(timezone.utc) + timedelta(days=2),
        "duration": 60,
        "status": "scheduled",
        "recurrence": False,
        "attendance": [],
    }


@pytest.fixture
def old_meeting_no_field():
    """Old meeting document without recurrence field (backward compat)."""
    return {
        "_id": ObjectId(),
        "groupId": ObjectId(),
        "title": "Legacy Meeting",
        "scheduledAt": datetime.now(timezone.utc) + timedelta(days=1),
        "duration": 60,
        "status": "scheduled",
        "attendance": [],
    }


# ─────────────────────────────────────────────────────────────────
# get_upcoming_occurrences
# ─────────────────────────────────────────────────────────────────


class TestGetUpcomingOccurrences:
    def test_weekly_returns_future_dates(self, meeting_service, recurring_meeting):
        results = meeting_service.get_upcoming_occurrences(recurring_meeting, count=4)

        assert len(results) == 4
        # All results should be in the future
        now = datetime.now(timezone.utc)
        for dt in results:
            assert dt > now
        # Each should be 7 days apart
        for i in range(1, len(results)):
            diff = results[i] - results[i - 1]
            assert diff == timedelta(weeks=1)

    def test_biweekly_returns_correct_interval(self, meeting_service, biweekly_meeting):
        results = meeting_service.get_upcoming_occurrences(biweekly_meeting, count=3)

        assert len(results) == 3
        for i in range(1, len(results)):
            diff = results[i] - results[i - 1]
            assert diff == timedelta(weeks=2)

    def test_skipped_dates_are_excluded(self, meeting_service, recurring_meeting):
        # Get first two upcoming dates, then skip the first one
        all_dates = meeting_service.get_upcoming_occurrences(recurring_meeting, count=2)
        skip_date = all_dates[0].strftime("%Y-%m-%d")
        recurring_meeting["skippedDates"] = [skip_date]

        results = meeting_service.get_upcoming_occurrences(recurring_meeting, count=2)

        # The skipped date should not be in results
        result_dates = [r.strftime("%Y-%m-%d") for r in results]
        assert skip_date not in result_dates
        assert len(results) == 2

    def test_non_recurring_returns_empty(self, meeting_service, non_recurring_meeting):
        results = meeting_service.get_upcoming_occurrences(non_recurring_meeting, count=4)
        assert results == []

    def test_old_meeting_without_field_returns_empty(self, meeting_service, old_meeting_no_field):
        results = meeting_service.get_upcoming_occurrences(old_meeting_no_field, count=4)
        assert results == []


# ─────────────────────────────────────────────────────────────────
# skip_occurrence
# ─────────────────────────────────────────────────────────────────


class TestSkipOccurrence:
    @pytest.mark.asyncio
    async def test_adds_date_to_skipped_dates(
        self, meeting_service, mock_meeting_db, recurring_meeting,
    ):
        _, meetings_col, groups_col = mock_meeting_db
        meetings_col.find_one.return_value = recurring_meeting
        groups_col.find_one.return_value = {
            "_id": recurring_meeting["groupId"],
            "poolId": ObjectId(),
            "members": [{"userId": ObjectId()}],
            "status": "active",
        }

        user_id = str(recurring_meeting["attendance"][0]["userId"]) if recurring_meeting["attendance"] else str(ObjectId())
        # Patch _user_has_access to return True
        meeting_service._user_has_access = AsyncMock(return_value=True)

        await meeting_service.skip_occurrence(
            meeting_id=str(recurring_meeting["_id"]),
            date="2026-03-01",
            user_id=user_id,
        )

        meetings_col.update_one.assert_called_once()
        call_args = meetings_col.update_one.call_args[0]
        assert call_args[1]["$addToSet"]["skippedDates"] == "2026-03-01"

    @pytest.mark.asyncio
    async def test_rejects_non_recurring_meeting(
        self, meeting_service, mock_meeting_db, non_recurring_meeting,
    ):
        _, meetings_col, _ = mock_meeting_db
        meetings_col.find_one.return_value = non_recurring_meeting
        meeting_service._user_has_access = AsyncMock(return_value=True)

        from common.utils.exceptions import ValidationException
        with pytest.raises(ValidationException):
            await meeting_service.skip_occurrence(
                meeting_id=str(non_recurring_meeting["_id"]),
                date="2026-03-01",
                user_id=str(ObjectId()),
            )


# ─────────────────────────────────────────────────────────────────
# decline_occurrence (user-level, single occurrence)
# ─────────────────────────────────────────────────────────────────


class TestDeclineOccurrence:
    @pytest.mark.asyncio
    async def test_adds_date_to_user_declined_occurrences(
        self, meeting_service, mock_meeting_db, recurring_meeting,
    ):
        _, meetings_col, _ = mock_meeting_db
        user_id = ObjectId()
        recurring_meeting["attendance"] = [
            {"userId": user_id, "status": "pending", "declinedOccurrences": []},
        ]
        meetings_col.find_one.return_value = recurring_meeting
        meetings_col.update_one.return_value = MagicMock(modified_count=1)

        await meeting_service.decline_occurrence(
            meeting_id=str(recurring_meeting["_id"]),
            date="2026-03-15",
            user_id=str(user_id),
        )

        meetings_col.update_one.assert_called_once()
        call_args = meetings_col.update_one.call_args[0]
        assert call_args[1]["$addToSet"]["attendance.$.declinedOccurrences"] == "2026-03-15"

    @pytest.mark.asyncio
    async def test_pushes_new_entry_when_no_attendance_match(
        self, meeting_service, mock_meeting_db, recurring_meeting,
    ):
        _, meetings_col, _ = mock_meeting_db
        user_id = ObjectId()
        recurring_meeting["attendance"] = []  # no entry for this user
        meetings_col.find_one.return_value = recurring_meeting
        # First call: positional update finds no match
        # Second call: push new entry
        meetings_col.update_one.side_effect = [
            MagicMock(modified_count=0),
            MagicMock(modified_count=1),
        ]

        await meeting_service.decline_occurrence(
            meeting_id=str(recurring_meeting["_id"]),
            date="2026-03-15",
            user_id=str(user_id),
        )

        assert meetings_col.update_one.call_count == 2
        push_args = meetings_col.update_one.call_args_list[1][0]
        pushed_entry = push_args[1]["$push"]["attendance"]
        assert pushed_entry["userId"] == ObjectId(str(user_id))
        assert pushed_entry["declinedOccurrences"] == ["2026-03-15"]

    @pytest.mark.asyncio
    async def test_rejects_non_recurring_meeting(
        self, meeting_service, mock_meeting_db, non_recurring_meeting,
    ):
        _, meetings_col, _ = mock_meeting_db
        meetings_col.find_one.return_value = non_recurring_meeting

        from common.utils.exceptions import ValidationException
        with pytest.raises(ValidationException):
            await meeting_service.decline_occurrence(
                meeting_id=str(non_recurring_meeting["_id"]),
                date="2026-03-15",
                user_id=str(ObjectId()),
            )


# ─────────────────────────────────────────────────────────────────
# update_attendance (push-if-no-match)
# ─────────────────────────────────────────────────────────────────


class TestUpdateAttendance:
    @pytest.mark.asyncio
    async def test_updates_existing_attendance_entry(
        self, meeting_service, mock_meeting_db, non_recurring_meeting,
    ):
        _, meetings_col, _ = mock_meeting_db
        user_id = ObjectId()
        non_recurring_meeting["attendance"] = [
            {"userId": user_id, "status": "pending", "respondedAt": None},
        ]
        meetings_col.find_one.return_value = non_recurring_meeting
        meetings_col.update_one.return_value = MagicMock(modified_count=1)

        await meeting_service.update_attendance(
            meeting_id=str(non_recurring_meeting["_id"]),
            user_id=str(user_id),
            status="declined",
        )

        meetings_col.update_one.assert_called_once()
        call_args = meetings_col.update_one.call_args[0]
        assert call_args[1]["$set"]["attendance.$.status"] == "declined"

    @pytest.mark.asyncio
    async def test_pushes_new_entry_when_no_attendance_match(
        self, meeting_service, mock_meeting_db, non_recurring_meeting,
    ):
        _, meetings_col, _ = mock_meeting_db
        user_id = ObjectId()
        non_recurring_meeting["attendance"] = []  # no entry for this user
        meetings_col.find_one.return_value = non_recurring_meeting
        meetings_col.update_one.side_effect = [
            MagicMock(modified_count=0),
            MagicMock(modified_count=1),
        ]

        await meeting_service.update_attendance(
            meeting_id=str(non_recurring_meeting["_id"]),
            user_id=str(user_id),
            status="declined",
        )

        assert meetings_col.update_one.call_count == 2
        push_args = meetings_col.update_one.call_args_list[1][0]
        pushed_entry = push_args[1]["$push"]["attendance"]
        assert pushed_entry["userId"] == ObjectId(str(user_id))
        assert pushed_entry["status"] == "declined"


# ─────────────────────────────────────────────────────────────────
# schedule_meeting with recurrence
# ─────────────────────────────────────────────────────────────────


class TestScheduleMeetingRecurrence:
    @pytest.mark.asyncio
    async def test_stores_recurrence_fields(self, meeting_service, mock_meeting_db):
        _, meetings_col, groups_col = mock_meeting_db
        groups_col.find_one.return_value = {
            "_id": ObjectId(),
            "status": "active",
            "poolId": ObjectId(),
            "members": [{"userId": ObjectId()}],
        }
        meetings_col.insert_one.return_value = MagicMock(inserted_id=ObjectId())
        meeting_service._user_has_access = AsyncMock(return_value=True)

        future_time = datetime.now(timezone.utc) + timedelta(days=1)
        result = await meeting_service.schedule_meeting(
            group_id=str(ObjectId()),
            scheduled_by=str(ObjectId()),
            title="Weekly Standup",
            scheduled_at=future_time,
            recurrence=True,
            frequency="weekly",
        )

        insert_doc = meetings_col.insert_one.call_args[0][0]
        assert insert_doc["recurrence"] is True
        assert insert_doc["frequency"] == "weekly"
        assert insert_doc["skippedDates"] == []

    @pytest.mark.asyncio
    async def test_defaults_recurrence_to_false(self, meeting_service, mock_meeting_db):
        _, meetings_col, groups_col = mock_meeting_db
        groups_col.find_one.return_value = {
            "_id": ObjectId(),
            "status": "active",
            "poolId": ObjectId(),
            "members": [{"userId": ObjectId()}],
        }
        meetings_col.insert_one.return_value = MagicMock(inserted_id=ObjectId())
        meeting_service._user_has_access = AsyncMock(return_value=True)

        future_time = datetime.now(timezone.utc) + timedelta(days=1)
        result = await meeting_service.schedule_meeting(
            group_id=str(ObjectId()),
            scheduled_by=str(ObjectId()),
            title="One-off",
            scheduled_at=future_time,
        )

        insert_doc = meetings_col.insert_one.call_args[0][0]
        assert insert_doc["recurrence"] is False
        assert insert_doc.get("frequency") is None

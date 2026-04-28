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
def user_id():
    return str(ObjectId())


@pytest.fixture
def recurring_meeting(user_id):
    """A weekly recurring meeting starting 3 weeks ago."""
    start = datetime.now(timezone.utc) - timedelta(weeks=3)
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
        "skippedOccurrences": [],
        "attendance": [
            {"userId": ObjectId(user_id), "status": "invited", "respondedAt": None},
        ],
    }


@pytest.fixture
def biweekly_meeting(user_id):
    """A biweekly recurring meeting starting 6 weeks ago."""
    start = datetime.now(timezone.utc) - timedelta(weeks=6)
    start = start.replace(hour=10, minute=0, second=0, microsecond=0)
    return {
        "_id": ObjectId(),
        "groupId": ObjectId(),
        "title": "Biweekly Review",
        "scheduledAt": start,
        "duration": 60,
        "status": "scheduled",
        "recurrence": True,
        "frequency": "biweekly",
        "skippedOccurrences": [],
        "attendance": [
            {"userId": ObjectId(user_id), "status": "invited", "respondedAt": None},
        ],
    }


@pytest.fixture
def monthly_meeting(user_id):
    """A monthly recurring meeting starting 3 months ago."""
    start = datetime.now(timezone.utc) - timedelta(weeks=12)
    start = start.replace(hour=9, minute=0, second=0, microsecond=0)
    return {
        "_id": ObjectId(),
        "groupId": ObjectId(),
        "title": "Monthly Retro",
        "scheduledAt": start,
        "duration": 60,
        "status": "scheduled",
        "recurrence": True,
        "frequency": "monthly",
        "skippedOccurrences": [],
        "attendance": [
            {"userId": ObjectId(user_id), "status": "invited", "respondedAt": None},
        ],
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
            "members": [{"userId": ObjectId(), "name": "Alice"}],
        }
        meetings_col.insert_one.return_value = MagicMock(inserted_id=ObjectId())
        meeting_service._user_has_access = AsyncMock(return_value=True)

        future_time = datetime.now(timezone.utc) + timedelta(days=1)
        await meeting_service.schedule_meeting(
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
        assert insert_doc["skippedOccurrences"] == []

    @pytest.mark.asyncio
    async def test_defaults_recurrence_to_false(self, meeting_service, mock_meeting_db):
        _, meetings_col, groups_col = mock_meeting_db
        groups_col.find_one.return_value = {
            "_id": ObjectId(),
            "status": "active",
            "poolId": ObjectId(),
            "members": [{"userId": ObjectId(), "name": "Alice"}],
        }
        meetings_col.insert_one.return_value = MagicMock(inserted_id=ObjectId())
        meeting_service._user_has_access = AsyncMock(return_value=True)

        future_time = datetime.now(timezone.utc) + timedelta(days=1)
        await meeting_service.schedule_meeting(
            group_id=str(ObjectId()),
            scheduled_by=str(ObjectId()),
            title="One-off",
            scheduled_at=future_time,
        )

        insert_doc = meetings_col.insert_one.call_args[0][0]
        assert insert_doc["recurrence"] is False
        assert insert_doc.get("frequency") is None


# ─────────────────────────────────────────────────────────────────
# compute_upcoming_occurrences
# ─────────────────────────────────────────────────────────────────


class TestComputeUpcomingOccurrences:
    def test_weekly_returns_future_dates(self, meeting_service, recurring_meeting, user_id):
        results = meeting_service.compute_upcoming_occurrences(recurring_meeting, user_id)

        assert len(results) == 2
        now = datetime.now(timezone.utc)
        for occ in results:
            assert occ["date"] > now
            assert occ["skipped"] is False
        # Should be 7 days apart
        diff = results[1]["date"] - results[0]["date"]
        assert diff == timedelta(weeks=1)

    def test_biweekly_returns_correct_interval(self, meeting_service, biweekly_meeting, user_id):
        results = meeting_service.compute_upcoming_occurrences(biweekly_meeting, user_id)

        assert len(results) == 2
        diff = results[1]["date"] - results[0]["date"]
        assert diff == timedelta(weeks=2)

    def test_monthly_returns_future_dates(self, meeting_service, monthly_meeting, user_id):
        results = meeting_service.compute_upcoming_occurrences(monthly_meeting, user_id)

        assert len(results) == 2
        now = datetime.now(timezone.utc)
        for occ in results:
            assert occ["date"] > now
        # Roughly 28-31 days apart
        diff = (results[1]["date"] - results[0]["date"]).days
        assert 28 <= diff <= 31

    def test_non_recurring_returns_empty(self, meeting_service, non_recurring_meeting, user_id):
        results = meeting_service.compute_upcoming_occurrences(non_recurring_meeting, user_id)
        assert results == []

    def test_old_doc_without_field_returns_empty(self, meeting_service, old_meeting_no_field, user_id):
        results = meeting_service.compute_upcoming_occurrences(old_meeting_no_field, user_id)
        assert results == []

    def test_skipped_dates_marked(self, meeting_service, recurring_meeting, user_id):
        # First get the upcoming dates
        all_dates = meeting_service.compute_upcoming_occurrences(recurring_meeting, user_id)
        skip_date = all_dates[0]["date"].strftime("%Y-%m-%d")

        # Add a skip for this user on that date
        recurring_meeting["skippedOccurrences"] = [
            {"userId": ObjectId(user_id), "date": skip_date}
        ]

        results = meeting_service.compute_upcoming_occurrences(recurring_meeting, user_id)

        assert len(results) == 2
        # First result should be the skipped one, marked as skipped
        assert results[0]["date"].strftime("%Y-%m-%d") == skip_date
        assert results[0]["skipped"] is True
        # Second result should not be skipped
        assert results[1]["skipped"] is False


# ─────────────────────────────────────────────────────────────────
# skip_occurrence
# ─────────────────────────────────────────────────────────────────


class TestSkipOccurrence:
    @pytest.mark.asyncio
    async def test_adds_to_skipped_occurrences(
        self, meeting_service, mock_meeting_db, recurring_meeting, user_id,
    ):
        _, meetings_col, _ = mock_meeting_db
        meetings_col.find_one.return_value = recurring_meeting

        await meeting_service.skip_occurrence(
            meeting_id=str(recurring_meeting["_id"]),
            user_id=user_id,
            date="2026-03-01",
        )

        meetings_col.update_one.assert_called_once()
        call_args = meetings_col.update_one.call_args[0]
        pushed = call_args[1]["$push"]["skippedOccurrences"]
        assert pushed["userId"] == ObjectId(user_id)
        assert pushed["date"] == "2026-03-01"

    @pytest.mark.asyncio
    async def test_rejects_non_recurring(
        self, meeting_service, mock_meeting_db, non_recurring_meeting, user_id,
    ):
        _, meetings_col, _ = mock_meeting_db
        meetings_col.find_one.return_value = non_recurring_meeting

        from common.utils.exceptions import ValidationException
        with pytest.raises(ValidationException):
            await meeting_service.skip_occurrence(
                meeting_id=str(non_recurring_meeting["_id"]),
                user_id=user_id,
                date="2026-03-01",
            )

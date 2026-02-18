"""Unit tests for group message pipeline functions."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from bson import ObjectId

from app_v2.pipelines.group_messages import (
    send_group_message,
    list_group_messages,
)


# ─────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────


@pytest.fixture
def sample_group_id():
    return str(ObjectId())


@pytest.fixture
def mock_message_service():
    service = AsyncMock()
    return service


@pytest.fixture
def mock_group_service():
    service = AsyncMock()
    return service


@pytest.fixture
def mock_notification_service():
    service = AsyncMock()
    return service


@pytest.fixture
def mock_email_service():
    service = AsyncMock()
    return service


@pytest.fixture
def member_ids():
    """Fixed ObjectIds for group members (excluding sender)."""
    return [ObjectId(), ObjectId()]


@pytest.fixture
def sample_group_doc(sample_group_id, sample_user_id, member_ids):
    """A group with 3 members. First member is the sender."""
    return {
        "_id": ObjectId(sample_group_id),
        "name": "Engineering Leaders",
        "poolId": ObjectId(),
        "members": [
            {"userId": ObjectId(sample_user_id), "name": "Anna Svensson"},
            {"userId": member_ids[0], "name": "Erik Lindqvist"},
            {"userId": member_ids[1], "name": "Maria Karlsson"},
        ],
        "status": "active",
    }


@pytest.fixture
def mock_users_collection(member_ids):
    """Mock users collection that returns user docs with emails."""
    async def _find_one(query):
        uid = query.get("_id")
        if uid == member_ids[0]:
            return {"_id": uid, "email": "erik@example.com", "profile": {"firstName": "Erik"}}
        if uid == member_ids[1]:
            return {"_id": uid, "email": "maria@example.com", "profile": {"firstName": "Maria"}}
        return None

    collection = AsyncMock()
    collection.find_one = AsyncMock(side_effect=_find_one)
    return collection


@pytest.fixture
def mock_pipeline_db(mock_users_collection):
    """Mock db that returns the users collection."""
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=mock_users_collection)
    return db


@pytest.fixture
def sample_saved_message(sample_user_id, sample_group_id):
    now = datetime.now(timezone.utc)
    return {
        "id": str(ObjectId()),
        "groupId": sample_group_id,
        "userId": sample_user_id,
        "userName": "Anna Svensson",
        "content": "Let's focus on week 7",
        "createdAt": now.isoformat(),
    }


# ─────────────────────────────────────────────────────────────────
# send_group_message
# ─────────────────────────────────────────────────────────────────


class TestSendGroupMessage:
    @pytest.mark.asyncio
    async def test_saves_message_and_returns_it(
        self,
        mock_message_service,
        mock_group_service,
        mock_notification_service,
        mock_email_service,
        mock_pipeline_db,
        sample_user_id,
        sample_group_id,
        sample_group_doc,
        sample_saved_message,
    ):
        mock_group_service.user_has_group_access.return_value = True
        mock_group_service.get_group.return_value = sample_group_doc
        mock_message_service.create_message.return_value = sample_saved_message

        result = await send_group_message(
            message_service=mock_message_service,
            group_service=mock_group_service,
            notification_service=mock_notification_service,
            email_service=mock_email_service,
            db=mock_pipeline_db,
            user_id=sample_user_id,
            group_id=sample_group_id,
            content="Let's focus on week 7",
        )

        mock_message_service.create_message.assert_called_once()
        assert result["content"] == "Let's focus on week 7"

    @pytest.mark.asyncio
    async def test_creates_notifications_for_other_members(
        self,
        mock_message_service,
        mock_group_service,
        mock_notification_service,
        mock_email_service,
        mock_pipeline_db,
        sample_user_id,
        sample_group_id,
        sample_group_doc,
        sample_saved_message,
    ):
        mock_group_service.user_has_group_access.return_value = True
        mock_group_service.get_group.return_value = sample_group_doc
        mock_message_service.create_message.return_value = sample_saved_message

        await send_group_message(
            message_service=mock_message_service,
            group_service=mock_group_service,
            notification_service=mock_notification_service,
            email_service=mock_email_service,
            db=mock_pipeline_db,
            user_id=sample_user_id,
            group_id=sample_group_id,
            content="Let's focus on week 7",
        )

        # 3 members - 1 sender = 2 notifications
        assert mock_notification_service.create_notification.call_count == 2

    @pytest.mark.asyncio
    async def test_does_not_notify_sender(
        self,
        mock_message_service,
        mock_group_service,
        mock_notification_service,
        mock_email_service,
        mock_pipeline_db,
        sample_user_id,
        sample_group_id,
        sample_group_doc,
        sample_saved_message,
    ):
        mock_group_service.user_has_group_access.return_value = True
        mock_group_service.get_group.return_value = sample_group_doc
        mock_message_service.create_message.return_value = sample_saved_message

        await send_group_message(
            message_service=mock_message_service,
            group_service=mock_group_service,
            notification_service=mock_notification_service,
            email_service=mock_email_service,
            db=mock_pipeline_db,
            user_id=sample_user_id,
            group_id=sample_group_id,
            content="Let's focus on week 7",
        )

        # Check no notification was created for the sender
        for call in mock_notification_service.create_notification.call_args_list:
            assert call.kwargs.get("user_id") != sample_user_id

    @pytest.mark.asyncio
    async def test_raises_forbidden_when_not_member(
        self,
        mock_message_service,
        mock_group_service,
        mock_notification_service,
        mock_email_service,
        mock_pipeline_db,
        sample_group_id,
    ):
        mock_group_service.user_has_group_access.return_value = False
        non_member_id = str(ObjectId())

        from common.utils.exceptions import ForbiddenException

        with pytest.raises(ForbiddenException):
            await send_group_message(
                message_service=mock_message_service,
                group_service=mock_group_service,
                notification_service=mock_notification_service,
                email_service=mock_email_service,
                db=mock_pipeline_db,
                user_id=non_member_id,
                group_id=sample_group_id,
                content="Hello",
            )

        mock_message_service.create_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_notification_failure_does_not_block_message(
        self,
        mock_message_service,
        mock_group_service,
        mock_notification_service,
        mock_email_service,
        mock_pipeline_db,
        sample_user_id,
        sample_group_id,
        sample_group_doc,
        sample_saved_message,
    ):
        mock_group_service.user_has_group_access.return_value = True
        mock_group_service.get_group.return_value = sample_group_doc
        mock_message_service.create_message.return_value = sample_saved_message
        mock_notification_service.create_notification.side_effect = Exception("DB down")

        # Should not raise — message still returned
        result = await send_group_message(
            message_service=mock_message_service,
            group_service=mock_group_service,
            notification_service=mock_notification_service,
            email_service=mock_email_service,
            db=mock_pipeline_db,
            user_id=sample_user_id,
            group_id=sample_group_id,
            content="Let's focus on week 7",
        )

        assert result["content"] == "Let's focus on week 7"

    @pytest.mark.asyncio
    async def test_email_failure_does_not_block_message(
        self,
        mock_message_service,
        mock_group_service,
        mock_notification_service,
        mock_email_service,
        mock_pipeline_db,
        sample_user_id,
        sample_group_id,
        sample_group_doc,
        sample_saved_message,
    ):
        mock_group_service.user_has_group_access.return_value = True
        mock_group_service.get_group.return_value = sample_group_doc
        mock_message_service.create_message.return_value = sample_saved_message
        mock_email_service.send_group_message_email.side_effect = Exception("SMTP fail")

        result = await send_group_message(
            message_service=mock_message_service,
            group_service=mock_group_service,
            notification_service=mock_notification_service,
            email_service=mock_email_service,
            db=mock_pipeline_db,
            user_id=sample_user_id,
            group_id=sample_group_id,
            content="Let's focus on week 7",
        )

        assert result["content"] == "Let's focus on week 7"

    @pytest.mark.asyncio
    async def test_sends_emails_to_other_members(
        self,
        mock_message_service,
        mock_group_service,
        mock_notification_service,
        mock_email_service,
        mock_pipeline_db,
        sample_user_id,
        sample_group_id,
        sample_group_doc,
        sample_saved_message,
    ):
        mock_group_service.user_has_group_access.return_value = True
        mock_group_service.get_group.return_value = sample_group_doc
        mock_message_service.create_message.return_value = sample_saved_message

        await send_group_message(
            message_service=mock_message_service,
            group_service=mock_group_service,
            notification_service=mock_notification_service,
            email_service=mock_email_service,
            db=mock_pipeline_db,
            user_id=sample_user_id,
            group_id=sample_group_id,
            content="Let's focus on week 7",
        )

        # 3 members - 1 sender = 2 emails
        assert mock_email_service.send_group_message_email.call_count == 2
        # Verify emails were sent to the right addresses
        email_calls = mock_email_service.send_group_message_email.call_args_list
        sent_emails = {call.kwargs["to_email"] for call in email_calls}
        assert sent_emails == {"erik@example.com", "maria@example.com"}


# ─────────────────────────────────────────────────────────────────
# list_group_messages
# ─────────────────────────────────────────────────────────────────


class TestListGroupMessages:
    @pytest.mark.asyncio
    async def test_returns_messages_and_pagination(
        self,
        mock_message_service,
        mock_group_service,
        sample_user_id,
        sample_group_id,
        sample_saved_message,
    ):
        mock_group_service.user_has_group_access.return_value = True
        mock_message_service.get_messages.return_value = [sample_saved_message]
        mock_message_service.get_message_count.return_value = 1

        result = await list_group_messages(
            message_service=mock_message_service,
            group_service=mock_group_service,
            user_id=sample_user_id,
            group_id=sample_group_id,
        )

        assert len(result["messages"]) == 1
        assert result["total"] == 1
        assert result["hasMore"] is False

    @pytest.mark.asyncio
    async def test_has_more_when_total_exceeds_page(
        self,
        mock_message_service,
        mock_group_service,
        sample_user_id,
        sample_group_id,
        sample_saved_message,
    ):
        mock_group_service.user_has_group_access.return_value = True
        mock_message_service.get_messages.return_value = [sample_saved_message]
        mock_message_service.get_message_count.return_value = 100

        result = await list_group_messages(
            message_service=mock_message_service,
            group_service=mock_group_service,
            user_id=sample_user_id,
            group_id=sample_group_id,
            limit=50,
            offset=0,
        )

        assert result["hasMore"] is True

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_messages(
        self,
        mock_message_service,
        mock_group_service,
        sample_user_id,
        sample_group_id,
    ):
        mock_group_service.user_has_group_access.return_value = True
        mock_message_service.get_messages.return_value = []
        mock_message_service.get_message_count.return_value = 0

        result = await list_group_messages(
            message_service=mock_message_service,
            group_service=mock_group_service,
            user_id=sample_user_id,
            group_id=sample_group_id,
        )

        assert result["messages"] == []
        assert result["total"] == 0
        assert result["hasMore"] is False

    @pytest.mark.asyncio
    async def test_raises_forbidden_when_not_member(
        self,
        mock_message_service,
        mock_group_service,
        sample_group_id,
    ):
        mock_group_service.user_has_group_access.return_value = False
        non_member_id = str(ObjectId())

        from common.utils.exceptions import ForbiddenException

        with pytest.raises(ForbiddenException):
            await list_group_messages(
                message_service=mock_message_service,
                group_service=mock_group_service,
                user_id=non_member_id,
                group_id=sample_group_id,
            )

        mock_message_service.get_messages.assert_not_called()

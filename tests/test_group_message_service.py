"""Unit tests for GroupMessageService (embedded array + encryption pattern)."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from bson import ObjectId

from app_v2.services.circles.message_service import GroupMessageService


# ─────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_messages_collection():
    collection = AsyncMock()
    return collection


@pytest.fixture
def mock_msg_db(mock_messages_collection):
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=mock_messages_collection)
    return db


@pytest.fixture
def sample_group_id():
    return str(ObjectId())


@pytest.fixture
def service_no_encryption(mock_msg_db):
    return GroupMessageService(mock_msg_db)


@pytest.fixture
def service_with_encryption(mock_msg_db, mock_encryption_service):
    return GroupMessageService(mock_msg_db, encryption_service=mock_encryption_service)


@pytest.fixture
def sample_group_doc(sample_group_id, sample_user_id):
    """A group messages document with embedded messages array."""
    now = datetime.now(timezone.utc)
    return {
        "_id": ObjectId(),
        "groupId": ObjectId(sample_group_id),
        "messages": [
            {
                "messageId": "msg_abc123",
                "userId": ObjectId(sample_user_id),
                "userName": "Anna Svensson",
                "content": "encrypted:Let's focus on week 7",
                "encrypted": True,
                "createdAt": now,
            },
            {
                "messageId": "msg_def456",
                "userId": ObjectId(),
                "userName": "Erik Lindqvist",
                "content": "encrypted:Sounds good!",
                "encrypted": True,
                "createdAt": now,
            },
        ],
        "createdAt": now,
        "updatedAt": now,
    }


# ─────────────────────────────────────────────────────────────────
# create_message
# ─────────────────────────────────────────────────────────────────


class TestCreateMessage:
    @pytest.mark.asyncio
    async def test_upserts_message_into_embedded_array(
        self, service_with_encryption, mock_messages_collection,
        sample_user_id, sample_group_id,
    ):
        await service_with_encryption.create_message(
            group_id=sample_group_id,
            user_id=sample_user_id,
            user_name="Anna Svensson",
            content="Let's focus on week 7",
        )

        mock_messages_collection.update_one.assert_called_once()
        call_args = mock_messages_collection.update_one.call_args
        # First arg is the filter
        assert call_args[0][0] == {"groupId": ObjectId(sample_group_id)}
        # Second arg is the update doc
        update = call_args[0][1]
        assert "$push" in update
        assert "$set" in update
        assert "$setOnInsert" in update
        # Upsert should be True
        assert call_args[1]["upsert"] is True

    @pytest.mark.asyncio
    async def test_encrypts_content_when_service_available(
        self, service_with_encryption, mock_messages_collection,
        mock_encryption_service, sample_user_id, sample_group_id,
    ):
        await service_with_encryption.create_message(
            group_id=sample_group_id,
            user_id=sample_user_id,
            user_name="Anna Svensson",
            content="Secret message",
        )

        mock_encryption_service.encrypt.assert_called_once_with("Secret message")
        # Check the pushed message has encrypted content
        update = mock_messages_collection.update_one.call_args[0][1]
        pushed_msg = update["$push"]["messages"]
        assert pushed_msg["content"] == "encrypted:Secret message"
        assert pushed_msg["encrypted"] is True

    @pytest.mark.asyncio
    async def test_stores_plaintext_without_encryption_service(
        self, service_no_encryption, mock_messages_collection,
        sample_user_id, sample_group_id,
    ):
        await service_no_encryption.create_message(
            group_id=sample_group_id,
            user_id=sample_user_id,
            user_name="Anna Svensson",
            content="Plain message",
        )

        update = mock_messages_collection.update_one.call_args[0][1]
        pushed_msg = update["$push"]["messages"]
        assert pushed_msg["content"] == "Plain message"
        assert pushed_msg["encrypted"] is False

    @pytest.mark.asyncio
    async def test_returns_plaintext_to_caller(
        self, service_with_encryption, mock_messages_collection,
        sample_user_id, sample_group_id,
    ):
        result = await service_with_encryption.create_message(
            group_id=sample_group_id,
            user_id=sample_user_id,
            user_name="Anna Svensson",
            content="Let's focus on week 7",
        )

        assert result["content"] == "Let's focus on week 7"
        assert result["userName"] == "Anna Svensson"
        assert "id" in result
        assert result["id"].startswith("msg_")

    @pytest.mark.asyncio
    async def test_rejects_empty_content(
        self, service_with_encryption, sample_user_id, sample_group_id,
    ):
        with pytest.raises(Exception):
            await service_with_encryption.create_message(
                group_id=sample_group_id,
                user_id=sample_user_id,
                user_name="Anna Svensson",
                content="",
            )

    @pytest.mark.asyncio
    async def test_rejects_whitespace_only_content(
        self, service_with_encryption, sample_user_id, sample_group_id,
    ):
        with pytest.raises(Exception):
            await service_with_encryption.create_message(
                group_id=sample_group_id,
                user_id=sample_user_id,
                user_name="Anna Svensson",
                content="   ",
            )

    @pytest.mark.asyncio
    async def test_rejects_content_over_500_chars(
        self, service_with_encryption, sample_user_id, sample_group_id,
    ):
        with pytest.raises(Exception):
            await service_with_encryption.create_message(
                group_id=sample_group_id,
                user_id=sample_user_id,
                user_name="Anna Svensson",
                content="A" * 501,
            )


# ─────────────────────────────────────────────────────────────────
# get_messages
# ─────────────────────────────────────────────────────────────────


class TestGetMessages:
    @pytest.mark.asyncio
    async def test_returns_decrypted_messages(
        self, service_with_encryption, mock_messages_collection,
        sample_group_doc, sample_group_id,
    ):
        mock_messages_collection.find_one.return_value = sample_group_doc

        result = await service_with_encryption.get_messages(group_id=sample_group_id)

        assert len(result) == 2
        assert result[0]["content"] == "Let's focus on week 7"
        assert result[1]["content"] == "Sounds good!"
        assert result[0]["userName"] == "Anna Svensson"

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_document(
        self, service_with_encryption, mock_messages_collection, sample_group_id,
    ):
        mock_messages_collection.find_one.return_value = None

        result = await service_with_encryption.get_messages(group_id=sample_group_id)

        assert result == []

    @pytest.mark.asyncio
    async def test_applies_offset_and_limit(
        self, service_with_encryption, mock_messages_collection,
        sample_group_doc, sample_group_id,
    ):
        mock_messages_collection.find_one.return_value = sample_group_doc

        # Offset=1, limit=1 should return only the second message
        result = await service_with_encryption.get_messages(
            group_id=sample_group_id, limit=1, offset=1,
        )

        assert len(result) == 1
        assert result[0]["userName"] == "Erik Lindqvist"


# ─────────────────────────────────────────────────────────────────
# get_message_count
# ─────────────────────────────────────────────────────────────────


class TestGetMessageCount:
    @pytest.mark.asyncio
    async def test_returns_correct_count(
        self, service_with_encryption, mock_messages_collection,
        sample_group_doc, sample_group_id,
    ):
        mock_messages_collection.find_one.return_value = sample_group_doc

        result = await service_with_encryption.get_message_count(sample_group_id)

        assert result == 2

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_document(
        self, service_with_encryption, mock_messages_collection, sample_group_id,
    ):
        mock_messages_collection.find_one.return_value = None

        result = await service_with_encryption.get_message_count(sample_group_id)

        assert result == 0

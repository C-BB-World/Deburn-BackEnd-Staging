"""Unit tests for conversation pipeline functions."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId

from app_v2.pipelines.conversation import (
    get_or_create_conversation,
    list_conversation_summaries,
    delete_conversation_by_id,
    rename_conversation,
    _format_conversation,
)


# ─────────────────────────────────────────────────────────────────
# get_or_create_conversation
# ─────────────────────────────────────────────────────────────────


class TestGetOrCreateConversation:
    @pytest.mark.asyncio
    async def test_creates_new_with_title_from_first_message(
        self, mock_db, mock_collection, mock_encryption_service, sample_user_id
    ):
        mock_collection.find_one.return_value = None
        mock_collection.insert_one.return_value = MagicMock(inserted_id=ObjectId())

        result = await get_or_create_conversation(
            db=mock_db,
            encryption_service=mock_encryption_service,
            conversation_id=None,
            user_id=sample_user_id,
            first_message="How can I improve my leadership skills?",
        )

        # Verify the inserted doc had a title
        insert_call = mock_collection.insert_one.call_args[0][0]
        assert insert_call["title"] == "How can I improve my leadership skills?"

    @pytest.mark.asyncio
    async def test_title_truncated_to_50_chars(
        self, mock_db, mock_collection, mock_encryption_service, sample_user_id
    ):
        mock_collection.find_one.return_value = None
        mock_collection.insert_one.return_value = MagicMock(inserted_id=ObjectId())

        long_message = "A" * 100
        result = await get_or_create_conversation(
            db=mock_db,
            encryption_service=mock_encryption_service,
            conversation_id=None,
            user_id=sample_user_id,
            first_message=long_message,
        )

        insert_call = mock_collection.insert_one.call_args[0][0]
        assert len(insert_call["title"]) == 50

    @pytest.mark.asyncio
    async def test_title_none_when_first_message_omitted(
        self, mock_db, mock_collection, mock_encryption_service, sample_user_id
    ):
        mock_collection.find_one.return_value = None
        mock_collection.insert_one.return_value = MagicMock(inserted_id=ObjectId())

        result = await get_or_create_conversation(
            db=mock_db,
            encryption_service=mock_encryption_service,
            conversation_id=None,
            user_id=sample_user_id,
        )

        insert_call = mock_collection.insert_one.call_args[0][0]
        assert insert_call.get("title") is None

    @pytest.mark.asyncio
    async def test_existing_conversation_returned_unchanged(
        self, mock_db, mock_collection, mock_encryption_service, sample_user_id, sample_conversation_doc
    ):
        mock_collection.find_one.return_value = sample_conversation_doc

        result = await get_or_create_conversation(
            db=mock_db,
            encryption_service=mock_encryption_service,
            conversation_id=sample_conversation_doc["conversationId"],
            user_id=sample_user_id,
        )

        mock_collection.insert_one.assert_not_called()
        assert result["conversationId"] == sample_conversation_doc["conversationId"]
        assert result["title"] == "How can I improve my leadership"


# ─────────────────────────────────────────────────────────────────
# list_conversation_summaries
# ─────────────────────────────────────────────────────────────────


class TestListConversationSummaries:
    @staticmethod
    def _make_cursor(docs):
        """Create a mock Motor cursor (sync chaining, async to_list)."""
        cursor = MagicMock()
        cursor.sort.return_value = cursor
        cursor.skip.return_value = cursor
        cursor.limit.return_value = cursor
        cursor.to_list = AsyncMock(return_value=docs)
        return cursor

    @pytest.mark.asyncio
    async def test_returns_summaries_without_messages(
        self, mock_db, mock_collection, sample_user_id, sample_conversation_doc
    ):
        mock_collection.find.return_value = self._make_cursor([sample_conversation_doc])
        mock_collection.count_documents.return_value = 1

        result = await list_conversation_summaries(
            db=mock_db, user_id=sample_user_id, skip=0, limit=20
        )

        assert len(result["conversations"]) == 1
        summary = result["conversations"][0]
        assert "messages" not in summary
        assert summary["messageCount"] == 2
        assert summary["title"] == "How can I improve my leadership"

    @pytest.mark.asyncio
    async def test_pagination_has_more(
        self, mock_db, mock_collection, sample_user_id, sample_conversation_doc
    ):
        mock_collection.find.return_value = self._make_cursor([sample_conversation_doc])
        mock_collection.count_documents.return_value = 25

        result = await list_conversation_summaries(
            db=mock_db, user_id=sample_user_id, skip=0, limit=20
        )

        assert result["total"] == 25
        assert result["hasMore"] is True

    @pytest.mark.asyncio
    async def test_pagination_no_more(
        self, mock_db, mock_collection, sample_user_id, sample_conversation_doc
    ):
        mock_collection.find.return_value = self._make_cursor([sample_conversation_doc])
        mock_collection.count_documents.return_value = 1

        result = await list_conversation_summaries(
            db=mock_db, user_id=sample_user_id, skip=0, limit=20
        )

        assert result["hasMore"] is False

    @pytest.mark.asyncio
    async def test_old_doc_without_title_returns_none(
        self, mock_db, mock_collection, sample_user_id, sample_conversation_doc_no_title
    ):
        mock_collection.find.return_value = self._make_cursor([sample_conversation_doc_no_title])
        mock_collection.count_documents.return_value = 1

        result = await list_conversation_summaries(
            db=mock_db, user_id=sample_user_id, skip=0, limit=20
        )

        assert result["conversations"][0]["title"] is None


# ─────────────────────────────────────────────────────────────────
# delete_conversation_by_id
# ─────────────────────────────────────────────────────────────────


class TestDeleteConversationById:
    @pytest.mark.asyncio
    async def test_delete_existing_returns_true(
        self, mock_db, mock_collection, sample_user_id
    ):
        mock_collection.delete_one.return_value = MagicMock(deleted_count=1)

        result = await delete_conversation_by_id(
            db=mock_db,
            conversation_id="conv_123",
            user_id=sample_user_id,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(
        self, mock_db, mock_collection, sample_user_id
    ):
        mock_collection.delete_one.return_value = MagicMock(deleted_count=0)

        result = await delete_conversation_by_id(
            db=mock_db,
            conversation_id="conv_nonexistent",
            user_id=sample_user_id,
        )

        assert result is False


# ─────────────────────────────────────────────────────────────────
# rename_conversation
# ─────────────────────────────────────────────────────────────────


class TestRenameConversation:
    @pytest.mark.asyncio
    async def test_rename_existing_returns_id_and_title(
        self, mock_db, mock_collection, sample_user_id
    ):
        mock_collection.update_one.return_value = MagicMock(matched_count=1)

        result = await rename_conversation(
            db=mock_db,
            conversation_id="conv_123",
            user_id=sample_user_id,
            title="New Title",
        )

        assert result == {"id": "conv_123", "title": "New Title"}

    @pytest.mark.asyncio
    async def test_rename_nonexistent_returns_none(
        self, mock_db, mock_collection, sample_user_id
    ):
        mock_collection.update_one.return_value = MagicMock(matched_count=0)

        result = await rename_conversation(
            db=mock_db,
            conversation_id="conv_nonexistent",
            user_id=sample_user_id,
            title="New Title",
        )

        assert result is None


# ─────────────────────────────────────────────────────────────────
# _format_conversation
# ─────────────────────────────────────────────────────────────────


class TestFormatConversation:
    def test_includes_title_when_present(
        self, mock_encryption_service, sample_conversation_doc
    ):
        result = _format_conversation(sample_conversation_doc, mock_encryption_service)

        assert result["title"] == "How can I improve my leadership"

    def test_title_none_for_old_docs(
        self, mock_encryption_service, sample_conversation_doc_no_title
    ):
        result = _format_conversation(sample_conversation_doc_no_title, mock_encryption_service)

        assert result["title"] is None

    def test_preserves_all_existing_keys(
        self, mock_encryption_service, sample_conversation_doc
    ):
        result = _format_conversation(sample_conversation_doc, mock_encryption_service)

        assert "id" in result
        assert "conversationId" in result
        assert "userId" in result
        assert "messages" in result
        assert "topics" in result
        assert "status" in result
        assert "lastMessageAt" in result
        assert "createdAt" in result

"""Tests for coach streaming error handling and partial-save logic."""

import json
import pytest
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch


@dataclass
class FakeChunk:
    """Mirrors CoachResponseChunk for test purposes."""
    type: str
    content: Any


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _collect_sse(generator):
    """Drain an async generator and return a list of SSE data-line strings."""
    events = []
    async for raw in generator:
        if raw.startswith("data: "):
            payload = raw[len("data: "):].strip()
            events.append(json.loads(payload))
    return events


def _make_mock_chat(*chunks, error=None):
    """
    Return an async-generator factory that yields *chunks* then optionally
    raises *error*.  Designed to replace coach_service.chat().
    """
    async def _stream(**kwargs):
        for c in chunks:
            yield c
        if error:
            raise error
    return _stream


CONVERSATION_ID = "conv_test_123"
USER_ID = "user_abc"


@pytest.fixture
def fake_conversation():
    return {
        "conversationId": CONVERSATION_ID,
        "messages": [],
    }


@pytest.fixture
def body():
    body = MagicMock()
    body.message = "Hello coach"
    body.conversationId = CONVERSATION_ID
    body.language = "en"
    body.context = {}
    return body


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCoachStreamErrorHandling:
    """Tests for the except-Exception block in generate()."""

    @pytest.mark.asyncio
    async def test_happy_path_no_error_event(self, fake_conversation, body):
        """Normal stream completes without an error event."""
        chunks = [
            FakeChunk(type="text", content="Hello "),
            FakeChunk(type="text", content="there!"),
            FakeChunk(type="metadata", content={"topics": ["greeting"], "commitment": None}),
        ]

        mock_coach = MagicMock()
        mock_coach.chat = MagicMock(return_value=_make_mock_chat(*chunks)())

        mock_save = AsyncMock()
        mock_update_topics = AsyncMock()
        mock_db = MagicMock()
        mock_enc = MagicMock()

        with patch("app_v2.routers.coach.conversation_pipeline") as mock_pipeline:
            mock_pipeline.get_or_create_conversation = AsyncMock(return_value=fake_conversation)
            mock_pipeline.save_message = mock_save
            mock_pipeline.update_topics = mock_update_topics

            from app_v2.routers.coach import send_message

            response = await send_message(
                body=body,
                user={"_id": "user_abc"},
                coach_service=mock_coach,
                hub_db=mock_db,
                encryption_service=mock_enc,
            )

            events = await _collect_sse(response.body_iterator)

        # No error events
        error_events = [e for e in events if e.get("type") == "error"]
        assert error_events == []

        # Text was streamed
        text_events = [e for e in events if e["type"] == "text"]
        assert len(text_events) == 2

        # Assistant message saved (non-partial)
        save_calls = [c for c in mock_save.call_args_list if c.kwargs.get("role") == "assistant" or (c.args and len(c.args) > 3 and c.args[3] == "assistant")]
        # Using keyword args in the pipeline call
        assistant_saves = [
            c for c in mock_save.call_args_list
            if c.kwargs.get("role") == "assistant"
        ]
        assert len(assistant_saves) == 1
        assert assistant_saves[0].kwargs["content"] == "Hello there!"
        assert assistant_saves[0].kwargs.get("metadata", {}).get("partial") is None

    @pytest.mark.asyncio
    async def test_api_error_emits_error_event(self, fake_conversation, body):
        """When the Claude API raises mid-stream, an error SSE event is emitted."""
        chunks = [
            FakeChunk(type="text", content="Partial "),
        ]

        mock_coach = MagicMock()
        mock_coach.chat = MagicMock(
            return_value=_make_mock_chat(*chunks, error=RuntimeError("API rate limited"))()
        )

        mock_save = AsyncMock()
        mock_db = MagicMock()
        mock_enc = MagicMock()

        with patch("app_v2.routers.coach.conversation_pipeline") as mock_pipeline:
            mock_pipeline.get_or_create_conversation = AsyncMock(return_value=fake_conversation)
            mock_pipeline.save_message = mock_save

            from app_v2.routers.coach import send_message

            response = await send_message(
                body=body,
                user={"_id": USER_ID},
                coach_service=mock_coach,
                hub_db=mock_db,
                encryption_service=mock_enc,
            )

            events = await _collect_sse(response.body_iterator)

        error_events = [e for e in events if e.get("type") == "error"]
        assert len(error_events) == 1
        assert error_events[0]["retryable"] is True
        assert error_events[0]["content"] == "Stream failed"

    @pytest.mark.asyncio
    async def test_api_error_saves_partial_response(self, fake_conversation, body):
        """When error occurs after some text, partial response is saved."""
        chunks = [
            FakeChunk(type="text", content="Some partial "),
            FakeChunk(type="text", content="content"),
        ]

        mock_coach = MagicMock()
        mock_coach.chat = MagicMock(
            return_value=_make_mock_chat(*chunks, error=Exception("timeout"))()
        )

        mock_save = AsyncMock()
        mock_db = MagicMock()
        mock_enc = MagicMock()

        with patch("app_v2.routers.coach.conversation_pipeline") as mock_pipeline:
            mock_pipeline.get_or_create_conversation = AsyncMock(return_value=fake_conversation)
            mock_pipeline.save_message = mock_save

            from app_v2.routers.coach import send_message

            response = await send_message(
                body=body,
                user={"_id": USER_ID},
                coach_service=mock_coach,
                hub_db=mock_db,
                encryption_service=mock_enc,
            )

            await _collect_sse(response.body_iterator)

        # Find the assistant save call
        assistant_saves = [
            c for c in mock_save.call_args_list
            if c.kwargs.get("role") == "assistant"
        ]
        assert len(assistant_saves) == 1
        assert assistant_saves[0].kwargs["content"] == "Some partial content"
        assert assistant_saves[0].kwargs["metadata"]["partial"] is True

    @pytest.mark.asyncio
    async def test_api_error_no_content_skips_save(self, fake_conversation, body):
        """When error occurs before any text, no assistant message is saved."""
        mock_coach = MagicMock()
        mock_coach.chat = MagicMock(
            return_value=_make_mock_chat(error=Exception("immediate failure"))()
        )

        mock_save = AsyncMock()
        mock_db = MagicMock()
        mock_enc = MagicMock()

        with patch("app_v2.routers.coach.conversation_pipeline") as mock_pipeline:
            mock_pipeline.get_or_create_conversation = AsyncMock(return_value=fake_conversation)
            mock_pipeline.save_message = mock_save

            from app_v2.routers.coach import send_message

            response = await send_message(
                body=body,
                user={"_id": USER_ID},
                coach_service=mock_coach,
                hub_db=mock_db,
                encryption_service=mock_enc,
            )

            events = await _collect_sse(response.body_iterator)

        # Error event still emitted
        error_events = [e for e in events if e.get("type") == "error"]
        assert len(error_events) == 1

        # No assistant save (only the user message save from before generate())
        assistant_saves = [
            c for c in mock_save.call_args_list
            if c.kwargs.get("role") == "assistant"
        ]
        assert len(assistant_saves) == 0

    @pytest.mark.asyncio
    async def test_error_event_format(self, fake_conversation, body):
        """Error event JSON has exactly the expected fields."""
        mock_coach = MagicMock()
        mock_coach.chat = MagicMock(
            return_value=_make_mock_chat(error=ValueError("bad"))()
        )

        mock_save = AsyncMock()
        mock_db = MagicMock()
        mock_enc = MagicMock()

        with patch("app_v2.routers.coach.conversation_pipeline") as mock_pipeline:
            mock_pipeline.get_or_create_conversation = AsyncMock(return_value=fake_conversation)
            mock_pipeline.save_message = mock_save

            from app_v2.routers.coach import send_message

            response = await send_message(
                body=body,
                user={"_id": USER_ID},
                coach_service=mock_coach,
                hub_db=mock_db,
                encryption_service=mock_enc,
            )

            events = await _collect_sse(response.body_iterator)

        error_event = [e for e in events if e.get("type") == "error"][0]
        assert set(error_event.keys()) == {"type", "content", "retryable"}
        assert error_event["type"] == "error"
        assert isinstance(error_event["content"], str)
        assert error_event["retryable"] is True

    @pytest.mark.asyncio
    async def test_client_disconnect_no_error_event(self, fake_conversation, body):
        """ConnectionResetError (client disconnect) does NOT emit an error event."""
        chunks = [
            FakeChunk(type="text", content="Before disconnect"),
        ]

        mock_coach = MagicMock()
        mock_coach.chat = MagicMock(
            return_value=_make_mock_chat(*chunks, error=ConnectionResetError())()
        )

        mock_save = AsyncMock()
        mock_db = MagicMock()
        mock_enc = MagicMock()

        with patch("app_v2.routers.coach.conversation_pipeline") as mock_pipeline:
            mock_pipeline.get_or_create_conversation = AsyncMock(return_value=fake_conversation)
            mock_pipeline.save_message = mock_save

            from app_v2.routers.coach import send_message

            response = await send_message(
                body=body,
                user={"_id": USER_ID},
                coach_service=mock_coach,
                hub_db=mock_db,
                encryption_service=mock_enc,
            )

            events = await _collect_sse(response.body_iterator)

        # No error event — client disconnects are silent
        error_events = [e for e in events if e.get("type") == "error"]
        assert error_events == []

        # But partial content IS still saved
        assistant_saves = [
            c for c in mock_save.call_args_list
            if c.kwargs.get("role") == "assistant"
        ]
        assert len(assistant_saves) == 1
        assert assistant_saves[0].kwargs["metadata"]["partial"] is True

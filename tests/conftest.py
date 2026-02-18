"""Shared test fixtures for Deburn backend tests."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId


@pytest.fixture
def sample_user_id():
    return str(ObjectId())


@pytest.fixture
def mock_encryption_service():
    service = MagicMock()
    service.encrypt = MagicMock(side_effect=lambda text: f"encrypted:{text}")
    service.decrypt = MagicMock(side_effect=lambda text: text.replace("encrypted:", "") if text.startswith("encrypted:") else None)
    return service


@pytest.fixture
def mock_collection():
    collection = AsyncMock()
    # Motor's find() returns a cursor synchronously (not a coroutine),
    # so use MagicMock for it. Async methods like find_one, insert_one,
    # count_documents etc. stay as AsyncMock.
    collection.find = MagicMock()
    return collection


@pytest.fixture
def mock_db(mock_collection):
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=mock_collection)
    return db


@pytest.fixture
def sample_conversation_doc(sample_user_id):
    now = datetime.now(timezone.utc)
    return {
        "_id": ObjectId(),
        "conversationId": "conv_20260218120000_abc12345",
        "userId": ObjectId(sample_user_id),
        "title": "How can I improve my leadership",
        "messages": [
            {
                "role": "user",
                "content": "encrypted:How can I improve my leadership skills?",
                "encrypted": True,
                "language": "en",
                "timestamp": now,
                "metadata": {},
                "translations": {},
            },
            {
                "role": "assistant",
                "content": "encrypted:Great question! Let me share some strategies.",
                "encrypted": True,
                "language": "en",
                "timestamp": now,
                "metadata": {},
                "translations": {},
            },
        ],
        "topics": ["leadership"],
        "status": "active",
        "lastMessageAt": now,
        "createdAt": now,
        "updatedAt": now,
    }


@pytest.fixture
def sample_conversation_doc_no_title(sample_conversation_doc):
    """Old-format document without a title field."""
    doc = dict(sample_conversation_doc)
    doc.pop("title", None)
    return doc

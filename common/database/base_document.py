"""
Base document class with common fields for all models.

Provides created_at and updated_at timestamps that are automatically
managed. Extend this class for your application-specific models.

Example:
    from common.database import BaseDocument

    class User(BaseDocument):
        email: str
        name: str

        class Settings:
            name = "users"  # MongoDB collection name
"""

from datetime import datetime, timezone
from typing import Optional
from beanie import Document
from pydantic import Field


def _utcnow() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class BaseDocument(Document):
    """
    Base document with common fields.

    All documents extending this class will have:
    - created_at: Timestamp when document was created
    - updated_at: Timestamp when document was last modified

    Use Beanie's state management for automatic tracking of changes.
    """

    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        use_state_management = True

    async def save(self, *args, **kwargs):
        """Override save to automatically update updated_at timestamp."""
        self.updated_at = _utcnow()
        return await super().save(*args, **kwargs)

    async def update(self, *args, **kwargs):
        """Override update to automatically update updated_at timestamp."""
        # Ensure updated_at is included in updates
        if args and isinstance(args[0], dict):
            if "$set" in args[0]:
                args[0]["$set"]["updated_at"] = _utcnow()
            else:
                args = ({"$set": {"updated_at": _utcnow()}, **args[0]},) + args[1:]
        return await super().update(*args, **kwargs)

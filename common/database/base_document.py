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

import logging
from datetime import datetime, timezone
from typing import Optional
from beanie import Document
from pydantic import Field

logger = logging.getLogger(__name__)


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
        collection_name = self.Settings.name if hasattr(self.Settings, "name") else self.__class__.__name__
        logger.debug(f"Saving document to {collection_name}: {self.id}")
        try:
            result = await super().save(*args, **kwargs)
            logger.debug(f"Document saved successfully: {self.id}")
            return result
        except Exception as e:
            logger.error(f"Failed to save document to {collection_name}: {e}")
            raise

    async def update(self, *args, **kwargs):
        """Override update to automatically update updated_at timestamp."""
        # Ensure updated_at is included in updates
        if args and isinstance(args[0], dict):
            if "$set" in args[0]:
                args[0]["$set"]["updated_at"] = _utcnow()
            else:
                args = ({"$set": {"updated_at": _utcnow()}, **args[0]},) + args[1:]
        collection_name = self.Settings.name if hasattr(self.Settings, "name") else self.__class__.__name__
        logger.debug(f"Updating document in {collection_name}: {self.id}")
        try:
            result = await super().update(*args, **kwargs)
            logger.debug(f"Document updated successfully: {self.id}")
            return result
        except Exception as e:
            logger.error(f"Failed to update document in {collection_name}: {e}")
            raise

"""
FastAPI dependencies for Content system.

Provides dependency injection for content-related services.
"""

import os
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app_v2.content.services.content_service import ContentService
from app_v2.content.services.learning_progress_service import LearningProgressService


_content_service: Optional[ContentService] = None
_learning_progress_service: Optional[LearningProgressService] = None


def init_content_services(db: AsyncIOMotorDatabase) -> None:
    """
    Initialize content services with database connection.

    Called once at application startup.

    Args:
        db: MongoDB database connection
    """
    global _content_service, _learning_progress_service

    source_type = os.getenv("CONTENT_SOURCE_TYPE", "file")
    filepath = os.getenv("CONTENT_FILEPATH")

    _content_service = ContentService(
        source_type=source_type,
        filepath=filepath,
        db=db if source_type == "database" else None
    )

    _learning_progress_service = LearningProgressService(db=db)


def get_content_service() -> ContentService:
    """Get content service instance."""
    if _content_service is None:
        raise RuntimeError("Content services not initialized.")
    return _content_service


def get_learning_progress_service() -> LearningProgressService:
    """Get learning progress service instance."""
    if _learning_progress_service is None:
        raise RuntimeError("Content services not initialized.")
    return _learning_progress_service

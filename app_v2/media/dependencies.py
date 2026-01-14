"""
FastAPI dependencies for Media system.

Provides dependency injection for media-related services.
"""

from typing import Optional, Dict, Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app_v2.media.services.tts_service import TTSService
from app_v2.media.services.image_service import ImageService


_tts_service: Optional[TTSService] = None
_image_service: Optional[ImageService] = None


def init_media_services(
    db: AsyncIOMotorDatabase,
    tts_config: Optional[Dict[str, Any]] = None,
    image_config: Optional[Dict[str, Any]] = None
) -> None:
    """
    Initialize media services with database connection.

    Called once at application startup.

    Args:
        db: MongoDB database connection
        tts_config: Optional TTS service configuration
        image_config: Optional image service configuration
    """
    global _tts_service, _image_service

    _tts_service = TTSService(db=db, config=tts_config)
    _image_service = ImageService(db=db, config=image_config)


def get_tts_service() -> TTSService:
    """Get TTS service instance."""
    if _tts_service is None:
        raise RuntimeError("Media services not initialized.")
    return _tts_service


def get_image_service() -> ImageService:
    """Get image service instance."""
    if _image_service is None:
        raise RuntimeError("Media services not initialized.")
    return _image_service

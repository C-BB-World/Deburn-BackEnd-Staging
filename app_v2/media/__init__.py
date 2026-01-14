"""
Media Services System.

Provides AI-powered media generation including text-to-speech (ElevenLabs)
and image generation (FAL.ai).
"""

from app_v2.media.services.tts_service import TTSService
from app_v2.media.services.image_service import ImageService
from app_v2.media.dependencies import (
    init_media_services,
    get_tts_service,
    get_image_service,
)
from app_v2.media.router import router

__all__ = [
    "TTSService",
    "ImageService",
    "init_media_services",
    "get_tts_service",
    "get_image_service",
    "router",
]

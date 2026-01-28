"""
Voice module for AI agent.

Re-exports TTSService from media services.
"""

from app_v2.services.media.tts_service import TTSService

__all__ = ["TTSService"]

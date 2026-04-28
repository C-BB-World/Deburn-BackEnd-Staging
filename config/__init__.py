"""
Configuration module - Base settings and app-specific configs.
"""

from config.base_settings import BaseAppSettings
from config.tts_config import VOICE_MAPPINGS, TTS_DEFAULTS

__all__ = ["BaseAppSettings", "VOICE_MAPPINGS", "TTS_DEFAULTS"]

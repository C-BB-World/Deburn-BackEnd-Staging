"""
BrainBank application settings.

Extends the base settings with BrainBank-specific configuration.
"""

from typing import Optional
from common.config import BaseAppSettings


class Settings(BaseAppSettings):
    """BrainBank-specific settings."""

    # ==========================================================================
    # Secondary Database (Hub)
    # ==========================================================================
    HUB_MONGODB_URI: Optional[str] = None
    HUB_MONGODB_DATABASE: str = "brainbank_hub"

    # ==========================================================================
    # External Services
    # ==========================================================================
    # ElevenLabs TTS
    ELEVENLABS_API_KEY: Optional[str] = None
    ELEVENLABS_VOICE_ID: str = "EXAVITQu4vr4xnSDxMaL"  # Default voice

    # FAL.ai Image Generation
    FAL_API_KEY: Optional[str] = None

    # ==========================================================================
    # Application Settings
    # ==========================================================================
    # Daily coach exchange limit per user
    DAILY_EXCHANGE_LIMIT: int = 15

    # Session settings
    SESSION_EXPIRE_DAYS: int = 30

    # Password reset settings
    PASSWORD_RESET_EXPIRE_HOURS: int = 24

    # Email verification settings
    EMAIL_VERIFICATION_EXPIRE_HOURS: int = 48

    # Account deletion grace period (GDPR)
    DELETION_GRACE_PERIOD_DAYS: int = 30

    # ==========================================================================
    # Circle Settings
    # ==========================================================================
    # Default meeting duration in minutes
    DEFAULT_MEETING_DURATION: int = 60

    # Default group size for circles
    DEFAULT_GROUP_SIZE: int = 4

    # ==========================================================================
    # Email Settings (for password reset, verification, etc.)
    # ==========================================================================
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: str = "noreply@brainbank.ai"
    SMTP_FROM_NAME: str = "BrainBank"

    # ==========================================================================
    # Frontend URL (for email links)
    # ==========================================================================
    FRONTEND_URL: str = "http://localhost:3000"

    def get_hub_uri(self) -> str:
        """Get Hub MongoDB URI, falling back to main URI if not set."""
        return self.HUB_MONGODB_URI or self.MONGODB_URI


# Global settings instance
settings = Settings()

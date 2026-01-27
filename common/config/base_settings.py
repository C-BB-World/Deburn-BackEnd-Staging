"""
Base settings class for environment configuration.

Uses Pydantic Settings for automatic environment variable loading.
Extend this class for application-specific settings.

Example:
    from common.config import BaseAppSettings

    class Settings(BaseAppSettings):
        # App-specific settings
        STRIPE_API_KEY: str = ""
        SENDGRID_API_KEY: str = ""

        class Config:
            env_file = ".env"

    settings = Settings()
    print(settings.MONGODB_URI)
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseAppSettings(BaseSettings):
    """
    Base settings class with common configuration options.

    Automatically loads values from environment variables.
    Extend this class for application-specific settings.
    """

    # ==========================================================================
    # Database Settings
    # ==========================================================================
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DATABASE: str = "deburn"

    # ==========================================================================
    # Authentication Settings
    # ==========================================================================
    AUTH_PROVIDER: str = "jwt"  # "jwt" or "firebase"

    # JWT Settings (used when AUTH_PROVIDER = "jwt")
    JWT_SECRET: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Firebase Settings (used when AUTH_PROVIDER = "firebase")
    FIREBASE_CREDENTIALS_PATH: Optional[str] = None
    FIREBASE_PROJECT_ID: Optional[str] = None

    # ==========================================================================
    # AI Settings
    # ==========================================================================
    AI_PROVIDER: str = "claude"  # "claude" or "openai"
    AI_PROMPT_SOURCE: str = "aiprompt"  # "aiprompt" (MongoDB) or "file" (local files)

    # Claude Settings (used when AI_PROVIDER = "claude")
    CLAUDE_API_KEY: Optional[str] = None
    CLAUDE_MODEL: str = "claude-sonnet-4-5-20250929"

    # OpenAI Settings (used when AI_PROVIDER = "openai")
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # ==========================================================================
    # Server Settings
    # ==========================================================================
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, staging, production

    # CORS Settings
    CORS_ORIGINS: str = "*"  # Comma-separated origins or "*"
    CORS_ALLOW_CREDENTIALS: bool = True

    # ==========================================================================
    # Insight Settings
    # ==========================================================================
    INSIGHT_LOOKBACK_DAYS: int = 7  # Days of history for insight generation

    # ==========================================================================
    # Internationalization
    # ==========================================================================
    DEFAULT_LANGUAGE: str = "en"
    SUPPORTED_LANGUAGES: str = "en,sv"  # Comma-separated

    # ==========================================================================
    # Pydantic Settings Configuration
    # ==========================================================================
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",  # Allow app-specific settings
        case_sensitive=True,
    )

    def get_cors_origins(self) -> list:
        """Parse CORS_ORIGINS into a list."""
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    def get_supported_languages(self) -> list:
        """Parse SUPPORTED_LANGUAGES into a list."""
        return [lang.strip() for lang in self.SUPPORTED_LANGUAGES.split(",")]

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT.lower() == "production"

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT.lower() == "development"

    def validate_required(self) -> None:
        """
        Validate that required settings are configured.

        Raises:
            ValueError: If required settings are missing
        """
        errors = []

        # Check auth provider requirements
        if self.AUTH_PROVIDER == "jwt" and not self.JWT_SECRET:
            errors.append("JWT_SECRET is required when using JWT authentication")

        if self.AUTH_PROVIDER == "firebase" and not self.FIREBASE_CREDENTIALS_PATH:
            errors.append(
                "FIREBASE_CREDENTIALS_PATH is required when using Firebase authentication"
            )

        # Check AI provider requirements
        if self.AI_PROVIDER == "claude" and not self.CLAUDE_API_KEY:
            errors.append("CLAUDE_API_KEY is required when using Claude AI")

        if self.AI_PROVIDER == "openai" and not self.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY is required when using OpenAI")

        if errors:
            raise ValueError("Configuration errors:\n- " + "\n- ".join(errors))

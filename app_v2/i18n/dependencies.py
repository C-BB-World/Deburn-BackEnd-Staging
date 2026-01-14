"""
FastAPI dependencies for i18n system.

Provides dependency injection for i18n-related services.
"""

from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app_v2.i18n.services.language_config import LanguageConfig
from app_v2.i18n.services.i18n_service import I18nService
from app_v2.i18n.middleware import I18nMiddleware


_language_config: Optional[LanguageConfig] = None
_i18n_service: Optional[I18nService] = None
_i18n_middleware: Optional[I18nMiddleware] = None


def init_i18n_services(
    db: Optional[AsyncIOMotorDatabase] = None,
    locales_path: str = "public/locales",
    emails_path: str = "locales/emails",
    source_mode: str = "file"
) -> None:
    """
    Initialize i18n services.

    Called once at application startup.

    Args:
        db: MongoDB database connection (for database mode)
        locales_path: Path to UI locales directory
        emails_path: Path to email translations directory
        source_mode: "file" or "database"
    """
    global _language_config, _i18n_service, _i18n_middleware

    _language_config = LanguageConfig(db=db, source_mode=source_mode)

    _i18n_service = I18nService(
        language_config=_language_config,
        locales_path=locales_path,
        emails_path=emails_path,
        source_mode=source_mode
    )

    _i18n_middleware = I18nMiddleware(
        i18n_service=_i18n_service,
        language_config=_language_config
    )


def get_language_config() -> LanguageConfig:
    """Get language config instance."""
    if _language_config is None:
        raise RuntimeError("i18n services not initialized. Call init_i18n_services first.")
    return _language_config


def get_i18n_service() -> I18nService:
    """Get i18n service instance."""
    if _i18n_service is None:
        raise RuntimeError("i18n services not initialized. Call init_i18n_services first.")
    return _i18n_service


def get_i18n_middleware() -> I18nMiddleware:
    """Get i18n middleware instance."""
    if _i18n_middleware is None:
        raise RuntimeError("i18n services not initialized. Call init_i18n_services first.")
    return _i18n_middleware

"""
FastAPI dependencies for User system.

Provides dependency injection for user-related services.
"""

from motor.motor_asyncio import AsyncIOMotorDatabase

from app_v2.user.services.user_service import UserService
from app_v2.user.services.profile_service import ProfileService
from app_v2.user.services.consent_service import ConsentService


_user_service: UserService | None = None
_profile_service: ProfileService | None = None
_consent_service: ConsentService | None = None


def init_user_services(db: AsyncIOMotorDatabase) -> None:
    """
    Initialize user services with database connection.

    Called once at application startup.

    Args:
        db: MongoDB database connection
    """
    global _user_service, _profile_service, _consent_service

    _consent_service = ConsentService(db=db)
    _profile_service = ProfileService(db=db)
    _user_service = UserService(
        db=db,
        consent_service=_consent_service
    )


def get_user_service() -> UserService:
    """Get user service instance."""
    if _user_service is None:
        raise RuntimeError("User services not initialized. Call init_user_services first.")
    return _user_service


def get_profile_service() -> ProfileService:
    """Get profile service instance."""
    if _profile_service is None:
        raise RuntimeError("User services not initialized. Call init_user_services first.")
    return _profile_service


def get_consent_service() -> ConsentService:
    """Get consent service instance."""
    if _consent_service is None:
        raise RuntimeError("User services not initialized. Call init_user_services first.")
    return _consent_service

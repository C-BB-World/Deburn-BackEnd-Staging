"""
User System

Manages user data and lifecycle including profile information,
GDPR consent tracking, and account deletion.
"""

from app_v2.user.services.user_service import UserService
from app_v2.user.services.profile_service import ProfileService
from app_v2.user.services.consent_service import ConsentService

__all__ = [
    "UserService",
    "ProfileService",
    "ConsentService",
]

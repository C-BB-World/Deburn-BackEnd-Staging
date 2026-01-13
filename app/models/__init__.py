"""
BrainBank database models.

All models extend BaseDocument from common/ for consistent
timestamp handling and save behavior.
"""

from app.models.user import User, UserProfile, UserConsent, UserSession
from app.models.checkin import CheckIn, CheckInMetrics
from app.models.organization import Organization, OrganizationSettings

__all__ = [
    # User models
    "User",
    "UserProfile",
    "UserConsent",
    "UserSession",
    # Check-in models
    "CheckIn",
    "CheckInMetrics",
    # Organization models
    "Organization",
    "OrganizationSettings",
]

"""
User system pipeline functions.

Stateless orchestration logic for user operations.
"""

import logging
from datetime import datetime

from app_v2.user.services.user_service import UserService
from app_v2.user.services.profile_service import ProfileService
from app_v2.user.services.consent_service import ConsentService

logger = logging.getLogger(__name__)


async def get_profile_pipeline(
    profile_service: ProfileService,
    user_id: str
) -> dict:
    """
    Get user's profile.

    Args:
        profile_service: For profile retrieval
        user_id: MongoDB user ID

    Returns:
        Profile dict
    """
    return await profile_service.get_profile(user_id)


async def update_profile_pipeline(
    profile_service: ProfileService,
    user_id: str,
    updates: dict
) -> dict:
    """
    Update user's profile.

    Args:
        profile_service: For profile updates
        user_id: MongoDB user ID
        updates: Fields to update

    Returns:
        Updated profile dict
    """
    return await profile_service.update_profile(user_id, updates)


async def get_consents_pipeline(
    consent_service: ConsentService,
    user_id: str
) -> dict:
    """
    Get user's consents.

    Args:
        consent_service: For consent retrieval
        user_id: MongoDB user ID

    Returns:
        dict with consents, needsUpdate flag, and outdatedConsents list
    """
    return await consent_service.get_consents(user_id)


async def update_consent_pipeline(
    consent_service: ConsentService,
    user_id: str,
    consent_type: str,
    accepted: bool,
    version: str
) -> dict:
    """
    Update a user's consent.

    Args:
        consent_service: For consent updates
        user_id: MongoDB user ID
        consent_type: Type of consent
        accepted: Whether user accepts
        version: Version being accepted

    Returns:
        Updated consent record
    """
    return await consent_service.update_consent(
        user_id=user_id,
        consent_type=consent_type,
        accepted=accepted,
        version=version
    )


async def request_deletion_pipeline(
    user_service: UserService,
    user_id: str,
    reason: str | None = None
) -> datetime:
    """
    Request account deletion.

    Args:
        user_service: For deletion request
        user_id: MongoDB user ID
        reason: Optional reason for deletion

    Returns:
        Scheduled deletion datetime
    """
    return await user_service.request_deletion(user_id, reason)


async def cancel_deletion_pipeline(
    user_service: UserService,
    user_id: str
) -> None:
    """
    Cancel pending account deletion.

    Args:
        user_service: For cancellation
        user_id: MongoDB user ID
    """
    await user_service.cancel_deletion(user_id)

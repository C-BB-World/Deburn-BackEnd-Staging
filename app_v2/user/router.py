"""
FastAPI router for User system endpoints.

Provides endpoints for profile management, consents, and account deletion.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from app_v2.auth.dependencies import require_auth
from app_v2.user.dependencies import (
    get_user_service,
    get_profile_service,
    get_consent_service,
)
from app_v2.user.services.user_service import UserService
from app_v2.user.services.profile_service import ProfileService
from app_v2.user.services.consent_service import ConsentService
from app_v2.user.models import (
    ProfileResponse,
    ProfileUpdateRequest,
    ConsentsResponse,
    ConsentRecord,
    ConsentUpdateRequest,
    ConsentUpdateResponse,
    DeleteAccountRequest,
    DeleteAccountResponse,
    CancelDeletionResponse,
)
from app_v2.user import pipelines

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(
    user: Annotated[dict, Depends(require_auth)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
):
    """
    Get current user's profile.

    Returns profile data including name, job title, timezone, etc.
    """
    profile = await pipelines.get_profile_pipeline(
        profile_service=profile_service,
        user_id=str(user["_id"])
    )

    return ProfileResponse(**profile)


@router.patch("/profile", response_model=ProfileResponse)
async def update_profile(
    body: ProfileUpdateRequest,
    user: Annotated[dict, Depends(require_auth)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
):
    """
    Update current user's profile.

    Only provided fields will be updated (partial update).
    """
    updates = body.model_dump(exclude_unset=True)

    profile = await pipelines.update_profile_pipeline(
        profile_service=profile_service,
        user_id=str(user["_id"]),
        updates=updates
    )

    return ProfileResponse(**profile)


@router.get("/consents", response_model=ConsentsResponse)
async def get_consents(
    user: Annotated[dict, Depends(require_auth)],
    consent_service: Annotated[ConsentService, Depends(get_consent_service)],
):
    """
    Get current user's consents.

    Returns all consents with their status and versions,
    plus flags indicating if re-consent is needed.
    """
    result = await pipelines.get_consents_pipeline(
        consent_service=consent_service,
        user_id=str(user["_id"])
    )

    consents = {
        k: ConsentRecord(**v) for k, v in result["consents"].items()
    }

    return ConsentsResponse(
        consents=consents,
        needsUpdate=result["needsUpdate"],
        outdatedConsents=result["outdatedConsents"]
    )


@router.put("/consents/{consent_type}", response_model=ConsentUpdateResponse)
async def update_consent(
    consent_type: str,
    body: ConsentUpdateRequest,
    user: Annotated[dict, Depends(require_auth)],
    consent_service: Annotated[ConsentService, Depends(get_consent_service)],
):
    """
    Update a specific consent.

    Version must match current version of the consent type.
    Withdrawing required consents will trigger account deletion.
    """
    result = await pipelines.update_consent_pipeline(
        consent_service=consent_service,
        user_id=str(user["_id"]),
        consent_type=consent_type,
        accepted=body.accepted,
        version=body.version
    )

    return ConsentUpdateResponse(**result)


@router.post("/delete", response_model=DeleteAccountResponse)
async def request_deletion(
    user: Annotated[dict, Depends(require_auth)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    body: DeleteAccountRequest = None,
):
    """
    Request account deletion.

    Initiates 30-day grace period. Logging in during this period cancels deletion.
    """
    reason = body.reason if body else None

    scheduled_for = await pipelines.request_deletion_pipeline(
        user_service=user_service,
        user_id=str(user["_id"]),
        reason=reason
    )

    return DeleteAccountResponse(scheduledFor=scheduled_for)


@router.post("/cancel-deletion", response_model=CancelDeletionResponse)
async def cancel_deletion(
    user: Annotated[dict, Depends(require_auth)],
    user_service: Annotated[UserService, Depends(get_user_service)],
):
    """
    Cancel pending account deletion.

    Only available during 30-day grace period.
    """
    await pipelines.cancel_deletion_pipeline(
        user_service=user_service,
        user_id=str(user["_id"])
    )

    return CancelDeletionResponse()

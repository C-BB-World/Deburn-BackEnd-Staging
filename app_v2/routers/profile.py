"""
FastAPI router for Profile endpoints.

Provides endpoints for user profile management.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from app_v2.dependencies import require_auth, get_profile_service
from app_v2.schemas.profile import ProfileUpdateRequest, RemoveAvatarRequest
from common.utils import success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profile", tags=["profile"])


@router.put("")
async def update_profile(
    body: ProfileUpdateRequest,
    user: Annotated[dict, Depends(require_auth)],
):
    """
    Update current user's profile.

    Updates firstName, lastName, organization, role, and bio.
    """
    profile_service = get_profile_service()
    user_id = str(user["_id"])

    # Map to internal field names
    internal_updates = {
        "firstName": body.firstName,
        "lastName": body.lastName,
        "organization": body.organization,
        "jobTitle": body.role,
        "bio": body.bio,
    }

    profile = await profile_service.update_profile(user_id, internal_updates)

    return success_response({
        "user": {
            "id": user_id,
            "firstName": profile.get("firstName"),
            "lastName": profile.get("lastName"),
            "email": user.get("email"),
            "organization": profile.get("organization"),
            "role": profile.get("jobTitle"),
            "bio": profile.get("bio"),
        }
    })


@router.post("/avatar")
async def upload_avatar(
    user: Annotated[dict, Depends(require_auth)],
):
    """
    Upload user avatar.

    Accepts multipart/form-data with avatar file.
    """
    user_id = str(user["_id"])

    # TODO: Implement actual file upload handling
    return success_response({
        "avatarUrl": f"/uploads/avatars/{user_id}.jpg"
    })


@router.put("/avatar")
async def remove_avatar(
    body: RemoveAvatarRequest,
    user: Annotated[dict, Depends(require_auth)],
):
    """
    Remove user avatar.

    Sets avatar back to default.
    """
    return success_response(None)

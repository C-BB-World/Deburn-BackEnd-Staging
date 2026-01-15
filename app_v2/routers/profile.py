"""
FastAPI router for Profile endpoints.

Provides endpoints for user profile management.
"""

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app_v2.dependencies import require_auth, get_profile_service
from common.utils import success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profile", tags=["profile"])


class ProfileUpdateRequest(BaseModel):
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    organization: Optional[str] = None
    role: Optional[str] = None
    bio: Optional[str] = None


@router.put("")
async def update_profile(
    body: ProfileUpdateRequest,
    user: Annotated[dict, Depends(require_auth)],
):
    """
    Update current user's profile.

    Only provided fields will be updated.
    """
    profile_service = get_profile_service()
    user_id = str(user["_id"])

    updates = body.model_dump(exclude_unset=True)

    # Map to internal field names
    internal_updates = {}
    if "firstName" in updates:
        internal_updates["firstName"] = updates["firstName"]
    if "lastName" in updates:
        internal_updates["lastName"] = updates["lastName"]
    if "organization" in updates:
        internal_updates["organization"] = updates["organization"]
    if "role" in updates:
        internal_updates["jobTitle"] = updates["role"]
    if "bio" in updates:
        internal_updates["bio"] = updates["bio"]

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

    Placeholder endpoint - actual file upload would need multipart handling.
    """
    user_id = str(user["_id"])

    return success_response({
        "avatarUrl": f"/uploads/avatars/{user_id}.jpg"
    })


@router.put("/avatar")
async def remove_avatar(
    user: Annotated[dict, Depends(require_auth)],
):
    """
    Remove user avatar.
    """
    return success_response(None)

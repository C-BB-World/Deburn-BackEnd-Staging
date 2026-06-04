"""
FastAPI router for Profile endpoints.

Provides endpoints for user profile management.
"""

import logging
import os
from typing import Annotated

import httpx
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, UploadFile

from app_v2.dependencies import require_auth, get_profile_service, get_main_db
from app_v2.schemas.profile import ProfileUpdateRequest, RemoveAvatarRequest
from common.utils import success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profile", tags=["profile"])

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_STORAGE_URL = f"{SUPABASE_URL}/storage/v1/object"
AVATAR_BUCKET = "avatars"


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
            "avatarUrl": profile.get("avatarUrl"),
        }
    })


@router.post("/avatar")
async def upload_avatar(
    avatar: UploadFile,
    user: Annotated[dict, Depends(require_auth)],
):
    """
    Upload user avatar.

    Accepts multipart/form-data with avatar file.
    Stores in Supabase Storage bucket 'avatars' as {userId}_avatar.{ext}.
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise HTTPException(status_code=500, detail={"message": "Storage not configured"})

    user_id = str(user["_id"])

    ext = os.path.splitext(avatar.filename or "")[1].lower() or ".jpg"
    filename = f"{user_id}_avatar{ext}"

    file_bytes = await avatar.read()
    content_type = avatar.content_type or "image/jpeg"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SUPABASE_STORAGE_URL}/{AVATAR_BUCKET}/{filename}",
            headers={
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                "Content-Type": content_type,
                "x-upsert": "true",
            },
            content=file_bytes,
        )
        if response.status_code not in (200, 201):
            logger.error(f"Supabase upload failed: {response.text}")
            raise HTTPException(status_code=500, detail={"message": "Upload failed"})

    avatar_url = f"{SUPABASE_URL}/storage/v1/object/public/{AVATAR_BUCKET}/{filename}"

    db = get_main_db()
    await db["users"].update_one(
        {"_id": user["_id"]},
        {"$set": {"profile.avatarUrl": avatar_url}}
    )

    return success_response({"avatarUrl": avatar_url})


@router.put("/avatar")
async def remove_avatar(
    body: RemoveAvatarRequest,
    user: Annotated[dict, Depends(require_auth)],
):
    """
    Remove user avatar.

    Deletes avatar from Supabase Storage and clears avatarUrl in profile.
    """
    user_id = str(user["_id"])
    profile = user.get("profile", {})
    avatar_url = profile.get("avatarUrl")

    if avatar_url and SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
        # Extract filename from URL (last path segment)
        filename = avatar_url.split("/")[-1]
        async with httpx.AsyncClient() as client:
            await client.delete(
                f"{SUPABASE_STORAGE_URL}/{AVATAR_BUCKET}/{filename}",
                headers={"Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}"},
            )

    db = get_main_db()
    await db["users"].update_one(
        {"_id": ObjectId(user_id)},
        {"$unset": {"profile.avatarUrl": ""}}
    )

    return success_response(None)

"""
Profile Router.

Handles user profile management and avatar uploads.
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse

from common.utils import success_response, error_response

from app_v1.models import User
from app_v1.schemas.profile import ProfileUpdateRequest
from app_v1.dependencies import get_current_user

router = APIRouter()


# =============================================================================
# Helper Functions
# =============================================================================
def profile_to_response(user: User) -> dict:
    """Convert user profile to response dictionary."""
    profile = user.profile
    return {
        "firstName": profile.first_name if profile else None,
        "lastName": profile.last_name if profile else None,
        "jobTitle": profile.job_title if profile else None,
        "leadershipLevel": profile.leadership_level if profile else None,
        "preferredLanguage": profile.preferred_language if profile else "en",
        "timezone": profile.timezone if profile else None,
        "avatarUrl": profile.avatar_url if profile else None,
    }


def user_to_response(user: User) -> dict:
    """Convert User model to response dictionary."""
    return {
        "id": str(user.id),
        "email": user.email,
        "organization": user.organization,
        "country": user.country,
        "profile": profile_to_response(user),
        "displayName": user.display_name,
        "status": user.status,
    }


# =============================================================================
# PUT /api/profile
# =============================================================================
@router.put("")
async def update_profile(
    request: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
):
    """
    Update the current user's profile.
    """
    # Update profile fields if provided
    if user.profile is None:
        from app_v1.models import UserProfile
        user.profile = UserProfile()

    if request.firstName is not None:
        user.profile.first_name = request.firstName
    if request.lastName is not None:
        user.profile.last_name = request.lastName
    if request.jobTitle is not None:
        user.profile.job_title = request.jobTitle
    if request.leadershipLevel is not None:
        user.profile.leadership_level = request.leadershipLevel
    if request.preferredLanguage is not None:
        user.profile.preferred_language = request.preferredLanguage
    if request.timezone is not None:
        user.profile.timezone = request.timezone

    await user.save()

    return success_response(
        {"user": user_to_response(user)},
        message="Profile updated successfully",
    )


# =============================================================================
# POST /api/profile/avatar
# =============================================================================
@router.post("/avatar")
async def upload_avatar(
    user: User = Depends(get_current_user),
    avatar: UploadFile = File(...),
):
    """
    Upload a new profile avatar.
    """
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if avatar.content_type not in allowed_types:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response(
                "Invalid file type. Allowed: JPEG, PNG, GIF, WebP",
                code="INVALID_FILE_TYPE",
            ),
        )

    # Validate file size (max 5MB)
    max_size = 5 * 1024 * 1024  # 5MB
    contents = await avatar.read()
    if len(contents) > max_size:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response(
                "File too large. Maximum size is 5MB",
                code="FILE_TOO_LARGE",
            ),
        )

    # TODO: Upload to storage service (FAL.ai, S3, etc.)
    # For now, we'll just simulate storing the URL
    # avatar_url = await storage_service.upload_avatar(str(user.id), contents)

    # Placeholder URL
    avatar_url = f"/api/avatars/{user.id}"

    # Update user profile
    if user.profile is None:
        from app_v1.models import UserProfile
        user.profile = UserProfile()

    user.profile.avatar_url = avatar_url
    await user.save()

    return success_response(
        {"avatarUrl": avatar_url},
        message="Avatar uploaded successfully",
    )


# =============================================================================
# PUT /api/profile/avatar (remove)
# =============================================================================
@router.put("/avatar")
async def remove_avatar(
    user: User = Depends(get_current_user),
):
    """
    Remove the current user's avatar.
    """
    if user.profile:
        # TODO: Delete from storage if needed
        user.profile.avatar_url = None
        await user.save()

    return success_response(message="Avatar removed successfully")

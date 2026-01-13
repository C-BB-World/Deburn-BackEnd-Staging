"""
Authentication Router.

Handles user registration, login, logout, password reset, and email verification.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from common.auth import AuthProvider
from common.utils import success_response, error_response
from common.utils.password import validate_password

from app.config import settings
from app.models import User, UserProfile
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
    ResendVerificationRequest,
)
from app.dependencies import get_auth_provider, get_current_user

router = APIRouter()


# =============================================================================
# Helper Functions
# =============================================================================
def generate_token() -> str:
    """Generate a secure random token."""
    return secrets.token_urlsafe(32)


def user_to_response(user: User) -> dict:
    """Convert User model to response dictionary."""
    return {
        "id": str(user.id),
        "email": user.email,
        "organization": user.organization,
        "country": user.country,
        "profile": {
            "firstName": user.profile.first_name if user.profile else None,
            "lastName": user.profile.last_name if user.profile else None,
            "jobTitle": user.profile.job_title if user.profile else None,
            "leadershipLevel": user.profile.leadership_level if user.profile else None,
            "preferredLanguage": user.profile.preferred_language if user.profile else "en",
        },
        "displayName": user.display_name,
        "status": user.status,
        "createdAt": user.created_at.isoformat() if user.created_at else None,
    }


# =============================================================================
# POST /api/auth/register
# =============================================================================
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    auth: AuthProvider = Depends(get_auth_provider),
):
    """
    Register a new user account.

    Creates the user with pending_verification status and sends verification email.
    """
    # Validate password strength
    is_valid, error_msg = validate_password(request.password)
    if not is_valid:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response(error_msg, code="WEAK_PASSWORD"),
        )

    # Check if email already exists
    existing_user = await User.find_one(User.email == request.email.lower())
    if existing_user:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=error_response(
                "This email is already registered",
                code="EMAIL_EXISTS",
            ),
        )

    # Hash password
    password_hash = auth.hash_password(request.password)

    # Generate verification token
    verification_token = generate_token()
    verification_expiry = datetime.now(timezone.utc) + timedelta(
        hours=settings.EMAIL_VERIFICATION_EXPIRE_HOURS
    )

    # Create user
    user = User(
        email=request.email.lower(),
        password_hash=password_hash,
        organization=request.organization,
        country=request.country.upper(),
        profile=UserProfile(
            first_name=request.firstName,
            last_name=request.lastName,
            preferred_language="en",
        ),
        status="pending_verification",
        email_verification_token=verification_token,
        email_verification_expires_at=verification_expiry,
    )
    await user.insert()

    # TODO: Send verification email
    # await email_service.send_verification_email(user.email, verification_token)

    return success_response(
        {"user": user_to_response(user)},
        message="Registration successful. Please check your email to verify your account.",
    )


# =============================================================================
# POST /api/auth/login
# =============================================================================
@router.post("/login")
async def login(
    request: LoginRequest,
    auth: AuthProvider = Depends(get_auth_provider),
):
    """
    Authenticate user and return access token.
    """
    # Find user by email
    user = await User.find_one(User.email == request.email.lower())

    # Generic error to prevent enumeration
    login_error = JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content=error_response(
            "Invalid email or password",
            code="LOGIN_FAILED",
        ),
    )

    if not user:
        return login_error

    # Check if user is active
    if user.status != "active":
        return login_error

    # Verify password
    if not auth.verify_password(request.password, user.password_hash):
        return login_error

    # Create access token
    token = auth.create_token(str(user.id))

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    await user.save()

    return success_response(
        {
            "user": user_to_response(user),
            "accessToken": token,
        },
        message="Signed in successfully",
    )


# =============================================================================
# POST /api/auth/logout
# =============================================================================
@router.post("/logout")
async def logout(
    user: User = Depends(get_current_user),
):
    """
    Sign out the current user.

    In a stateless JWT setup, the client simply discards the token.
    For session tracking, we would invalidate the session here.
    """
    # TODO: If tracking sessions, remove the session from user.sessions
    return success_response(message="Signed out successfully")


# =============================================================================
# POST /api/auth/forgot-password
# =============================================================================
@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    auth: AuthProvider = Depends(get_auth_provider),
):
    """
    Request a password reset email.

    Always returns success to prevent email enumeration.
    """
    # Find user by email
    user = await User.find_one(User.email == request.email.lower())

    if user and user.status == "active":
        # Generate reset token
        reset_token = generate_token()
        reset_expiry = datetime.now(timezone.utc) + timedelta(
            hours=settings.PASSWORD_RESET_EXPIRE_HOURS
        )

        # Store token (hashed in production)
        user.password_reset_token = reset_token
        user.password_reset_expires_at = reset_expiry
        await user.save()

        # TODO: Send reset email
        # await email_service.send_password_reset_email(user.email, reset_token)

    # Always return success to prevent enumeration
    return success_response(
        message="If this email is registered, we've sent password reset instructions."
    )


# =============================================================================
# POST /api/auth/reset-password
# =============================================================================
@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    auth: AuthProvider = Depends(get_auth_provider),
):
    """
    Reset password using a reset token.
    """
    # Validate password strength
    is_valid, error_msg = validate_password(request.password)
    if not is_valid:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response(error_msg, code="WEAK_PASSWORD"),
        )

    # Find user by reset token
    user = await User.find_one(User.password_reset_token == request.token)

    if not user:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response(
                "Invalid or expired reset token",
                code="RESET_FAILED",
            ),
        )

    # Check if token expired
    if user.password_reset_expires_at and user.password_reset_expires_at < datetime.now(
        timezone.utc
    ):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response(
                "Reset token has expired",
                code="TOKEN_EXPIRED",
            ),
        )

    # Update password
    user.password_hash = auth.hash_password(request.password)
    user.password_reset_token = None
    user.password_reset_expires_at = None
    await user.save()

    return success_response(
        message="Password has been reset successfully. You can now sign in."
    )


# =============================================================================
# POST /api/auth/verify-email
# =============================================================================
@router.post("/verify-email")
async def verify_email(request: VerifyEmailRequest):
    """
    Verify email address using verification token.
    """
    # Find user by verification token
    user = await User.find_one(User.email_verification_token == request.token)

    if not user:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response(
                "Invalid verification token",
                code="VERIFICATION_FAILED",
            ),
        )

    # Check if token expired
    if (
        user.email_verification_expires_at
        and user.email_verification_expires_at < datetime.now(timezone.utc)
    ):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response(
                "Verification token has expired",
                code="TOKEN_EXPIRED",
            ),
        )

    # Activate user
    user.status = "active"
    user.email_verified_at = datetime.now(timezone.utc)
    user.email_verification_token = None
    user.email_verification_expires_at = None
    await user.save()

    return success_response(
        {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "status": user.status,
            }
        },
        message="Email verified successfully",
    )


# =============================================================================
# POST /api/auth/resend-verification
# =============================================================================
@router.post("/resend-verification")
async def resend_verification(request: ResendVerificationRequest):
    """
    Resend email verification link.

    Always returns success to prevent email enumeration.
    """
    # Find user by email
    user = await User.find_one(User.email == request.email.lower())

    if user and user.status == "pending_verification":
        # Generate new verification token
        verification_token = generate_token()
        verification_expiry = datetime.now(timezone.utc) + timedelta(
            hours=settings.EMAIL_VERIFICATION_EXPIRE_HOURS
        )

        user.email_verification_token = verification_token
        user.email_verification_expires_at = verification_expiry
        await user.save()

        # TODO: Send verification email
        # await email_service.send_verification_email(user.email, verification_token)

    # Always return success to prevent enumeration
    return success_response(
        message="If this email is registered and unverified, we've sent a new verification link."
    )

"""
Authentication Router.

Handles user registration, login, logout, password reset, and email verification.
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

logger = logging.getLogger(__name__)
from fastapi.responses import JSONResponse

from common.auth import AuthProvider
from common.utils import success_response, error_response
from common.utils.password import validate_password

from app_v1.config import settings
from app_v1.models import User, UserProfile
from app_v1.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
    ResendVerificationRequest,
)
from app_v1.dependencies import get_auth_provider, get_current_user

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
    logger.info(f"Registration attempt for email: {request.email}")

    # Validate password strength
    is_valid, error_msg = validate_password(request.password)
    if not is_valid:
        logger.warning(f"Registration failed - weak password for email: {request.email}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response(error_msg, code="WEAK_PASSWORD"),
        )

    # Check if email already exists
    logger.debug(f"Checking if email exists: {request.email.lower()}")
    existing_user = await User.find_one(User.email == request.email.lower())
    if existing_user:
        logger.warning(f"Registration failed - email already exists: {request.email}")
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=error_response(
                "This email is already registered",
                code="EMAIL_EXISTS",
            ),
        )

    # Hash password
    logger.debug("Hashing password")
    password_hash = auth.hash_password(request.password)

    # Generate verification token
    verification_token = generate_token()
    verification_expiry = datetime.now(timezone.utc) + timedelta(
        hours=settings.EMAIL_VERIFICATION_EXPIRE_HOURS
    )

    # Create user
    logger.debug(f"Creating user record for: {request.email.lower()}")
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
    logger.info(f"User registered successfully: {user.id} ({request.email.lower()})")

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
    logger.info(f"Login attempt for email: {request.email}")

    # Find user by email
    logger.warning(f"DEBUG: Looking up user by email: {request.email.lower()}")
    user = await User.find_one(User.email == request.email.lower())

    # Debug: Check if any users exist at all
    if not user:
        all_users = await User.find_all().to_list()
        logger.warning(f"DEBUG: Total users in database: {len(all_users)}")
        if all_users:
            logger.warning(f"DEBUG: Sample emails in DB: {[u.email for u in all_users[:3]]}")

    # Generic error to prevent enumeration
    login_error = JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content=error_response(
            "Invalid email or password",
            code="LOGIN_FAILED",
        ),
    )

    if not user:
        logger.warning(f"Login failed - user not found: {request.email}")
        return login_error

    # Check if user is active
    if user.status != "active":
        logger.warning(f"Login failed - user not active: {request.email} (status: {user.status})")
        return login_error

    # Verify password
    logger.debug(f"Verifying password for user: {user.id}")
    if not auth.verify_password(request.password, user.password_hash):
        logger.warning(f"Login failed - invalid password for user: {request.email}")
        return login_error

    # Create access token
    logger.debug(f"Creating access token for user: {user.id}")
    token = await auth.create_token(str(user.id))

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    await user.save()
    logger.info(f"Login successful for user: {user.id} ({request.email})")

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
    logger.info(f"Logout for user: {user.id} ({user.email})")
    # TODO: If tracking sessions, remove the session from user.sessions
    return success_response(message="Signed out successfully")


# =============================================================================
# POST /api/auth/forgot-password
# =============================================================================
@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
):
    """
    Request a password reset email.

    Always returns success to prevent email enumeration.
    """
    logger.info(f"Password reset requested for email: {request.email}")

    # Find user by email
    user = await User.find_one(User.email == request.email.lower())

    if user and user.status == "active":
        logger.debug(f"User found, generating reset token for: {user.id}")
        # Generate reset token
        reset_token = generate_token()
        reset_expiry = datetime.now(timezone.utc) + timedelta(
            hours=settings.PASSWORD_RESET_EXPIRE_HOURS
        )

        # Store token (hashed in production)
        user.password_reset_token = reset_token
        user.password_reset_expires_at = reset_expiry
        await user.save()
        logger.info(f"Password reset token generated for user: {user.id}")

        # TODO: Send reset email
        # await email_service.send_password_reset_email(user.email, reset_token)
    else:
        logger.debug(f"Password reset requested for non-existent or inactive email: {request.email}")

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
    logger.info("Password reset attempt with token")

    # Validate password strength
    is_valid, error_msg = validate_password(request.password)
    if not is_valid:
        logger.warning("Password reset failed - weak password")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response(error_msg, code="WEAK_PASSWORD"),
        )

    # Find user by reset token
    logger.debug("Looking up user by reset token")
    user = await User.find_one(User.password_reset_token == request.token)

    if not user:
        logger.warning("Password reset failed - invalid token")
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
        logger.warning(f"Password reset failed - token expired for user: {user.id}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response(
                "Reset token has expired",
                code="TOKEN_EXPIRED",
            ),
        )

    # Update password
    logger.debug(f"Updating password for user: {user.id}")
    user.password_hash = auth.hash_password(request.password)
    user.password_reset_token = None
    user.password_reset_expires_at = None
    await user.save()
    logger.info(f"Password reset successful for user: {user.id}")

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
    logger.info("Email verification attempt with token")

    # Find user by verification token
    logger.debug("Looking up user by verification token")
    user = await User.find_one(User.email_verification_token == request.token)

    if not user:
        logger.warning("Email verification failed - invalid token")
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
        logger.warning(f"Email verification failed - token expired for user: {user.id}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response(
                "Verification token has expired",
                code="TOKEN_EXPIRED",
            ),
        )

    # Activate user
    logger.debug(f"Activating user: {user.id}")
    user.status = "active"
    user.email_verified_at = datetime.now(timezone.utc)
    user.email_verification_token = None
    user.email_verification_expires_at = None
    await user.save()
    logger.info(f"Email verified successfully for user: {user.id} ({user.email})")

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
    logger.info(f"Resend verification requested for email: {request.email}")

    # Find user by email
    user = await User.find_one(User.email == request.email.lower())

    if user and user.status == "pending_verification":
        logger.debug(f"User found with pending verification: {user.id}")
        # Generate new verification token
        verification_token = generate_token()
        verification_expiry = datetime.now(timezone.utc) + timedelta(
            hours=settings.EMAIL_VERIFICATION_EXPIRE_HOURS
        )

        user.email_verification_token = verification_token
        user.email_verification_expires_at = verification_expiry
        await user.save()
        logger.info(f"New verification token generated for user: {user.id}")

        # TODO: Send verification email
        # await email_service.send_verification_email(user.email, verification_token)
    else:
        logger.debug(f"Resend verification skipped - user not found or not pending: {request.email}")

    # Always return success to prevent enumeration
    return success_response(
        message="If this email is registered and unverified, we've sent a new verification link."
    )

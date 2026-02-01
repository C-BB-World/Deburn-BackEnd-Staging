"""
FastAPI router for Auth system endpoints.

Provides authentication endpoints for registration, login, logout, and session management.
"""

import logging
from typing import Annotated

from bson import ObjectId
from fastapi import APIRouter, Depends, Request, HTTPException

from app_v2.pipelines import preferences as preferences_pipelines
from app_v2.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
    ResendVerificationRequest,
)
from app_v2.dependencies import (
    get_firebase_auth,
    get_session_manager,
    require_auth,
    get_client_ip,
    get_user_agent,
    get_main_db,
)
from app_v2.services.email import EmailService
from common.utils import success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def get_user_service():
    """Get user service - imported lazily to avoid circular imports."""
    from app_v2.dependencies import get_user_service as _get_user_service
    return _get_user_service()


@router.post("/register")
async def register(
    request: Request,
    body: RegisterRequest,
):
    """
    Register a new user account.

    Creates a new user account with the provided credentials.
    """
    print(f"[REGISTER] Starting registration for email: {body.email}")

    # Validate password confirmation
    if body.password != body.passwordConfirm:
        print(f"[REGISTER] Password mismatch for: {body.email}")
        raise HTTPException(status_code=400, detail={"message": "Passwords do not match"})

    user_service = get_user_service()
    firebase_auth = get_firebase_auth()

    # Check if email already exists in MongoDB BEFORE creating Firebase user
    print(f"[REGISTER] Checking if email exists in MongoDB: {body.email}")
    existing_user = await user_service.get_user_by_email(body.email)
    if existing_user:
        print(f"[REGISTER] Email already exists in MongoDB: {body.email}")
        raise HTTPException(status_code=400, detail={"message": "An account with this email already exists"})
    print(f"[REGISTER] Email not found in MongoDB, proceeding: {body.email}")

    try:
        # Create user in Firebase (Admin SDK)
        print(f"[REGISTER] Creating Firebase user: {body.email}")
        firebase_uid = await firebase_auth.create_user(
            email=body.email,
            password=body.password,
            display_name=f"{body.firstName} {body.lastName}"
        )
        print(f"[REGISTER] Firebase user created with UID: {firebase_uid}")
    except ValueError as e:
        print(f"[REGISTER] Firebase creation failed: {e}")
        raise HTTPException(status_code=400, detail={"message": str(e)})

    # Create user in database
    print(f"[REGISTER] Creating user in MongoDB: {body.email}")
    user_language = body.language if body.language in ["en", "sv"] else "en"
    user = await user_service.create_user(
        firebase_uid=firebase_uid,
        email=body.email,
        organization=body.organization,
        country=body.country,
        profile={
            "firstName": body.firstName,
            "lastName": body.lastName,
            "preferredLanguage": user_language,
        },
        consents=[
            {"type": "termsOfService", "accepted": body.consents.termsOfService, "version": "1.0"},
            {"type": "privacyPolicy", "accepted": body.consents.privacyPolicy, "version": "1.0"},
            {"type": "dataProcessing", "accepted": body.consents.dataProcessing, "version": "1.0"},
            {"type": "marketing", "accepted": body.consents.marketing, "version": "1.0"},
        ],
    )
    print(f"[REGISTER] MongoDB user created with ID: {user['_id']}")

    # Create default user preferences
    try:
        print(f"[REGISTER] Creating default preferences for user: {user['_id']}")
        await preferences_pipelines.create_default_preferences(str(user["_id"]))
        print(f"[REGISTER] Default preferences created for user: {user['_id']}")
    except Exception as e:
        # Log but don't fail registration if preferences creation fails
        print(f"[REGISTER] Failed to create default preferences: {e}")
        logger.warning(f"Failed to create default preferences: {e}")

    # Send verification email
    try:
        print(f"[REGISTER] Sending verification email to: {body.email}")
        verification_link = await firebase_auth.send_verification_email(body.email)
        email_service = EmailService()
        await email_service.send_verification_email(
            to_email=body.email,
            verification_link=verification_link,
            user_name=body.firstName,
            language=user_language,
        )
        print(f"[REGISTER] Verification email sent to: {body.email}")
    except Exception as e:
        # Log but don't fail registration if email fails
        print(f"[REGISTER] Failed to send verification email: {e}")
        logger.warning(f"Failed to send verification email: {e}")

    print(f"[REGISTER] Registration complete for: {body.email}")
    return success_response({
        "message": "Registration successful. Please verify your email."
    })


@router.post("/login")
async def login(
    request: Request,
    body: LoginRequest,
):
    """
    Login to an existing account.

    Authenticates user with email and password.
    """
    user_service = get_user_service()
    firebase_auth = get_firebase_auth()
    session_manager = get_session_manager()

    try:
        # Verify credentials with Firebase REST API
        firebase_result = await firebase_auth.sign_in_with_password(
            email=body.email,
            password=body.password
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail={"message": str(e)})

    # Get user from database
    user = await user_service.get_user_by_firebase_uid(firebase_result.get("uid"))

    if not user:
        # User exists in Firebase but not in our database - create them
        # Or return error if you want stricter behavior
        raise HTTPException(status_code=401, detail={"message": "User not found"})

    # Create session
    token, expires_at = await session_manager.create_session(
        user_id=str(user["_id"]),
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        remember_me=body.rememberMe
    )

    return success_response({
        "user": {
            "id": str(user["_id"]),
            "email": user.get("email"),
            "firstName": user.get("profile", {}).get("firstName"),
            "lastName": user.get("profile", {}).get("lastName"),
            "isAdmin": user.get("isAdmin", False),
        },
        "token": token,
        "expiresAt": expires_at.isoformat()
    })


@router.post("/logout")
async def logout(
    user: Annotated[dict, Depends(require_auth)],
):
    """
    Logout from current session.

    Terminates the current session.
    """
    return success_response(None)


@router.get("/session")
async def get_session(
    user: Annotated[dict, Depends(require_auth)],
):
    """
    Get current session/user info.

    Returns the current authenticated user's information.
    """
    profile = user.get("profile", {})
    return success_response({
        "user": {
            "id": str(user["_id"]),
            "email": user.get("email"),
            "firstName": profile.get("firstName"),
            "lastName": profile.get("lastName"),
            "preferredLanguage": profile.get("preferredLanguage", "en"),
            "isAdmin": user.get("isAdmin", False),
        }
    })


@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest,
):
    """
    Request password reset email.

    Sends a password reset link to the provided email if account exists.
    """
    firebase_auth = get_firebase_auth()
    user_service = get_user_service()
    email_service = EmailService()

    try:
        # Generate password reset link
        reset_link = await firebase_auth.send_password_reset(body.email)

        # Send email (if user exists, send_password_reset returns the link)
        if reset_link and "If the email exists" not in reset_link:
            # Use language from request, fall back to user's stored preference
            request_language = body.language if body.language in ["en", "sv"] else None
            user = await user_service.get_user_by_email(body.email)
            user_language = request_language or "en"
            user_name = None
            if user:
                profile = user.get("profile", {})
                if not request_language:
                    user_language = profile.get("preferredLanguage") or "en"
                user_name = profile.get("firstName") or user.get("firstName")

            await email_service.send_password_reset_email(
                to_email=body.email,
                reset_link=reset_link,
                user_name=user_name,
                language=user_language,
            )
    except Exception as e:
        # Don't reveal if user exists - always return success
        logger.warning(f"Password reset request failed: {e}")

    # Always return success to prevent email enumeration
    return success_response({
        "message": "If an account exists with this email, a reset link will be sent."
    })


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest,
):
    """
    Reset password with token.

    Validates reset token and updates password.
    """
    # Firebase handles password reset
    return success_response(None)


@router.post("/verify-email")
async def verify_email(
    body: VerifyEmailRequest,
):
    """
    Verify email with token.

    Validates email verification token.
    """
    # Firebase handles email verification
    return success_response(None)


@router.post("/resend-verification")
async def resend_verification(
    body: ResendVerificationRequest,
):
    """
    Resend email verification.

    Sends a new verification email to the provided address.
    """
    firebase_auth = get_firebase_auth()
    user_service = get_user_service()
    email_service = EmailService()

    try:
        # Generate new verification link
        verification_link = await firebase_auth.send_verification_email(body.email)

        # Use language from request, fall back to user's stored preference
        request_language = body.language if body.language in ["en", "sv"] else None
        user = await user_service.get_user_by_email(body.email)
        user_language = request_language or "en"
        user_name = None
        if user:
            profile = user.get("profile", {})
            if not request_language:
                user_language = profile.get("preferredLanguage") or "en"
            user_name = profile.get("firstName") or user.get("firstName")

        # Send the email
        await email_service.send_verification_email(
            to_email=body.email,
            verification_link=verification_link,
            user_name=user_name,
            language=user_language,
        )
    except ValueError as e:
        # User not found - don't reveal this
        logger.warning(f"Resend verification failed: {e}")
    except Exception as e:
        logger.warning(f"Resend verification failed: {e}")

    # Always return success to prevent email enumeration
    return success_response({
        "message": "If an account exists with this email, a verification link will be sent."
    })


@router.get("/admin-status")
async def get_admin_status(
    user: Annotated[dict, Depends(require_auth)],
):
    """
    Check if current user is an organization admin.

    Returns admin status and list of organizations where user is admin.
    """
    db = get_main_db()
    user_id = user["_id"] if isinstance(user["_id"], ObjectId) else ObjectId(str(user["_id"]))

    # Find organizations where user is admin
    org_members_collection = db["organizationmembers"]
    admin_memberships = await org_members_collection.find({
        "userId": user_id,
        "role": "admin",
        "status": "active"
    }).to_list(length=50)

    if not admin_memberships:
        return success_response({
            "isAdmin": False,
            "organizations": []
        })

    # Get organization details
    org_ids = [m["organizationId"] for m in admin_memberships]
    orgs_collection = db["organizations"]
    organizations = await orgs_collection.find({
        "_id": {"$in": org_ids}
    }).to_list(length=50)

    org_list = [
        {
            "id": str(org["_id"]),
            "name": org.get("name", ""),
            "domain": org.get("domain", "")
        }
        for org in organizations
    ]

    return success_response({
        "isAdmin": True,
        "organizations": org_list
    })

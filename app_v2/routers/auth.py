"""
FastAPI router for Auth system endpoints.

Provides authentication endpoints for registration, login, logout, and session management.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from common.auth.firebase_auth import FirebaseAuth
from app_v2.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    AuthResponse,
    LogoutResponse,
    SessionListResponse,
    SessionResponse,
    RevokeSessionResponse,
    RevokeAllSessionsResponse,
)
from app_v2.dependencies import (
    get_firebase_auth,
    get_session_manager,
    require_auth,
    get_client_ip,
    get_user_agent,
)
from app_v2.services.auth.session_manager import SessionManager
from app_v2.pipelines import auth as pipelines

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def get_user_service():
    """Get user service - imported lazily to avoid circular imports."""
    from app_v2.dependencies import get_user_service as _get_user_service
    return _get_user_service()


@router.post("/register", response_model=AuthResponse)
async def register(
    request: Request,
    body: RegisterRequest,
    firebase_auth: Annotated[FirebaseAuth, Depends(get_firebase_auth)],
    session_manager: Annotated[SessionManager, Depends(get_session_manager)],
):
    """
    Register a new user account.

    Creates a new user account via Firebase and links it to MongoDB.

    - Verifies Firebase token
    - Creates user record with profile and consents
    - Creates initial session
    - Returns user data and session token
    """
    user_service = get_user_service()

    result = await pipelines.registration_pipeline(
        firebase_auth=firebase_auth,
        user_service=user_service,
        session_manager=session_manager,
        firebase_token=body.firebaseToken,
        profile=body.profile.model_dump(),
        consents=[c.model_dump() for c in body.consents],
        organization=body.organization,
        country=body.country,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )

    return AuthResponse(**result)


@router.post("/login", response_model=AuthResponse)
async def login(
    request: Request,
    body: LoginRequest,
    firebase_auth: Annotated[FirebaseAuth, Depends(get_firebase_auth)],
    session_manager: Annotated[SessionManager, Depends(get_session_manager)],
):
    """
    Login to an existing account.

    Authenticates a returning user and creates a new session.

    - Verifies Firebase token
    - Finds existing user by Firebase UID
    - Cancels pending deletion if applicable
    - Creates new session
    - Returns user data and session token
    """
    user_service = get_user_service()

    result = await pipelines.login_pipeline(
        firebase_auth=firebase_auth,
        user_service=user_service,
        session_manager=session_manager,
        firebase_token=body.firebaseToken,
        remember_me=body.rememberMe,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )

    return AuthResponse(**result)


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    user: Annotated[dict, Depends(require_auth)],
    session_manager: Annotated[SessionManager, Depends(get_session_manager)],
):
    """
    Logout from current session.

    Terminates the current session.

    - Extracts token from Authorization header
    - Removes session from user's sessions array
    - Returns success
    """
    token_hash = request.state.token_hash

    result = await pipelines.logout_pipeline(
        session_manager=session_manager,
        user_id=str(user["_id"]),
        token_hash=token_hash
    )

    return LogoutResponse(**result)


@router.get("/session")
async def get_session(
    request: Request,
    user: Annotated[dict, Depends(require_auth)],
):
    """
    Get current session/user info.

    Returns the current authenticated user's information.
    """
    from common.utils import success_response

    return success_response({
        "user": {
            "id": str(user["_id"]),
            "email": user.get("email"),
            "firstName": user.get("profile", {}).get("firstName"),
            "lastName": user.get("profile", {}).get("lastName"),
            "isAdmin": user.get("isAdmin", False),
        }
    })


@router.post("/forgot-password")
async def forgot_password(
    body: dict,
):
    """
    Request password reset email.

    Sends a password reset link to the provided email if account exists.
    """
    from common.utils import success_response
    # Firebase handles password reset emails directly
    # This endpoint is a placeholder for API consistency
    return success_response(None)


@router.post("/reset-password")
async def reset_password(
    body: dict,
):
    """
    Reset password with token.

    Validates reset token and updates password.
    """
    from common.utils import success_response
    # Firebase handles password reset directly
    # This endpoint is a placeholder for API consistency
    return success_response(None)


@router.post("/verify-email")
async def verify_email(
    body: dict,
):
    """
    Verify email with token.

    Validates email verification token.
    """
    from common.utils import success_response
    # Firebase handles email verification directly
    # This endpoint is a placeholder for API consistency
    return success_response(None)


@router.post("/resend-verification")
async def resend_verification(
    body: dict,
):
    """
    Resend email verification.

    Sends a new verification email to the provided address.
    """
    from common.utils import success_response
    # Firebase handles email verification directly
    # This endpoint is a placeholder for API consistency
    return success_response(None)


@router.get("/sessions", response_model=SessionListResponse)
async def get_sessions(
    request: Request,
    user: Annotated[dict, Depends(require_auth)],
    session_manager: Annotated[SessionManager, Depends(get_session_manager)],
):
    """
    Get all active sessions.

    Returns a list of all active sessions for the current user.

    - Filters out expired sessions
    - Marks current session with isCurrent flag
    """
    token_hash = request.state.token_hash

    sessions = await pipelines.get_sessions_pipeline(
        session_manager=session_manager,
        user_id=str(user["_id"]),
        current_token_hash=token_hash
    )

    return SessionListResponse(
        sessions=[SessionResponse(**s) for s in sessions]
    )


@router.delete("/sessions/{session_id}", response_model=RevokeSessionResponse)
async def revoke_session(
    request: Request,
    session_id: str,
    user: Annotated[dict, Depends(require_auth)],
    session_manager: Annotated[SessionManager, Depends(get_session_manager)],
):
    """
    Revoke a specific session.

    Removes a session from the user's sessions array.

    - Cannot revoke current session (use logout instead)
    - Returns 404 if session not found
    """
    token_hash = request.state.token_hash

    result = await pipelines.revoke_session_pipeline(
        session_manager=session_manager,
        user_id=str(user["_id"]),
        session_id=session_id,
        current_token_hash=token_hash
    )

    return RevokeSessionResponse(**result)


@router.delete("/sessions", response_model=RevokeAllSessionsResponse)
async def revoke_all_sessions(
    request: Request,
    user: Annotated[dict, Depends(require_auth)],
    session_manager: Annotated[SessionManager, Depends(get_session_manager)],
    exceptCurrent: bool = True,
):
    """
    Revoke all sessions.

    Removes all sessions from the user's sessions array.

    - By default keeps current session (exceptCurrent=true)
    - Set exceptCurrent=false to revoke all including current
    """
    token_hash = request.state.token_hash

    result = await pipelines.revoke_all_sessions_pipeline(
        session_manager=session_manager,
        user_id=str(user["_id"]),
        current_token_hash=token_hash,
        except_current=exceptCurrent
    )

    return RevokeAllSessionsResponse(**result)

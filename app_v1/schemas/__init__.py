"""
BrainBank Pydantic Schemas.

Request and response models for API endpoints.
"""

from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
    ResendVerificationRequest,
    UserResponse,
    LoginResponse,
)
from app.schemas.checkin import (
    CheckInRequest,
    CheckInMetrics,
    CheckInResponse,
    StreakResponse,
    TrendData,
    TrendsResponse,
)
from app.schemas.coach import (
    WellbeingContext,
    CoachContext,
    ChatRequest,
    SuggestedAction,
    ChatResponse,
    ConversationStarter,
)
from app.schemas.profile import (
    ProfileUpdateRequest,
    ProfileResponse,
)

__all__ = [
    # Auth schemas
    "RegisterRequest",
    "LoginRequest",
    "ForgotPasswordRequest",
    "ResetPasswordRequest",
    "VerifyEmailRequest",
    "ResendVerificationRequest",
    "UserResponse",
    "LoginResponse",
    # CheckIn schemas
    "CheckInRequest",
    "CheckInMetrics",
    "CheckInResponse",
    "StreakResponse",
    "TrendData",
    "TrendsResponse",
    # Coach schemas
    "WellbeingContext",
    "CoachContext",
    "ChatRequest",
    "SuggestedAction",
    "ChatResponse",
    "ConversationStarter",
    # Profile schemas
    "ProfileUpdateRequest",
    "ProfileResponse",
]

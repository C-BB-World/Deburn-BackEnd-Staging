"""
BrainBank Pydantic Schemas.

Request and response models for API endpoints.
"""

from app_v1.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
    ResendVerificationRequest,
    UserResponse,
    LoginResponse,
)
from app_v1.schemas.checkin import (
    CheckInRequest,
    CheckInMetrics,
    CheckInResponse,
    StreakResponse,
    TrendData,
    TrendsResponse,
)
from app_v1.schemas.coach import (
    WellbeingContext,
    CoachContext,
    ChatRequest,
    SuggestedAction,
    ChatResponse,
    ConversationStarter,
)
from app_v1.schemas.profile import (
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

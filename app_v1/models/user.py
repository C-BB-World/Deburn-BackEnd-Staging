"""
User model for BrainBank.

Matches the original Mongoose schema from models/User.js.
"""

from datetime import datetime, timezone
from typing import Optional, List
from pydantic import Field, EmailStr
from beanie import Indexed

from common.database import BaseDocument


class UserConsent(BaseDocument):
    """Embedded consent tracking (GDPR compliance)."""

    accepted: bool = False
    accepted_at: Optional[datetime] = None
    version: Optional[str] = None
    withdrawn_at: Optional[datetime] = None

    class Settings:
        name = "user_consents"


class UserSession(BaseDocument):
    """Embedded session tracking."""

    token_hash: str
    expires_at: datetime
    last_activity_at: Optional[datetime] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_info: Optional[str] = None

    class Settings:
        name = "user_sessions"


class UserProfile(BaseDocument):
    """Embedded user profile (optional, populated during onboarding)."""

    first_name: Optional[str] = Field(None, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)
    job_title: Optional[str] = Field(None, max_length=100)
    leadership_level: Optional[str] = Field(
        None,
        pattern="^(new|mid|senior|executive)$",
    )
    timezone: str = "Europe/Stockholm"
    preferred_language: str = Field("en", pattern="^(en|sv)$")
    avatar_url: Optional[str] = None

    class Settings:
        name = "user_profiles"


class User(BaseDocument):
    """
    User document for BrainBank.

    Stores user account information, authentication data, profile,
    consent tracking, and session management.
    """

    # Core identity
    email: Indexed(EmailStr, unique=True)  # type: ignore

    # Authentication
    password_hash: str = Field(..., alias="passwordHash")

    # Profile - required at registration
    organization: str = Field(..., min_length=2, max_length=100)
    country: str = Field(..., min_length=2, max_length=2)

    # Profile - optional, populated during onboarding
    profile: UserProfile = Field(default_factory=UserProfile)

    # Account status
    status: str = Field(
        "pending_verification",
        pattern="^(pending_verification|active|suspended|deleted)$",
    )

    # Email verification
    email_verification_token: Optional[str] = None
    email_verification_expires_at: Optional[datetime] = None
    email_verified_at: Optional[datetime] = None

    # Password reset
    password_reset_token: Optional[str] = None
    password_reset_expires_at: Optional[datetime] = None

    # GDPR Consent tracking
    consents: dict = Field(default_factory=lambda: {
        "terms_of_service": {"accepted": False},
        "privacy_policy": {"accepted": False},
        "data_processing": {"accepted": False},
        "marketing": {"accepted": False},
    })

    # Session tracking (simplified - full sessions in separate collection in production)
    active_sessions: List[str] = Field(default_factory=list)

    # Account deletion (GDPR right to erasure)
    deletion_requested_at: Optional[datetime] = None
    deletion_scheduled_for: Optional[datetime] = None
    deletion_completed_at: Optional[datetime] = None
    deletion_reason: Optional[str] = None

    # Coach exchange tracking for daily quota
    coach_exchange_count: int = 0
    coach_exchange_last_reset: Optional[datetime] = None

    # Timestamps
    last_login_at: Optional[datetime] = None

    class Settings:
        name = "users"
        indexes = [
            # Note: "email" is already indexed via Indexed() on the field
            "email_verification_token",
            "password_reset_token",
            "status",
            "deletion_scheduled_for",
        ]

    model_config = {"populate_by_name": True}

    @property
    def full_name(self) -> Optional[str]:
        """Get user's full name."""
        if self.profile.first_name and self.profile.last_name:
            return f"{self.profile.first_name} {self.profile.last_name}"
        return self.profile.first_name

    @property
    def display_name(self) -> str:
        """Get display name (falls back to email)."""
        return self.full_name or self.email.split("@")[0]

    def is_verified(self) -> bool:
        """Check if email is verified."""
        return self.status == "active" and self.email_verified_at is not None

    def is_active(self) -> bool:
        """Check if account is active."""
        return self.status == "active"

    def is_pending_deletion(self) -> bool:
        """Check if pending deletion."""
        return (
            self.deletion_scheduled_for is not None
            and self.deletion_completed_at is None
        )

    def to_public_dict(self) -> dict:
        """Get public profile (safe to return to client)."""
        return {
            "id": str(self.id),
            "email": self.email,
            "organization": self.organization,
            "country": self.country,
            "profile": {
                "firstName": self.profile.first_name,
                "lastName": self.profile.last_name,
                "jobTitle": self.profile.job_title,
                "leadershipLevel": self.profile.leadership_level,
                "preferredLanguage": self.profile.preferred_language,
                "avatarUrl": self.profile.avatar_url,
            },
            "displayName": self.display_name,
            "status": self.status,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    async def find_by_email(cls, email: str) -> Optional["User"]:
        """Find user by email (case-insensitive)."""
        return await cls.find_one({"email": email.lower().strip()})

    @classmethod
    async def find_pending_deletion(cls) -> List["User"]:
        """Find users pending deletion."""
        now = datetime.now(timezone.utc)
        return await cls.find(
            {
                "deletion_scheduled_for": {"$lte": now},
                "deletion_completed_at": None,
            }
        ).to_list()

    def can_use_coach(self, daily_limit: int = 15) -> bool:
        """Check if user can use coach (within daily limit)."""
        now = datetime.now(timezone.utc)

        # Reset count if it's a new day
        if self.coach_exchange_last_reset:
            last_reset_date = self.coach_exchange_last_reset.date()
            if last_reset_date < now.date():
                return True  # New day, will be reset on use

        return self.coach_exchange_count < daily_limit

    async def increment_coach_exchange(self) -> None:
        """Increment coach exchange count (resets daily)."""
        now = datetime.now(timezone.utc)

        # Reset if it's a new day
        if self.coach_exchange_last_reset:
            last_reset_date = self.coach_exchange_last_reset.date()
            if last_reset_date < now.date():
                self.coach_exchange_count = 0

        self.coach_exchange_count += 1
        self.coach_exchange_last_reset = now
        await self.save()

"""
Pydantic models for Profile request/response validation.

Matches the API documentation in docs/v2/architecture/api/profile.md
"""

from typing import Optional
from pydantic import BaseModel


# =============================================================================
# Request Schemas
# =============================================================================

class ProfileUpdateRequest(BaseModel):
    """PUT /api/profile"""
    firstName: str
    lastName: str
    organization: str
    role: str
    bio: str


class RemoveAvatarRequest(BaseModel):
    """PUT /api/profile/avatar (remove)"""
    remove: bool = True


# =============================================================================
# Response Schemas (used inside success_response data)
# =============================================================================

class UserProfile(BaseModel):
    """User profile in responses."""
    id: str
    firstName: str
    lastName: str
    email: str
    organization: str
    role: str
    bio: str

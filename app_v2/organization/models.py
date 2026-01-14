"""
Pydantic models for Organization system request/response validation.

Defines schemas for organizations and memberships.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class OrganizationSettings(BaseModel):
    """Organization settings."""
    defaultMeetingDuration: int = Field(default=60, ge=15, le=180)
    defaultGroupSize: int = Field(default=4, ge=3, le=4)
    allowMemberPoolCreation: bool = Field(default=False)
    timezone: str = Field(default="Europe/Stockholm")


class CreateOrganizationRequest(BaseModel):
    """Request to create an organization."""
    name: str = Field(..., min_length=2, max_length=100)
    domain: Optional[str] = None
    settings: Optional[OrganizationSettings] = None


class UpdateOrganizationRequest(BaseModel):
    """Request to update an organization."""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    domain: Optional[str] = None
    settings: Optional[OrganizationSettings] = None


class OrganizationResponse(BaseModel):
    """Organization in API responses."""
    id: str
    name: str
    domain: Optional[str] = None
    settings: Dict[str, Any] = {}
    status: str
    createdBy: Optional[str] = None
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None
    memberCount: Optional[int] = None
    adminCount: Optional[int] = None

    class Config:
        from_attributes = True


class AddMemberRequest(BaseModel):
    """Request to add a member."""
    userId: str
    role: str = Field(default="member", pattern="^(admin|member)$")


class ChangeMemberRoleRequest(BaseModel):
    """Request to change a member's role."""
    role: str = Field(..., pattern="^(admin|member)$")


class TransferOwnershipRequest(BaseModel):
    """Request to transfer ownership."""
    newOwnerId: str


class UserInfo(BaseModel):
    """Basic user information."""
    id: Optional[str] = None
    email: Optional[str] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None


class MemberResponse(BaseModel):
    """Member in API responses."""
    id: str
    organizationId: str
    userId: str
    role: str
    status: str
    joinedAt: Optional[datetime] = None
    invitedBy: Optional[str] = None
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None
    user: Optional[UserInfo] = None

    class Config:
        from_attributes = True


class MembersListResponse(BaseModel):
    """List of members."""
    members: List[MemberResponse]


class UserOrganization(BaseModel):
    """Organization with user's role."""
    organization: OrganizationResponse
    role: str
    joinedAt: Optional[datetime] = None


class UserOrganizationsResponse(BaseModel):
    """User's organizations."""
    organizations: List[UserOrganization]

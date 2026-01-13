"""
Organization model for BrainBank.

Matches the original Mongoose schema from models/Organization.js.
Represents a company/organization that can have multiple users and circle pools.
"""

from datetime import datetime, timezone
from typing import Optional, List
from pydantic import Field
from beanie import Indexed, PydanticObjectId

from common.database import BaseDocument


class OrganizationSettings(BaseDocument):
    """Embedded organization settings."""

    # Default meeting duration in minutes
    default_meeting_duration: int = Field(60, ge=15, le=180)

    # Default group size for circles
    default_group_size: int = Field(4, ge=3, le=4)

    # Allow members to create their own pools
    allow_member_pool_creation: bool = False

    # Timezone for organization-wide scheduling
    timezone: str = "Europe/Stockholm"

    class Settings:
        name = "organization_settings"


class Organization(BaseDocument):
    """
    Organization document for BrainBank.

    Represents a company or organization that can have multiple users
    and circle pools.
    """

    # Core identity
    name: Indexed(str)  # type: ignore

    # Optional domain for email matching (e.g., "acme.com")
    domain: Optional[str] = Field(None)

    # Organization settings
    settings: OrganizationSettings = Field(default_factory=OrganizationSettings)

    # Status
    status: str = Field("active", pattern="^(active|suspended|deleted)$")

    # Created by (first admin)
    created_by: PydanticObjectId

    class Settings:
        name = "organizations"
        indexes = [
            "name",
            "domain",
            "status",
        ]

    def is_active(self) -> bool:
        """Check if organization is active."""
        return self.status == "active"

    def to_public_dict(self) -> dict:
        """Get public representation."""
        return {
            "id": str(self.id),
            "name": self.name,
            "domain": self.domain,
            "settings": {
                "defaultMeetingDuration": self.settings.default_meeting_duration,
                "defaultGroupSize": self.settings.default_group_size,
                "allowMemberPoolCreation": self.settings.allow_member_pool_creation,
                "timezone": self.settings.timezone,
            },
            "status": self.status,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    async def find_by_domain(cls, domain: str) -> Optional["Organization"]:
        """Find organization by domain."""
        return await cls.find_one({
            "domain": domain.lower().strip(),
            "status": "active",
        })

    @classmethod
    async def find_active(cls) -> List["Organization"]:
        """Find all active organizations."""
        return await cls.find({"status": "active"}).to_list()

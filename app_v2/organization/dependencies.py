"""
FastAPI dependencies for Organization system.

Provides dependency injection for organization-related services.
"""

from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app_v2.organization.services.organization_service import OrganizationService


_organization_service: Optional[OrganizationService] = None


def init_organization_services(db: AsyncIOMotorDatabase) -> None:
    """
    Initialize organization services with database connection.

    Called once at application startup.

    Args:
        db: MongoDB database connection
    """
    global _organization_service

    _organization_service = OrganizationService(db=db)


def get_organization_service() -> OrganizationService:
    """Get organization service instance."""
    if _organization_service is None:
        raise RuntimeError("Organization services not initialized.")
    return _organization_service

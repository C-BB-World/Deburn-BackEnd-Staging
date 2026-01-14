"""
FastAPI dependencies for Hub system.

Provides dependency injection for hub-related services.
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app_v2.auth.dependencies import require_auth
from app_v2.hub.services.hub_admin_service import HubAdminService
from app_v2.hub.services.hub_content_service import HubContentService
from app_v2.hub.services.coach_config_service import CoachConfigService
from app_v2.hub.services.compliance_service import ComplianceService


_hub_db: Optional[AsyncIOMotorDatabase] = None
_app_db: Optional[AsyncIOMotorDatabase] = None
_hub_admin_service: Optional[HubAdminService] = None
_hub_content_service: Optional[HubContentService] = None
_coach_config_service: Optional[CoachConfigService] = None
_compliance_service: Optional[ComplianceService] = None


def init_hub_services(
    hub_db: AsyncIOMotorDatabase,
    app_db: AsyncIOMotorDatabase,
    prompts_dir: Optional[str] = None,
    knowledge_base_dir: Optional[str] = None
) -> None:
    """
    Initialize hub services with database connections.

    Called once at application startup.

    Args:
        hub_db: Hub MongoDB database connection
        app_db: Main application database connection
        prompts_dir: Optional prompts directory path
        knowledge_base_dir: Optional knowledge base directory path
    """
    global _hub_db, _app_db
    global _hub_admin_service, _hub_content_service
    global _coach_config_service, _compliance_service

    _hub_db = hub_db
    _app_db = app_db

    _hub_admin_service = HubAdminService(hub_db=hub_db)
    _hub_content_service = HubContentService(hub_db=hub_db)
    _coach_config_service = CoachConfigService(
        hub_db=hub_db,
        prompts_dir=prompts_dir,
        knowledge_base_dir=knowledge_base_dir
    )
    _compliance_service = ComplianceService(app_db=app_db, hub_db=hub_db)


def get_hub_admin_service() -> HubAdminService:
    """Get hub admin service instance."""
    if _hub_admin_service is None:
        raise RuntimeError("Hub services not initialized.")
    return _hub_admin_service


def get_hub_content_service() -> HubContentService:
    """Get hub content service instance."""
    if _hub_content_service is None:
        raise RuntimeError("Hub services not initialized.")
    return _hub_content_service


def get_coach_config_service() -> CoachConfigService:
    """Get coach config service instance."""
    if _coach_config_service is None:
        raise RuntimeError("Hub services not initialized.")
    return _coach_config_service


def get_compliance_service() -> ComplianceService:
    """Get compliance service instance."""
    if _compliance_service is None:
        raise RuntimeError("Hub services not initialized.")
    return _compliance_service


async def require_hub_admin(
    user: dict = Depends(require_auth),
    hub_admin_service: HubAdminService = Depends(get_hub_admin_service)
) -> dict:
    """
    Dependency that requires the user to be a hub admin.

    Args:
        user: Authenticated user
        hub_admin_service: Hub admin service

    Returns:
        User dict if they are a hub admin

    Raises:
        HTTPException: If user is not a hub admin
    """
    email = user.get("email", "")

    if not await hub_admin_service.is_hub_admin(email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hub admin access required"
        )

    return user

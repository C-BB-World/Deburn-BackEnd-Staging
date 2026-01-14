"""
Organization System.

Manages companies and groups that use the platform including
member management and organization-level settings.
"""

from app_v2.organization.services.organization_service import OrganizationService
from app_v2.organization.dependencies import (
    init_organization_services,
    get_organization_service,
)
from app_v2.organization.router import router

__all__ = [
    "OrganizationService",
    "init_organization_services",
    "get_organization_service",
    "router",
]

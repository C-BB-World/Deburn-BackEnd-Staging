"""
Hub (Platform Admin) System.

Global platform administration for managing hub admins, organizations,
content library, AI coach configuration, and GDPR compliance.
Uses a separate MongoDB database.
"""

from app_v2.hub.services.hub_admin_service import HubAdminService
from app_v2.hub.services.hub_content_service import HubContentService
from app_v2.hub.services.coach_config_service import CoachConfigService
from app_v2.hub.services.compliance_service import ComplianceService
from app_v2.hub.dependencies import (
    init_hub_services,
    get_hub_admin_service,
    get_hub_content_service,
    get_coach_config_service,
    get_compliance_service,
)
from app_v2.hub.router import router

__all__ = [
    "HubAdminService",
    "HubContentService",
    "CoachConfigService",
    "ComplianceService",
    "init_hub_services",
    "get_hub_admin_service",
    "get_hub_content_service",
    "get_coach_config_service",
    "get_compliance_service",
    "router",
]

"""
FastAPI router for Admin endpoints.

Provides admin-only statistics and management endpoints.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from app_v2.dependencies import require_hub_admin, get_compliance_service
from common.utils import success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats")
async def get_admin_stats(
    user: Annotated[dict, Depends(require_hub_admin)],
):
    """
    Get admin dashboard statistics.

    Returns high-level platform statistics for administrators.
    """
    compliance_service = get_compliance_service()

    stats = await compliance_service.get_stats()

    return success_response({
        "totalUsers": stats.get("totalUsers", 0),
        "activeUsers": stats.get("activeUsers", 0),
        "totalCheckins": stats.get("totalCheckins", 0),
        "totalSessions": stats.get("activeSessions", 0),
    })

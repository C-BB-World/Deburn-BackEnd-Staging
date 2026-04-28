"""
Admin Router.

Handles admin statistics and management.
"""

from fastapi import APIRouter, Depends

from common.utils import success_response

from app_v1.models import User, CheckIn
from app_v1.dependencies import get_current_user, require_admin

router = APIRouter()


# =============================================================================
# GET /api/admin/stats
# =============================================================================
@router.get("/stats")
async def get_stats(
    user: User = Depends(require_admin),
):
    """
    Get admin statistics.

    Requires admin access.
    """
    # Get counts for the user's organization
    org_name = user.organization

    # Total users in org
    total_users = await User.find(User.organization == org_name).count()

    # Active users (status = active)
    active_users = await User.find(
        User.organization == org_name,
        User.status == "active",
    ).count()

    # Total check-ins from org users
    org_users = await User.find(User.organization == org_name).to_list()
    user_ids = [str(u.id) for u in org_users]

    total_checkins = 0
    if user_ids:
        total_checkins = await CheckIn.find(
            {"user_id": {"$in": user_ids}}
        ).count()

    # Calculate average streak (simplified - just use active users)
    # In production, you'd calculate this properly
    average_streak = 0.0
    if active_users > 0:
        # Just a placeholder calculation
        average_streak = total_checkins / active_users if active_users else 0

    return success_response({
        "totalUsers": total_users,
        "activeUsers": active_users,
        "totalCheckIns": total_checkins,
        "averageStreak": round(average_streak, 1),
    })

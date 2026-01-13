"""
Hub Router.

Handles hub admin and organization management.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from common.utils import success_response

from app.models import User, Organization
from app.dependencies import get_current_user

router = APIRouter()


# =============================================================================
# Helper Functions
# =============================================================================
async def get_user_organization(user: User) -> Organization:
    """
    Get the organization where the user is an admin.

    Raises:
        HTTPException: If user is not an org admin.
    """
    # TODO: Implement proper org admin check via OrganizationMember
    # For now, find organization by name matching user's organization field
    org = await Organization.find_one(Organization.name == user.organization)

    if not org:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "error": {
                    "code": "NOT_ORG_ADMIN",
                    "message": "You are not an admin of any organization",
                },
            },
        )

    return org


# =============================================================================
# GET /api/hub/organization
# =============================================================================
@router.get("/organization")
async def get_organization(
    user: User = Depends(get_current_user),
):
    """
    Get organization details for the current user's organization.
    """
    org = await get_user_organization(user)

    # Count members (users with matching organization name)
    member_count = await User.find(User.organization == org.name).count()

    return success_response({
        "organization": {
            "id": str(org.id),
            "name": org.name,
            "domain": org.domain,
            "memberCount": member_count,
            "createdAt": org.created_at.isoformat() if org.created_at else None,
        },
    })


# =============================================================================
# GET /api/hub/members
# =============================================================================
@router.get("/members")
async def get_members(
    user: User = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0,
    status_filter: str = None,
):
    """
    Get members of the current user's organization.
    """
    org = await get_user_organization(user)

    # Build query
    query = User.find(User.organization == org.name)

    if status_filter:
        query = query.find(User.status == status_filter)

    # Get total count
    total = await User.find(User.organization == org.name).count()

    # Get paginated members
    members = await query.skip(offset).limit(limit).to_list()

    return success_response({
        "members": [
            {
                "id": str(m.id),
                "email": m.email,
                "name": f"{m.profile.first_name or ''} {m.profile.last_name or ''}".strip() if m.profile else None,
                "role": "member",  # TODO: Get from OrganizationMember
                "status": m.status,
                "joinedAt": m.created_at.isoformat() if m.created_at else None,
            }
            for m in members
        ],
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "hasMore": offset + len(members) < total,
        },
    })

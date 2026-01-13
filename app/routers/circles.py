"""
Circles Router.

Handles peer support groups and invitations.
"""

from fastapi import APIRouter, Depends

from common.utils import success_response

from app.models import User
from app.dependencies import get_current_user

router = APIRouter()


# =============================================================================
# GET /api/circles/groups
# =============================================================================
@router.get("/groups")
async def get_groups(
    user: User = Depends(get_current_user),
):
    """
    Get the user's peer support groups.
    """
    # TODO: Implement when CircleGroup model is added
    # groups = await CircleGroup.find(
    #     CircleGroup.members.user_id == str(user.id),
    #     CircleGroup.status == "active",
    # ).to_list()

    return success_response({
        "groups": [],
    })


# =============================================================================
# GET /api/circles/invitations
# =============================================================================
@router.get("/invitations")
async def get_invitations(
    user: User = Depends(get_current_user),
):
    """
    Get pending circle invitations for the user.
    """
    # TODO: Implement when CircleInvitation model is added
    # invitations = await CircleInvitation.find(
    #     CircleInvitation.email == user.email,
    #     CircleInvitation.status == "pending",
    # ).to_list()

    return success_response({
        "invitations": [],
    })

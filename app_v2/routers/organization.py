"""
FastAPI router for Organization system endpoints.

Provides endpoints for organization and member management.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from app_v2.dependencies import require_auth, get_organization_service
from app_v2.services.organization.organization_service import OrganizationService
from app_v2.schemas.organization import (
    CreateOrganizationRequest,
    UpdateOrganizationRequest,
    AddMemberRequest,
    ChangeMemberRoleRequest,
    TransferOwnershipRequest,
    OrganizationResponse,
    MemberResponse,
    MembersListResponse,
    UserOrganizationsResponse,
    UserOrganization,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("", response_model=OrganizationResponse)
async def create_organization(
    request: CreateOrganizationRequest,
    user: Annotated[dict, Depends(require_auth)],
    org_service: Annotated[OrganizationService, Depends(get_organization_service)],
):
    """Create a new organization. Creator becomes first admin."""
    settings_dict = request.settings.model_dump() if request.settings else None

    org = await org_service.create_organization(
        name=request.name,
        created_by=str(user["_id"]),
        domain=request.domain,
        settings=settings_dict,
    )

    return OrganizationResponse(**org)


@router.get("/mine", response_model=UserOrganizationsResponse)
async def get_my_organizations(
    user: Annotated[dict, Depends(require_auth)],
    org_service: Annotated[OrganizationService, Depends(get_organization_service)],
):
    """Get all organizations the current user belongs to."""
    orgs = await org_service.get_user_organizations(str(user["_id"]))

    return UserOrganizationsResponse(
        organizations=[
            UserOrganization(
                organization=OrganizationResponse(**o["organization"]),
                role=o["role"],
                joinedAt=o["joinedAt"],
            )
            for o in orgs
        ]
    )


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization_id: str,
    user: Annotated[dict, Depends(require_auth)],
    org_service: Annotated[OrganizationService, Depends(get_organization_service)],
):
    """Get organization details with stats."""
    org = await org_service.get_organization_with_stats(organization_id)
    return OrganizationResponse(**org)


@router.put("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: str,
    request: UpdateOrganizationRequest,
    user: Annotated[dict, Depends(require_auth)],
    org_service: Annotated[OrganizationService, Depends(get_organization_service)],
):
    """Update organization settings. Admin only."""
    updates = request.model_dump(exclude_unset=True)

    if "settings" in updates and updates["settings"]:
        updates["settings"] = updates["settings"].model_dump() if hasattr(updates["settings"], "model_dump") else updates["settings"]

    org = await org_service.update_organization(
        organization_id=organization_id,
        updates=updates,
        updated_by=str(user["_id"]),
    )

    return OrganizationResponse(**org)


@router.get("/{organization_id}/members", response_model=MembersListResponse)
async def get_members(
    organization_id: str,
    user: Annotated[dict, Depends(require_auth)],
    org_service: Annotated[OrganizationService, Depends(get_organization_service)],
    role: str = None,
):
    """Get organization members."""
    members = await org_service.get_members(organization_id, role=role)

    return MembersListResponse(
        members=[MemberResponse(**m) for m in members]
    )


@router.post("/{organization_id}/members", response_model=MemberResponse)
async def add_member(
    organization_id: str,
    request: AddMemberRequest,
    user: Annotated[dict, Depends(require_auth)],
    org_service: Annotated[OrganizationService, Depends(get_organization_service)],
):
    """Add a member to the organization. Admin only."""
    member = await org_service.add_member(
        organization_id=organization_id,
        user_id=request.userId,
        role=request.role,
        invited_by=str(user["_id"]),
    )

    return MemberResponse(**member)


@router.delete("/{organization_id}/members/{user_id}")
async def remove_member(
    organization_id: str,
    user_id: str,
    user: Annotated[dict, Depends(require_auth)],
    org_service: Annotated[OrganizationService, Depends(get_organization_service)],
):
    """Remove a member from the organization. Admin only."""
    await org_service.remove_member(
        organization_id=organization_id,
        user_id=user_id,
        removed_by=str(user["_id"]),
    )

    return {"success": True}


@router.post("/{organization_id}/leave")
async def leave_organization(
    organization_id: str,
    user: Annotated[dict, Depends(require_auth)],
    org_service: Annotated[OrganizationService, Depends(get_organization_service)],
):
    """Leave an organization voluntarily."""
    await org_service.leave_organization(
        organization_id=organization_id,
        user_id=str(user["_id"]),
    )

    return {"success": True}


@router.put("/{organization_id}/members/{user_id}/role", response_model=MemberResponse)
async def change_member_role(
    organization_id: str,
    user_id: str,
    request: ChangeMemberRoleRequest,
    user: Annotated[dict, Depends(require_auth)],
    org_service: Annotated[OrganizationService, Depends(get_organization_service)],
):
    """Change a member's role. Admin only."""
    member = await org_service.change_member_role(
        organization_id=organization_id,
        user_id=user_id,
        new_role=request.role,
        changed_by=str(user["_id"]),
    )

    return MemberResponse(**member)


@router.post("/{organization_id}/transfer-ownership", response_model=OrganizationResponse)
async def transfer_ownership(
    organization_id: str,
    request: TransferOwnershipRequest,
    user: Annotated[dict, Depends(require_auth)],
    org_service: Annotated[OrganizationService, Depends(get_organization_service)],
):
    """Transfer organization ownership to another member. Admin only."""
    org = await org_service.transfer_ownership(
        organization_id=organization_id,
        new_owner_id=request.newOwnerId,
        transferred_by=str(user["_id"]),
    )

    return OrganizationResponse(**org)

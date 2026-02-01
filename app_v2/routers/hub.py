"""
FastAPI router for Hub system endpoints.

Provides endpoints for platform administration.
"""

import io
import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, UploadFile, File, Query, HTTPException
from fastapi.responses import StreamingResponse

from app_v2.dependencies import (
    require_hub_admin,
    get_hub_admin_service,
    get_hub_content_service,
    get_coach_config_service,
    get_compliance_service,
    get_organization_service,
)
from app_v2.schemas.hub import (
    AddHubAdminRequest,
    CreateOrganizationRequest,
    AddOrgAdminRequest,
    UpdateCoachSettingsRequest,
    UpdatePromptRequest,
    UpdateExercisesRequest,
    CreateContentRequest,
    UpdateContentRequest,
)
from common.utils import success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hub", tags=["hub"])


# =============================================================================
# Hub Admin Endpoints
# =============================================================================

@router.get("/admins")
async def get_hub_admins(
    user: Annotated[dict, Depends(require_hub_admin)],
):
    """List all active hub admins."""
    admin_service = get_hub_admin_service()
    admins = await admin_service.get_active_admins()

    return success_response({
        "admins": [
            {
                "id": str(a.get("_id", a.get("id", ""))),
                "email": a.get("email", ""),
            }
            for a in admins
        ]
    })


@router.post("/admins")
async def add_hub_admin(
    body: AddHubAdminRequest,
    user: Annotated[dict, Depends(require_hub_admin)],
):
    """Add a new hub admin."""
    admin_service = get_hub_admin_service()
    await admin_service.add_admin(
        email=body.email,
        added_by=user.get("email", "")
    )

    return success_response(None)


@router.delete("/admins/{email}")
async def remove_hub_admin(
    email: str,
    user: Annotated[dict, Depends(require_hub_admin)],
):
    """Remove a hub admin."""
    admin_service = get_hub_admin_service()
    await admin_service.remove_admin(
        email=email,
        removed_by=user.get("email", "")
    )

    return success_response(None)


# =============================================================================
# Organization Endpoints
# =============================================================================

@router.get("/organization")
async def get_organization(
    user: Annotated[dict, Depends(require_hub_admin)],
):
    """Get organization details."""

    org_service = get_organization_service()
    # Get first organization (or user's organization)
    organizations = await org_service.get_all_organizations()

    if not organizations:
        return success_response(None)

    org = organizations[0]
    return success_response({
        "id": str(org["_id"]),
        "name": org.get("name"),
        "memberCount": org.get("memberCount", 0),
        "activeUsers": org.get("activeUsers", 0),
        "completedLessons": org.get("completedLessons", 0),
        "avgEngagement": org.get("avgEngagement", 0),
    })


@router.get("/members")
async def get_members(
    user: Annotated[dict, Depends(require_hub_admin)],
):
    """Get organization members."""

    org_service = get_organization_service()
    members = await org_service.get_organization_members()

    return success_response({
        "members": [
            {
                "id": str(m.get("_id", m.get("id", ""))),
                "name": f"{m.get('firstName', '')} {m.get('lastName', '')}".strip(),
                "email": m.get("email", ""),
                "role": m.get("role", "member"),
            }
            for m in members
        ]
    })


@router.get("/organizations")
async def get_organizations(
    user: Annotated[dict, Depends(require_hub_admin)],
):
    """Get all organizations."""

    org_service = get_organization_service()
    organizations = await org_service.get_all_organizations()

    return success_response({
        "organizations": [
            {
                "id": str(org["_id"]),
                "name": org.get("name"),
                "domain": org.get("domain"),
                "memberCount": org.get("memberCount", 0),
            }
            for org in organizations
        ]
    })


@router.post("/organizations")
async def create_organization(
    body: CreateOrganizationRequest,
    user: Annotated[dict, Depends(require_hub_admin)],
):
    """Create a new organization."""

    org_service = get_organization_service()
    org = await org_service.create_organization(
        name=body.name,
        domain=body.domain
    )

    return success_response({
        "organization": {
            "id": str(org["_id"]),
            "name": org.get("name"),
            "domain": org.get("domain"),
            "memberCount": 0,
        }
    })


# =============================================================================
# Org Admin Endpoints
# =============================================================================

@router.get("/org-admins")
async def get_org_admins(
    user: Annotated[dict, Depends(require_hub_admin)],
):
    """Get all organization admins."""

    org_service = get_organization_service()
    admins = await org_service.get_org_admins()

    return success_response({"admins": admins})


@router.post("/org-admins")
async def add_org_admin(
    body: AddOrgAdminRequest,
    user: Annotated[dict, Depends(require_hub_admin)],
):
    """Add an organization admin."""

    org_service = get_organization_service()
    await org_service.add_org_admin(
        email=body.email,
        organization_id=body.organizationId
    )

    return success_response(None)


@router.delete("/org-admins/{membership_id}")
async def remove_org_admin(
    membership_id: str,
    user: Annotated[dict, Depends(require_hub_admin)],
):
    """Remove an organization admin membership."""

    org_service = get_organization_service()
    await org_service.remove_org_admin(membership_id)

    return success_response(None)


# =============================================================================
# Coach Settings Endpoints
# =============================================================================

@router.get("/settings/coach")
async def get_coach_settings(
    user: Annotated[dict, Depends(require_hub_admin)],
):
    """Get AI coach settings."""
    config_service = get_coach_config_service()
    settings = await config_service.get_coach_settings()

    return success_response(settings)


@router.put("/settings/coach")
async def update_coach_settings(
    body: UpdateCoachSettingsRequest,
    user: Annotated[dict, Depends(require_hub_admin)],
):
    """Update AI coach settings."""
    config_service = get_coach_config_service()
    settings = await config_service.update_coach_settings(
        daily_exchange_limit=body.maxTokens,
        deletion_grace_period_days=None,
        admin_email=user.get("email", "")
    )

    return success_response(settings)


@router.get("/coach/prompts")
async def get_prompts(
    user: Annotated[dict, Depends(require_hub_admin)],
):
    """Get coach prompts."""
    config_service = get_coach_config_service()
    prompts = await config_service.get_prompts()

    return success_response({"prompts": prompts})


@router.put("/coach/prompts/{language}/{prompt_name}")
async def update_prompt(
    language: str,
    prompt_name: str,
    body: UpdatePromptRequest,
    user: Annotated[dict, Depends(require_hub_admin)],
):
    """Update a coach prompt."""
    config_service = get_coach_config_service()
    await config_service.update_prompt(
        language=language,
        prompt_name=prompt_name,
        content=body.content
    )

    return success_response(None)


@router.get("/coach/exercises")
async def get_exercises(
    user: Annotated[dict, Depends(require_hub_admin)],
):
    """Get coach exercises."""
    config_service = get_coach_config_service()
    data = await config_service.get_exercises()

    return success_response({"exercises": data.get("exercises", [])})


@router.put("/coach/exercises")
async def update_exercises(
    body: UpdateExercisesRequest,
    user: Annotated[dict, Depends(require_hub_admin)],
):
    """Update coach exercises."""
    config_service = get_coach_config_service()
    await config_service.update_exercises(
        exercises=[e.model_dump() for e in body.exercises],
        modules=[]
    )

    return success_response(None)


@router.get("/coach/config")
async def get_coach_config(
    user: Annotated[dict, Depends(require_hub_admin)],
):
    """Get coach configuration."""
    config_service = get_coach_config_service()
    config = await config_service.get_coach_settings()

    return success_response(config)


# =============================================================================
# Content Library Endpoints
# =============================================================================

@router.get("/content")
async def get_content_list(
    user: Annotated[dict, Depends(require_hub_admin)],
    contentType: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
):
    """Get content library items."""
    content_service = get_hub_content_service()
    items = await content_service.get_all(
        content_type=contentType,
        status=status,
        category=category
    )

    return success_response({
        "items": [
            {
                "id": str(i.get("_id", i.get("id", ""))),
                "title": i.get("titleEn", ""),
                "description": i.get("purpose", ""),
                "contentType": i.get("contentType", ""),
                "category": i.get("category", ""),
                "duration": i.get("lengthMinutes", 0),
                "thumbnail": i.get("thumbnail"),
                "status": i.get("status", "draft"),
            }
            for i in items
        ]
    })


@router.get("/content/{content_id}")
async def get_content_item(
    content_id: str,
    user: Annotated[dict, Depends(require_hub_admin)],
):
    """Get a single content item."""
    content_service = get_hub_content_service()
    item = await content_service.get_by_id(content_id)

    if not item:
        raise HTTPException(status_code=404, detail={"message": "Content not found"})

    return success_response({
        "id": str(item.get("_id", item.get("id", ""))),
        "title": item.get("titleEn", ""),
        "description": item.get("purpose", ""),
        "contentType": item.get("contentType", ""),
        "category": item.get("category", ""),
        "duration": item.get("lengthMinutes", 0),
        "thumbnail": item.get("thumbnail"),
        "status": item.get("status", "draft"),
        "content": item,
    })


@router.post("/content")
async def create_content_item(
    body: CreateContentRequest,
    user: Annotated[dict, Depends(require_hub_admin)],
):
    """Create new content."""
    content_service = get_hub_content_service()

    data = {
        "titleEn": body.title,
        "purpose": body.description,
        "contentType": body.contentType,
        "category": body.category,
        "lengthMinutes": body.duration or 0,
        "thumbnail": body.thumbnail,
        "status": body.status,
    }
    if body.content:
        data.update(body.content)

    item = await content_service.create(data)

    return success_response({
        "id": str(item.get("_id", item.get("id", ""))),
        "title": item.get("titleEn", ""),
        "status": item.get("status", "draft"),
    })


@router.put("/content/{content_id}")
async def update_content_item(
    content_id: str,
    body: UpdateContentRequest,
    user: Annotated[dict, Depends(require_hub_admin)],
):
    """Update content."""
    content_service = get_hub_content_service()

    data = {}
    if body.title is not None:
        data["titleEn"] = body.title
    if body.description is not None:
        data["purpose"] = body.description
    if body.category is not None:
        data["category"] = body.category
    if body.duration is not None:
        data["lengthMinutes"] = body.duration
    if body.thumbnail is not None:
        data["thumbnail"] = body.thumbnail
    if body.status is not None:
        data["status"] = body.status
    if body.content is not None:
        data.update(body.content)

    item = await content_service.update(
        content_id=content_id,
        data=data
    )

    if not item:
        raise HTTPException(status_code=404, detail={"message": "Content not found"})

    return success_response({
        "id": str(item.get("_id", item.get("id", ""))),
        "title": item.get("titleEn", ""),
        "status": item.get("status", "draft"),
    })


@router.delete("/content/{content_id}")
async def delete_content_item(
    content_id: str,
    user: Annotated[dict, Depends(require_hub_admin)],
):
    """Delete content."""
    content_service = get_hub_content_service()
    await content_service.delete(content_id)

    return success_response(None)


@router.post("/content/{content_id}/audio/{lang}")
async def upload_content_audio(
    content_id: str,
    lang: str,
    file: UploadFile = File(...),
    user: Annotated[dict, Depends(require_hub_admin)] = None,
):
    """Upload audio for content."""
    content_service = get_hub_content_service()
    audio_data = await file.read()

    url = await content_service.upload_audio(
        content_id=content_id,
        language=lang,
        audio_data=audio_data,
        mime_type=file.content_type or "audio/mpeg"
    )

    return success_response({"audioUrl": url})


@router.delete("/content/{content_id}/audio/{lang}")
async def remove_content_audio(
    content_id: str,
    lang: str,
    user: Annotated[dict, Depends(require_hub_admin)],
):
    """Remove audio from content."""
    content_service = get_hub_content_service()
    await content_service.remove_audio(content_id, lang)

    return success_response(None)


# =============================================================================
# Compliance Endpoints
# =============================================================================

@router.get("/compliance/stats")
async def get_compliance_stats(
    user: Annotated[dict, Depends(require_hub_admin)],
):
    """Get compliance statistics."""
    compliance_service = get_compliance_service()
    stats = await compliance_service.get_stats()

    return success_response(stats)


@router.get("/compliance/user/{email}")
async def get_user_compliance(
    email: str,
    user: Annotated[dict, Depends(require_hub_admin)],
):
    """Get compliance info for a user."""
    compliance_service = get_compliance_service()
    data = await compliance_service.get_user_compliance_data(email)

    if not data:
        raise HTTPException(status_code=404, detail={"message": "User not found"})

    return success_response(data)


@router.post("/compliance/export/{user_id}")
async def export_user_data(
    user_id: str,
    user: Annotated[dict, Depends(require_hub_admin)],
):
    """Export user data."""
    compliance_service = get_compliance_service()
    data = await compliance_service.export_user_data(
        user_id=user_id,
        exported_by=user.get("email", "")
    )

    return success_response(data)


@router.post("/compliance/delete/{user_id}")
async def delete_user_data(
    user_id: str,
    user: Annotated[dict, Depends(require_hub_admin)],
):
    """Delete user account."""
    compliance_service = get_compliance_service()
    result = await compliance_service.delete_user_account(
        user_id=user_id,
        deleted_by=user.get("email", "")
    )

    return success_response(result)


@router.get("/compliance/pending-deletions")
async def get_pending_deletions(
    user: Annotated[dict, Depends(require_hub_admin)],
):
    """Get pending account deletions."""
    compliance_service = get_compliance_service()
    deletions = await compliance_service.get_pending_deletions()

    return success_response({"pendingDeletions": deletions})


@router.post("/compliance/cleanup-sessions")
async def cleanup_sessions(
    user: Annotated[dict, Depends(require_hub_admin)],
):
    """Clean up expired sessions."""
    compliance_service = get_compliance_service()
    count = await compliance_service.cleanup_expired_sessions()

    return success_response({"cleanedCount": count})


@router.get("/compliance/security-config")
async def get_security_config(
    user: Annotated[dict, Depends(require_hub_admin)],
):
    """Get security configuration."""
    compliance_service = get_compliance_service()
    config = await compliance_service.get_security_config()

    return success_response(config)

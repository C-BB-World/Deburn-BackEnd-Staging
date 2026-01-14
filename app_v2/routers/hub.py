"""
FastAPI router for Hub system endpoints.

Provides endpoints for platform administration.
"""

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, UploadFile, File, Query
from fastapi.responses import StreamingResponse
import io

from app_v2.dependencies import (
    require_hub_admin,
    get_hub_admin_service,
    get_hub_content_service,
    get_coach_config_service,
    get_compliance_service,
)
from app_v2.services.hub.hub_admin_service import HubAdminService
from app_v2.services.hub.hub_content_service import HubContentService
from app_v2.services.hub.coach_config_service import CoachConfigService
from app_v2.services.hub.compliance_service import ComplianceService
from app_v2.schemas.hub import (
    AddHubAdminRequest,
    RemoveHubAdminRequest,
    HubAdminResponse,
    HubAdminsListResponse,
    CreateContentRequest,
    UpdateContentRequest,
    ContentResponse,
    ContentListResponse,
    UpdatePromptRequest,
    PromptsResponse,
    ExercisesResponse,
    UpdateExercisesRequest,
    CoachSettingsResponse,
    UpdateCoachSettingsRequest,
    SafetyConfigResponse,
    SafetyLevelInfo,
    ComplianceStatsResponse,
    UserComplianceResponse,
    LookupUserRequest,
    DeleteUserRequest,
    ExportUserRequest,
    PendingDeletionsListResponse,
    PendingDeletionResponse,
    DeletionResultResponse,
    SecurityConfigResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hub", tags=["hub"])


# ─────────────────────────────────────────────────────────────────
# Hub Admin Endpoints
# ─────────────────────────────────────────────────────────────────

@router.get("/admins", response_model=HubAdminsListResponse)
async def get_hub_admins(
    user: Annotated[dict, Depends(require_hub_admin)],
    admin_service: Annotated[HubAdminService, Depends(get_hub_admin_service)],
):
    """List all active hub admins."""
    admins = await admin_service.get_active_admins()
    return HubAdminsListResponse(
        admins=[HubAdminResponse(**a) for a in admins]
    )


@router.post("/admins", response_model=HubAdminResponse)
async def add_hub_admin(
    request: AddHubAdminRequest,
    user: Annotated[dict, Depends(require_hub_admin)],
    admin_service: Annotated[HubAdminService, Depends(get_hub_admin_service)],
):
    """Add a new hub admin or reactivate a removed one."""
    admin = await admin_service.add_admin(
        email=request.email,
        added_by=user.get("email", "")
    )
    return HubAdminResponse(**admin)


@router.delete("/admins", response_model=HubAdminResponse)
async def remove_hub_admin(
    request: RemoveHubAdminRequest,
    user: Annotated[dict, Depends(require_hub_admin)],
    admin_service: Annotated[HubAdminService, Depends(get_hub_admin_service)],
):
    """Remove (soft delete) a hub admin."""
    admin = await admin_service.remove_admin(
        email=request.email,
        removed_by=user.get("email", "")
    )
    return HubAdminResponse(**admin)


# ─────────────────────────────────────────────────────────────────
# Content Library Endpoints
# ─────────────────────────────────────────────────────────────────

@router.get("/content", response_model=ContentListResponse)
async def get_content_list(
    user: Annotated[dict, Depends(require_hub_admin)],
    content_service: Annotated[HubContentService, Depends(get_hub_content_service)],
    content_type: Optional[str] = Query(None, alias="contentType"),
    status: Optional[str] = None,
    category: Optional[str] = None,
):
    """Get all content items with optional filters."""
    items = await content_service.get_all(
        content_type=content_type,
        status=status,
        category=category
    )
    return ContentListResponse(items=[ContentResponse(**i) for i in items])


@router.get("/content/{content_id}", response_model=ContentResponse)
async def get_content_item(
    content_id: str,
    user: Annotated[dict, Depends(require_hub_admin)],
    content_service: Annotated[HubContentService, Depends(get_hub_content_service)],
):
    """Get a single content item."""
    item = await content_service.get_by_id(content_id)
    if not item:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Content not found")
    return ContentResponse(**item)


@router.post("/content", response_model=ContentResponse)
async def create_content_item(
    request: CreateContentRequest,
    user: Annotated[dict, Depends(require_hub_admin)],
    content_service: Annotated[HubContentService, Depends(get_hub_content_service)],
):
    """Create a new content item."""
    item = await content_service.create(request.model_dump())
    return ContentResponse(**item)


@router.put("/content/{content_id}", response_model=ContentResponse)
async def update_content_item(
    content_id: str,
    request: UpdateContentRequest,
    user: Annotated[dict, Depends(require_hub_admin)],
    content_service: Annotated[HubContentService, Depends(get_hub_content_service)],
):
    """Update a content item."""
    item = await content_service.update(
        content_id=content_id,
        data=request.model_dump(exclude_unset=True)
    )
    if not item:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Content not found")
    return ContentResponse(**item)


@router.delete("/content/{content_id}")
async def delete_content_item(
    content_id: str,
    user: Annotated[dict, Depends(require_hub_admin)],
    content_service: Annotated[HubContentService, Depends(get_hub_content_service)],
):
    """Delete a content item."""
    deleted = await content_service.delete(content_id)
    return {"success": deleted}


@router.post("/content/{content_id}/audio/{language}")
async def upload_content_audio(
    content_id: str,
    language: str,
    file: UploadFile = File(...),
    user: Annotated[dict, Depends(require_hub_admin)] = None,
    content_service: Annotated[HubContentService, Depends(get_hub_content_service)] = None,
):
    """Upload audio file for a content item."""
    audio_data = await file.read()
    url = await content_service.upload_audio(
        content_id=content_id,
        language=language,
        audio_data=audio_data,
        mime_type=file.content_type or "audio/mpeg"
    )
    return {"success": True, "audioUrl": url}


@router.get("/content/{content_id}/audio/{language}")
async def stream_content_audio(
    content_id: str,
    language: str,
    content_service: Annotated[HubContentService, Depends(get_hub_content_service)],
):
    """Stream audio file for a content item."""
    audio = await content_service.get_audio(content_id, language)
    if not audio:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Audio not found")

    return StreamingResponse(
        io.BytesIO(audio["audioData"]),
        media_type=audio["mimeType"],
        headers={
            "Content-Disposition": f"inline; filename={content_id}_{language}.mp3"
        }
    )


@router.delete("/content/{content_id}/audio/{language}")
async def remove_content_audio(
    content_id: str,
    language: str,
    user: Annotated[dict, Depends(require_hub_admin)],
    content_service: Annotated[HubContentService, Depends(get_hub_content_service)],
):
    """Remove audio file from a content item."""
    removed = await content_service.remove_audio(content_id, language)
    return {"success": removed}


# ─────────────────────────────────────────────────────────────────
# Coach Configuration Endpoints
# ─────────────────────────────────────────────────────────────────

@router.get("/coach/prompts", response_model=PromptsResponse)
async def get_prompts(
    user: Annotated[dict, Depends(require_hub_admin)],
    config_service: Annotated[CoachConfigService, Depends(get_coach_config_service)],
):
    """Get all system prompts."""
    prompts = await config_service.get_prompts()
    return PromptsResponse(prompts=prompts)


@router.put("/coach/prompts")
async def update_prompt(
    request: UpdatePromptRequest,
    user: Annotated[dict, Depends(require_hub_admin)],
    config_service: Annotated[CoachConfigService, Depends(get_coach_config_service)],
):
    """Update a system prompt."""
    await config_service.update_prompt(
        language=request.language,
        prompt_name=request.promptName,
        content=request.content
    )
    return {"success": True}


@router.get("/coach/exercises", response_model=ExercisesResponse)
async def get_exercises(
    user: Annotated[dict, Depends(require_hub_admin)],
    config_service: Annotated[CoachConfigService, Depends(get_coach_config_service)],
):
    """Get exercises and modules."""
    data = await config_service.get_exercises()
    return ExercisesResponse(
        exercises=data.get("exercises", []),
        modules=data.get("modules", [])
    )


@router.put("/coach/exercises")
async def update_exercises(
    request: UpdateExercisesRequest,
    user: Annotated[dict, Depends(require_hub_admin)],
    config_service: Annotated[CoachConfigService, Depends(get_coach_config_service)],
):
    """Update exercises and modules."""
    await config_service.update_exercises(
        exercises=request.exercises,
        modules=request.modules
    )
    return {"success": True}


@router.get("/coach/settings", response_model=CoachSettingsResponse)
async def get_coach_settings(
    user: Annotated[dict, Depends(require_hub_admin)],
    config_service: Annotated[CoachConfigService, Depends(get_coach_config_service)],
):
    """Get coach settings."""
    settings = await config_service.get_coach_settings()
    return CoachSettingsResponse(**settings)


@router.put("/coach/settings", response_model=CoachSettingsResponse)
async def update_coach_settings(
    request: UpdateCoachSettingsRequest,
    user: Annotated[dict, Depends(require_hub_admin)],
    config_service: Annotated[CoachConfigService, Depends(get_coach_config_service)],
):
    """Update coach settings."""
    settings = await config_service.update_coach_settings(
        daily_exchange_limit=request.dailyExchangeLimit,
        deletion_grace_period_days=request.deletionGracePeriodDays,
        admin_email=user.get("email", "")
    )
    return CoachSettingsResponse(**settings)


@router.get("/coach/safety", response_model=SafetyConfigResponse)
async def get_safety_config(
    user: Annotated[dict, Depends(require_hub_admin)],
    config_service: Annotated[CoachConfigService, Depends(get_coach_config_service)],
):
    """Get safety configuration (read-only)."""
    config = config_service.get_safety_config()
    return SafetyConfigResponse(
        levels=[SafetyLevelInfo(**level) for level in config["levels"]],
        hard_boundaries=config["hard_boundaries"]
    )


# ─────────────────────────────────────────────────────────────────
# Compliance Endpoints
# ─────────────────────────────────────────────────────────────────

@router.get("/compliance/stats", response_model=ComplianceStatsResponse)
async def get_compliance_stats(
    user: Annotated[dict, Depends(require_hub_admin)],
    compliance_service: Annotated[ComplianceService, Depends(get_compliance_service)],
):
    """Get compliance dashboard statistics."""
    stats = await compliance_service.get_stats()
    return ComplianceStatsResponse(**stats)


@router.post("/compliance/lookup", response_model=UserComplianceResponse)
async def lookup_user(
    request: LookupUserRequest,
    user: Annotated[dict, Depends(require_hub_admin)],
    compliance_service: Annotated[ComplianceService, Depends(get_compliance_service)],
):
    """Look up user by email for compliance review."""
    data = await compliance_service.get_user_compliance_data(request.email)
    if not data:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")
    return UserComplianceResponse(**data)


@router.post("/compliance/export")
async def export_user_data(
    request: ExportUserRequest,
    user: Annotated[dict, Depends(require_hub_admin)],
    compliance_service: Annotated[ComplianceService, Depends(get_compliance_service)],
):
    """Export user data (GDPR Article 20)."""
    data = await compliance_service.export_user_data(
        user_id=request.userId,
        exported_by=user.get("email", "")
    )
    return data


@router.delete("/compliance/user", response_model=DeletionResultResponse)
async def delete_user_account(
    request: DeleteUserRequest,
    user: Annotated[dict, Depends(require_hub_admin)],
    compliance_service: Annotated[ComplianceService, Depends(get_compliance_service)],
):
    """Permanently delete user account (GDPR Article 17)."""
    result = await compliance_service.delete_user_account(
        user_id=request.userId,
        deleted_by=user.get("email", "")
    )
    return DeletionResultResponse(**result)


@router.get("/compliance/pending-deletions", response_model=PendingDeletionsListResponse)
async def get_pending_deletions(
    user: Annotated[dict, Depends(require_hub_admin)],
    compliance_service: Annotated[ComplianceService, Depends(get_compliance_service)],
):
    """Get users with pending deletion requests."""
    deletions = await compliance_service.get_pending_deletions()
    return PendingDeletionsListResponse(
        pendingDeletions=[PendingDeletionResponse(**d) for d in deletions]
    )


@router.post("/compliance/cleanup-sessions")
async def cleanup_sessions(
    user: Annotated[dict, Depends(require_hub_admin)],
    compliance_service: Annotated[ComplianceService, Depends(get_compliance_service)],
):
    """Remove expired sessions from all users."""
    count = await compliance_service.cleanup_expired_sessions()
    return {"success": True, "cleanedCount": count}


@router.get("/compliance/security", response_model=SecurityConfigResponse)
async def get_security_config(
    user: Annotated[dict, Depends(require_hub_admin)],
    compliance_service: Annotated[ComplianceService, Depends(get_compliance_service)],
):
    """Get security configuration (read-only)."""
    config = await compliance_service.get_security_config()
    return SecurityConfigResponse(**config)

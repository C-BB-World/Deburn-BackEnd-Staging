"""
FastAPI router for Reflection endpoints.

Provides endpoints for retrieving the daily reflection prompt,
submitting user reflections, listing past reflections, and editing them.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app_v2.dependencies import require_auth, get_reflection_service
from app_v2.services.reflection import ReflectionService
import app_v2.pipelines.reflection as reflection_pipeline
from common.utils import success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reflection", tags=["reflection"])


# ─────────────────────────────────────────────────────────────────
# Request schemas
# ─────────────────────────────────────────────────────────────────

class SubmitReflectionRequest(BaseModel):
    reflection: str


class UpdateReflectionRequest(BaseModel):
    reflection: str = Field(..., min_length=1, max_length=500)


# ─────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────

@router.get("/prompt")
async def get_reflection_prompt(
    user: Annotated[dict, Depends(require_auth)],
    reflection_service: Annotated[ReflectionService, Depends(get_reflection_service)],
):
    """Get the current reflection prompt."""
    prompt = reflection_service.get_prompt()
    return success_response({"prompt": prompt})


@router.post("")
async def submit_reflection(
    body: SubmitReflectionRequest,
    user: Annotated[dict, Depends(require_auth)],
    reflection_service: Annotated[ReflectionService, Depends(get_reflection_service)],
):
    """Submit a reflection."""
    user_id = str(user.get("_id", ""))

    result = await reflection_service.submit_reflection(
        user_id=user_id,
        reflection=body.reflection,
    )

    return success_response({"message": "Reflection saved"})


@router.get("")
async def get_reflections(
    user: Annotated[dict, Depends(require_auth)],
    reflection_service: Annotated[ReflectionService, Depends(get_reflection_service)],
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
):
    """Get paginated list of the current user's reflections."""
    user_id = str(user.get("_id", ""))
    result = await reflection_pipeline.get_reflections_pipeline(
        reflection_service, user_id, page, limit
    )
    return success_response(result)


@router.patch("/{reflection_id}")
async def update_reflection(
    reflection_id: str,
    body: UpdateReflectionRequest,
    user: Annotated[dict, Depends(require_auth)],
    reflection_service: Annotated[ReflectionService, Depends(get_reflection_service)],
):
    """Update the text of an existing reflection (owner only)."""
    user_id = str(user.get("_id", ""))
    result = await reflection_pipeline.update_reflection_pipeline(
        reflection_service, reflection_id, user_id, body.reflection
    )
    return success_response(result)

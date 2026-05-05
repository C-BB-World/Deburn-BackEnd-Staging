"""
FastAPI router for Reflection endpoints.

Provides endpoints for retrieving the daily reflection prompt
and submitting user reflections.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app_v2.dependencies import require_auth, get_reflection_service
from app_v2.services.reflection import ReflectionService
from common.utils import success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reflection", tags=["reflection"])


# ─────────────────────────────────────────────────────────────────
# Request schemas
# ─────────────────────────────────────────────────────────────────

class SubmitReflectionRequest(BaseModel):
    reflection: str


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

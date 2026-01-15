"""
FastAPI router for Learning endpoints.

Provides endpoints for learning modules and content.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from app_v2.dependencies import require_auth, get_hub_content_service
from common.utils import success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/learning", tags=["learning"])


@router.get("/modules")
async def get_learning_modules(
    user: Annotated[dict, Depends(require_auth)],
):
    """
    Get available learning modules for the user.

    Returns a list of learning modules with progress information.
    """
    content_service = get_hub_content_service()

    # Get published content items
    items = await content_service.get_all(status="published")

    # Transform to learning module format
    modules = []
    for item in items:
        module = {
            "id": item.get("id", str(item.get("_id", ""))),
            "title": item.get("titleEn", ""),
            "titleSv": item.get("titleSv", ""),
            "description": item.get("purpose", ""),
            "descriptionSv": item.get("purpose", ""),  # Use same for now
            "type": _map_content_type(item.get("contentType", "")),
            "duration": item.get("lengthMinutes", 0),
            "thumbnail": None,
            "progress": 0,  # TODO: Track user progress
        }
        modules.append(module)

    return success_response({"modules": modules})


def _map_content_type(content_type: str) -> str:
    """Map content type to module type."""
    mapping = {
        "text_article": "article",
        "audio_article": "audio",
        "audio_exercise": "exercise",
        "video_link": "video",
    }
    return mapping.get(content_type, "article")

"""
FastAPI router for Content system endpoints.

Provides endpoints for content retrieval and progress tracking.
"""

import logging
from typing import Annotated, Optional, List

from fastapi import APIRouter, Depends, Query, HTTPException

from app_v2.auth.dependencies import require_auth
from app_v2.content.dependencies import (
    get_content_service,
    get_learning_progress_service,
)
from app_v2.content.services.content_service import ContentService
from app_v2.content.services.learning_progress_service import LearningProgressService
from app_v2.content.models import (
    ContentItemResponse,
    ContentListResponse,
    CreateContentRequest,
    UpdateContentRequest,
    ProgressUpdateRequest,
    ProgressResponse,
    CompletionStatsResponse,
    CoachRecommendationsRequest,
)
from common.utils.exceptions import NotFoundException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/learning", tags=["learning"])


def _merge_progress(content: dict, progress_map: dict) -> dict:
    """Merge progress data into content item."""
    content_id = content.get("id")
    content["progress"] = progress_map.get(content_id, 0)
    return content


@router.get("/content", response_model=ContentListResponse)
async def get_content_list(
    user: Annotated[dict, Depends(require_auth)],
    content_service: Annotated[ContentService, Depends(get_content_service)],
    progress_service: Annotated[LearningProgressService, Depends(get_learning_progress_service)],
    content_type: Optional[str] = Query(None, alias="contentType"),
    category: Optional[str] = None,
):
    """Get list of published content with user's progress."""
    filters = {}
    if content_type:
        filters["contentType"] = content_type
    if category:
        filters["category"] = category

    content_items = await content_service.get_published(filters)

    progress_map = await progress_service.get_user_progress(str(user["_id"]))

    items_with_progress = [
        _merge_progress(item, progress_map)
        for item in content_items
    ]

    return ContentListResponse(
        items=[ContentItemResponse(**item) for item in items_with_progress],
        total=len(items_with_progress)
    )


@router.get("/content/{content_id}", response_model=ContentItemResponse)
async def get_content_item(
    content_id: str,
    user: Annotated[dict, Depends(require_auth)],
    content_service: Annotated[ContentService, Depends(get_content_service)],
    progress_service: Annotated[LearningProgressService, Depends(get_learning_progress_service)],
):
    """Get a single content item with user's progress."""
    content = await content_service.get_by_id(content_id)
    if not content:
        raise NotFoundException(message="Content not found", code="NOT_FOUND")

    progress = await progress_service.get_item_progress(str(user["_id"]), content_id)
    content["progress"] = progress

    return ContentItemResponse(**content)


@router.post("/content/{content_id}/complete", response_model=ProgressResponse)
async def mark_content_complete(
    content_id: str,
    body: ProgressUpdateRequest,
    user: Annotated[dict, Depends(require_auth)],
    content_service: Annotated[ContentService, Depends(get_content_service)],
    progress_service: Annotated[LearningProgressService, Depends(get_learning_progress_service)],
):
    """Mark content as complete or update progress."""
    content = await content_service.get_by_id(content_id)
    if not content:
        raise NotFoundException(message="Content not found", code="NOT_FOUND")

    record = await progress_service.update_progress(
        user_id=str(user["_id"]),
        content_id=content_id,
        progress=body.progress,
        content_type=content.get("contentType")
    )

    return ProgressResponse(**record)


@router.get("/progress", response_model=List[ProgressResponse])
async def get_my_progress(
    user: Annotated[dict, Depends(require_auth)],
    progress_service: Annotated[LearningProgressService, Depends(get_learning_progress_service)],
):
    """Get current user's learning progress."""
    records = await progress_service.get_recent_progress(str(user["_id"]), limit=50)
    return [ProgressResponse(**r) for r in records]


@router.get("/progress/stats", response_model=CompletionStatsResponse)
async def get_my_stats(
    user: Annotated[dict, Depends(require_auth)],
    progress_service: Annotated[LearningProgressService, Depends(get_learning_progress_service)],
):
    """Get current user's learning statistics."""
    stats = await progress_service.get_completion_stats(str(user["_id"]))
    return CompletionStatsResponse(**stats)


@router.get("/progress/in-progress", response_model=List[ProgressResponse])
async def get_in_progress(
    user: Annotated[dict, Depends(require_auth)],
    progress_service: Annotated[LearningProgressService, Depends(get_learning_progress_service)],
):
    """Get content items that are started but not completed."""
    records = await progress_service.get_in_progress(str(user["_id"]))
    return [ProgressResponse(**r) for r in records]


@router.post("/recommendations", response_model=List[ContentItemResponse])
async def get_coach_recommendations(
    body: CoachRecommendationsRequest,
    user: Annotated[dict, Depends(require_auth)],
    content_service: Annotated[ContentService, Depends(get_content_service)],
):
    """Get content recommendations for given topics (used by coach)."""
    items = await content_service.get_for_coach(
        topics=body.topics,
        limit=body.limit
    )
    return [ContentItemResponse(**item) for item in items]

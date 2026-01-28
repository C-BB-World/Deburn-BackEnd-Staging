"""
FastAPI router for Feedback endpoints.

Provides endpoints for general feedback and learning content ratings.
"""

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app_v2.dependencies import require_auth, get_feedback_service
from app_v2.services.feedback import FeedbackService
from common.utils import success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["feedback"])


# ─────────────────────────────────────────────────────────────────
# Request schemas
# ─────────────────────────────────────────────────────────────────

class SubmitFeedbackRequest(BaseModel):
    content: Optional[str] = Field(None, max_length=2000)
    rating: Optional[int] = Field(None, ge=1, le=5)
    isAnonymous: bool = False


class SubmitLearningRatingRequest(BaseModel):
    contentId: str
    contentTitle: str
    rating: int = Field(..., ge=-1, le=1)
    isAnonymous: bool = False


# ─────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────

@router.post("")
async def submit_feedback(
    body: SubmitFeedbackRequest,
    user: Annotated[dict, Depends(require_auth)],
    feedback_service: Annotated[FeedbackService, Depends(get_feedback_service)],
):
    """
    Submit general feedback.

    Stores feedback in deburn-hub.feedback collection.
    Requires at least a rating or content.
    """
    from app_v2.pipelines import feedback as pipelines

    # Validate that at least rating or content is provided
    if not body.rating and not body.content:
        raise HTTPException(
            status_code=400,
            detail="Please provide a rating or feedback content"
        )

    user_id = str(user.get("_id", ""))
    user_name = f"{user.get('profile', {}).get('firstName', '')} {user.get('profile', {}).get('lastName', '')}".strip()

    result = await pipelines.submit_general_feedback_pipeline(
        feedback_service=feedback_service,
        user_id=user_id,
        user_name=user_name,
        rating=body.rating,
        content=body.content,
        is_anonymous=body.isAnonymous
    )

    return success_response(result)


@router.post("/learning")
async def submit_learning_rating(
    body: SubmitLearningRatingRequest,
    user: Annotated[dict, Depends(require_auth)],
    feedback_service: Annotated[FeedbackService, Depends(get_feedback_service)],
):
    """
    Submit rating for learning content.

    Stores rating in deburn-hub.learningfeedback collection.
    If user already rated (non-anonymous), updates their rating.
    Anonymous ratings are always added as new entries.
    """
    from app_v2.pipelines import feedback as pipelines

    user_id = str(user.get("_id", ""))

    result = await pipelines.submit_learning_rating_pipeline(
        feedback_service=feedback_service,
        user_id=user_id,
        content_id=body.contentId,
        content_title=body.contentTitle,
        rating=body.rating,
        is_anonymous=body.isAnonymous
    )

    return success_response(result)


@router.get("/learning/{content_id}")
async def get_learning_ratings(
    content_id: str,
    user: Annotated[dict, Depends(require_auth)],
    feedback_service: Annotated[FeedbackService, Depends(get_feedback_service)],
):
    """
    Get ratings for a specific learning content.

    Returns total ratings and user's own rating if exists.
    """
    from app_v2.pipelines import feedback as pipelines

    user_id = str(user.get("_id", ""))

    result = await pipelines.get_learning_ratings_pipeline(
        feedback_service=feedback_service,
        content_id=content_id,
        user_id=user_id
    )

    return success_response(result)

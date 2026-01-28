"""
Feedback pipeline functions.

Stateless orchestration logic for feedback operations.
"""

import logging
from typing import Optional, Dict, Any

from app_v2.services.feedback.feedback_service import FeedbackService

logger = logging.getLogger(__name__)


async def submit_general_feedback_pipeline(
    feedback_service: FeedbackService,
    user_id: str,
    user_name: str,
    rating: Optional[int] = None,
    content: Optional[str] = None,
    is_anonymous: bool = False
) -> Dict[str, Any]:
    """
    Orchestrates general feedback submission.

    Args:
        feedback_service: For data persistence
        user_id: Current user's ID
        user_name: Current user's display name
        rating: Optional rating (1-5)
        content: Optional feedback text
        is_anonymous: Whether to hide user info

    Returns:
        Response dict with feedback id and message
    """
    result = await feedback_service.submit_general_feedback(
        user_id=user_id,
        user_name=user_name,
        rating=rating,
        content=content,
        is_anonymous=is_anonymous
    )

    return {
        "id": str(result["_id"]),
        "message": "Feedback submitted successfully"
    }


async def submit_learning_rating_pipeline(
    feedback_service: FeedbackService,
    user_id: str,
    content_id: str,
    content_title: str,
    rating: int,
    is_anonymous: bool = False
) -> Dict[str, Any]:
    """
    Orchestrates learning content rating submission.

    Args:
        feedback_service: For data persistence
        user_id: Current user's ID
        content_id: Learning content ID
        content_title: Learning content title
        rating: Rating value (-1, 0, or 1)
        is_anonymous: Whether to hide user info

    Returns:
        Response dict with message
    """
    await feedback_service.submit_learning_rating(
        user_id=user_id,
        content_id=content_id,
        content_title=content_title,
        rating=rating,
        is_anonymous=is_anonymous
    )

    return {
        "message": "Rating submitted successfully"
    }


async def get_learning_ratings_pipeline(
    feedback_service: FeedbackService,
    content_id: str,
    user_id: str
) -> Dict[str, Any]:
    """
    Get learning content ratings.

    Args:
        feedback_service: For data retrieval
        content_id: Learning content ID
        user_id: Current user's ID

    Returns:
        dict with totalRatings and userRating
    """
    return await feedback_service.get_learning_ratings(
        content_id=content_id,
        user_id=user_id
    )

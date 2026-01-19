"""
FastAPI router for Feedback endpoints.

Provides endpoints for general feedback and learning content ratings.
Stores data in deburn-hub database.
"""

import logging
from datetime import datetime, timezone
from typing import Annotated, Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorDatabase

from app_v2.dependencies import require_auth, get_hub_db
from common.utils import success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["feedback"])


# Request schemas
class SubmitFeedbackRequest(BaseModel):
    content: Optional[str] = Field(None, max_length=2000)
    rating: Optional[int] = Field(None, ge=1, le=5)
    isAnonymous: bool = False


class SubmitLearningRatingRequest(BaseModel):
    contentId: str
    contentTitle: str
    rating: int = Field(..., ge=1, le=5)
    isAnonymous: bool = False


# Response schemas
class FeedbackResponse(BaseModel):
    id: str
    message: str


@router.post("")
async def submit_feedback(
    body: SubmitFeedbackRequest,
    user: Annotated[dict, Depends(require_auth)],
    hub_db: Annotated[AsyncIOMotorDatabase, Depends(get_hub_db)],
):
    """
    Submit general feedback.

    Stores feedback in deburn-hub.feedback collection.
    Requires at least a rating or content.
    """
    # Validate that at least rating or content is provided
    if not body.rating and not body.content:
        raise HTTPException(status_code=400, detail="Please provide a rating or feedback content")

    user_id = str(user.get("_id", ""))
    user_name = f"{user.get('profile', {}).get('firstName', '')} {user.get('profile', {}).get('lastName', '')}".strip()

    feedback_doc = {
        "userId": None if body.isAnonymous else user_id,
        "userName": None if body.isAnonymous else user_name,
        "isAnonymous": body.isAnonymous,
        "rating": body.rating,
        "content": body.content.strip() if body.content else None,
        "createdAt": datetime.now(timezone.utc),
    }

    collection = hub_db["feedback"]
    result = await collection.insert_one(feedback_doc)

    logger.info(f"Feedback submitted: {result.inserted_id} (anonymous: {body.isAnonymous}, rating: {body.rating})")

    return success_response({
        "id": str(result.inserted_id),
        "message": "Feedback submitted successfully"
    })


@router.post("/learning")
async def submit_learning_rating(
    body: SubmitLearningRatingRequest,
    user: Annotated[dict, Depends(require_auth)],
    hub_db: Annotated[AsyncIOMotorDatabase, Depends(get_hub_db)],
):
    """
    Submit rating for learning content.

    Stores rating in deburn-hub.learningfeedback collection.
    If user already rated (non-anonymous), updates their rating.
    Anonymous ratings are always added as new entries.
    """
    user_id = str(user.get("_id", ""))
    now = datetime.now(timezone.utc)

    collection = hub_db["learningfeedback"]

    rating_entry = {
        "userId": None if body.isAnonymous else user_id,
        "isAnonymous": body.isAnonymous,
        "rating": body.rating,
        "createdAt": now,
    }

    # Check if document exists for this content
    existing = await collection.find_one({"contentId": body.contentId})

    if existing:
        if body.isAnonymous:
            # Anonymous: always add new rating
            await collection.update_one(
                {"contentId": body.contentId},
                {
                    "$push": {"ratings": rating_entry},
                    "$inc": {"totalRatings": 1}
                }
            )
        else:
            # Non-anonymous: check if user already rated
            user_rating_exists = any(
                r.get("userId") == user_id and not r.get("isAnonymous")
                for r in existing.get("ratings", [])
            )

            if user_rating_exists:
                # Update existing rating
                await collection.update_one(
                    {
                        "contentId": body.contentId,
                        "ratings.userId": user_id,
                        "ratings.isAnonymous": False
                    },
                    {
                        "$set": {
                            "ratings.$.rating": body.rating,
                            "ratings.$.createdAt": now
                        }
                    }
                )
            else:
                # Add new rating
                await collection.update_one(
                    {"contentId": body.contentId},
                    {
                        "$push": {"ratings": rating_entry},
                        "$inc": {"totalRatings": 1}
                    }
                )
    else:
        # Create new document
        await collection.insert_one({
            "contentId": body.contentId,
            "contentTitle": body.contentTitle,
            "ratings": [rating_entry],
            "totalRatings": 1,
        })

    logger.info(f"Learning rating submitted: contentId={body.contentId}, rating={body.rating}, anonymous={body.isAnonymous}")

    return success_response({
        "message": "Rating submitted successfully"
    })


@router.get("/learning/{content_id}")
async def get_learning_ratings(
    content_id: str,
    user: Annotated[dict, Depends(require_auth)],
    hub_db: Annotated[AsyncIOMotorDatabase, Depends(get_hub_db)],
):
    """
    Get ratings for a specific learning content.

    Returns total ratings and user's own rating if exists.
    """
    user_id = str(user.get("_id", ""))
    collection = hub_db["learningfeedback"]

    doc = await collection.find_one({"contentId": content_id})

    if not doc:
        return success_response({
            "totalRatings": 0,
            "userRating": None
        })

    # Find user's rating
    user_rating = None
    for r in doc.get("ratings", []):
        if r.get("userId") == user_id and not r.get("isAnonymous"):
            user_rating = r.get("rating")
            break

    return success_response({
        "totalRatings": doc.get("totalRatings", 0),
        "userRating": user_rating
    })

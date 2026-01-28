"""
Feedback CRUD service.

Handles feedback storage and retrieval operations.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class FeedbackService:
    """
    Handles feedback storage and retrieval.
    Pure CRUD - no business logic.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize FeedbackService.

        Args:
            db: MongoDB database connection (hub_db)
        """
        self._db = db
        self._feedback_collection = db["feedback"]
        self._learning_feedback_collection = db["learningfeedback"]

    async def submit_general_feedback(
        self,
        user_id: str,
        user_name: str,
        rating: Optional[int] = None,
        content: Optional[str] = None,
        is_anonymous: bool = False
    ) -> Dict[str, Any]:
        """
        Submit general feedback.

        Args:
            user_id: User's ID
            user_name: User's display name
            rating: Optional rating (1-5)
            content: Optional feedback text
            is_anonymous: Whether to hide user info

        Returns:
            Created feedback document
        """
        now = datetime.now(timezone.utc)

        feedback_doc = {
            "userId": None if is_anonymous else user_id,
            "userName": None if is_anonymous else user_name,
            "isAnonymous": is_anonymous,
            "rating": rating,
            "content": content.strip() if content else None,
            "createdAt": now,
        }

        result = await self._feedback_collection.insert_one(feedback_doc)
        feedback_doc["_id"] = result.inserted_id

        logger.info(f"General feedback submitted: {result.inserted_id} (anonymous: {is_anonymous})")
        return feedback_doc

    async def submit_learning_rating(
        self,
        user_id: str,
        content_id: str,
        content_title: str,
        rating: int,
        is_anonymous: bool = False
    ) -> Dict[str, Any]:
        """
        Submit rating for learning content.

        Args:
            user_id: User's ID
            content_id: Learning content ID
            content_title: Learning content title
            rating: Rating value (-1, 0, or 1)
            is_anonymous: Whether to hide user info

        Returns:
            Updated/created feedback document
        """
        now = datetime.now(timezone.utc)

        rating_entry = {
            "userId": None if is_anonymous else user_id,
            "isAnonymous": is_anonymous,
            "rating": rating,
            "createdAt": now,
        }

        # Check if document exists for this content
        existing = await self._learning_feedback_collection.find_one(
            {"contentId": content_id}
        )

        if existing:
            if is_anonymous:
                # Anonymous: always add new rating
                await self._learning_feedback_collection.update_one(
                    {"contentId": content_id},
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
                    await self._learning_feedback_collection.update_one(
                        {
                            "contentId": content_id,
                            "ratings.userId": user_id,
                            "ratings.isAnonymous": False
                        },
                        {
                            "$set": {
                                "ratings.$.rating": rating,
                                "ratings.$.createdAt": now
                            }
                        }
                    )
                else:
                    # Add new rating
                    await self._learning_feedback_collection.update_one(
                        {"contentId": content_id},
                        {
                            "$push": {"ratings": rating_entry},
                            "$inc": {"totalRatings": 1}
                        }
                    )

            # Return updated document
            result = await self._learning_feedback_collection.find_one(
                {"contentId": content_id}
            )
        else:
            # Create new document
            result = await self._learning_feedback_collection.insert_one({
                "contentId": content_id,
                "contentTitle": content_title,
                "ratings": [rating_entry],
                "totalRatings": 1,
            })
            result = await self._learning_feedback_collection.find_one(
                {"_id": result.inserted_id}
            )

        logger.info(f"Learning rating submitted: contentId={content_id}, rating={rating}")
        return result

    async def get_learning_ratings(
        self,
        content_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get ratings for learning content.

        Args:
            content_id: Learning content ID
            user_id: Current user's ID

        Returns:
            dict with totalRatings and userRating
        """
        doc = await self._learning_feedback_collection.find_one(
            {"contentId": content_id}
        )

        if not doc:
            return {
                "totalRatings": 0,
                "userRating": None
            }

        # Find user's rating
        user_rating = None
        for r in doc.get("ratings", []):
            if r.get("userId") == user_id and not r.get("isAnonymous"):
                user_rating = r.get("rating")
                break

        return {
            "totalRatings": doc.get("totalRatings", 0),
            "userRating": user_rating
        }

    async def get_feedback_list(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get list of general feedback (for admin).

        Args:
            limit: Max records to return
            offset: Records to skip

        Returns:
            List of feedback documents
        """
        cursor = self._feedback_collection.find().sort("createdAt", -1)
        cursor = cursor.skip(offset).limit(limit)
        return await cursor.to_list(length=limit)

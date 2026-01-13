"""
Coach Router.

Handles AI coaching conversations with streaming support.
"""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from common.utils import success_response

from app.config import settings
from app.models import User
from app.schemas.coach import ChatRequest, ConversationStarter
from app.dependencies import get_current_user, get_coach_service
from app.services.coach_service import CoachService

router = APIRouter()


# =============================================================================
# Quota Management
# =============================================================================
async def check_quota(user: User) -> dict:
    """
    Check if user has exceeded daily exchange limit.

    Returns:
        dict with allowed (bool), limit (int), count (int)
    """
    limit = settings.DAILY_EXCHANGE_LIMIT

    # Get today's date at midnight UTC
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    # Check if we need to reset the count
    last_reset = user.coach_exchanges_last_reset
    if not last_reset or last_reset < today:
        user.coach_exchanges_count = 0
        user.coach_exchanges_last_reset = today
        await user.save()

    count = user.coach_exchanges_count or 0
    return {"allowed": count < limit, "limit": limit, "count": count}


async def increment_exchange_count(user: User):
    """Increment the user's exchange count."""
    user.coach_exchanges_count = (user.coach_exchanges_count or 0) + 1
    await user.save()


# =============================================================================
# Quota Messages
# =============================================================================
QUOTA_MESSAGES = {
    "en": lambda limit: f"You've reached your daily conversation limit of {limit} messages. Please come back tomorrow to continue our coaching session.",
    "sv": lambda limit: f"Du har nått din dagliga samtalsgräns på {limit} meddelanden. Kom tillbaka imorgon för att fortsätta din coachingsession.",
}


# =============================================================================
# POST /api/coach/chat
# =============================================================================
@router.post("/chat")
async def chat(
    request: ChatRequest,
    user: User = Depends(get_current_user),
    coach: CoachService = Depends(get_coach_service),
):
    """
    Send a message to the AI coach and get a response.
    """
    user_id = str(user.id)
    language = request.language or (user.profile.preferred_language if user.profile else "en")

    # Check daily quota
    quota = await check_quota(user)
    if not quota["allowed"]:
        get_message = QUOTA_MESSAGES.get(language, QUOTA_MESSAGES["en"])
        return success_response({
            "quotaExceeded": True,
            "response": {
                "text": get_message(quota["limit"]),
                "isSystemMessage": True,
            },
            "conversationId": request.conversationId,
        })

    # Build user context
    user_context = {
        "name": user.profile.first_name if user.profile else user.email.split("@")[0],
        "role": user.profile.job_title if user.profile else None,
        "organization": user.organization,
    }

    # Add wellbeing context if provided
    if request.context and request.context.recentCheckin:
        user_context["wellbeing"] = {
            "mood": request.context.recentCheckin.mood,
            "energy": request.context.recentCheckin.energy,
            "stress": request.context.recentCheckin.stress,
            "streak": request.context.recentCheckin.streak,
        }

    # Get response from coach service
    result = await coach.chat(
        message=request.message,
        conversation_id=request.conversationId,
        user_id=user_id,
        user_context=user_context,
        language=language,
    )

    # Increment exchange count
    await increment_exchange_count(user)

    return success_response({
        "quotaExceeded": False,
        "response": result,
    })


# =============================================================================
# POST /api/coach/stream
# =============================================================================
@router.post("/stream")
async def stream_chat(
    request: ChatRequest,
    user: User = Depends(get_current_user),
    coach: CoachService = Depends(get_coach_service),
):
    """
    Stream a conversation with the AI coach using Server-Sent Events.
    """
    user_id = str(user.id)
    language = request.language or (user.profile.preferred_language if user.profile else "en")

    # Check daily quota
    quota = await check_quota(user)

    async def event_generator():
        if not quota["allowed"]:
            # Send quota exceeded message
            get_message = QUOTA_MESSAGES.get(language, QUOTA_MESSAGES["en"])
            yield f"data: {json.dumps({'type': 'quotaExceeded', 'content': get_message(quota['limit']), 'conversationId': request.conversationId})}\n\n"
            yield "data: [DONE]\n\n"
            return

        # Build user context
        user_context = {
            "name": user.profile.first_name if user.profile else user.email.split("@")[0],
            "role": user.profile.job_title if user.profile else None,
            "organization": user.organization,
        }

        if request.context and request.context.recentCheckin:
            user_context["wellbeing"] = {
                "mood": request.context.recentCheckin.mood,
                "energy": request.context.recentCheckin.energy,
                "stress": request.context.recentCheckin.stress,
                "streak": request.context.recentCheckin.streak,
            }

        # Stream from coach service
        async for chunk in coach.stream_chat(
            message=request.message,
            conversation_id=request.conversationId,
            user_id=user_id,
            user_context=user_context,
            language=language,
        ):
            yield f"data: {json.dumps(chunk)}\n\n"

            if chunk.get("type") == "done" or chunk.get("type") == "error":
                break

        # Increment exchange count after successful stream
        await increment_exchange_count(user)

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# =============================================================================
# GET /api/coach/starters
# =============================================================================
@router.get("/starters")
async def get_starters(
    user: User = Depends(get_current_user),
    coach: CoachService = Depends(get_coach_service),
    language: str = Query("en", pattern=r"^(en|sv)$"),
    includeWellbeing: bool = Query(False),
    mood: int = Query(None, ge=1, le=5),
    energy: int = Query(None, ge=1, le=10),
    stress: int = Query(None, ge=1, le=10),
):
    """
    Get conversation starters based on user context.
    """
    # Use user's preferred language if not specified
    lang = language or (user.profile.preferred_language if user.profile else "en")

    # Build context
    context = {}
    if includeWellbeing:
        context["wellbeing"] = {
            "mood": mood,
            "energy": energy,
            "stress": stress,
        }

    starters = coach.get_conversation_starters(context, lang)

    return success_response({"starters": starters})

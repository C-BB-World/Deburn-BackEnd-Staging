"""
FastAPI router for AI Coaching system endpoints.

Provides endpoints for coaching conversations and commitments.
"""

import logging
from typing import Annotated, Optional, List

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
import json

from app_v2.dependencies import (
    require_auth,
    get_coach_service,
    get_conversation_service,
    get_commitment_service,
    get_pattern_detector,
)
from app_v2.services.coach.coach_service import CoachService
from app_v2.services.coach.conversation_service import ConversationService
from app_v2.services.coach.commitment_service import CommitmentService
from app_v2.services.coach.pattern_detector import PatternDetector
from app_v2.schemas.coach import (
    SendMessageRequest,
    ConversationResponse,
    ConversationMessageResponse,
    ConversationStarterResponse,
    StartersResponse,
    CommitmentResponse,
    CompleteCommitmentRequest,
    CommitmentStatsResponse,
    PatternResultResponse,
    RecentConversationsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/coach", tags=["coach"])


def _format_conversation(conv: dict) -> ConversationResponse:
    """Format conversation for response."""
    messages = [
        ConversationMessageResponse(
            role=m["role"],
            content=m["content"],
            timestamp=m["timestamp"],
            metadata=m.get("metadata")
        )
        for m in conv.get("messages", [])
    ]

    return ConversationResponse(
        id=conv["id"],
        conversationId=conv["conversationId"],
        userId=conv["userId"],
        messages=messages,
        topics=conv.get("topics", []),
        status=conv.get("status", "active"),
        lastMessageAt=conv.get("lastMessageAt"),
        createdAt=conv.get("createdAt")
    )


@router.post("/chat")
async def send_message(
    body: SendMessageRequest,
    user: Annotated[dict, Depends(require_auth)],
    coach_service: Annotated[CoachService, Depends(get_coach_service)],
):
    """Send a message and get a streaming coaching response."""

    async def generate():
        async for chunk in coach_service.chat(
            user_id=str(user["_id"]),
            message=body.message,
            conversation_id=body.conversationId,
            language=body.language,
            stream=True
        ):
            data = json.dumps({
                "type": chunk.type,
                "content": chunk.content
            })
            yield f"data: {data}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )


@router.get("/starters", response_model=StartersResponse)
async def get_starters(
    user: Annotated[dict, Depends(require_auth)],
    coach_service: Annotated[CoachService, Depends(get_coach_service)],
    language: str = Query("en", pattern="^(en|sv)$"),
    include_wellbeing: bool = True,
):
    """Get personalized conversation starters."""
    starters = await coach_service.get_starters(
        user_id=str(user["_id"]),
        language=language,
        include_wellbeing=include_wellbeing
    )

    return StartersResponse(
        starters=[
            ConversationStarterResponse(label=s.label, context=s.context)
            for s in starters
        ]
    )


@router.get("/conversations", response_model=RecentConversationsResponse)
async def get_recent_conversations(
    user: Annotated[dict, Depends(require_auth)],
    conversation_service: Annotated[ConversationService, Depends(get_conversation_service)],
    limit: int = Query(10, ge=1, le=50),
):
    """Get recent conversations."""
    conversations = await conversation_service.get_recent_conversations(
        user_id=str(user["_id"]),
        limit=limit
    )

    return RecentConversationsResponse(
        conversations=[_format_conversation(c) for c in conversations]
    )


@router.get("/conversations/{conversation_id}", response_model=Optional[ConversationResponse])
async def get_conversation(
    conversation_id: str,
    user: Annotated[dict, Depends(require_auth)],
    conversation_service: Annotated[ConversationService, Depends(get_conversation_service)],
):
    """Get a specific conversation."""
    conversation = await conversation_service.get_conversation(conversation_id)

    if not conversation:
        return None

    if conversation["userId"] != str(user["_id"]):
        return None

    return _format_conversation(conversation)


@router.get("/commitments", response_model=List[CommitmentResponse])
async def get_active_commitments(
    user: Annotated[dict, Depends(require_auth)],
    commitment_service: Annotated[CommitmentService, Depends(get_commitment_service)],
):
    """Get active commitments."""
    commitments = await commitment_service.get_active_commitments(str(user["_id"]))
    return [CommitmentResponse(**c) for c in commitments]


@router.get("/commitments/due", response_model=List[CommitmentResponse])
async def get_due_followups(
    user: Annotated[dict, Depends(require_auth)],
    commitment_service: Annotated[CommitmentService, Depends(get_commitment_service)],
):
    """Get commitments due for follow-up."""
    commitments = await commitment_service.get_due_followups(str(user["_id"]))
    return [CommitmentResponse(**c) for c in commitments]


@router.get("/commitments/stats", response_model=CommitmentStatsResponse)
async def get_commitment_stats(
    user: Annotated[dict, Depends(require_auth)],
    commitment_service: Annotated[CommitmentService, Depends(get_commitment_service)],
):
    """Get commitment statistics."""
    stats = await commitment_service.get_stats(str(user["_id"]))

    return CommitmentStatsResponse(
        active=stats.active,
        completed=stats.completed,
        expired=stats.expired,
        dismissed=stats.dismissed,
        total=stats.total,
        completionRate=stats.completion_rate
    )


@router.post("/commitments/{commitment_id}/complete", response_model=CommitmentResponse)
async def complete_commitment(
    commitment_id: str,
    body: CompleteCommitmentRequest,
    user: Annotated[dict, Depends(require_auth)],
    commitment_service: Annotated[CommitmentService, Depends(get_commitment_service)],
):
    """Complete a commitment with reflection."""
    commitment = await commitment_service.complete_commitment(
        commitment_id=commitment_id,
        user_id=str(user["_id"]),
        reflection_notes=body.reflectionNotes,
        helpfulness_rating=body.helpfulnessRating
    )
    return CommitmentResponse(**commitment)


@router.post("/commitments/{commitment_id}/dismiss", response_model=CommitmentResponse)
async def dismiss_commitment(
    commitment_id: str,
    user: Annotated[dict, Depends(require_auth)],
    commitment_service: Annotated[CommitmentService, Depends(get_commitment_service)],
):
    """Dismiss a commitment."""
    commitment = await commitment_service.dismiss_commitment(
        commitment_id=commitment_id,
        user_id=str(user["_id"])
    )
    return CommitmentResponse(**commitment)


@router.get("/patterns", response_model=Optional[PatternResultResponse])
async def get_patterns(
    user: Annotated[dict, Depends(require_auth)],
    pattern_detector: Annotated[PatternDetector, Depends(get_pattern_detector)],
    days: int = Query(30, ge=7, le=90),
):
    """Get detected patterns from check-in data."""
    result = await pattern_detector.detect(
        user_id=str(user["_id"]),
        days=days
    )

    if not result:
        return None

    return PatternResultResponse(
        streak=result.streak,
        morningCheckins=result.morning_checkins,
        stressDayPattern=result.stress_day_pattern,
        moodChange=result.mood_change,
        stressChange=result.stress_change,
        energyChange=result.energy_change,
        lowEnergyDays=result.low_energy_days,
        sleepMoodCorrelation=result.sleep_mood_correlation
    )

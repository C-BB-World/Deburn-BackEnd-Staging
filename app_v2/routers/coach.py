"""
FastAPI router for AI Coaching system endpoints.

Provides endpoints for coaching conversations and commitments.
"""

import asyncio
import logging
from typing import Annotated, Optional, List

from fastapi import APIRouter, Depends, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse
import json

from fastapi import Response
from motor.motor_asyncio import AsyncIOMotorDatabase

from app_v2.dependencies import (
    require_auth,
    get_coach_service,
    get_commitment_service,
    get_pattern_detector,
    get_tts_service,
    get_stt_service,
    get_hub_db,
    get_memory_encryption_service,
    get_translation_service,
)
from app_v2.services.media.stt_service import STTService
from common.utils.responses import success_response
from app_v2.services.media.tts_service import TTSService
from app_v2.services.coach.coach_service import CoachService
from app_v2.services.coach.commitment_service import CommitmentService
from app_v2.services.coach.pattern_detector import PatternDetector
from app_v2.services.translation import TranslationService
from app_v2.agent.memory.encryption import MemoryEncryptionService
from app_v2.pipelines import conversation as conversation_pipeline
from app_v2.pipelines import translation as translation_pipeline
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
    VoiceRequest,
    TranslateConversationRequest,
    TranslateConversationResponse,
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
    hub_db: Annotated[AsyncIOMotorDatabase, Depends(get_hub_db)],
    encryption_service: Annotated[MemoryEncryptionService, Depends(get_memory_encryption_service)],
):
    """Send a message and get a streaming coaching response."""
    user_id = str(user["_id"])

    # Step 1: Get or create conversation (decrypted)
    conversation = await conversation_pipeline.get_or_create_conversation(
        db=hub_db,
        encryption_service=encryption_service,
        conversation_id=body.conversationId,
        user_id=user_id
    )

    # Step 2: Save user message (encrypted)
    await conversation_pipeline.save_message(
        db=hub_db,
        encryption_service=encryption_service,
        conversation_id=conversation["conversationId"],
        role="user",
        content=body.message,
        language=body.language
    )

    async def generate():
        full_response = ""
        topics = []
        actions = []
        commitment_info = None
        conversation_id = conversation["conversationId"]

        try:
            # Step 3: Stream AI response with keepalive pings
            stream = coach_service.chat(
                user_id=user_id,
                message=body.message,
                conversation_history=conversation.get("messages", []),
                language=body.language,
            ).__aiter__()

            pending_next = None

            while True:
                if pending_next is None:
                    pending_next = asyncio.ensure_future(stream.__anext__())

                done, _ = await asyncio.wait({pending_next}, timeout=15)

                if not done:
                    # Timeout — send keepalive, keep waiting for same chunk
                    yield ": keepalive\n\n"
                    continue

                try:
                    chunk = pending_next.result()
                    pending_next = None
                except StopAsyncIteration:
                    break

                # Collect data for persistence
                if chunk.type == "text":
                    full_response += chunk.content
                elif chunk.type == "actions":
                    actions = chunk.content or []
                elif chunk.type == "metadata":
                    topics = chunk.content.get("topics", [])
                    commitment_info = chunk.content.get("commitment")
                    # Add conversationId to metadata for frontend
                    chunk.content["conversationId"] = conversation_id

                data = json.dumps({
                    "type": chunk.type,
                    "content": chunk.content
                })
                yield f"data: {data}\n\n"

            # Step 4: Save assistant message (encrypted) with actions
            await conversation_pipeline.save_message(
                db=hub_db,
                encryption_service=encryption_service,
                conversation_id=conversation_id,
                role="assistant",
                content=full_response,
                metadata={"topics": topics, "commitment": commitment_info, "actions": actions},
                language=body.language
            )

            # Step 5: Update topics
            if topics:
                await conversation_pipeline.update_topics(
                    db=hub_db,
                    conversation_id=conversation_id,
                    topics=topics
                )

        except Exception as e:
            # Client disconnected mid-stream — save partial response
            logger.warning(f"Stream interrupted for {conversation_id}: {type(e).__name__}")

            if full_response:
                await conversation_pipeline.save_message(
                    db=hub_db,
                    encryption_service=encryption_service,
                    conversation_id=conversation_id,
                    role="assistant",
                    content=full_response,
                    metadata={"topics": topics, "commitment": commitment_info, "actions": actions, "partial": True},
                    language=body.language
                )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
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
    hub_db: Annotated[AsyncIOMotorDatabase, Depends(get_hub_db)],
    encryption_service: Annotated[MemoryEncryptionService, Depends(get_memory_encryption_service)],
    limit: int = Query(10, ge=1, le=50),
):
    """Get recent conversations."""
    conversations = await conversation_pipeline.get_recent_conversations(
        db=hub_db,
        encryption_service=encryption_service,
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
    hub_db: Annotated[AsyncIOMotorDatabase, Depends(get_hub_db)],
    encryption_service: Annotated[MemoryEncryptionService, Depends(get_memory_encryption_service)],
):
    """Get a specific conversation."""
    conversation = await conversation_pipeline.get_conversation(
        db=hub_db,
        encryption_service=encryption_service,
        conversation_id=conversation_id,
        user_id=str(user["_id"])
    )

    if not conversation:
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


@router.post("/voice")
async def text_to_speech(
    body: VoiceRequest,
    user: Annotated[dict, Depends(require_auth)],
    tts_service: Annotated[TTSService, Depends(get_tts_service)],
):
    """
    Convert text to speech using ElevenLabs.

    Returns MP3 audio stream.
    """
    result = await tts_service.generate_speech(
        text=body.text,
        voice=body.voice,
        language=body.language,
        speed=1.0
    )

    return Response(
        content=result["audioBuffer"],
        media_type="audio/mpeg",
        headers={
            "Content-Length": str(len(result["audioBuffer"])),
            "Cache-Control": "private, max-age=3600",
        }
    )


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(..., description="Audio file to transcribe"),
    language: str = Form(default="en"),
    user: Annotated[dict, Depends(require_auth)] = None,
    stt_service: Annotated[STTService, Depends(get_stt_service)] = None,
):
    """
    Transcribe audio to text using Whisper.

    Accepts audio file via multipart/form-data.
    Supported formats: webm, mp4, mp3, wav, m4a, ogg, flac.
    Max file size: 25MB.
    """
    audio_bytes = await file.read()
    filename = file.filename or "recording.webm"

    transcript = await stt_service.transcribe(
        audio_bytes=audio_bytes,
        filename=filename,
        language=language,
    )

    return success_response(data={"text": transcript})


@router.post("/conversations/translate", response_model=TranslateConversationResponse)
async def translate_conversation(
    body: TranslateConversationRequest,
    user: Annotated[dict, Depends(require_auth)],
    hub_db: Annotated[AsyncIOMotorDatabase, Depends(get_hub_db)],
    translation_service: Annotated[TranslationService, Depends(get_translation_service)],
    encryption_service: Annotated[MemoryEncryptionService, Depends(get_memory_encryption_service)],
):
    """
    Translate conversation messages to target language.

    Caches translations in the database for future requests.
    Returns both cached and newly translated messages.
    """
    result = await translation_pipeline.translate_conversation_messages(
        db=hub_db,
        translation_service=translation_service,
        encryption_service=encryption_service,
        conversation_id=body.conversationId,
        user_id=str(user["_id"]),
        target_language=body.targetLanguage,
        start_index=body.startIndex,
        count=body.count,
    )

    if "error" in result:
        return TranslateConversationResponse(
            translatedMessages=[],
            totalMessages=0,
            startIndex=0,
            endIndex=0,
            newlyTranslated=0,
            fromCache=0,
        )

    return TranslateConversationResponse(
        translatedMessages=result["translatedMessages"],
        totalMessages=result["totalMessages"],
        startIndex=result["startIndex"],
        endIndex=result["endIndex"],
        newlyTranslated=result["newlyTranslated"],
        fromCache=result["fromCache"],
    )

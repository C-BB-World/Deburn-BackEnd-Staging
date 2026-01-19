"""
Main coaching service.

Orchestrates coaching conversations with safety, history, and commitments.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, AsyncIterator
from dataclasses import dataclass

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app_v2.services.coach.agent import Agent, CoachingContext
from app_v2.services.coach.safety_checker import SafetyChecker
from app_v2.services.coach.conversation_service import ConversationService
from app_v2.services.coach.commitment_service import CommitmentService
from app_v2.services.coach.commitment_extractor import CommitmentExtractor
from app_v2.services.coach.quick_reply_generator import QuickReplyGenerator
from common.utils.exceptions import ValidationException

logger = logging.getLogger(__name__)


@dataclass
class ConversationStarter:
    """Suggested conversation starter."""
    label: str
    context: Optional[str] = None


@dataclass
class CoachResponseChunk:
    """Chunk of streaming response."""
    type: str  # 'text', 'actions', 'quickReplies', 'metadata', 'done'
    content: Any


class CoachService:
    """
    Main service for AI coaching conversations.
    """

    DEFAULT_DAILY_LIMIT = 15

    STARTERS = {
        "en": {
            "stress_high": ("My stress has been building up", "stress"),
            "energy_low": ("I'm feeling low on energy lately", "energy"),
            "mood_low": ("I've been feeling off lately", "mood"),
            "default": [
                ("I want to work on my leadership", "leadership"),
                ("I'm struggling with delegation", "delegation"),
                ("I need help with a difficult conversation", "conflict"),
                ("I want to prevent burnout", "burnout"),
            ]
        },
        "sv": {
            "stress_high": ("Min stress har ökat på sistone", "stress"),
            "energy_low": ("Jag känner mig energilös på sistone", "energy"),
            "mood_low": ("Jag har inte mått så bra på sistone", "mood"),
            "default": [
                ("Jag vill utveckla mitt ledarskap", "leadership"),
                ("Jag har svårt att delegera", "delegation"),
                ("Jag behöver hjälp med ett svårt samtal", "conflict"),
                ("Jag vill förebygga utbrändhet", "burnout"),
            ]
        }
    }

    def __init__(
        self,
        agent: Agent,
        safety_checker: SafetyChecker,
        conversation_service: ConversationService,
        commitment_service: CommitmentService,
        commitment_extractor: CommitmentExtractor,
        quick_reply_generator: QuickReplyGenerator,
        db: AsyncIOMotorDatabase,
        daily_limit: int = 15
    ):
        """
        Initialize CoachService.

        Args:
            agent: AI agent for response generation
            safety_checker: For message safety checking
            conversation_service: For history management
            commitment_service: For commitment tracking
            commitment_extractor: For extracting commitments
            quick_reply_generator: For quick replies
            db: Database connection
            daily_limit: Daily exchange limit
        """
        self._agent = agent
        self._safety_checker = safety_checker
        self._conversation_service = conversation_service
        self._commitment_service = commitment_service
        self._commitment_extractor = commitment_extractor
        self._quick_reply_generator = quick_reply_generator
        self._db = db
        self._daily_limit = daily_limit
        self._users_collection = db["users"]
        self._checkins_collection = db["checkins"]

    async def chat(
        self,
        user_id: str,
        message: str,
        conversation_id: Optional[str] = None,
        language: str = "en",
        stream: bool = True
    ) -> AsyncIterator[CoachResponseChunk]:
        """
        Send a message and get a coaching response.

        Args:
            user_id: User's ID
            message: User's message
            conversation_id: Existing conversation or None for new
            language: 'en' or 'sv'
            stream: Whether to stream response

        Yields:
            CoachResponseChunk objects

        Raises:
            ValidationException: Daily exchange limit exceeded
        """
        if not await self._check_daily_limit(user_id):
            raise ValidationException(
                message="Daily exchange limit exceeded",
                code="RATE_LIMIT_EXCEEDED"
            )

        safety_result = self._safety_checker.check(message)

        if safety_result.is_crisis:
            crisis_response = self._safety_checker.get_crisis_response(language)
            yield CoachResponseChunk(type="text", content=crisis_response.text)
            yield CoachResponseChunk(type="metadata", content={
                "safetyLevel": 3,
                "resources": crisis_response.resources
            })
            yield CoachResponseChunk(type="done", content=None)
            return

        conversation = await self._conversation_service.get_or_create(
            conversation_id, user_id
        )

        due_commitments = await self._commitment_service.get_due_followups(user_id)

        context = await self._build_context(
            user_id, conversation, language, safety_result.level, due_commitments
        )

        await self._conversation_service.add_message(
            conversation["conversationId"],
            "user",
            message
        )

        full_response = ""

        if stream:
            response_iterator = await self._agent.generate_coaching_response(context, message, stream=True)
            async for chunk in response_iterator:
                full_response += chunk
                yield CoachResponseChunk(type="text", content=chunk)
        else:
            full_response = await self._agent.generate_coaching_response(context, message, stream=False)
            yield CoachResponseChunk(type="text", content=full_response)

        topics = self._agent.extract_topics(message + " " + full_response)

        await self._conversation_service.update_topics(
            conversation["conversationId"], topics
        )

        commitment_data = self._commitment_extractor.extract(full_response)
        commitment_info = None

        if commitment_data:
            topic = topics[0] if topics else "other"
            commitment = await self._commitment_service.create_commitment(
                user_id=user_id,
                conversation_id=conversation["conversationId"],
                commitment_data=commitment_data,
                topic=topic
            )
            commitment_info = {
                "id": commitment["id"],
                "commitment": commitment["commitment"],
                "followUpDate": commitment["followUpDate"].isoformat() if commitment.get("followUpDate") else None
            }

        await self._conversation_service.add_message(
            conversation["conversationId"],
            "assistant",
            full_response,
            metadata={"topics": topics, "commitment": commitment_info}
        )

        for commitment in due_commitments:
            await self._commitment_service.record_followup(commitment["id"])

        await self._increment_exchange_count(user_id)

        quick_replies = self._quick_reply_generator.generate(
            full_response, topics, language
        )

        yield CoachResponseChunk(type="quickReplies", content=quick_replies)

        yield CoachResponseChunk(type="metadata", content={
            "conversationId": conversation["conversationId"],
            "topics": topics,
            "commitment": commitment_info,
            "safetyLevel": safety_result.level
        })

        yield CoachResponseChunk(type="done", content=None)

    async def get_starters(
        self,
        user_id: str,
        language: str = "en",
        include_wellbeing: bool = True
    ) -> List[ConversationStarter]:
        """Get personalized conversation starters."""
        starters = []
        lang_starters = self.STARTERS.get(language, self.STARTERS["en"])

        if include_wellbeing:
            wellbeing = await self._get_latest_wellbeing(user_id)

            if wellbeing:
                if wellbeing.get("stress", 0) >= 7:
                    label, context = lang_starters["stress_high"]
                    starters.append(ConversationStarter(label=label, context=context))

                if wellbeing.get("energy", 10) <= 4:
                    label, context = lang_starters["energy_low"]
                    starters.append(ConversationStarter(label=label, context=context))

                if wellbeing.get("mood", 5) <= 2:
                    label, context = lang_starters["mood_low"]
                    starters.append(ConversationStarter(label=label, context=context))

        for label, context in lang_starters["default"]:
            if len(starters) >= 4:
                break
            starters.append(ConversationStarter(label=label, context=context))

        return starters[:4]

    async def get_history(
        self,
        conversation_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get conversation history."""
        return await self._conversation_service.get_conversation(conversation_id)

    async def _check_daily_limit(self, user_id: str) -> bool:
        """Check if user has exceeded daily exchange limit."""
        user = await self._users_collection.find_one(
            {"_id": ObjectId(user_id)},
            {"coachExchanges": 1}
        )

        if not user:
            return True

        exchanges = user.get("coachExchanges", {})
        daily_count = exchanges.get("dailyCount", 0)
        last_reset = exchanges.get("lastResetAt")

        if last_reset:
            if last_reset.date() < datetime.now(timezone.utc).date():
                return True

        return daily_count < self._daily_limit

    async def _increment_exchange_count(self, user_id: str) -> None:
        """Increment user's daily exchange count."""
        now = datetime.now(timezone.utc)

        user = await self._users_collection.find_one(
            {"_id": ObjectId(user_id)},
            {"coachExchanges": 1}
        )

        exchanges = user.get("coachExchanges", {}) if user else {}
        last_reset = exchanges.get("lastResetAt")

        if not last_reset or last_reset.date() < now.date():
            await self._users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "coachExchanges.dailyCount": 1,
                        "coachExchanges.lastResetAt": now,
                        "coachExchanges.lastExchangeAt": now
                    },
                    "$inc": {"coachExchanges.count": 1}
                }
            )
        else:
            await self._users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$inc": {
                        "coachExchanges.dailyCount": 1,
                        "coachExchanges.count": 1
                    },
                    "$set": {"coachExchanges.lastExchangeAt": now}
                }
            )

    async def _build_context(
        self,
        user_id: str,
        conversation: Dict[str, Any],
        language: str,
        safety_level: int,
        due_commitments: List[Dict[str, Any]]
    ) -> CoachingContext:
        """Build context object for Agent."""
        user = await self._users_collection.find_one(
            {"_id": ObjectId(user_id)},
            {"profile": 1, "firstName": 1, "lastName": 1}
        )

        user_profile = {}
        if user:
            profile = user.get("profile", {})
            user_profile = {
                "firstName": user.get("firstName") or profile.get("firstName"),
                "lastName": user.get("lastName") or profile.get("lastName"),
                "role": profile.get("role"),
                "organization": profile.get("organization"),
            }

        wellbeing = await self._get_latest_wellbeing(user_id)

        return CoachingContext(
            user_profile=user_profile,
            wellbeing=wellbeing or {},
            conversation_history=conversation.get("messages", []),
            due_commitments=due_commitments,
            safety_level=safety_level,
            language=language
        )

    async def _get_latest_wellbeing(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's latest check-in data."""
        checkin = await self._checkins_collection.find_one(
            {"userId": ObjectId(user_id)},
            sort=[("date", -1)]
        )

        if not checkin:
            return None

        return {
            "mood": checkin.get("mood"),
            "energy": checkin.get("energy"),
            "stress": checkin.get("stress"),
            "sleep": checkin.get("sleep"),
            "date": checkin.get("date")
        }

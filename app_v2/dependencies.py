"""
FastAPI dependencies for Deburn application.

Provides dependency injection for all services.
"""

import os
from functools import lru_cache
from typing import Annotated, Optional, Dict, Any

from fastapi import Depends, Request, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from common.auth.firebase_auth import FirebaseAuth

# Auth services
from app_v2.services.auth.device_detector import DeviceDetector
from app_v2.services.auth.geo_ip_service import GeoIPService
from app_v2.services.auth.session_manager import SessionManager
from app_v2.middleware.auth import AuthMiddleware

# User services
from app_v2.services.user.user_service import UserService
from app_v2.services.user.profile_service import ProfileService
from app_v2.services.user.consent_service import ConsentService

# i18n services
from app_v2.services.i18n.language_config import LanguageConfig
from app_v2.services.i18n.i18n_service import I18nService
from app_v2.middleware.i18n import I18nMiddleware

# Check-in services
from app_v2.services.checkin.checkin_service import CheckInService
from app_v2.services.checkin.checkin_analytics import CheckInAnalytics
from app_v2.services.checkin.insight_generator import InsightGenerator

# Circles services
from app_v2.services.circles.pool_service import PoolService
from app_v2.services.circles.invitation_service import InvitationService
from app_v2.services.circles.group_service import GroupService
from app_v2.services.circles.meeting_service import MeetingService
from app_v2.services.circles.availability_service import AvailabilityService

# Calendar services
from app_v2.services.calendar.google_calendar_service import GoogleCalendarService
from app_v2.services.calendar.token_encryption import TokenEncryptionService
from app_v2.services.calendar.connection_service import CalendarConnectionService
from app_v2.services.calendar.calendar_availability_service import CalendarAvailabilityService

# Content services
from app_v2.services.content.content_service import ContentService
from app_v2.services.content.learning_progress_service import LearningProgressService

# AI/Coach services
from app_v2.services.coach.safety_checker import SafetyChecker
from app_v2.services.coach.conversation_service import ConversationService
from app_v2.services.coach.commitment_service import CommitmentService
from app_v2.services.coach.commitment_extractor import CommitmentExtractor
from app_v2.services.coach.quick_reply_generator import QuickReplyGenerator
from app_v2.services.coach.coach_service import CoachService
from app_v2.services.coach.pattern_detector import PatternDetector

# Agent system (new)
from app_v2.agent import (
    Agent,
    ClaudeAgent,
    PromptService,
    MemoryProvider,
    EncryptedMemory,
    MemoryEncryptionService,
    # Actions
    ActionGenerator,
    ActionRegistry,
    TopicDetector,
    StaticRetriever,
    LearningHandler,
    ExerciseHandler,
    get_knowledge,
)
from common.ai.claude import ClaudeProvider

# Progress services
from app_v2.services.progress.stats_service import ProgressStatsService
from app_v2.services.progress.insight_service import InsightService
from app_v2.services.progress.insight_engine import InsightEngine

# Media services
from app_v2.services.media.tts_service import TTSService
from app_v2.services.media.image_service import ImageService

# Organization services
from app_v2.services.organization.organization_service import OrganizationService

# Hub services
from app_v2.services.hub.hub_admin_service import HubAdminService
from app_v2.services.hub.hub_content_service import HubContentService
from app_v2.services.hub.coach_config_service import CoachConfigService
from app_v2.services.hub.compliance_service import ComplianceService


# ─────────────────────────────────────────────────────────────────
# Global service instances
# ─────────────────────────────────────────────────────────────────

# Auth
_firebase_auth: Optional[FirebaseAuth] = None
_session_manager: Optional[SessionManager] = None
_auth_middleware: Optional[AuthMiddleware] = None

# User
_user_service: Optional[UserService] = None
_profile_service: Optional[ProfileService] = None
_consent_service: Optional[ConsentService] = None

# i18n
_language_config: Optional[LanguageConfig] = None
_i18n_service: Optional[I18nService] = None
_i18n_middleware: Optional[I18nMiddleware] = None

# Check-in
_checkin_service: Optional[CheckInService] = None
_checkin_analytics: Optional[CheckInAnalytics] = None
_insight_generator: Optional[InsightGenerator] = None

# Circles
_pool_service: Optional[PoolService] = None
_invitation_service: Optional[InvitationService] = None
_group_service: Optional[GroupService] = None
_meeting_service: Optional[MeetingService] = None
_circles_availability_service: Optional[AvailabilityService] = None

# Calendar
_google_calendar_service: Optional[GoogleCalendarService] = None
_token_encryption_service: Optional[TokenEncryptionService] = None
_connection_service: Optional[CalendarConnectionService] = None
_calendar_availability_service: Optional[CalendarAvailabilityService] = None

# Content
_content_service: Optional[ContentService] = None
_learning_progress_service: Optional[LearningProgressService] = None

# AI/Coach
_agent: Optional[Agent] = None
_safety_checker: Optional[SafetyChecker] = None
_conversation_service: Optional[ConversationService] = None
_commitment_service: Optional[CommitmentService] = None
_commitment_extractor: Optional[CommitmentExtractor] = None
_quick_reply_generator: Optional[QuickReplyGenerator] = None
_coach_service: Optional[CoachService] = None
_pattern_detector: Optional[PatternDetector] = None

# Agent system (new)
_claude_provider: Optional[ClaudeProvider] = None
_prompt_service: Optional[PromptService] = None
_memory_encryption_service: Optional[MemoryEncryptionService] = None
_memory_provider: Optional[MemoryProvider] = None
_action_generator: Optional[ActionGenerator] = None

# Progress
_stats_service: Optional[ProgressStatsService] = None
_progress_insight_service: Optional[InsightService] = None
_insight_engine: Optional[InsightEngine] = None

# Media
_tts_service: Optional[TTSService] = None
_image_service: Optional[ImageService] = None

# Organization
_organization_service: Optional[OrganizationService] = None

# Hub
_hub_db: Optional[AsyncIOMotorDatabase] = None
_hub_admin_service: Optional[HubAdminService] = None
_hub_content_service: Optional[HubContentService] = None
_coach_config_service: Optional[CoachConfigService] = None
_compliance_service: Optional[ComplianceService] = None

# Main database (for learning content)
_main_db: Optional[AsyncIOMotorDatabase] = None


# ─────────────────────────────────────────────────────────────────
# Cached singletons
# ─────────────────────────────────────────────────────────────────

@lru_cache()
def get_device_detector() -> DeviceDetector:
    """Get cached DeviceDetector instance."""
    return DeviceDetector()


# ─────────────────────────────────────────────────────────────────
# Initialization functions
# ─────────────────────────────────────────────────────────────────

def init_auth_services(
    db: AsyncIOMotorDatabase,
    firebase_credentials_path: Optional[str] = None,
    firebase_credentials_dict: Optional[dict] = None,
    geoip_database_path: Optional[str] = None
) -> None:
    """Initialize auth services."""
    global _firebase_auth, _session_manager, _auth_middleware

    _firebase_auth = FirebaseAuth(
        credentials_path=firebase_credentials_path,
        credentials_dict=firebase_credentials_dict
    )

    device_detector = get_device_detector()
    geo_service = GeoIPService(database_path=geoip_database_path)

    _session_manager = SessionManager(
        db=db,
        device_detector=device_detector,
        geo_service=geo_service
    )

    _auth_middleware = AuthMiddleware(session_manager=_session_manager)


def init_user_services(db: AsyncIOMotorDatabase) -> None:
    """Initialize user services."""
    global _user_service, _profile_service, _consent_service

    _consent_service = ConsentService(db=db)
    _profile_service = ProfileService(db=db)
    _user_service = UserService(db=db, consent_service=_consent_service)


def init_i18n_services(
    db: Optional[AsyncIOMotorDatabase] = None,
    locales_path: str = "public/locales",
    emails_path: str = "locales/emails",
    source_mode: str = "file"
) -> None:
    """Initialize i18n services."""
    global _language_config, _i18n_service, _i18n_middleware

    _language_config = LanguageConfig(db=db, source_mode=source_mode)
    _i18n_service = I18nService(
        language_config=_language_config,
        locales_path=locales_path,
        emails_path=emails_path,
        source_mode=source_mode
    )
    _i18n_middleware = I18nMiddleware(
        i18n_service=_i18n_service,
        language_config=_language_config
    )


def init_checkin_services(db: AsyncIOMotorDatabase, ai_client=None) -> None:
    """Initialize check-in services."""
    global _checkin_service, _checkin_analytics, _insight_generator

    _checkin_service = CheckInService(db=db)
    _checkin_analytics = CheckInAnalytics(checkin_service=_checkin_service)
    _insight_generator = InsightGenerator(
        ai_client=ai_client,
        checkin_service=_checkin_service
    )


def init_circles_services(db: AsyncIOMotorDatabase, calendar_service=None) -> None:
    """Initialize circles services."""
    global _pool_service, _invitation_service, _group_service
    global _meeting_service, _circles_availability_service

    _pool_service = PoolService(db=db)
    _invitation_service = InvitationService(db=db)
    _group_service = GroupService(db=db)
    _meeting_service = MeetingService(db=db, calendar_service=calendar_service)
    _circles_availability_service = AvailabilityService(db=db)


def init_calendar_services(db: AsyncIOMotorDatabase) -> None:
    """Initialize calendar services."""
    global _google_calendar_service, _token_encryption_service
    global _connection_service, _calendar_availability_service

    _google_calendar_service = GoogleCalendarService(
        client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
        redirect_uri=os.getenv("GOOGLE_REDIRECT_URI", ""),
        webhook_url=os.getenv("CALENDAR_WEBHOOK_URL"),
    )

    encryption_key = os.getenv("CALENDAR_ENCRYPTION_KEY", "")
    if encryption_key:
        _token_encryption_service = TokenEncryptionService(encryption_key=encryption_key)

        _connection_service = CalendarConnectionService(
            db=db,
            google_calendar=_google_calendar_service,
            token_encryption=_token_encryption_service,
        )

        _calendar_availability_service = CalendarAvailabilityService(
            db=db,
            google_calendar=_google_calendar_service,
            connection_service=_connection_service,
        )


def init_content_services(db: AsyncIOMotorDatabase) -> None:
    """Initialize content services."""
    global _content_service, _learning_progress_service

    source_type = os.getenv("CONTENT_SOURCE_TYPE", "file")
    filepath = os.getenv("CONTENT_FILEPATH")

    _content_service = ContentService(
        source_type=source_type,
        filepath=filepath,
        db=db if source_type == "database" else None
    )
    _learning_progress_service = LearningProgressService(db=db)


def init_ai_services(
    db: AsyncIOMotorDatabase,
    hub_db: Optional[AsyncIOMotorDatabase] = None
) -> None:
    """
    Initialize AI coaching services.

    Args:
        db: Main application database
        hub_db: Hub database for prompts and encrypted memory (optional)
    """
    global _agent, _safety_checker, _conversation_service, _commitment_service
    global _commitment_extractor, _quick_reply_generator, _coach_service, _pattern_detector
    global _claude_provider, _prompt_service, _memory_encryption_service, _memory_provider

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    model = os.getenv("AGENT_MODEL", "claude-sonnet-4-5-20250514")
    max_tokens = int(os.getenv("AGENT_MAX_TOKENS", "1024"))
    daily_limit = int(os.getenv("COACH_DAILY_LIMIT", "15"))

    # Initialize new agent system if API key available
    prompt_source = os.getenv("AI_PROMPT_SOURCE", "aiprompt")

    if api_key:
        # Claude provider (from common/ai/)
        _claude_provider = ClaudeProvider(
            api_key=api_key,
            model=model
        )

        # Prompt service (loads from MongoDB or files based on AI_PROMPT_SOURCE)
        _prompt_service = PromptService(
            db=hub_db if prompt_source == "aiprompt" else None,
            cache_ttl=int(os.getenv("PROMPT_CACHE_TTL", "300")),
            source=prompt_source,
            prompts_dir=os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "system")
        )

        # Memory encryption
        encryption_key = os.getenv("MEMORY_ENCRYPTION_KEY", "default-dev-key")
        _memory_encryption_service = MemoryEncryptionService(encryption_key)

        # Encrypted memory (stores in MongoDB conversations collection)
        # Requires hub_db for conversation storage
        if hub_db is not None:
            _memory_provider = EncryptedMemory(
                db=hub_db,
                encryption_service=_memory_encryption_service
            )

        # Claude agent (uses provider + prompt service)
        _agent = ClaudeAgent(
            provider=_claude_provider,
            prompt_service=_prompt_service,
            max_tokens=max_tokens
        )

    _safety_checker = SafetyChecker()
    # Store conversations in hub_db for centralized storage
    _conversation_service = ConversationService(db=hub_db if hub_db is not None else db)
    _commitment_service = CommitmentService(db=db)
    _commitment_extractor = CommitmentExtractor()
    _quick_reply_generator = QuickReplyGenerator()
    _pattern_detector = PatternDetector(db=db)

    # Initialize action generator
    knowledge = get_knowledge()
    retriever = StaticRetriever(knowledge=knowledge)
    topic_detector = TopicDetector(knowledge=knowledge)

    registry = ActionRegistry()
    registry.register(LearningHandler(retriever=retriever))
    registry.register(ExerciseHandler(retriever=retriever))

    _action_generator = ActionGenerator(
        registry=registry,
        topic_detector=topic_detector
    )

    if _agent:
        _coach_service = CoachService(
            agent=_agent,
            safety_checker=_safety_checker,
            commitment_service=_commitment_service,
            commitment_extractor=_commitment_extractor,
            quick_reply_generator=_quick_reply_generator,
            action_generator=_action_generator,
            db=db,
            daily_limit=daily_limit
        )


def init_progress_services(
    db: AsyncIOMotorDatabase,
    pattern_detector: Optional[PatternDetector] = None,
    agent=None
) -> None:
    """Initialize progress services."""
    global _stats_service, _progress_insight_service, _insight_engine

    _stats_service = ProgressStatsService(db=db)
    _progress_insight_service = InsightService(db=db)

    if pattern_detector is None:
        pattern_detector = PatternDetector(db=db)

    _insight_engine = InsightEngine(
        db=db,
        insight_service=_progress_insight_service,
        pattern_detector=pattern_detector,
        agent=agent
    )


def init_media_services(
    db: AsyncIOMotorDatabase,
    tts_config: Optional[Dict[str, Any]] = None,
    image_config: Optional[Dict[str, Any]] = None
) -> None:
    """Initialize media services."""
    global _tts_service, _image_service

    _tts_service = TTSService(db=db, config=tts_config)
    _image_service = ImageService(db=db, config=image_config)


def init_organization_services(db: AsyncIOMotorDatabase) -> None:
    """Initialize organization services."""
    global _organization_service
    _organization_service = OrganizationService(db=db)


def init_hub_services(
    hub_db: AsyncIOMotorDatabase,
    app_db: AsyncIOMotorDatabase,
    prompts_dir: Optional[str] = None,
    knowledge_base_dir: Optional[str] = None
) -> None:
    """Initialize hub services."""
    global _hub_db, _hub_admin_service, _hub_content_service
    global _coach_config_service, _compliance_service

    _hub_db = hub_db

    _hub_admin_service = HubAdminService(hub_db=hub_db)
    _hub_content_service = HubContentService(hub_db=hub_db)
    _coach_config_service = CoachConfigService(
        hub_db=hub_db,
        prompts_dir=prompts_dir,
        knowledge_base_dir=knowledge_base_dir
    )
    _compliance_service = ComplianceService(app_db=app_db, hub_db=hub_db)


def init_all_services(
    db: AsyncIOMotorDatabase,
    hub_db: Optional[AsyncIOMotorDatabase] = None,
    firebase_credentials_path: Optional[str] = None,
    firebase_credentials_dict: Optional[dict] = None,
    geoip_database_path: Optional[str] = None
) -> None:
    """
    Initialize all services at application startup.

    Args:
        db: Main MongoDB database connection
        hub_db: Hub MongoDB database connection (optional)
        firebase_credentials_path: Path to Firebase credentials
        firebase_credentials_dict: Firebase credentials as dict
        geoip_database_path: Path to GeoIP database
    """
    global _main_db
    _main_db = db

    init_auth_services(db, firebase_credentials_path, firebase_credentials_dict, geoip_database_path)
    init_user_services(db)
    init_i18n_services(db)
    init_checkin_services(db)
    init_calendar_services(db)
    init_circles_services(db, _google_calendar_service)
    init_content_services(db)
    init_ai_services(db, hub_db)  # Pass hub_db for new agent system
    init_progress_services(db, _pattern_detector, _agent)
    init_media_services(db)
    init_organization_services(db)

    if hub_db is not None:
        init_hub_services(hub_db, db)


# ─────────────────────────────────────────────────────────────────
# Auth getters
# ─────────────────────────────────────────────────────────────────

def get_firebase_auth() -> FirebaseAuth:
    """Get Firebase auth client."""
    if _firebase_auth is None:
        raise RuntimeError("Auth services not initialized.")
    return _firebase_auth


def get_session_manager() -> SessionManager:
    """Get session manager instance."""
    if _session_manager is None:
        raise RuntimeError("Auth services not initialized.")
    return _session_manager


def get_auth_middleware() -> AuthMiddleware:
    """Get auth middleware instance."""
    if _auth_middleware is None:
        raise RuntimeError("Auth services not initialized.")
    return _auth_middleware


async def require_auth(
    request: Request,
    auth_middleware: Annotated[AuthMiddleware, Depends(get_auth_middleware)]
) -> dict:
    """Dependency that requires authentication."""
    return await auth_middleware.require_auth(request)


async def optional_auth(
    request: Request,
    auth_middleware: Annotated[AuthMiddleware, Depends(get_auth_middleware)]
) -> Optional[dict]:
    """Dependency that optionally authenticates."""
    return await auth_middleware.optional_auth(request)


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    if request.client:
        return request.client.host
    return "0.0.0.0"


def get_user_agent(request: Request) -> str:
    """Extract User-Agent from request."""
    return request.headers.get("User-Agent", "")


# ─────────────────────────────────────────────────────────────────
# User getters
# ─────────────────────────────────────────────────────────────────

def get_user_service() -> UserService:
    """Get user service instance."""
    if _user_service is None:
        raise RuntimeError("User services not initialized.")
    return _user_service


def get_profile_service() -> ProfileService:
    """Get profile service instance."""
    if _profile_service is None:
        raise RuntimeError("User services not initialized.")
    return _profile_service


def get_consent_service() -> ConsentService:
    """Get consent service instance."""
    if _consent_service is None:
        raise RuntimeError("User services not initialized.")
    return _consent_service


# ─────────────────────────────────────────────────────────────────
# i18n getters
# ─────────────────────────────────────────────────────────────────

def get_language_config() -> LanguageConfig:
    """Get language config instance."""
    if _language_config is None:
        raise RuntimeError("i18n services not initialized.")
    return _language_config


def get_i18n_service() -> I18nService:
    """Get i18n service instance."""
    if _i18n_service is None:
        raise RuntimeError("i18n services not initialized.")
    return _i18n_service


def get_i18n_middleware() -> I18nMiddleware:
    """Get i18n middleware instance."""
    if _i18n_middleware is None:
        raise RuntimeError("i18n services not initialized.")
    return _i18n_middleware


# ─────────────────────────────────────────────────────────────────
# Check-in getters
# ─────────────────────────────────────────────────────────────────

def get_checkin_service() -> CheckInService:
    """Get check-in service instance."""
    if _checkin_service is None:
        raise RuntimeError("Check-in services not initialized.")
    return _checkin_service


def get_checkin_analytics() -> CheckInAnalytics:
    """Get check-in analytics instance."""
    if _checkin_analytics is None:
        raise RuntimeError("Check-in services not initialized.")
    return _checkin_analytics


def get_insight_generator() -> InsightGenerator:
    """Get insight generator instance."""
    if _insight_generator is None:
        raise RuntimeError("Check-in services not initialized.")
    return _insight_generator


# ─────────────────────────────────────────────────────────────────
# Circles getters
# ─────────────────────────────────────────────────────────────────

def get_pool_service() -> PoolService:
    """Get pool service instance."""
    if _pool_service is None:
        raise RuntimeError("Circles services not initialized.")
    return _pool_service


def get_invitation_service() -> InvitationService:
    """Get invitation service instance."""
    if _invitation_service is None:
        raise RuntimeError("Circles services not initialized.")
    return _invitation_service


def get_group_service() -> GroupService:
    """Get group service instance."""
    if _group_service is None:
        raise RuntimeError("Circles services not initialized.")
    return _group_service


def get_meeting_service() -> MeetingService:
    """Get meeting service instance."""
    if _meeting_service is None:
        raise RuntimeError("Circles services not initialized.")
    return _meeting_service


def get_circles_availability_service() -> AvailabilityService:
    """Get circles availability service instance."""
    if _circles_availability_service is None:
        raise RuntimeError("Circles services not initialized.")
    return _circles_availability_service


# Alias for backwards compatibility
get_availability_service = get_circles_availability_service


# ─────────────────────────────────────────────────────────────────
# Calendar getters
# ─────────────────────────────────────────────────────────────────

def get_google_calendar_service() -> GoogleCalendarService:
    """Get Google Calendar service instance."""
    if _google_calendar_service is None:
        raise RuntimeError("Calendar services not initialized.")
    return _google_calendar_service


def get_token_encryption_service() -> TokenEncryptionService:
    """Get token encryption service instance."""
    if _token_encryption_service is None:
        raise RuntimeError("Calendar services not initialized.")
    return _token_encryption_service


def get_connection_service() -> CalendarConnectionService:
    """Get calendar connection service instance."""
    if _connection_service is None:
        raise RuntimeError("Calendar services not initialized.")
    return _connection_service


def get_calendar_availability_service() -> CalendarAvailabilityService:
    """Get calendar availability service instance."""
    if _calendar_availability_service is None:
        raise RuntimeError("Calendar services not initialized.")
    return _calendar_availability_service


# ─────────────────────────────────────────────────────────────────
# Content getters
# ─────────────────────────────────────────────────────────────────

def get_content_service() -> ContentService:
    """Get content service instance."""
    if _content_service is None:
        raise RuntimeError("Content services not initialized.")
    return _content_service


def get_learning_progress_service() -> LearningProgressService:
    """Get learning progress service instance."""
    if _learning_progress_service is None:
        raise RuntimeError("Content services not initialized.")
    return _learning_progress_service


# ─────────────────────────────────────────────────────────────────
# AI/Coach getters
# ─────────────────────────────────────────────────────────────────

def get_agent() -> Agent:
    """Get AI agent instance."""
    if _agent is None:
        raise RuntimeError("AI agent not initialized.")
    return _agent


def get_safety_checker() -> SafetyChecker:
    """Get safety checker instance."""
    if _safety_checker is None:
        raise RuntimeError("AI services not initialized.")
    return _safety_checker


def get_conversation_service() -> ConversationService:
    """Get conversation service instance."""
    if _conversation_service is None:
        raise RuntimeError("AI services not initialized.")
    return _conversation_service


def get_commitment_service() -> CommitmentService:
    """Get commitment service instance."""
    if _commitment_service is None:
        raise RuntimeError("AI services not initialized.")
    return _commitment_service


def get_coach_service() -> CoachService:
    """Get coach service instance."""
    if _coach_service is None:
        raise RuntimeError("AI services not initialized.")
    return _coach_service


def get_pattern_detector() -> PatternDetector:
    """Get pattern detector instance."""
    if _pattern_detector is None:
        raise RuntimeError("AI services not initialized.")
    return _pattern_detector


def get_action_generator() -> ActionGenerator:
    """Get action generator instance."""
    if _action_generator is None:
        raise RuntimeError("AI services not initialized.")
    return _action_generator


def get_prompt_service() -> PromptService:
    """Get prompt service instance."""
    if _prompt_service is None:
        raise RuntimeError("Agent services not initialized (requires hub_db).")
    return _prompt_service


def get_memory_provider() -> MemoryProvider:
    """Get memory provider instance."""
    if _memory_provider is None:
        raise RuntimeError("Agent services not initialized (requires hub_db).")
    return _memory_provider


def get_claude_provider() -> ClaudeProvider:
    """Get Claude provider instance."""
    if _claude_provider is None:
        raise RuntimeError("Agent services not initialized (requires hub_db).")
    return _claude_provider


def get_memory_encryption_service() -> MemoryEncryptionService:
    """Get memory encryption service instance."""
    if _memory_encryption_service is None:
        raise RuntimeError("Agent services not initialized (requires hub_db).")
    return _memory_encryption_service


# ─────────────────────────────────────────────────────────────────
# Progress getters
# ─────────────────────────────────────────────────────────────────

def get_stats_service() -> ProgressStatsService:
    """Get progress stats service instance."""
    if _stats_service is None:
        raise RuntimeError("Progress services not initialized.")
    return _stats_service


def get_progress_insight_service() -> InsightService:
    """Get progress insight service instance."""
    if _progress_insight_service is None:
        raise RuntimeError("Progress services not initialized.")
    return _progress_insight_service


def get_insight_engine() -> InsightEngine:
    """Get insight engine instance."""
    if _insight_engine is None:
        raise RuntimeError("Progress services not initialized.")
    return _insight_engine


# Alias for backwards compatibility
get_insight_service = get_progress_insight_service


# ─────────────────────────────────────────────────────────────────
# Media getters
# ─────────────────────────────────────────────────────────────────

def get_tts_service() -> TTSService:
    """Get TTS service instance."""
    if _tts_service is None:
        raise RuntimeError("Media services not initialized.")
    return _tts_service


def get_image_service() -> ImageService:
    """Get image service instance."""
    if _image_service is None:
        raise RuntimeError("Media services not initialized.")
    return _image_service


# ─────────────────────────────────────────────────────────────────
# Organization getters
# ─────────────────────────────────────────────────────────────────

def get_organization_service() -> OrganizationService:
    """Get organization service instance."""
    if _organization_service is None:
        raise RuntimeError("Organization services not initialized.")
    return _organization_service


# ─────────────────────────────────────────────────────────────────
# Hub getters
# ─────────────────────────────────────────────────────────────────

def get_hub_admin_service() -> HubAdminService:
    """Get hub admin service instance."""
    if _hub_admin_service is None:
        raise RuntimeError("Hub services not initialized.")
    return _hub_admin_service


def get_hub_content_service() -> HubContentService:
    """Get hub content service instance."""
    if _hub_content_service is None:
        raise RuntimeError("Hub services not initialized.")
    return _hub_content_service


def get_coach_config_service() -> CoachConfigService:
    """Get coach config service instance."""
    if _coach_config_service is None:
        raise RuntimeError("Hub services not initialized.")
    return _coach_config_service


def get_compliance_service() -> ComplianceService:
    """Get compliance service instance."""
    if _compliance_service is None:
        raise RuntimeError("Hub services not initialized.")
    return _compliance_service


async def require_hub_admin(
    user: dict = Depends(require_auth),
    hub_admin_service: HubAdminService = Depends(get_hub_admin_service)
) -> dict:
    """Dependency that requires the user to be a hub admin."""
    email = user.get("email", "")

    if not await hub_admin_service.is_hub_admin(email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hub admin access required"
        )

    return user


# ─────────────────────────────────────────────────────────────────
# Main database getter
# ─────────────────────────────────────────────────────────────────

def get_main_db() -> AsyncIOMotorDatabase:
    """Get main database instance."""
    if _main_db is None:
        raise RuntimeError("Main database not initialized.")
    return _main_db


def get_hub_db() -> AsyncIOMotorDatabase:
    """Get hub database instance."""
    if _hub_db is None:
        raise RuntimeError("Hub database not initialized.")
    return _hub_db

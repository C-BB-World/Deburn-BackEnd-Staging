"""
Deburn Services.

All service classes organized by feature.
"""

# Auth services
from app_v2.services.auth.token_hasher import TokenHasher
from app_v2.services.auth.device_detector import DeviceDetector
from app_v2.services.auth.geo_ip_service import GeoIPService
from app_v2.services.auth.session_manager import SessionManager

# User services
from app_v2.services.user.user_service import UserService
from app_v2.services.user.profile_service import ProfileService
from app_v2.services.user.consent_service import ConsentService

# i18n services
from app_v2.services.i18n.language_config import LanguageConfig
from app_v2.services.i18n.i18n_service import I18nService

# Check-in services
from app_v2.services.checkin.metrics_validator import MetricsValidator
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
from app_v2.services.calendar.token_encryption import TokenEncryptionService
from app_v2.services.calendar.google_calendar_service import GoogleCalendarService
from app_v2.services.calendar.connection_service import CalendarConnectionService
from app_v2.services.calendar.calendar_availability_service import CalendarAvailabilityService

# Content services
from app_v2.services.content.content_service import ContentService
from app_v2.services.content.learning_progress_service import LearningProgressService

# AI/Coach services
from app_v2.services.coach.agent import Agent
from app_v2.services.coach.claude_agent import ClaudeAgent
from app_v2.services.coach.safety_checker import SafetyChecker
from app_v2.services.coach.conversation_service import ConversationService
from app_v2.services.coach.commitment_service import CommitmentService
from app_v2.services.coach.commitment_extractor import CommitmentExtractor
from app_v2.services.coach.pattern_detector import PatternDetector
from app_v2.services.coach.quick_reply_generator import QuickReplyGenerator
from app_v2.services.coach.coach_service import CoachService

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

"""
Deburn Mock API Server v2

A FastAPI mock server that simulates all API v2 endpoints for frontend development
and testing without requiring MongoDB, Firebase, or Claude API.

Run with: uvicorn mock_v2:app --port 5002 --reload
"""

import asyncio
import json
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from fastapi import FastAPI, Header, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel, Field


# =============================================================================
# APP SETUP
# =============================================================================

app = FastAPI(
    title="Deburn Mock API v2",
    description="Mock API server for frontend development",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
)


# =============================================================================
# MOCK DATA STORES
# =============================================================================

mock_tokens: dict[str, dict] = {}

MOCK_USER = {
    "_id": "usr_mock123",
    "id": "usr_mock123",
    "email": "user@example.com",
    "firstName": "John",
    "lastName": "Doe",
    "isAdmin": False,
    "profile": {
        "firstName": "John",
        "lastName": "Doe",
        "organization": "Acme Corp",
        "jobTitle": "Engineering Manager",
        "preferredLanguage": "en",
        "timezone": "Europe/Stockholm",
        "country": "SE",
    },
}

MOCK_ADMIN_USER = {
    "_id": "usr_admin456",
    "id": "usr_admin456",
    "email": "admin@example.com",
    "firstName": "Admin",
    "lastName": "User",
    "isAdmin": True,
    "profile": {
        "firstName": "Admin",
        "lastName": "User",
        "organization": "Deburn",
        "jobTitle": "Administrator",
        "preferredLanguage": "en",
        "timezone": "Europe/Stockholm",
    },
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def generate_token() -> str:
    return f"mock_token_{secrets.token_hex(16)}"


def success_response(data):
    """Wrap data in standard success response format."""
    return {"success": True, "data": data}


def require_auth(authorization: Optional[str] = Header(None)) -> dict:
    """Accept any token - just check if header exists."""
    if authorization:
        token = authorization.replace("Bearer ", "")
        if token in mock_tokens:
            return mock_tokens[token]
    # For mock server, always return mock user
    return MOCK_USER


def require_hub_admin(authorization: Optional[str] = Header(None)) -> dict:
    """For mock, always return admin user."""
    return MOCK_ADMIN_USER


# =============================================================================
# REQUEST MODELS
# =============================================================================

# Auth
class RegisterRequest(BaseModel):
    firstName: str
    lastName: str
    email: str
    password: str
    passwordConfirm: str
    organization: Optional[str] = None
    country: Optional[str] = None
    consents: Optional[dict] = None


class LoginRequest(BaseModel):
    email: str
    password: str
    rememberMe: bool = False


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: str


# User
class ProfileUpdateRequest(BaseModel):
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    organization: Optional[str] = None
    role: Optional[str] = None
    bio: Optional[str] = None
    jobTitle: Optional[str] = None
    leadershipLevel: Optional[str] = None
    timezone: Optional[str] = None
    preferredLanguage: Optional[str] = None


class ConsentUpdateRequest(BaseModel):
    accepted: bool


class DeleteAccountRequest(BaseModel):
    password: Optional[str] = None


# Check-in
class CheckInRequest(BaseModel):
    mood: int = Field(..., ge=1, le=5)
    physicalEnergy: int = Field(..., ge=1, le=10)
    mentalEnergy: int = Field(..., ge=1, le=10)
    sleep: int = Field(..., ge=1, le=5)
    stress: int = Field(..., ge=1, le=10)


# Coach
class SendMessageRequest(BaseModel):
    message: str
    conversationId: Optional[str] = None
    context: Optional[dict] = None
    language: str = "en"


class VoiceRequest(BaseModel):
    text: str
    voice: str = "alloy"


class CompleteCommitmentRequest(BaseModel):
    reflectionNotes: Optional[str] = None
    helpfulnessRating: Optional[int] = None


# Circles
class UpdateAvailabilityRequest(BaseModel):
    slots: List[dict]


class ScheduleMeetingRequest(BaseModel):
    title: str
    scheduledAt: str
    day: Optional[str] = None
    hour: Optional[int] = None


class UpdateAttendanceRequest(BaseModel):
    attending: bool


class CreatePoolRequest(BaseModel):
    name: str
    topic: Optional[str] = None
    description: Optional[str] = None
    organizationId: Optional[str] = None
    targetGroupSize: int = 5
    cadence: str = "bi-weekly"


class SendInvitationsRequest(BaseModel):
    emails: List[str]


# Organization
class CreateOrganizationRequest(BaseModel):
    name: str
    domain: Optional[str] = None


class UpdateOrganizationRequest(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    settings: Optional[dict] = None


class AddMemberRequest(BaseModel):
    email: str
    role: str = "member"


class ChangeMemberRoleRequest(BaseModel):
    role: str


class TransferOwnershipRequest(BaseModel):
    newOwnerId: str


# Hub
class AddHubAdminRequest(BaseModel):
    email: str


class AddOrgAdminRequest(BaseModel):
    email: str
    organizationId: str


class UpdateCoachSettingsRequest(BaseModel):
    dailyExchangeLimit: Optional[int] = None


class UpdatePromptRequest(BaseModel):
    content: str


class UpdateExercisesRequest(BaseModel):
    exercises: List[dict]


class CreateContentRequest(BaseModel):
    contentType: str
    category: str
    status: str = "draft"
    titleEn: str
    titleSv: Optional[str] = None
    purpose: Optional[str] = None
    lengthMinutes: Optional[float] = None
    coachTopics: Optional[List[str]] = None
    coachPriority: Optional[int] = 0
    coachEnabled: Optional[bool] = True
    textContentEn: Optional[str] = None
    textContentSv: Optional[str] = None
    videoUrl: Optional[str] = None


class UpdateContentRequest(CreateContentRequest):
    pass


# Feedback
class SubmitFeedbackRequest(BaseModel):
    content: Optional[str] = Field(None, max_length=2000)
    rating: Optional[int] = Field(None, ge=1, le=5)
    isAnonymous: bool = False


class SubmitLearningRatingRequest(BaseModel):
    contentId: str
    contentTitle: str
    rating: int = Field(..., ge=1, le=5)
    isAnonymous: bool = False


# Image
class GenerateImageRequest(BaseModel):
    prompt: str
    width: int = 1024
    height: int = 1024
    seed: Optional[int] = None


class GenerateImageFastRequest(BaseModel):
    prompt: str
    size: str = "square"


class GenerateImageToImageRequest(BaseModel):
    prompt: str
    image: str
    strength: float = 0.7


# Learning
class CoachRecommendationsRequest(BaseModel):
    topics: List[str]
    language: str = "en"


class ProgressUpdateRequest(BaseModel):
    progress: int = 100


# Avatar
class RemoveAvatarRequest(BaseModel):
    remove: bool = True


# =============================================================================
# MOCK DATA
# =============================================================================

MOCK_LANGUAGES = [
    {"code": "en", "name": "English", "nativeName": "English"},
    {"code": "sv", "name": "Swedish", "nativeName": "Svenska"},
]

MOCK_CHECKIN_INSIGHTS = {
    "en": [
        "Your stress tends to spike on Thursdays. Consider blocking 30 minutes before your afternoon meetings.",
        "Your energy levels are highest in the morning. Schedule demanding tasks during this time.",
        "You've maintained consistent sleep patterns this week. Great job!",
    ],
    "sv": [
        "Din stress tenderar att toppa p\u00e5 torsdagar. \u00d6verv\u00e4g att blockera 30 minuter f\u00f6re dina eftermiddagsm\u00f6ten.",
        "Din energiniv\u00e5 \u00e4r h\u00f6gst p\u00e5 morgonen. Schemal\u00e4gg kr\u00e4vande uppgifter under denna tid.",
        "Du har h\u00e5llit ett konsekvent s\u00f6mnm\u00f6nster denna vecka. Bra jobbat!",
    ],
}

MOCK_CHECKIN_TIPS = {
    "en": [
        "Try the 2-minute breathing exercise before your 10am call",
        "Consider a short walk after lunch to boost afternoon energy",
        "Take a 5-minute break every 90 minutes for optimal focus",
    ],
    "sv": [
        "Prova 2-minuters andnings\u00f6vning f\u00f6re ditt 10-samtal",
        "\u00d6verv\u00e4g en kort promenad efter lunch f\u00f6r att \u00f6ka eftermiddagsenergin",
        "Ta en 5-minuters paus var 90:e minut f\u00f6r optimalt fokus",
    ],
}

MOCK_CIRCLE_GROUPS = [
    {
        "id": "grp_123",
        "name": "Engineering Leaders",
        "memberCount": 6,
        "members": [
            {"id": "usr_1", "name": "Anna Svensson", "email": "anna@acme.com", "avatar": None},
            {"id": "usr_2", "name": "Erik Lindqvist", "email": "erik@acme.com", "avatar": None},
            {"id": "usr_3", "name": "Maria Karlsson", "email": "maria@acme.com", "avatar": None},
        ],
        "nextMeeting": {
            "id": "mtg_123",
            "title": "Bi-weekly Check-in",
            "scheduledAt": "2026-01-20T15:00:00Z",
            "meetingLink": "https://meet.google.com/abc-defg-hij",
        },
        "pool": {"cadence": "bi-weekly", "topic": "Managing remote team dynamics"},
    },
    {
        "id": "grp_456",
        "name": "Product Managers Circle",
        "memberCount": 4,
        "members": [
            {"id": "usr_7", "name": "Sara Andersson", "email": "sara@techstart.se", "avatar": None},
            {"id": "usr_8", "name": "Mikael Johansson", "email": "mikael@techstart.se", "avatar": None},
        ],
        "nextMeeting": None,
        "pool": {"cadence": "weekly", "topic": "Stakeholder communication strategies"},
    },
]

MOCK_PENDING_INVITATIONS = [
    {
        "id": "inv_pending_1",
        "token": "abc123token",
        "poolName": "Senior Leadership Circle",
        "expiresAt": "2026-02-15T00:00:00Z",
    },
]

MOCK_USER_AVAILABILITY = [
    {"dayOfWeek": "monday", "startTime": "10:00", "endTime": "11:00"},
    {"dayOfWeek": "monday", "startTime": "14:00", "endTime": "16:00"},
    {"dayOfWeek": "wednesday", "startTime": "10:00", "endTime": "12:00"},
    {"dayOfWeek": "friday", "startTime": "09:00", "endTime": "11:00"},
]

MOCK_CONVERSATIONS = {}

MOCK_COMMITMENTS = [
    {
        "id": "cmt_001",
        "userId": "usr_mock123",
        "conversationId": "conv_123",
        "commitment": "Schedule a 1:1 with each team member this week",
        "reflectionQuestion": "What did you learn about your team?",
        "topic": "leadership",
        "status": "active",
        "followUpDate": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
        "createdAt": datetime.now(timezone.utc).isoformat(),
    },
]

MOCK_CONTENT_ITEMS = [
    # Featured
    {
        "id": "cnt_featured_1",
        "contentType": "text_article",
        "category": "featured",
        "status": "published",
        "sortOrder": 1,
        "titleEn": "Welcome to Eve",
        "titleSv": "V\u00e4lkommen till Eve",
        "purpose": "Introduction to your AI leadership coach",
        "lengthMinutes": 3,
        "textContentEn": "<h2>Welcome to Eve</h2><p>Eve is your personal AI leadership coach, designed to help you grow as a leader...</p>",
        "textContentSv": "<h2>V\u00e4lkommen till Eve</h2><p>Eve \u00e4r din personliga AI-ledarskapscoach...</p>",
        "coachTopics": ["leadership"],
        "coachPriority": 10,
        "coachEnabled": True,
        "hasContent": True,
    },
    {
        "id": "cnt_featured_2",
        "contentType": "audio_exercise",
        "category": "featured",
        "status": "published",
        "sortOrder": 2,
        "titleEn": "Morning Energy Boost",
        "titleSv": "Morgonens energiboost",
        "purpose": "Start your day with intention and focus",
        "lengthMinutes": 5,
        "audioFileEn": "/audio/morning-energy-en.mp3",
        "audioFileSv": "/audio/morning-energy-sv.mp3",
        "coachTopics": ["motivation", "mindfulness"],
        "coachPriority": 9,
        "coachEnabled": True,
        "hasContent": True,
    },
    # Leadership
    {
        "id": "cnt_1",
        "contentType": "text_article",
        "category": "leadership",
        "status": "published",
        "sortOrder": 1,
        "titleEn": "The Art of Delegation",
        "titleSv": "Konsten att delegera",
        "purpose": "Help leaders understand when and how to delegate effectively",
        "lengthMinutes": 8,
        "textContentEn": "<h2>The Art of Delegation</h2><p>Delegation is a crucial leadership skill that separates good managers from great leaders...</p><h3>When to Delegate</h3><p>Consider delegating when:</p><ul><li>The task helps develop team members</li><li>Someone else can do it better</li><li>It frees you for strategic work</li></ul>",
        "textContentSv": "<h2>Konsten att delegera</h2><p>Delegering \u00e4r en avg\u00f6rande ledarskapsf\u00e4rdighet...</p>",
        "coachTopics": ["delegation", "leadership", "time_management"],
        "coachPriority": 8,
        "coachEnabled": True,
        "hasContent": True,
    },
    {
        "id": "cnt_3",
        "contentType": "video_link",
        "category": "leadership",
        "status": "published",
        "sortOrder": 3,
        "titleEn": "Building Psychological Safety",
        "titleSv": "Att bygga psykologisk trygghet",
        "purpose": "Create an environment where team members feel safe to speak up",
        "lengthMinutes": 15,
        "videoUrl": "https://www.youtube.com/watch?v=LhoLuui9gX8",
        "videoEmbedCode": "<iframe src='https://www.youtube.com/embed/LhoLuui9gX8'></iframe>",
        "videoAvailableInEn": True,
        "videoAvailableInSv": False,
        "coachTopics": ["team_dynamics", "leadership", "communication"],
        "coachPriority": 6,
        "coachEnabled": True,
        "hasContent": True,
    },
    {
        "id": "cnt_leadership_3",
        "contentType": "text_article",
        "category": "leadership",
        "status": "published",
        "sortOrder": 4,
        "titleEn": "Giving Effective Feedback",
        "titleSv": "Att ge effektiv feedback",
        "purpose": "Learn to deliver feedback that drives growth",
        "lengthMinutes": 7,
        "textContentEn": "<h2>Giving Effective Feedback</h2><p>Great leaders master the art of feedback...</p>",
        "textContentSv": "<h2>Att ge effektiv feedback</h2><p>Stora ledare beh\u00e4rskar konsten att ge feedback...</p>",
        "coachTopics": ["communication", "leadership", "team_dynamics"],
        "coachPriority": 7,
        "coachEnabled": True,
        "hasContent": True,
    },
    # Breath Techniques
    {
        "id": "cnt_breath_1",
        "contentType": "audio_exercise",
        "category": "breath",
        "status": "published",
        "sortOrder": 1,
        "titleEn": "Box Breathing",
        "titleSv": "Fyrkants-andning",
        "purpose": "Calm your nervous system with this Navy SEAL technique",
        "lengthMinutes": 4,
        "audioFileEn": "/audio/box-breathing-en.mp3",
        "audioFileSv": "/audio/box-breathing-sv.mp3",
        "coachTopics": ["stress", "mindfulness"],
        "coachPriority": 9,
        "coachEnabled": True,
        "hasContent": True,
    },
    {
        "id": "cnt_breath_2",
        "contentType": "audio_exercise",
        "category": "breath",
        "status": "published",
        "sortOrder": 2,
        "titleEn": "4-7-8 Relaxation Breath",
        "titleSv": "4-7-8 Avslappningsandning",
        "purpose": "A technique to reduce anxiety and promote sleep",
        "lengthMinutes": 5,
        "audioFileEn": "/audio/478-breath-en.mp3",
        "audioFileSv": "/audio/478-breath-sv.mp3",
        "coachTopics": ["stress", "resilience"],
        "coachPriority": 8,
        "coachEnabled": True,
        "hasContent": True,
    },
    # Meditation
    {
        "id": "cnt_2",
        "contentType": "audio_exercise",
        "category": "meditation",
        "status": "published",
        "sortOrder": 1,
        "titleEn": "5-Minute Breathing Reset",
        "titleSv": "5-minuters andnings\u00e5terst\u00e4llning",
        "purpose": "Quick stress relief through guided breathing",
        "lengthMinutes": 5,
        "audioFileEn": "/audio/breathing-reset-en.mp3",
        "audioFileSv": "/audio/breathing-reset-sv.mp3",
        "coachTopics": ["stress", "mindfulness", "resilience"],
        "coachPriority": 9,
        "coachEnabled": True,
        "hasContent": True,
    },
    {
        "id": "cnt_meditation_2",
        "contentType": "audio_exercise",
        "category": "meditation",
        "status": "published",
        "sortOrder": 2,
        "titleEn": "Body Scan Meditation",
        "titleSv": "Kroppsskanning Meditation",
        "purpose": "Release tension and reconnect with your body",
        "lengthMinutes": 10,
        "audioFileEn": "/audio/body-scan-en.mp3",
        "audioFileSv": "/audio/body-scan-sv.mp3",
        "coachTopics": ["mindfulness", "stress"],
        "coachPriority": 7,
        "coachEnabled": True,
        "hasContent": True,
    },
    # Burnout Prevention
    {
        "id": "cnt_burnout_1",
        "contentType": "text_article",
        "category": "burnout",
        "status": "published",
        "sortOrder": 1,
        "titleEn": "Recognizing Early Signs of Burnout",
        "titleSv": "Att k\u00e4nna igen tidiga tecken p\u00e5 utbr\u00e4ndhet",
        "purpose": "Learn to identify burnout symptoms before they become severe",
        "lengthMinutes": 8,
        "textContentEn": "<h2>Recognizing Early Signs of Burnout</h2><p>Burnout doesn't happen overnight. Here are the warning signs...</p>",
        "textContentSv": "<h2>Att k\u00e4nna igen tidiga tecken p\u00e5 utbr\u00e4ndhet</h2><p>Utbr\u00e4ndhet sker inte \u00f6ver en natt...</p>",
        "coachTopics": ["burnout", "stress", "resilience"],
        "coachPriority": 9,
        "coachEnabled": True,
        "hasContent": True,
    },
    {
        "id": "cnt_burnout_2",
        "contentType": "audio_article",
        "category": "burnout",
        "status": "published",
        "sortOrder": 2,
        "titleEn": "Setting Healthy Boundaries",
        "titleSv": "Att s\u00e4tta h\u00e4lsosamma gr\u00e4nser",
        "purpose": "Protect your energy by learning to say no",
        "lengthMinutes": 12,
        "audioFileEn": "/audio/boundaries-en.mp3",
        "audioFileSv": "/audio/boundaries-sv.mp3",
        "coachTopics": ["burnout", "time_management"],
        "coachPriority": 8,
        "coachEnabled": True,
        "hasContent": True,
    },
    # Wellbeing
    {
        "id": "cnt_wellbeing_1",
        "contentType": "text_article",
        "category": "wellbeing",
        "status": "published",
        "sortOrder": 1,
        "titleEn": "Managing Energy Throughout the Day",
        "titleSv": "Att hantera energi under dagen",
        "purpose": "Practical strategies for maintaining focus and energy",
        "lengthMinutes": 6,
        "textContentEn": "<h2>Managing Energy Throughout the Day</h2><p>Your energy is your most valuable resource...</p>",
        "textContentSv": "<h2>Att hantera energi under dagen</h2><p>Din energi \u00e4r din mest v\u00e4rdefulla resurs...</p>",
        "coachTopics": ["motivation", "time_management"],
        "coachPriority": 7,
        "coachEnabled": True,
        "hasContent": True,
    },
    {
        "id": "cnt_wellbeing_2",
        "contentType": "audio_exercise",
        "category": "wellbeing",
        "status": "published",
        "sortOrder": 2,
        "titleEn": "Gratitude Practice",
        "titleSv": "Tacksamhets\u00f6vning",
        "purpose": "Build resilience through daily gratitude",
        "lengthMinutes": 5,
        "audioFileEn": "/audio/gratitude-en.mp3",
        "audioFileSv": "/audio/gratitude-sv.mp3",
        "coachTopics": ["resilience", "mindfulness"],
        "coachPriority": 6,
        "coachEnabled": True,
        "hasContent": True,
    },
]

MOCK_ORGANIZATIONS = [
    {"id": "org_1", "name": "Acme Corporation", "domain": "acme.com", "memberCount": 45, "status": "active"},
    {"id": "org_2", "name": "TechStart AB", "domain": "techstart.se", "memberCount": 12, "status": "active"},
]

MOCK_HUB_ADMINS = [
    {"id": "adm_1", "email": "admin@example.com", "addedBy": "system", "addedAt": "2024-01-01T00:00:00Z"},
]

MOCK_COACH_PROMPTS = {
    "en": {
        "base-coach": "You are Eve, an AI leadership coach created by Deburn.",
        "safety-rules": "Always prioritize user wellbeing.",
        "tone-guidelines": "Be warm, professional, and supportive.",
    },
    "sv": {
        "base-coach": "Du \u00e4r Eve, en AI-ledarskapscoach skapad av Deburn.",
        "safety-rules": "Prioritera alltid anv\u00e4ndarens v\u00e4lbefinnande.",
        "tone-guidelines": "Var varm, professionell och st\u00f6djande.",
    },
}

MOCK_COACH_EXERCISES = [
    {"id": "breathing", "nameEn": "Breathing Exercise", "nameSv": "Andnings\u00f6vning", "duration": 5},
    {"id": "grounding", "nameEn": "Grounding Exercise", "nameSv": "Jordnings\u00f6vning", "duration": 3},
]

MOCK_STARTERS = {
    "en": [
        {"key": "leadership", "text": "I want to work on my leadership skills"},
        {"key": "stress", "text": "My stress has been building up"},
        {"key": "team", "text": "I need help with my team"},
        {"key": "decision", "text": "Help me think through a decision"},
    ],
    "sv": [
        {"key": "leadership", "text": "Jag vill utveckla mitt ledarskap"},
        {"key": "stress", "text": "Min stress har \u00f6kat p\u00e5 sistone"},
        {"key": "team", "text": "Jag beh\u00f6ver hj\u00e4lp med mitt team"},
        {"key": "decision", "text": "Hj\u00e4lp mig t\u00e4nka igenom ett beslut"},
    ],
}

MOCK_QUICK_REPLIES = {
    "en": ["Tell me more", "What should I try?", "Give me an example"],
    "sv": ["Ber\u00e4tta mer", "Vad ska jag prova?", "Ge mig ett exempel"],
}

MOCK_NOTIFICATIONS = [
    {
        "id": "notif_001",
        "userId": "usr_mock123",
        "type": "group_assignment",
        "title": "Assigned to Circle A",
        "message": "You have been assigned to Circle A in the Q1 Leadership pool.",
        "metadata": {"poolId": "pool_123", "groupId": "grp_123"},
        "read": False,
        "readAt": None,
        "createdAt": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
    },
    {
        "id": "notif_002",
        "userId": "usr_mock123",
        "type": "meeting_scheduled",
        "title": "Meeting Scheduled",
        "message": "A new meeting has been scheduled for your circle on January 20th at 3:00 PM.",
        "metadata": {"meetingId": "mtg_123", "groupId": "grp_123"},
        "read": False,
        "readAt": None,
        "createdAt": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
    },
    {
        "id": "notif_003",
        "userId": "usr_mock123",
        "type": "invitation",
        "title": "Circle Invitation Accepted",
        "message": "You have joined the Q1 Leadership pool.",
        "metadata": {"poolId": "pool_123"},
        "read": True,
        "readAt": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
        "createdAt": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
    },
]


# =============================================================================
# HEALTH CHECK
# =============================================================================

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "deburn-mock-api-v2",
        "version": "2.0.0",
        "database": True,
        "hub_database": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# =============================================================================
# AUTH ENDPOINTS (/api/auth)
# =============================================================================

@app.post("/api/auth/register")
async def register(request: RegisterRequest):
    return success_response({
        "message": "Registration successful. Please verify your email."
    })


@app.post("/api/auth/login")
async def login(request: LoginRequest):
    token = generate_token()
    user = MOCK_ADMIN_USER if "admin" in request.email else MOCK_USER
    user_copy = {**user, "email": request.email}
    mock_tokens[token] = user_copy

    return success_response({
        "user": {
            "id": user_copy["id"],
            "email": user_copy["email"],
            "firstName": user_copy["firstName"],
            "lastName": user_copy["lastName"],
            "isAdmin": user_copy["isAdmin"],
        },
        "token": token,
        "expiresAt": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
    })


@app.post("/api/auth/logout")
async def logout(authorization: Optional[str] = Header(None)):
    if authorization:
        token = authorization.replace("Bearer ", "")
        mock_tokens.pop(token, None)
    return success_response(None)


@app.get("/api/auth/session")
async def get_session(authorization: Optional[str] = Header(None)):
    if not authorization:
        return success_response({"user": None})

    token = authorization.replace("Bearer ", "")
    if token in mock_tokens:
        user = mock_tokens[token]
        return success_response({
            "user": {
                "id": user["id"],
                "email": user["email"],
                "firstName": user["firstName"],
                "lastName": user["lastName"],
                "isAdmin": user["isAdmin"],
            }
        })
    return success_response({"user": MOCK_USER})


@app.post("/api/auth/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    return success_response({
        "message": "If an account with that email exists, a password reset link has been sent."
    })


@app.post("/api/auth/reset-password")
async def reset_password(request: ResetPasswordRequest):
    if request.token == "invalid":
        raise HTTPException(status_code=400, detail={"message": "Reset token is invalid", "code": "TOKEN_INVALID"})
    return success_response(None)


@app.post("/api/auth/verify-email")
async def verify_email(request: VerifyEmailRequest):
    if request.token == "expired":
        raise HTTPException(status_code=400, detail={"message": "Token has expired", "code": "TOKEN_EXPIRED"})
    return success_response(None)


@app.post("/api/auth/resend-verification")
async def resend_verification(request: ResendVerificationRequest):
    return success_response({
        "message": "If an account with that email exists, a verification email has been sent."
    })


@app.get("/api/auth/admin-status")
async def get_admin_status(authorization: Optional[str] = Header(None)):
    user = require_auth(authorization)
    return success_response({
        "isAdmin": user.get("isAdmin", False),
        "organizations": [
            {"id": "org_1", "name": "Acme Corporation", "domain": "acme.com"}
        ] if user.get("isAdmin") else []
    })


# =============================================================================
# USER ENDPOINTS (/api/user)
# =============================================================================

@app.get("/api/user/profile")
async def get_user_profile(authorization: Optional[str] = Header(None)):
    user = require_auth(authorization)
    profile = user.get("profile", {})
    return success_response({
        "firstName": profile.get("firstName", user.get("firstName")),
        "lastName": profile.get("lastName", user.get("lastName")),
        "jobTitle": profile.get("jobTitle"),
        "leadershipLevel": profile.get("leadershipLevel"),
        "timezone": profile.get("timezone", "Europe/Stockholm"),
        "preferredLanguage": profile.get("preferredLanguage", "en"),
        "email": user.get("email"),
        "organization": profile.get("organization"),
        "country": profile.get("country"),
    })


@app.patch("/api/user/profile")
async def update_user_profile(request: ProfileUpdateRequest, authorization: Optional[str] = Header(None)):
    user = require_auth(authorization)
    profile = user.get("profile", {})
    return success_response({
        "firstName": request.firstName or profile.get("firstName"),
        "lastName": request.lastName or profile.get("lastName"),
        "jobTitle": request.jobTitle or profile.get("jobTitle"),
        "leadershipLevel": request.leadershipLevel or profile.get("leadershipLevel"),
        "timezone": request.timezone or profile.get("timezone", "Europe/Stockholm"),
        "preferredLanguage": request.preferredLanguage or profile.get("preferredLanguage", "en"),
        "email": user.get("email"),
        "organization": request.organization or profile.get("organization"),
        "country": profile.get("country"),
    })


@app.get("/api/user/consents")
async def get_user_consents(authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "consents": {
            "termsOfService": {"accepted": True, "acceptedAt": "2024-01-15T10:30:00Z", "version": "1.0"},
            "privacyPolicy": {"accepted": True, "acceptedAt": "2024-01-15T10:30:00Z", "version": "1.0"},
            "dataProcessing": {"accepted": True, "acceptedAt": "2024-01-15T10:30:00Z", "version": "1.0"},
            "marketing": {"accepted": False},
        },
        "needsUpdate": False,
        "outdatedConsents": [],
    })


@app.put("/api/user/consents/{consent_type}")
async def update_user_consent(consent_type: str, request: ConsentUpdateRequest, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "consentType": consent_type,
        "accepted": request.accepted,
        "acceptedAt": datetime.now(timezone.utc).isoformat() if request.accepted else None,
    })


@app.post("/api/user/delete")
async def request_account_deletion(request: DeleteAccountRequest = None, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "message": "Account deletion scheduled",
        "scheduledFor": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
    })


@app.post("/api/user/cancel-deletion")
async def cancel_account_deletion(authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "message": "Account deletion cancelled"
    })


# =============================================================================
# I18N ENDPOINTS (/api/i18n)
# =============================================================================

@app.get("/api/i18n/languages")
async def get_languages():
    return success_response({"languages": MOCK_LANGUAGES})


@app.post("/api/i18n/reload")
async def reload_translations():
    return success_response({
        "languages": ["en", "sv"],
        "namespaces": ["common", "auth", "coach", "checkin", "feedback"],
    })


# =============================================================================
# CHECKIN ENDPOINTS (/api/checkin)
# =============================================================================

@app.post("/api/checkin")
async def submit_checkin(request: CheckInRequest, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    import random

    return success_response({
        "streak": random.randint(1, 30),
        "insight": random.choice(MOCK_CHECKIN_INSIGHTS["en"]),
        "insightSv": random.choice(MOCK_CHECKIN_INSIGHTS["sv"]),
        "tip": random.choice(MOCK_CHECKIN_TIPS["en"]),
        "tipSv": random.choice(MOCK_CHECKIN_TIPS["sv"]),
    })


@app.get("/api/checkin/trends")
async def checkin_trends(period: int = 7, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    import random

    data_points = min(period, 90)
    return success_response({
        "dataPoints": data_points,
        "moodValues": [random.randint(2, 5) for _ in range(data_points)],
        "moodChange": random.randint(-20, 20),
        "energyValues": [random.randint(4, 8) for _ in range(data_points)],
        "energyChange": random.randint(-15, 15),
        "stressValues": [random.randint(2, 7) for _ in range(data_points)],
        "stressChange": random.randint(-25, 10),
    })


# =============================================================================
# CIRCLES ENDPOINTS (/api/circles)
# =============================================================================

@app.get("/api/circles/my-groups")
async def get_my_groups(authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    upcoming_meetings = []
    for g in MOCK_CIRCLE_GROUPS:
        if g.get("nextMeeting"):
            upcoming_meetings.append({
                "id": g["nextMeeting"]["id"],
                "title": g["nextMeeting"]["title"],
                "groupName": g["name"],
                "date": g["nextMeeting"]["scheduledAt"],
            })
    return success_response({
        "groups": MOCK_CIRCLE_GROUPS,
        "upcomingMeetings": upcoming_meetings,
    })


@app.get("/api/circles/my-invitations")
async def get_my_invitations(authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "pending": MOCK_PENDING_INVITATIONS,
        "accepted": [],
    })


@app.get("/api/circles/availability")
async def get_availability(authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({"slots": MOCK_USER_AVAILABILITY})


@app.put("/api/circles/availability")
async def update_availability(request: UpdateAvailabilityRequest, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({"slots": request.slots})


@app.get("/api/circles/groups/{group_id}")
async def get_group(group_id: str, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    group = next((g for g in MOCK_CIRCLE_GROUPS if g["id"] == group_id), None)
    if not group:
        raise HTTPException(status_code=404, detail={"message": "Group not found"})
    return success_response(group)


@app.get("/api/circles/groups/{group_id}/meetings")
async def get_group_meetings(group_id: str, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "meetings": [
            {"id": "mtg_123", "title": "Bi-weekly Check-in", "scheduledAt": "2026-01-20T15:00:00Z", "status": "scheduled"},
            {"id": "mtg_120", "title": "Bi-weekly Check-in", "scheduledAt": "2026-01-06T15:00:00Z", "status": "completed"},
        ]
    })


@app.get("/api/circles/groups/{group_id}/common-availability")
async def get_group_common_availability(group_id: str, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    # Return slots with availability counts and member names
    # day: 0=Sunday, 1=Monday, ..., 6=Saturday
    # hour: 0-23
    all_members = ["Alice Chen", "Bob Smith", "Carol Davis", "David Lee", "Emma Wilson"]
    return success_response({
        "totalMembers": 5,
        "members": all_members,
        "slots": [
            {"day": 2, "hour": 10, "availableCount": 5, "availableMembers": all_members},
            {"day": 2, "hour": 14, "availableCount": 4, "availableMembers": ["Alice Chen", "Bob Smith", "Carol Davis", "David Lee"]},
            {"day": 4, "hour": 10, "availableCount": 5, "availableMembers": all_members},
            {"day": 4, "hour": 14, "availableCount": 3, "availableMembers": ["Alice Chen", "Carol Davis", "Emma Wilson"]},
            {"day": 4, "hour": 15, "availableCount": 2, "availableMembers": ["Bob Smith", "Emma Wilson"]},
            {"day": 5, "hour": 9, "availableCount": 4, "availableMembers": ["Alice Chen", "Bob Smith", "David Lee", "Emma Wilson"]},
        ]
    })


@app.post("/api/circles/groups/{group_id}/meetings")
async def schedule_meeting(group_id: str, request: ScheduleMeetingRequest, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    meeting_id = f"mtg_{secrets.token_hex(4)}"
    return success_response({
        "id": meeting_id,
        "title": request.title,
        "groupName": "Engineering Leaders",
        "date": request.scheduledAt,
        "meetingLink": f"https://meet.google.com/{secrets.token_hex(3)}-{secrets.token_hex(4)}-{secrets.token_hex(3)}",
    })


@app.get("/api/circles/invitations/{token}")
async def get_invitation(token: str, authorization: Optional[str] = Header(None)):
    invitation = next((i for i in MOCK_PENDING_INVITATIONS if i["token"] == token), None)
    if not invitation:
        raise HTTPException(status_code=404, detail={"message": "Invitation not found or expired"})
    return success_response({
        "invitation": invitation,
        "pool": {"name": invitation["poolName"]},
    })


@app.post("/api/circles/invitations/{token}/accept")
async def accept_invitation(token: str, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({"message": "Invitation accepted"})


@app.post("/api/circles/invitations/{token}/decline")
async def decline_invitation(token: str, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({"message": "Invitation declined"})


@app.delete("/api/circles/invitations/{invitation_id}")
async def cancel_invitation(invitation_id: str, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({"message": "Invitation cancelled"})


@app.post("/api/circles/meetings/{meeting_id}/cancel")
async def cancel_meeting(meeting_id: str, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({"message": "Meeting cancelled"})


@app.post("/api/circles/meetings/{meeting_id}/attendance")
async def update_attendance(meeting_id: str, request: UpdateAttendanceRequest, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({"message": "Attendance updated"})


@app.post("/api/circles/pools")
async def create_pool(request: CreatePoolRequest, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    pool_id = f"pool_{secrets.token_hex(4)}"
    return success_response({
        "id": pool_id,
        "name": request.name,
        "status": "draft",
        "organizationId": request.organizationId,
        "stats": {"invited": 0, "accepted": 0, "declined": 0},
        "targetGroupSize": request.targetGroupSize,
        "cadence": request.cadence,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    })


@app.get("/api/circles/pools")
async def get_pools(status: Optional[str] = None, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "pools": [
            {
                "id": "pool_123",
                "name": "Q1 Leadership Circle",
                "status": status or "draft",
                "organizationId": "org_1",
                "stats": {"invited": 20, "accepted": 15, "declined": 2},
                "targetGroupSize": 5,
                "cadence": "bi-weekly",
                "createdAt": "2026-01-01T00:00:00Z",
            }
        ]
    })


@app.get("/api/circles/pools/{pool_id}")
async def get_pool(pool_id: str, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "id": pool_id,
        "name": "Q1 Leadership Circle",
        "status": "active",
        "topic": "Managing remote teams",
        "description": "A circle for leaders managing remote teams",
        "organizationId": "org_1",
        "targetGroupSize": 5,
        "cadence": "bi-weekly",
        "stats": {"invited": 20, "accepted": 15, "declined": 2},
        "invitationSettings": {"expirationDays": 14},
        "createdAt": "2026-01-01T00:00:00Z",
        "assignedAt": None,
    })


@app.post("/api/circles/pools/{pool_id}/invitations")
async def send_pool_invitations(pool_id: str, request: SendInvitationsRequest, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "sent": len(request.emails),
        "failed": 0,
        "duplicate": 0,
    })


@app.get("/api/circles/pools/{pool_id}/invitations")
async def get_pool_invitations(pool_id: str, status: Optional[str] = None, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "invitations": [
            {
                "id": "inv_1",
                "email": "user1@acme.com",
                "firstName": "User",
                "lastName": "One",
                "status": status or "pending",
                "createdAt": "2026-01-10T00:00:00Z",
                "expiresAt": "2026-01-24T00:00:00Z",
            }
        ]
    })


@app.post("/api/circles/pools/{pool_id}/assign")
async def assign_pool_groups(pool_id: str, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "groups": [
            {"id": "grp_new_1", "name": "Group A", "memberCount": 5},
            {"id": "grp_new_2", "name": "Group B", "memberCount": 5},
            {"id": "grp_new_3", "name": "Group C", "memberCount": 5},
        ],
        "totalMembers": 15,
    })


@app.get("/api/circles/pools/{pool_id}/groups")
async def get_pool_groups(pool_id: str, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "groups": [
            {
                "id": "grp_new_1",
                "name": "Group A",
                "memberCount": 5,
                "members": [
                    {"id": "usr_1", "name": "Anna Svensson", "avatar": None},
                    {"id": "usr_2", "name": "Erik Lindqvist", "avatar": None},
                ],
                "leaderId": "usr_1",
            }
        ]
    })


@app.post("/api/circles/pools/{pool_id}/groups/{group_id}/delete")
async def delete_group(pool_id: str, group_id: str, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "message": "Group deleted successfully",
        "deletedGroup": {
            "id": group_id,
            "name": "Group A",
            "memberCount": 5
        }
    })


@app.post("/api/circles/pools/{pool_id}/groups")
async def create_group(pool_id: str, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "id": "grp_new123",
        "name": "Circle D",
        "memberCount": 0
    })


@app.post("/api/circles/pools/{pool_id}/groups/{group_id}/add-member")
async def add_member_to_group(pool_id: str, group_id: str, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "message": "Member added successfully",
        "group": {
            "id": group_id,
            "name": "Circle A",
            "memberCount": 5
        },
        "addedMember": {
            "id": "usr_late123",
            "name": "Late Joiner"
        }
    })


@app.post("/api/circles/pools/{pool_id}/groups/{group_id}/remove-member")
async def remove_member_from_group(pool_id: str, group_id: str, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "message": "Member removed successfully",
        "group": {
            "id": group_id,
            "name": "Circle A",
            "memberCount": 4
        },
        "removedMember": {
            "id": "usr_removed123",
            "name": "Removed User"
        }
    })


# =============================================================================
# CALENDAR ENDPOINTS (/api/calendar)
# =============================================================================

@app.get("/api/calendar/auth/google")
async def get_google_auth_url(return_url: str = "/", authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "authUrl": f"https://accounts.google.com/o/oauth2/v2/auth?mock=true&return_url={return_url}"
    })


@app.get("/api/calendar/auth/google/callback")
async def google_oauth_callback(code: str, state: str):
    # In real implementation, this redirects to frontend
    return {"message": "OAuth callback received", "code": code}


@app.get("/api/calendar/connection")
async def get_calendar_connection(authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "id": "cal_conn_123",
        "provider": "google",
        "providerEmail": "user@gmail.com",
        "status": "active",
        "calendarIds": ["primary"],
        "primaryCalendarId": "primary",
        "connectedAt": "2025-12-01T00:00:00Z",
        "lastSyncAt": "2026-01-19T10:00:00Z",
    })


@app.delete("/api/calendar/connection")
async def disconnect_calendar(authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({"disconnected": True})


@app.get("/api/calendar/availability")
async def get_user_calendar_availability(
    timezone: str = "Europe/Stockholm",
    min_duration: int = 60,
    authorization: Optional[str] = Header(None)
):
    require_auth(authorization)
    return success_response({
        "slots": [
            {"start": "2026-01-20T09:00:00Z", "end": "2026-01-20T12:00:00Z", "duration": 180},
            {"start": "2026-01-20T14:00:00Z", "end": "2026-01-20T17:00:00Z", "duration": 180},
            {"start": "2026-01-21T10:00:00Z", "end": "2026-01-21T11:00:00Z", "duration": 60},
        ],
        "source": "calendar",
        "timezone": timezone,
    })


@app.get("/api/calendar/groups/{group_id}/availability")
async def get_group_calendar_availability(group_id: str, timezone: str = "Europe/Stockholm", authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "slots": [
            {"start": "2026-01-21T10:00:00Z", "end": "2026-01-21T11:00:00Z", "availableCount": 5},
            {"start": "2026-01-22T14:00:00Z", "end": "2026-01-22T15:00:00Z", "availableCount": 4},
        ],
        "timezone": timezone,
    })


@app.get("/api/calendar/working-hours")
async def get_working_hours(authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "workingHours": {
            "monday": {"start": "09:00", "end": "17:00"},
            "tuesday": {"start": "09:00", "end": "17:00"},
            "wednesday": {"start": "09:00", "end": "17:00"},
            "thursday": {"start": "09:00", "end": "17:00"},
            "friday": {"start": "09:00", "end": "16:00"},
        },
        "timezone": "Europe/Stockholm",
    })


@app.post("/api/calendar/webhook")
async def handle_calendar_webhook():
    return {"status": 200}


# =============================================================================
# COACH ENDPOINTS (/api/coach) - WITH STREAMING
# =============================================================================

@app.post("/api/coach/chat")
async def coach_chat(request: SendMessageRequest, authorization: Optional[str] = Header(None)):
    """Streaming coach chat endpoint."""
    require_auth(authorization)

    lang = request.language if request.language in ["en", "sv"] else "en"
    conversation_id = request.conversationId or f"conv_{secrets.token_hex(8)}"

    async def generate_stream():
        # Send metadata first
        metadata = {"type": "metadata", "content": {"conversationId": conversation_id}}
        yield f"data: {json.dumps(metadata)}\n\n"
        await asyncio.sleep(0.05)

        # Stream text chunks
        if lang == "sv":
            response_text = (
                "Det \u00e4r en utm\u00e4rkt fr\u00e5ga om ledarskap. "
                "Att utveckla ditt team kr\u00e4ver b\u00e5de t\u00e5lamod och strategi. "
                "L\u00e5t mig dela n\u00e5gra tankar som kan hj\u00e4lpa dig. "
                "F\u00f6rst, \u00f6verv\u00e4g att ha regelbundna en-till-en-samtal med varje teammedlem. "
                "Detta bygger f\u00f6rtroende och ger dig insikt i deras utmaningar."
            )
        else:
            response_text = (
                "That's an excellent question about leadership. "
                "Developing your team requires both patience and strategy. "
                "Let me share some thoughts that might help you. "
                "First, consider having regular one-on-one conversations with each team member. "
                "This builds trust and gives you insight into their challenges."
            )

        words = response_text.split()
        chunk_size = 3

        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i + chunk_size])
            if i > 0:
                chunk = " " + chunk
            text_chunk = {"type": "text", "content": chunk}
            yield f"data: {json.dumps(text_chunk)}\n\n"
            await asyncio.sleep(0.05)

        # Send actions
        actions = {
            "type": "actions",
            "content": [
                {
                    "type": "exercise",
                    "id": "breathing",
                    "label": "Prova en lugnande \u00f6vning" if lang == "sv" else "Try a Calming Exercise",
                },
                {
                    "type": "module",
                    "id": "delegation",
                    "label": "L\u00e4r dig: Delegera r\u00e4tt" if lang == "sv" else "Learn: Delegation Done Right",
                    "duration": "5 min",
                },
            ],
        }
        yield f"data: {json.dumps(actions)}\n\n"
        await asyncio.sleep(0.05)

        # Send quick replies
        quick_replies = {"type": "quickReplies", "content": MOCK_QUICK_REPLIES[lang]}
        yield f"data: {json.dumps(quick_replies)}\n\n"
        await asyncio.sleep(0.05)

        # Send final metadata with topics
        final_metadata = {
            "type": "metadata",
            "content": {
                "conversationId": conversation_id,
                "topics": ["leadership", "team_dynamics"],
            },
        }
        yield f"data: {json.dumps(final_metadata)}\n\n"

        # Send done signal
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/coach/starters")
async def get_coach_starters(
    language: str = "en",
    include_wellbeing: bool = False,
    mood: Optional[int] = None,
    energy: Optional[int] = None,
    stress: Optional[int] = None,
    authorization: Optional[str] = Header(None),
):
    require_auth(authorization)
    lang = language if language in ["en", "sv"] else "en"
    starters = MOCK_STARTERS[lang].copy()

    if include_wellbeing:
        if stress and stress >= 7:
            high_stress = (
                {"key": "high_stress", "text": "Min stress \u00e4r v\u00e4ldigt h\u00f6g just nu"}
                if lang == "sv"
                else {"key": "high_stress", "text": "My stress is really high right now"}
            )
            starters.insert(0, high_stress)

    return success_response({"starters": starters[:4]})


@app.get("/api/coach/conversations")
async def get_recent_conversations(limit: int = 10, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "conversations": [
            {
                "id": "conv_123",
                "conversationId": "conv_123",
                "preview": "We discussed leadership challenges...",
                "lastMessageAt": "2026-01-18T14:30:00Z",
                "messageCount": 12,
                "topics": ["leadership", "delegation"],
            },
            {
                "id": "conv_456",
                "conversationId": "conv_456",
                "preview": "Stress management techniques...",
                "lastMessageAt": "2026-01-17T10:00:00Z",
                "messageCount": 8,
                "topics": ["stress", "mindfulness"],
            },
        ]
    })


@app.get("/api/coach/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "id": conversation_id,
        "conversationId": conversation_id,
        "userId": "usr_mock123",
        "messages": [
            {"role": "user", "content": "How can I be a better leader?", "timestamp": "2026-01-18T14:00:00Z"},
            {"role": "assistant", "content": "That's a great question! Let's explore what leadership means to you...", "timestamp": "2026-01-18T14:00:30Z"},
        ],
        "topics": ["leadership"],
        "status": "active",
        "lastMessageAt": "2026-01-18T14:30:00Z",
        "createdAt": "2026-01-18T14:00:00Z",
    })


@app.get("/api/coach/commitments")
async def get_active_commitments(authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response(MOCK_COMMITMENTS)


@app.get("/api/coach/commitments/due")
async def get_due_followups(authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    due_commitments = [c for c in MOCK_COMMITMENTS if c["status"] == "active"]
    return success_response(due_commitments)


@app.get("/api/coach/commitments/stats")
async def get_commitment_stats(authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "active": 2,
        "completed": 5,
        "dismissed": 1,
        "completionRate": 0.71,
    })


@app.post("/api/coach/commitments/{commitment_id}/complete")
async def complete_commitment(commitment_id: str, request: CompleteCommitmentRequest, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "id": commitment_id,
        "status": "completed",
        "completedAt": datetime.now(timezone.utc).isoformat(),
        "reflectionNotes": request.reflectionNotes,
        "helpfulnessRating": request.helpfulnessRating,
    })


@app.post("/api/coach/commitments/{commitment_id}/dismiss")
async def dismiss_commitment(commitment_id: str, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "id": commitment_id,
        "status": "dismissed",
    })


@app.get("/api/coach/patterns")
async def get_patterns(days: int = 30, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "patterns": [
            {
                "type": "stress_spike",
                "description": "Your stress tends to spike on Thursdays",
                "frequency": 0.7,
                "recommendation": "Consider blocking prep time before afternoon meetings",
            },
            {
                "type": "energy_pattern",
                "description": "Your energy is highest in the morning",
                "frequency": 0.85,
                "recommendation": "Schedule demanding tasks before noon",
            },
        ],
        "analyzedDays": days,
    })


@app.post("/api/coach/voice")
async def text_to_speech(request: VoiceRequest, authorization: Optional[str] = Header(None)):
    """Mock TTS endpoint - returns empty audio."""
    require_auth(authorization)
    # Return a minimal valid MP3 file (silent)
    # This is a tiny valid MP3 frame (silent)
    silent_mp3 = bytes([
        0xFF, 0xFB, 0x90, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    ])
    return Response(
        content=silent_mp3,
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=speech.mp3"},
    )


class TranslateConversationRequest(BaseModel):
    conversationId: str
    targetLanguage: str
    startIndex: Optional[int] = None
    count: int = 20


@app.post("/api/coach/conversations/translate")
async def translate_conversation(request: TranslateConversationRequest, authorization: Optional[str] = Header(None)):
    """Mock translation endpoint - returns mock translated messages."""
    require_auth(authorization)

    # Mock translated messages based on target language
    mock_messages = [
        {"role": "user", "content": "I want to work on my leadership skills"},
        {"role": "assistant", "content": "That's a wonderful goal! Leadership is a journey of continuous growth."},
    ]

    translated_messages = []
    for i, msg in enumerate(mock_messages):
        if request.targetLanguage == "sv":
            # Mock Swedish translations
            if msg["role"] == "user":
                content = "Jag vill jobba på mitt ledarskap"
            else:
                content = "Det är ett fantastiskt mål! Ledarskap är en resa av ständig utveckling."
        else:
            content = msg["content"]

        translated_messages.append({
            "index": i,
            "content": content,
            "alreadyInTargetLanguage": False,
            "fromCache": i == 0,  # First one from cache, second newly translated
            "newlyTranslated": i == 1,
        })

    return {
        "translatedMessages": translated_messages,
        "totalMessages": len(mock_messages),
        "startIndex": 0,
        "endIndex": len(mock_messages),
        "newlyTranslated": 1,
        "fromCache": 1,
    }


# =============================================================================
# LEARNING/CONTENT ENDPOINTS (/api/learning)
# =============================================================================

@app.get("/api/learning/content")
async def get_learning_content(
    contentType: Optional[str] = None,
    category: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    require_auth(authorization)
    items = MOCK_CONTENT_ITEMS.copy()
    if contentType:
        items = [i for i in items if i["contentType"] == contentType]
    if category:
        items = [i for i in items if i["category"] == category]
    return success_response({"items": items})


@app.get("/api/learning/content/{content_id}")
async def get_learning_content_item(content_id: str, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    item = next((i for i in MOCK_CONTENT_ITEMS if i["id"] == content_id), None)
    if not item:
        raise HTTPException(status_code=404, detail={"message": "Content not found"})
    return success_response({"item": item})


@app.get("/api/learning/content/{content_id}/audio/{language}")
async def stream_learning_audio(content_id: str, language: str, authorization: Optional[str] = Header(None)):
    """Mock audio streaming - returns silent audio."""
    require_auth(authorization)
    # Return minimal silent MP3
    silent_mp3 = bytes([
        0xFF, 0xFB, 0x90, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    ])
    return Response(
        content=silent_mp3,
        media_type="audio/mpeg",
    )


@app.post("/api/learning/content/{content_id}/complete")
async def mark_content_complete(content_id: str, request: ProgressUpdateRequest = None, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "id": f"prog_{secrets.token_hex(4)}",
        "userId": "usr_mock123",
        "contentId": content_id,
        "progress": 100,
        "completedAt": datetime.now(timezone.utc).isoformat(),
    })


@app.get("/api/learning/progress")
async def get_learning_progress(authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response([
        {"id": "prog_1", "userId": "usr_mock123", "contentId": "cnt_1", "progress": 100, "completedAt": "2026-01-15T10:00:00Z"},
        {"id": "prog_2", "userId": "usr_mock123", "contentId": "cnt_2", "progress": 50, "completedAt": None},
    ])


@app.get("/api/learning/progress/stats")
async def get_learning_progress_stats(authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "totalContent": 10,
        "completed": 3,
        "inProgress": 2,
        "completionRate": 0.3,
    })


@app.get("/api/learning/progress/in-progress")
async def get_in_progress_content(authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response([
        {"id": "prog_2", "userId": "usr_mock123", "contentId": "cnt_2", "contentType": "audio_exercise", "progress": 50},
    ])


@app.post("/api/learning/recommendations")
async def get_coach_recommendations(request: CoachRecommendationsRequest, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    # Return content matching requested topics
    recommendations = [i for i in MOCK_CONTENT_ITEMS if any(t in i.get("coachTopics", []) for t in request.topics)]
    return success_response(recommendations[:3])


# =============================================================================
# PROGRESS ENDPOINTS (/api/progress)
# =============================================================================

@app.get("/api/progress/stats")
async def get_progress_stats(authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "streak": 12,
        "checkins": 45,
        "lessons": 8,
        "sessions": 23,
    })


@app.get("/api/progress/insights")
async def get_progress_insights(authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "insights": [
            {
                "title": "Thursday Stress Pattern",
                "titleSv": "Torsdagens stressm\u00f6nster",
                "description": "Your stress tends to spike on Thursdays. Consider blocking 30 minutes before your afternoon meetings for preparation.",
                "descriptionSv": "Din stress tenderar att toppa p\u00e5 torsdagar. \u00d6verv\u00e4g att blockera 30 minuter f\u00f6re dina eftermiddagsm\u00f6ten f\u00f6r f\u00f6rberedelse.",
            },
            {
                "title": "Morning Energy Peak",
                "titleSv": "Morgonens energitopp",
                "description": "You report highest energy levels between 9-11am. Schedule your most demanding tasks during this window.",
                "descriptionSv": "Du rapporterar h\u00f6gst energiniv\u00e5er mellan 9-11. Schemal\u00e4gg dina mest kr\u00e4vande uppgifter under detta f\u00f6nster.",
            },
        ]
    })


# =============================================================================
# MEDIA/IMAGE ENDPOINTS (/api/image)
# =============================================================================

@app.post("/api/image/generate")
async def generate_image(request: GenerateImageRequest, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "success": True,
        "imageUrl": "https://placehold.co/1024x1024/png?text=Generated+Image",
        "width": request.width,
        "height": request.height,
        "seed": request.seed or 12345,
        "prompt": request.prompt,
        "requestId": f"req_{secrets.token_hex(8)}",
        "model": "flux-schnell",
        "fromCache": False,
    })


@app.post("/api/image/generate-fast")
async def generate_image_fast(request: GenerateImageFastRequest, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    sizes = {"square": (1024, 1024), "portrait": (768, 1024), "landscape": (1024, 768)}
    w, h = sizes.get(request.size, (1024, 1024))
    return success_response({
        "success": True,
        "imageUrl": f"https://placehold.co/{w}x{h}/png?text=Fast+Image",
        "width": w,
        "height": h,
        "prompt": request.prompt,
        "requestId": f"req_{secrets.token_hex(8)}",
        "model": "flux-schnell",
        "fromCache": False,
    })


@app.post("/api/image/generate/transform")
async def transform_image(request: GenerateImageToImageRequest, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "success": True,
        "imageUrl": "https://placehold.co/1024x1024/png?text=Transformed+Image",
        "width": 1024,
        "height": 1024,
        "prompt": request.prompt,
        "requestId": f"req_{secrets.token_hex(8)}",
        "model": "flux-schnell",
        "fromCache": False,
    })


@app.get("/api/image/sizes")
async def get_image_sizes():
    return success_response({
        "sizes": {
            "square": {"width": 1024, "height": 1024},
            "portrait": {"width": 768, "height": 1024},
            "landscape": {"width": 1024, "height": 768},
            "wide": {"width": 1280, "height": 720},
        }
    })


# =============================================================================
# ORGANIZATION ENDPOINTS (/api/organizations)
# =============================================================================

@app.post("/api/organizations")
async def create_organization(request: CreateOrganizationRequest, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    org_id = f"org_{secrets.token_hex(4)}"
    return success_response({
        "id": org_id,
        "name": request.name,
        "domain": request.domain,
        "settings": {},
        "status": "active",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "memberCount": 1,
        "adminCount": 1,
    })


@app.get("/api/organizations/mine")
async def get_my_organizations(authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "organizations": [
            {"id": "org_1", "name": "Acme Corporation", "role": "admin", "memberCount": 45},
        ]
    })


@app.get("/api/organizations/{organization_id}")
async def get_organization(organization_id: str, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    org = next((o for o in MOCK_ORGANIZATIONS if o["id"] == organization_id), None)
    if not org:
        raise HTTPException(status_code=404, detail={"message": "Organization not found"})
    return success_response(org)


@app.put("/api/organizations/{organization_id}")
async def update_organization(organization_id: str, request: UpdateOrganizationRequest, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "id": organization_id,
        "name": request.name or "Acme Corporation",
        "domain": request.domain,
        "settings": request.settings or {},
        "status": "active",
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    })


@app.get("/api/organizations/{organization_id}/members")
async def get_organization_members(organization_id: str, role: Optional[str] = None, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "members": [
            {"id": "mem_1", "userId": "usr_1", "role": "owner", "status": "active", "user": {"email": "owner@acme.com", "firstName": "John", "lastName": "Owner"}},
            {"id": "mem_2", "userId": "usr_2", "role": "admin", "status": "active", "user": {"email": "admin@acme.com", "firstName": "Admin", "lastName": "User"}},
            {"id": "mem_3", "userId": "usr_3", "role": "member", "status": "active", "user": {"email": "user@acme.com", "firstName": "Regular", "lastName": "User"}},
        ]
    })


@app.post("/api/organizations/{organization_id}/members")
async def add_organization_member(organization_id: str, request: AddMemberRequest, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "id": f"mem_{secrets.token_hex(4)}",
        "organizationId": organization_id,
        "userId": None,
        "role": request.role,
        "status": "invited",
        "createdAt": datetime.now(timezone.utc).isoformat(),
    })


@app.delete("/api/organizations/{organization_id}/members/{user_id}")
async def remove_organization_member(organization_id: str, user_id: str, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({"success": True})


@app.post("/api/organizations/{organization_id}/leave")
async def leave_organization(organization_id: str, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({"success": True})


@app.put("/api/organizations/{organization_id}/members/{user_id}/role")
async def change_member_role(organization_id: str, user_id: str, request: ChangeMemberRoleRequest, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "id": f"mem_{user_id}",
        "organizationId": organization_id,
        "userId": user_id,
        "role": request.role,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    })


@app.post("/api/organizations/{organization_id}/transfer-ownership")
async def transfer_ownership(organization_id: str, request: TransferOwnershipRequest, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "id": organization_id,
        "name": "Acme Corporation",
        "createdBy": request.newOwnerId,
    })


# =============================================================================
# HUB ENDPOINTS (/api/hub) - Hub Admin Only
# =============================================================================

@app.get("/api/hub/admins")
async def get_hub_admins(authorization: Optional[str] = Header(None)):
    require_hub_admin(authorization)
    return success_response({"admins": MOCK_HUB_ADMINS})


@app.post("/api/hub/admins")
async def add_hub_admin(request: AddHubAdminRequest, authorization: Optional[str] = Header(None)):
    require_hub_admin(authorization)
    return success_response(None)


@app.delete("/api/hub/admins/{email}")
async def remove_hub_admin(email: str, authorization: Optional[str] = Header(None)):
    require_hub_admin(authorization)
    return success_response(None)


@app.get("/api/hub/organization")
async def get_hub_organization(authorization: Optional[str] = Header(None)):
    require_hub_admin(authorization)
    return success_response({
        "id": "org_hub",
        "name": "Deburn Hub",
        "memberCount": 150,
        "activeUsers": 87,
        "completedLessons": 450,
        "avgEngagement": 0.72,
    })


@app.get("/api/hub/members")
async def get_hub_members(authorization: Optional[str] = Header(None)):
    require_hub_admin(authorization)
    return success_response({
        "members": [
            {"id": "usr_1", "name": "John Doe", "email": "john@acme.com", "role": "user"},
            {"id": "usr_2", "name": "Jane Smith", "email": "jane@acme.com", "role": "user"},
        ]
    })


@app.get("/api/hub/organizations")
async def get_hub_organizations(authorization: Optional[str] = Header(None)):
    require_hub_admin(authorization)
    return success_response({"organizations": MOCK_ORGANIZATIONS})


@app.post("/api/hub/organizations")
async def create_hub_organization(request: CreateOrganizationRequest, authorization: Optional[str] = Header(None)):
    require_hub_admin(authorization)
    return success_response({
        "organization": {
            "id": f"org_{secrets.token_hex(4)}",
            "name": request.name,
            "domain": request.domain,
            "memberCount": 0,
        }
    })


@app.get("/api/hub/org-admins")
async def get_hub_org_admins(authorization: Optional[str] = Header(None)):
    require_hub_admin(authorization)
    return success_response({
        "admins": [
            {"email": "john@acme.com", "name": "John Doe", "organizations": [{"id": "org_1", "name": "Acme Corporation", "membershipId": "mem_1"}]},
        ]
    })


@app.post("/api/hub/org-admins")
async def add_hub_org_admin(request: AddOrgAdminRequest, authorization: Optional[str] = Header(None)):
    require_hub_admin(authorization)
    return success_response(None)


@app.delete("/api/hub/org-admins/{membership_id}")
async def remove_hub_org_admin(membership_id: str, authorization: Optional[str] = Header(None)):
    require_hub_admin(authorization)
    return success_response(None)


@app.get("/api/hub/settings/coach")
async def get_hub_coach_settings(authorization: Optional[str] = Header(None)):
    require_hub_admin(authorization)
    return success_response({"dailyExchangeLimit": 15})


@app.put("/api/hub/settings/coach")
async def update_hub_coach_settings(request: UpdateCoachSettingsRequest, authorization: Optional[str] = Header(None)):
    require_hub_admin(authorization)
    return success_response({"dailyExchangeLimit": request.dailyExchangeLimit})


@app.get("/api/hub/coach/prompts")
async def get_hub_coach_prompts(authorization: Optional[str] = Header(None)):
    require_hub_admin(authorization)
    return success_response({"prompts": MOCK_COACH_PROMPTS})


@app.put("/api/hub/coach/prompts/{language}/{prompt_name}")
async def update_hub_coach_prompt(language: str, prompt_name: str, request: UpdatePromptRequest, authorization: Optional[str] = Header(None)):
    require_hub_admin(authorization)
    return success_response(None)


@app.get("/api/hub/coach/exercises")
async def get_hub_coach_exercises(authorization: Optional[str] = Header(None)):
    require_hub_admin(authorization)
    return success_response({"exercises": MOCK_COACH_EXERCISES})


@app.put("/api/hub/coach/exercises")
async def update_hub_coach_exercises(request: UpdateExercisesRequest, authorization: Optional[str] = Header(None)):
    require_hub_admin(authorization)
    return success_response(None)


@app.get("/api/hub/coach/config")
async def get_hub_coach_config(authorization: Optional[str] = Header(None)):
    require_hub_admin(authorization)
    return success_response({
        "model": "claude-sonnet-4-5-20250929",
        "maxTokens": 1024,
        "temperature": 0.7,
        "methodology": {
            "primary": "EMCC",
            "ethical": "ICF",
            "frameworks": ["SDT", "JD-R", "CBC", "ACT", "Positive Psychology"],
        },
        "topics": ["delegation", "stress", "team_dynamics", "communication", "leadership"],
    })


@app.get("/api/hub/content")
async def get_hub_content(
    contentType: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    require_hub_admin(authorization)
    items = MOCK_CONTENT_ITEMS.copy()
    if contentType:
        items = [i for i in items if i["contentType"] == contentType]
    if status:
        items = [i for i in items if i["status"] == status]
    if category:
        items = [i for i in items if i["category"] == category]
    return success_response({"items": items})


@app.get("/api/hub/content/{content_id}")
async def get_hub_content_item(content_id: str, authorization: Optional[str] = Header(None)):
    require_hub_admin(authorization)
    item = next((i for i in MOCK_CONTENT_ITEMS if i["id"] == content_id), None)
    if not item:
        raise HTTPException(status_code=404, detail={"message": "Content not found"})
    return success_response(item)


@app.post("/api/hub/content")
async def create_hub_content(request: CreateContentRequest, authorization: Optional[str] = Header(None)):
    require_hub_admin(authorization)
    content_id = f"cnt_{secrets.token_hex(4)}"
    return success_response({
        "id": content_id,
        "title": request.titleEn,
        "status": request.status,
    })


@app.put("/api/hub/content/{content_id}")
async def update_hub_content(content_id: str, request: UpdateContentRequest, authorization: Optional[str] = Header(None)):
    require_hub_admin(authorization)
    return success_response({
        "id": content_id,
        "title": request.titleEn,
        "status": request.status,
    })


@app.delete("/api/hub/content/{content_id}")
async def delete_hub_content(content_id: str, authorization: Optional[str] = Header(None)):
    require_hub_admin(authorization)
    return success_response(None)


@app.post("/api/hub/content/{content_id}/audio/{lang}")
async def upload_hub_audio(content_id: str, lang: str, file: UploadFile = File(None), authorization: Optional[str] = Header(None)):
    require_hub_admin(authorization)
    return success_response({"audioUrl": f"/audio/{content_id}-{lang}.mp3"})


@app.delete("/api/hub/content/{content_id}/audio/{lang}")
async def remove_hub_audio(content_id: str, lang: str, authorization: Optional[str] = Header(None)):
    require_hub_admin(authorization)
    return success_response(None)


@app.get("/api/hub/compliance/stats")
async def get_hub_compliance_stats(authorization: Optional[str] = Header(None)):
    require_hub_admin(authorization)
    return success_response({
        "totalUsers": 150,
        "pendingDeletions": 2,
        "auditLogCount": 4523,
        "activeSessions": 87,
    })


@app.get("/api/hub/compliance/user/{email}")
async def get_hub_compliance_user(email: str, authorization: Optional[str] = Header(None)):
    require_hub_admin(authorization)
    return success_response({
        "id": "usr_mock123",
        "email": email,
        "organization": "Acme Corp",
        "status": "active",
        "createdAt": "2024-01-15T10:30:00Z",
        "lastLoginAt": "2026-01-10T14:22:00Z",
        "sessionCount": 45,
        "checkInCount": 120,
        "consents": {
            "termsOfService": {"accepted": True, "acceptedAt": "2024-01-15T10:30:00Z"},
            "privacyPolicy": {"accepted": True, "acceptedAt": "2024-01-15T10:30:00Z"},
        },
    })


@app.post("/api/hub/compliance/export/{user_id}")
async def export_hub_user_data(user_id: str, authorization: Optional[str] = Header(None)):
    require_hub_admin(authorization)
    return success_response({
        "user": {"id": user_id, "email": "user@example.com"},
        "checkins": [{"date": "2026-01-10", "mood": 4, "stress": 3}],
        "conversations": [{"id": "conv_1", "messageCount": 12}],
        "exportedAt": datetime.now(timezone.utc).isoformat(),
    })


@app.post("/api/hub/compliance/delete/{user_id}")
async def delete_hub_user_data(user_id: str, authorization: Optional[str] = Header(None)):
    require_hub_admin(authorization)
    return success_response({"message": "Account scheduled for deletion"})


@app.get("/api/hub/compliance/pending-deletions")
async def get_hub_pending_deletions(authorization: Optional[str] = Header(None)):
    require_hub_admin(authorization)
    return success_response({
        "pendingDeletions": [
            {
                "id": "usr_del1",
                "email": "leaving@acme.com",
                "requestedAt": "2026-01-01T00:00:00Z",
                "scheduledFor": "2026-01-31T00:00:00Z",
            }
        ]
    })


@app.post("/api/hub/compliance/cleanup-sessions")
async def cleanup_hub_sessions(authorization: Optional[str] = Header(None)):
    require_hub_admin(authorization)
    return success_response({"cleanedCount": 23})


@app.get("/api/hub/compliance/security-config")
async def get_hub_security_config(authorization: Optional[str] = Header(None)):
    require_hub_admin(authorization)
    return success_response({
        "sessionTimeout": 3600,
        "maxLoginAttempts": 5,
        "passwordMinLength": 12,
        "requireMFA": False,
        "allowedDomains": ["*"],
        "rateLimits": {
            "login": "10/minute",
            "api": "100/minute",
        },
    })


# =============================================================================
# DASHBOARD ENDPOINT (/api/dashboard)
# =============================================================================

@app.get("/api/dashboard")
async def get_dashboard(authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "todaysCheckin": {
            "mood": 4,
            "physicalEnergy": 7,
            "mentalEnergy": 6,
            "sleep": 4,
            "stress": 3,
        },
        "streak": 5,
        "insightsCount": 3,
        "todaysFocus": {
            "module": {
                "id": "cnt_featured_1",
                "contentType": "audio_article",
                "category": "featured",
                "titleEn": "Leading Through Uncertainty",
                "titleSv": "Leda genom osäkerhet",
                "lengthMinutes": 8,
            },
            "currentIndex": 5,
            "totalModules": 14,
            "progress": 0.357,
        },
        "nextCircle": {
            "date": "Jan 20, 3:00 PM",
            "dateSv": "20 jan, 15:00",
        },
    })


# =============================================================================
# ADMIN ENDPOINTS (/api/admin)
# =============================================================================

@app.get("/api/admin/stats")
async def get_admin_stats(authorization: Optional[str] = Header(None)):
    require_hub_admin(authorization)
    return success_response({
        "totalUsers": 150,
        "activeUsers": 87,
        "totalCheckins": 4523,
        "totalSessions": 892
    })


# =============================================================================
# PROFILE ENDPOINTS (/api/profile)
# =============================================================================

@app.put("/api/profile")
async def update_profile(request: ProfileUpdateRequest, authorization: Optional[str] = Header(None)):
    user = require_auth(authorization)
    return success_response({
        "user": {
            "id": user["id"],
            "firstName": request.firstName or user["firstName"],
            "lastName": request.lastName or user["lastName"],
            "email": user["email"],
            "organization": request.organization or user.get("profile", {}).get("organization"),
            "role": request.role or user.get("profile", {}).get("jobTitle"),
            "bio": request.bio or "Passionate about building great teams",
        }
    })


@app.post("/api/profile/avatar")
async def upload_avatar(file: UploadFile = File(None), authorization: Optional[str] = Header(None)):
    user = require_auth(authorization)
    return success_response({
        "avatarUrl": f"/uploads/avatars/{user['id']}.jpg"
    })


@app.put("/api/profile/avatar")
async def remove_avatar(request: RemoveAvatarRequest, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response(None)


# =============================================================================
# CONVERSATIONS ENDPOINTS (/api/conversations)
# =============================================================================

@app.get("/api/conversations")
async def get_conversation_history(authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "conversation": {
            "id": "conv_current",
            "messageCount": 5,
            "lastMessageAt": "2026-01-19T10:00:00Z",
            "createdAt": "2026-01-19T09:00:00Z",
        },
        "messages": [
            {"role": "user", "content": "Hello Eve!", "timestamp": "2026-01-19T09:00:00Z"},
            {"role": "assistant", "content": "Hello! How can I help you today?", "timestamp": "2026-01-19T09:00:30Z"},
        ],
    })


@app.post("/api/conversations")
async def save_conversation(authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({"synced": True})


@app.delete("/api/conversations")
async def delete_conversation_history(authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({"deleted": True, "deletedCount": 5})


# =============================================================================
# FEEDBACK ENDPOINTS (/api/feedback)
# =============================================================================

@app.post("/api/feedback")
async def submit_feedback(request: SubmitFeedbackRequest, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    # Always return success for feedback
    return success_response({
        "id": f"fb_{secrets.token_hex(8)}",
        "message": "Feedback submitted successfully"
    })


@app.post("/api/feedback/learning")
async def submit_learning_rating(request: SubmitLearningRatingRequest, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "message": "Rating submitted successfully"
    })


@app.get("/api/feedback/learning/{content_id}")
async def get_learning_ratings(content_id: str, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({
        "totalRatings": 42,
        "userRating": 4,
    })


# =============================================================================
# NOTIFICATION ENDPOINTS (/api/notifications)
# =============================================================================

@app.get("/api/notifications")
async def get_notifications(
    limit: int = 20,
    offset: int = 0,
    authorization: Optional[str] = Header(None)
):
    require_auth(authorization)
    notifications = MOCK_NOTIFICATIONS[offset:offset + limit]
    return success_response({
        "notifications": notifications,
        "total": len(MOCK_NOTIFICATIONS),
        "hasMore": offset + limit < len(MOCK_NOTIFICATIONS),
    })


@app.get("/api/notifications/count")
async def get_notification_count(authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    unread_count = sum(1 for n in MOCK_NOTIFICATIONS if not n["read"])
    return success_response({"unread": unread_count})


@app.post("/api/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    # Find and mark as read (in mock, just return success)
    notification = next((n for n in MOCK_NOTIFICATIONS if n["id"] == notification_id), None)
    if not notification:
        raise HTTPException(status_code=404, detail={"message": "Notification not found"})
    return success_response({"message": "Notification marked as read"})


@app.post("/api/notifications/read-all")
async def mark_all_notifications_read(authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return success_response({"message": "All notifications marked as read", "count": len(MOCK_NOTIFICATIONS)})


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5002)

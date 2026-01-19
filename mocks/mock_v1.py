"""
BrainBank Mock API Server

A FastAPI mock server that simulates all API endpoints for frontend development
and testing without requiring MongoDB, Firebase, or Claude API.

Run with: uvicorn mock_api:app --port 5002 --reload
"""

import asyncio
import json
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel


# =============================================================================
# APP SETUP
# =============================================================================

app = FastAPI(
    title="BrainBank Mock API",
    description="Mock API server for frontend development",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
)


# =============================================================================
# MOCK TOKEN STORE
# =============================================================================

mock_tokens: dict[str, dict] = {}

MOCK_USER = {
    "id": "usr_mock123",
    "email": "user@example.com",
    "firstName": "John",
    "lastName": "Doe",
    "isAdmin": False,
    "profile": {
        "organization": "Acme Corp",
        "jobTitle": "Engineering Manager",
        "preferredLanguage": "en",
    },
}

MOCK_ADMIN_USER = {
    "id": "usr_admin456",
    "email": "admin@example.com",
    "firstName": "Admin",
    "lastName": "User",
    "isAdmin": True,
    "profile": {
        "organization": "BrainBank",
        "jobTitle": "Administrator",
        "preferredLanguage": "en",
    },
}


def generate_token() -> str:
    return f"mock_token_{secrets.token_hex(16)}"


def get_user_from_token(authorization: Optional[str]) -> Optional[dict]:
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "")
    return mock_tokens.get(token)


def require_auth(authorization: Optional[str] = Header(None)) -> dict:
    user = get_user_from_token(authorization)
    if not user:
        # For mock server, always return mock user instead of 401
        return MOCK_USER
    return user


def require_admin(authorization: Optional[str] = Header(None)) -> dict:
    user = require_auth(authorization)
    if not user.get("isAdmin"):
        raise HTTPException(
            status_code=403,
            detail={"message": "Admin access required", "code": "FORBIDDEN"},
        )
    return user


# =============================================================================
# REQUEST MODELS
# =============================================================================


class LoginRequest(BaseModel):
    email: str
    password: str
    rememberMe: bool = False


class RegisterRequest(BaseModel):
    firstName: str
    lastName: str
    email: str
    password: str
    passwordConfirm: str
    organization: Optional[str] = None
    country: Optional[str] = None
    consents: Optional[dict] = None


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: str


class CheckinRequest(BaseModel):
    mood: int
    physicalEnergy: int
    mentalEnergy: int
    sleep: int
    stress: int


class CoachChatRequest(BaseModel):
    message: str
    conversationId: Optional[str] = None
    context: Optional[dict] = None
    language: str = "en"


class ProfileUpdateRequest(BaseModel):
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    organization: Optional[str] = None
    role: Optional[str] = None
    bio: Optional[str] = None


class AvatarRemoveRequest(BaseModel):
    remove: bool = True


# =============================================================================
# HEALTH CHECK
# =============================================================================


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "brainbank-mock-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# =============================================================================
# AUTH ENDPOINTS
# =============================================================================


@app.post("/api/auth/login")
async def login(request: LoginRequest):
    token = generate_token()
    user = MOCK_ADMIN_USER if "admin" in request.email else MOCK_USER
    user_copy = {**user, "email": request.email}
    mock_tokens[token] = user_copy

    return {
        "success": True,
        "data": {
            "user": {
                "id": user_copy["id"],
                "email": user_copy["email"],
                "firstName": user_copy["firstName"],
                "lastName": user_copy["lastName"],
                "isAdmin": user_copy["isAdmin"],
            },
            "token": token,
        },
    }


@app.post("/api/auth/register")
async def register(request: RegisterRequest):
    return {"success": True, "message": "Registration successful. Please verify your email."}


@app.post("/api/auth/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    return {"success": True}


@app.post("/api/auth/reset-password")
async def reset_password(request: ResetPasswordRequest):
    if request.token == "invalid":
        raise HTTPException(
            status_code=400,
            detail={"message": "Reset token is invalid", "code": "TOKEN_INVALID"},
        )
    return {"success": True}


@app.post("/api/auth/verify-email")
async def verify_email(request: VerifyEmailRequest):
    if request.token == "expired":
        raise HTTPException(
            status_code=400,
            detail={"message": "Token has expired", "code": "TOKEN_EXPIRED"},
        )
    return {"success": True}


@app.post("/api/auth/resend-verification")
async def resend_verification(request: ResendVerificationRequest):
    return {"success": True}


@app.post("/api/auth/logout")
async def logout(authorization: Optional[str] = Header(None)):
    if authorization:
        token = authorization.replace("Bearer ", "")
        mock_tokens.pop(token, None)
    return {"success": True}


@app.get("/api/auth/session")
async def get_session(authorization: Optional[str] = Header(None)):
    """Get current session/user info"""
    # For mock purposes, return null user if no auth (not logged in)
    if not authorization:
        return {"success": True, "data": {"user": None}}

    token = authorization.replace("Bearer ", "")
    if token in mock_tokens:
        return {
            "success": True,
            "data": {"user": MOCK_USER}
        }
    return {"success": True, "data": {"user": None}}


# =============================================================================
# ADMIN ENDPOINTS
# =============================================================================


@app.get("/api/admin/stats")
async def admin_stats(authorization: Optional[str] = Header(None)):
    require_admin(authorization)
    return {
        "success": True,
        "data": {
            "totalUsers": 150,
            "activeUsers": 87,
            "totalCheckins": 4523,
            "totalSessions": 892,
        },
    }


# =============================================================================
# CHECKIN ENDPOINTS
# =============================================================================


@app.post("/api/checkin")
async def submit_checkin(
    request: CheckinRequest, authorization: Optional[str] = Header(None)
):
    require_auth(authorization)

    insights_en = [
        "Your stress tends to spike on Thursdays. Consider blocking 30 minutes before your afternoon meetings.",
        "Your energy levels are highest in the morning. Schedule demanding tasks during this time.",
        "You've maintained consistent sleep patterns this week. Great job!",
    ]
    tips_en = [
        "Try the 2-minute breathing exercise before your 10am call",
        "Consider a short walk after lunch to boost afternoon energy",
        "Take a 5-minute break every 90 minutes for optimal focus",
    ]
    insights_sv = [
        "Din stress tenderar att toppa på torsdagar. Överväg att blockera 30 minuter före dina eftermiddagsmöten.",
        "Din energinivå är högst på morgonen. Schemalägg krävande uppgifter under denna tid.",
        "Du har haft ett konsekvent sömnmönster denna vecka. Bra jobbat!",
    ]
    tips_sv = [
        "Prova 2-minuters andningsövning före ditt 10-samtal",
        "Överväg en kort promenad efter lunch för att öka eftermiddagsenergin",
        "Ta en 5-minuters paus var 90:e minut för optimalt fokus",
    ]

    import random

    return {
        "success": True,
        "data": {
            "streak": random.randint(1, 30),
            "insight": random.choice(insights_en),
            "insightSv": random.choice(insights_sv),
            "tip": random.choice(tips_en),
            "tipSv": random.choice(tips_sv),
        },
    }


@app.get("/api/checkin/trends")
async def checkin_trends(
    period: int = 7, authorization: Optional[str] = Header(None)
):
    require_auth(authorization)

    import random

    data_points = min(period, 90)
    return {
        "success": True,
        "data": {
            "dataPoints": data_points,
            "moodValues": [random.randint(2, 5) for _ in range(data_points)],
            "moodChange": random.randint(-20, 20),
            "energyValues": [random.randint(4, 8) for _ in range(data_points)],
            "energyChange": random.randint(-15, 15),
            "stressValues": [random.randint(2, 7) for _ in range(data_points)],
            "stressChange": random.randint(-25, 10),
        },
    }


# =============================================================================
# CIRCLES ENDPOINTS - Leadership Circles
# =============================================================================

# Mock data stores for circles
MOCK_CIRCLE_GROUPS = [
    {
        "id": "grp_123",
        "name": "Engineering Leaders",
        "members": [
            {"id": "usr_1", "name": "Anna Svensson", "email": "anna@acme.com"},
            {"id": "usr_2", "name": "Erik Lindqvist", "email": "erik@acme.com"},
            {"id": "usr_3", "name": "Maria Karlsson", "email": "maria@acme.com"},
            {"id": "usr_4", "name": "Johan Berg", "email": "johan@acme.com"},
            {"id": "usr_5", "name": "Lisa Holm", "email": "lisa@acme.com"},
            {"id": "usr_6", "name": "Peter Nilsson", "email": "peter@acme.com"},
        ],
        "pool": {
            "cadence": "bi-weekly",
            "topic": "Managing remote team dynamics",
        },
        "nextMeeting": {
            "id": "mtg_123",
            "title": "Bi-weekly Check-in",
            "scheduledAt": "2026-01-20T15:00:00Z",
            "meetingLink": "https://meet.google.com/abc-defg-hij",
        },
    },
    {
        "id": "grp_456",
        "name": "Product Managers Circle",
        "members": [
            {"id": "usr_7", "name": "Sara Andersson", "email": "sara@techstart.se"},
            {"id": "usr_8", "name": "Mikael Johansson", "email": "mikael@techstart.se"},
            {"id": "usr_9", "name": "Emma Larsson", "email": "emma@techstart.se"},
            {"id": "usr_10", "name": "David Eriksson", "email": "david@techstart.se"},
        ],
        "pool": {
            "cadence": "weekly",
            "topic": "Stakeholder communication strategies",
        },
        "nextMeeting": None,
    },
    {
        "id": "grp_789",
        "name": "New Managers Support",
        "members": [
            {"id": "usr_11", "name": "Klara Björk", "email": "klara@growth.se"},
            {"id": "usr_12", "name": "Oscar Lund", "email": "oscar@growth.se"},
            {"id": "usr_13", "name": "Frida Ek", "email": "frida@growth.se"},
            {"id": "usr_14", "name": "Henrik Strand", "email": "henrik@growth.se"},
            {"id": "usr_15", "name": "Maja Lindgren", "email": "maja@growth.se"},
        ],
        "pool": {
            "cadence": "monthly",
            "topic": "Building trust with your team",
        },
        "nextMeeting": {
            "id": "mtg_456",
            "title": "Monthly Discussion",
            "scheduledAt": "2026-01-28T14:00:00Z",
            "meetingLink": None,
        },
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

MOCK_ACCEPTED_INVITATIONS = []

MOCK_USER_AVAILABILITY = [
    {"day": "monday", "hour": 10},
    {"day": "monday", "hour": 14},
    {"day": "monday", "hour": 15},
    {"day": "tuesday", "hour": 9},
    {"day": "tuesday", "hour": 10},
    {"day": "wednesday", "hour": 10},
    {"day": "wednesday", "hour": 14},
    {"day": "wednesday", "hour": 15},
    {"day": "thursday", "hour": 11},
    {"day": "thursday", "hour": 14},
    {"day": "friday", "hour": 9},
    {"day": "friday", "hour": 10},
]

# Mock meetings history for groups
MOCK_GROUP_MEETINGS = {
    "grp_123": [
        {
            "id": "mtg_123",
            "title": "Bi-weekly Check-in",
            "scheduledAt": "2026-01-20T15:00:00Z",
            "meetingLink": "https://meet.google.com/abc-defg-hij",
            "status": "scheduled",
        },
        {
            "id": "mtg_120",
            "title": "Bi-weekly Check-in",
            "scheduledAt": "2026-01-06T15:00:00Z",
            "meetingLink": None,
            "status": "completed",
        },
        {
            "id": "mtg_118",
            "title": "Holiday Planning",
            "scheduledAt": "2025-12-16T15:00:00Z",
            "meetingLink": None,
            "status": "completed",
        },
    ],
    "grp_456": [
        {
            "id": "mtg_200",
            "title": "Weekly Sync",
            "scheduledAt": "2026-01-06T10:00:00Z",
            "meetingLink": None,
            "status": "completed",
        },
        {
            "id": "mtg_199",
            "title": "Weekly Sync",
            "scheduledAt": "2025-12-30T10:00:00Z",
            "meetingLink": None,
            "status": "cancelled",
        },
    ],
    "grp_789": [
        {
            "id": "mtg_456",
            "title": "Monthly Discussion",
            "scheduledAt": "2026-01-28T14:00:00Z",
            "meetingLink": None,
            "status": "scheduled",
        },
        {
            "id": "mtg_400",
            "title": "Monthly Discussion",
            "scheduledAt": "2025-12-20T14:00:00Z",
            "meetingLink": None,
            "status": "completed",
        },
    ],
}

# Common availability slots (computed from all members)
MOCK_COMMON_AVAILABILITY = {
    "grp_123": [
        {"date": "2026-01-21", "hour": 10, "availableCount": 6},
        {"date": "2026-01-21", "hour": 14, "availableCount": 5},
        {"date": "2026-01-22", "hour": 15, "availableCount": 6},
        {"date": "2026-01-23", "hour": 10, "availableCount": 4},
        {"date": "2026-01-24", "hour": 9, "availableCount": 6},
    ],
    "grp_456": [
        {"date": "2026-01-20", "hour": 10, "availableCount": 4},
        {"date": "2026-01-21", "hour": 11, "availableCount": 3},
        {"date": "2026-01-22", "hour": 14, "availableCount": 4},
    ],
    "grp_789": [
        {"date": "2026-01-27", "hour": 14, "availableCount": 5},
        {"date": "2026-01-28", "hour": 10, "availableCount": 4},
        {"date": "2026-01-29", "hour": 15, "availableCount": 5},
    ],
}


class AvailabilityRequest(BaseModel):
    slots: list


class ScheduleMeetingRequest(BaseModel):
    title: str
    scheduledAt: str
    day: Optional[str] = None
    hour: Optional[int] = None


# User endpoints
@app.get("/api/circles/my-groups")
async def get_my_groups(authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return {"success": True, "data": {"groups": MOCK_CIRCLE_GROUPS}}


@app.get("/api/circles/my-invitations")
async def get_my_invitations(authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return {
        "success": True,
        "data": {
            "pending": MOCK_PENDING_INVITATIONS,
            "accepted": MOCK_ACCEPTED_INVITATIONS,
        },
    }


@app.get("/api/circles/availability")
async def get_availability(authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return {"success": True, "data": {"slots": MOCK_USER_AVAILABILITY}}


@app.put("/api/circles/availability")
async def update_availability(request: AvailabilityRequest, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    global MOCK_USER_AVAILABILITY
    MOCK_USER_AVAILABILITY = request.slots
    return {"success": True, "data": {"slots": MOCK_USER_AVAILABILITY}}


# Group endpoints
@app.get("/api/circles/groups/{group_id}")
async def get_group(group_id: str, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    group = next((g for g in MOCK_CIRCLE_GROUPS if g["id"] == group_id), None)
    if not group:
        raise HTTPException(status_code=404, detail={"message": "Group not found"})
    return {"success": True, "data": {"group": group}}


@app.get("/api/circles/groups/{group_id}/meetings")
async def get_group_meetings(group_id: str, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    group = next((g for g in MOCK_CIRCLE_GROUPS if g["id"] == group_id), None)
    if not group:
        raise HTTPException(status_code=404, detail={"message": "Group not found"})

    # Get meetings from MOCK_GROUP_MEETINGS
    meetings = MOCK_GROUP_MEETINGS.get(group_id, [])
    return {"success": True, "data": {"meetings": meetings}}


@app.get("/api/circles/groups/{group_id}/common-availability")
async def get_group_common_availability(group_id: str, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    # Return common availability slots from MOCK_COMMON_AVAILABILITY
    slots = MOCK_COMMON_AVAILABILITY.get(group_id, [])
    return {"success": True, "data": {"slots": slots}}


@app.post("/api/circles/groups/{group_id}/meetings")
async def schedule_meeting(group_id: str, request: ScheduleMeetingRequest, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    group = next((g for g in MOCK_CIRCLE_GROUPS if g["id"] == group_id), None)
    if not group:
        raise HTTPException(status_code=404, detail={"message": "Group not found"})

    new_meeting = {
        "id": f"mtg_{secrets.token_hex(4)}",
        "title": request.title,
        "scheduledAt": request.scheduledAt,
        "meetingLink": f"https://meet.google.com/{secrets.token_hex(3)}-{secrets.token_hex(4)}-{secrets.token_hex(3)}",
        "status": "scheduled",
    }

    # Update the group's next meeting
    group["nextMeeting"] = new_meeting

    # Add to meetings history
    if group_id not in MOCK_GROUP_MEETINGS:
        MOCK_GROUP_MEETINGS[group_id] = []
    MOCK_GROUP_MEETINGS[group_id].insert(0, new_meeting)

    return {"success": True, "data": {"meeting": new_meeting}}


# Invitation endpoints
@app.get("/api/circles/invitations/{token}")
async def get_invitation(token: str, authorization: Optional[str] = Header(None)):
    invitation = next((i for i in MOCK_PENDING_INVITATIONS if i["token"] == token), None)
    if not invitation:
        raise HTTPException(status_code=404, detail={"message": "Invitation not found or expired"})
    return {
        "success": True,
        "data": {
            "invitation": invitation,
            "pool": {"name": invitation["poolName"]},
        },
    }


@app.post("/api/circles/invitations/{token}/accept")
async def accept_invitation(token: str, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    global MOCK_PENDING_INVITATIONS, MOCK_ACCEPTED_INVITATIONS

    invitation = next((i for i in MOCK_PENDING_INVITATIONS if i["token"] == token), None)
    if not invitation:
        raise HTTPException(status_code=404, detail={"message": "Invitation not found or expired"})

    MOCK_PENDING_INVITATIONS = [i for i in MOCK_PENDING_INVITATIONS if i["token"] != token]
    MOCK_ACCEPTED_INVITATIONS.append(invitation)

    return {"success": True, "message": "Invitation accepted"}


@app.post("/api/circles/invitations/{token}/decline")
async def decline_invitation(token: str, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    global MOCK_PENDING_INVITATIONS

    invitation = next((i for i in MOCK_PENDING_INVITATIONS if i["token"] == token), None)
    if not invitation:
        raise HTTPException(status_code=404, detail={"message": "Invitation not found or expired"})

    MOCK_PENDING_INVITATIONS = [i for i in MOCK_PENDING_INVITATIONS if i["token"] != token]

    return {"success": True, "message": "Invitation declined"}


# Meeting endpoints
@app.post("/api/circles/meetings/{meeting_id}/cancel")
async def cancel_meeting(meeting_id: str, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    # Find and remove the meeting from any group
    for group in MOCK_CIRCLE_GROUPS:
        if group.get("nextMeeting") and group["nextMeeting"]["id"] == meeting_id:
            group["nextMeeting"] = None
            return {"success": True, "message": "Meeting cancelled"}

    raise HTTPException(status_code=404, detail={"message": "Meeting not found"})


@app.post("/api/circles/meetings/{meeting_id}/attendance")
async def update_attendance(meeting_id: str, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return {"success": True, "message": "Attendance updated"}


# Legacy endpoints (for backward compatibility)
@app.get("/api/circles/groups")
async def circles_groups_legacy(authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    # Transform to old format
    groups = []
    upcoming = []

    for g in MOCK_CIRCLE_GROUPS:
        groups.append({
            "id": g["id"],
            "name": g["name"],
            "memberCount": len(g["members"]),
            "members": [{"name": f"{m['profile']['firstName']} {m['profile']['lastName'][0]}.", "avatar": None} for m in g["members"][:3]],
            "nextMeeting": g["nextMeeting"]["scheduledAt"] if g.get("nextMeeting") else None,
        })
        if g.get("nextMeeting"):
            upcoming.append({
                "id": g["nextMeeting"]["id"],
                "title": g["nextMeeting"]["title"],
                "groupName": g["name"],
                "date": g["nextMeeting"]["scheduledAt"],
            })

    return {"success": True, "data": {"groups": groups, "upcomingMeetings": upcoming}}


@app.get("/api/circles/invitations")
async def circles_invitations_legacy(authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    invitations = [{"id": i["id"], "groupName": i["poolName"], "invitedBy": "Admin"} for i in MOCK_PENDING_INVITATIONS]
    return {"success": True, "data": {"invitations": invitations}}


# =============================================================================
# COACH ENDPOINTS
# =============================================================================

MOCK_COACH_RESPONSES = {
    "en": [
        "That's a great question about leadership. Let me share some thoughts...",
        "I understand the challenge you're facing. Here's what I'd suggest...",
        "Building trust in your team takes time. Consider these approaches...",
        "Delegation can be difficult, especially when you care about outcomes...",
    ],
    "sv": [
        "Det är en bra fråga om ledarskap. Låt mig dela några tankar...",
        "Jag förstår utmaningen du står inför. Här är vad jag skulle föreslå...",
        "Att bygga förtroende i ditt team tar tid. Överväg dessa tillvägagångssätt...",
        "Delegering kan vara svårt, särskilt när du bryr dig om resultaten...",
    ],
}

MOCK_QUICK_REPLIES = {
    "en": ["Tell me more", "What should I try?", "Give me an example"],
    "sv": ["Berätta mer", "Vad ska jag prova?", "Ge mig ett exempel"],
}


@app.post("/api/coach/chat")
async def coach_chat(
    request: CoachChatRequest, authorization: Optional[str] = Header(None)
):
    require_auth(authorization)
    import random

    lang = request.language if request.language in ["en", "sv"] else "en"
    conversation_id = request.conversationId or f"conv_{secrets.token_hex(8)}"

    return {
        "success": True,
        "data": {
            "message": random.choice(MOCK_COACH_RESPONSES[lang]),
            "conversationId": conversation_id,
            "quickReplies": MOCK_QUICK_REPLIES[lang],
        },
    }


@app.post("/api/coach/stream")
async def coach_stream(
    request: CoachChatRequest, authorization: Optional[str] = Header(None)
):
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
                "Det är en utmärkt fråga om ledarskap. "
                "Att utveckla ditt team kräver både tålamod och strategi. "
                "Låt mig dela några tankar som kan hjälpa dig. "
                "Först, överväg att ha regelbundna en-till-en-samtal med varje teammedlem. "
                "Detta bygger förtroende och ger dig insikt i deras utmaningar. "
                "För det andra, delegera inte bara uppgifter, utan också ansvar och befogenheter. "
                "Detta visar att du litar på ditt team."
            )
        else:
            response_text = (
                "That's an excellent question about leadership. "
                "Developing your team requires both patience and strategy. "
                "Let me share some thoughts that might help you. "
                "First, consider having regular one-on-one conversations with each team member. "
                "This builds trust and gives you insight into their challenges. "
                "Second, delegate not just tasks, but also responsibility and authority. "
                "This shows that you trust your team."
            )

        words = response_text.split()
        chunk_size = 3

        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i : i + chunk_size])
            if i > 0:
                chunk = " " + chunk
            text_chunk = {"type": "text", "content": chunk}
            yield f"data: {json.dumps(text_chunk)}\n\n"
            await asyncio.sleep(0.07)

        # Send actions
        actions = {
            "type": "actions",
            "content": [
                {
                    "type": "exercise",
                    "id": "breathing",
                    "label": "Prova en lugnande övning" if lang == "sv" else "Try a Calming Exercise",
                },
                {
                    "type": "module",
                    "id": "delegation",
                    "label": "Lär dig: Delegera rätt" if lang == "sv" else "Learn: Delegation Done Right",
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

        # Send final metadata
        final_metadata = {
            "type": "metadata",
            "content": {
                "conversationId": conversation_id,
                "intent": "coaching",
                "topics": ["leadership", "delegation"],
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
async def coach_starters(
    language: str = "en",
    includeWellbeing: bool = False,
    mood: Optional[int] = None,
    energy: Optional[int] = None,
    stress: Optional[int] = None,
    authorization: Optional[str] = Header(None),
):
    require_auth(authorization)

    starters_en = [
        {"key": "leadership", "text": "I want to work on my leadership skills"},
        {"key": "stress", "text": "My stress has been building up"},
        {"key": "team", "text": "I need help with my team"},
        {"key": "decision", "text": "Help me think through a decision"},
    ]
    starters_sv = [
        {"key": "leadership", "text": "Jag vill utveckla mitt ledarskap"},
        {"key": "stress", "text": "Min stress har ökat på sistone"},
        {"key": "team", "text": "Jag behöver hjälp med mitt team"},
        {"key": "decision", "text": "Hjälp mig tänka igenom ett beslut"},
    ]

    starters = starters_sv if language == "sv" else starters_en

    if includeWellbeing:
        if stress and stress >= 7:
            high_stress = (
                {"key": "high_stress", "text": "Min stress är väldigt hög just nu"}
                if language == "sv"
                else {"key": "high_stress", "text": "My stress is really high right now"}
            )
            starters.insert(0, high_stress)

        if energy and energy <= 4:
            low_energy = (
                {"key": "low_energy", "text": "Jag känner mig energilös"}
                if language == "sv"
                else {"key": "low_energy", "text": "I'm feeling low on energy"}
            )
            starters.insert(0, low_energy)

        if mood and mood <= 2:
            low_mood = (
                {"key": "low_mood", "text": "Jag har inte mått så bra"}
                if language == "sv"
                else {"key": "low_mood", "text": "I haven't been feeling great"}
            )
            starters.insert(0, low_mood)

    return {"success": True, "data": {"starters": starters[:4]}}


# =============================================================================
# DASHBOARD ENDPOINTS
# =============================================================================


@app.get("/api/dashboard")
async def dashboard(authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return {
        "success": True,
        "data": {
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
                "title": "Time Management Mastery",
                "titleSv": "Tidshanteringsmästerskap",
                "progress": 45,
            },
            "nextCircle": {"date": "Jan 13, 3:00 PM", "dateSv": "13 jan, 15:00"},
        },
    }


# =============================================================================
# HUB ENDPOINTS - Global Administration
# =============================================================================

# Mock data stores
MOCK_HUB_ADMINS = [
    {"email": "admin@example.com", "addedBy": "system", "addedAt": "2024-01-01T00:00:00Z"},
    {"email": "superadmin@deburn.com", "addedBy": "admin@example.com", "addedAt": "2024-06-15T10:30:00Z"},
]

MOCK_ORGANIZATIONS = [
    {"id": "org_1", "name": "Acme Corporation", "domain": "acme.com", "memberCount": 45},
    {"id": "org_2", "name": "TechStart AB", "domain": "techstart.se", "memberCount": 12},
    {"id": "org_3", "name": "Innovation Labs", "domain": None, "memberCount": 8},
]

MOCK_ORG_ADMINS = [
    {
        "email": "john@acme.com",
        "name": "John Doe",
        "organizations": [
            {"id": "org_1", "name": "Acme Corporation", "membershipId": "mem_1"},
        ],
    },
    {
        "email": "anna@techstart.se",
        "name": "Anna Svensson",
        "organizations": [
            {"id": "org_2", "name": "TechStart AB", "membershipId": "mem_2"},
            {"id": "org_3", "name": "Innovation Labs", "membershipId": "mem_3"},
        ],
    },
]

MOCK_COACH_CONFIG = {
    "model": "claude-sonnet-4-5-20250929",
    "maxTokens": 1024,
    "temperature": 0.7,
    "methodology": {
        "primary": "EMCC",
        "ethical": "ICF",
        "frameworks": ["SDT", "JD-R", "CBC", "ACT", "Positive Psychology", "EQ", "Systems Thinking"],
    },
    "topics": [
        "delegation", "stress", "team_dynamics", "communication", "leadership",
        "time_management", "conflict", "burnout", "motivation", "decision_making",
        "mindfulness", "resilience"
    ],
    "crisisKeywords": {
        "en": ["suicide", "kill myself", "end my life", "want to die", "self-harm", "cutting myself"],
        "sv": ["självmord", "ta mitt liv", "döda mig", "skada mig själv"],
    },
    "softEscalationKeywords": {
        "en": ["depressed", "anxiety", "panic attack", "can't cope", "overwhelmed", "breaking down"],
        "sv": ["deprimerad", "ångest", "panikattack", "klarar inte", "överväldigad"],
    },
    "hardBoundaries": [
        "Medical advice",
        "Legal counsel",
        "Financial planning",
        "Therapy/psychiatric treatment",
        "Medication recommendations",
    ],
}

MOCK_COACH_PROMPTS = {
    "en": {
        "base-coach": "You are Eve, an AI leadership coach created by Deburn. Your role is to help leaders grow, manage stress, and build stronger teams through evidence-based coaching conversations.",
        "safety-rules": "Always prioritize user wellbeing. If you detect signs of crisis, gently redirect to professional resources.",
        "tone-guidelines": "Be warm, professional, and supportive. Use a calm, measured tone. Ask thoughtful questions rather than giving direct advice.",
    },
    "sv": {
        "base-coach": "Du är Eve, en AI-ledarskapscoach skapad av Deburn. Din roll är att hjälpa ledare att växa, hantera stress och bygga starkare team genom evidensbaserade coachingsamtal.",
        "safety-rules": "Prioritera alltid användarens välbefinnande. Om du upptäcker tecken på kris, hänvisa varsamt till professionella resurser.",
        "tone-guidelines": "Var varm, professionell och stödjande. Använd en lugn, avvägd ton. Ställ eftertänksamma frågor istället för att ge direkta råd.",
    },
}

MOCK_CONTENT_ITEMS = [
    {
        "id": "cnt_1",
        "contentType": "text_article",
        "category": "leadership",
        "status": "published",
        "titleEn": "The Art of Delegation",
        "titleSv": "Konsten att delegera",
        "purpose": "Help leaders understand when and how to delegate effectively",
        "lengthMinutes": 8,
        "coachTopics": ["delegation", "leadership", "time_management"],
        "coachPriority": 8,
        "coachEnabled": True,
    },
    {
        "id": "cnt_2",
        "contentType": "audio_exercise",
        "category": "meditation",
        "status": "published",
        "titleEn": "5-Minute Breathing Reset",
        "titleSv": "5-minuters andningsåterställning",
        "purpose": "Quick stress relief through guided breathing",
        "lengthMinutes": 5,
        "coachTopics": ["stress", "mindfulness", "resilience"],
        "coachPriority": 9,
        "coachEnabled": True,
        "audioFileEn": "/audio/breathing-reset-en.mp3",
        "audioFileSv": "/audio/breathing-reset-sv.mp3",
    },
    {
        "id": "cnt_3",
        "contentType": "audio_article",
        "category": "burnout",
        "status": "published",
        "titleEn": "Recognizing Early Signs of Burnout",
        "titleSv": "Att känna igen tidiga tecken på utbrändhet",
        "purpose": "Learn to identify burnout symptoms before they become severe",
        "lengthMinutes": 12,
        "coachTopics": ["burnout", "stress", "resilience"],
        "coachPriority": 7,
        "coachEnabled": True,
    },
    {
        "id": "cnt_4",
        "contentType": "video_link",
        "category": "leadership",
        "status": "draft",
        "titleEn": "Building Psychological Safety",
        "titleSv": "Att bygga psykologisk trygghet",
        "purpose": "Create an environment where team members feel safe to speak up",
        "lengthMinutes": 15,
        "coachTopics": ["team_dynamics", "leadership", "communication"],
        "coachPriority": 6,
        "coachEnabled": False,
        "videoUrl": "https://example.com/video",
    },
    {
        "id": "cnt_5",
        "contentType": "text_article",
        "category": "wellbeing",
        "status": "in_review",
        "titleEn": "Managing Energy Throughout the Day",
        "titleSv": "Att hantera energi under dagen",
        "purpose": "Practical strategies for maintaining focus and energy",
        "lengthMinutes": 10,
        "coachTopics": ["motivation", "time_management"],
        "coachPriority": 5,
        "coachEnabled": True,
    },
]


class HubAdminRequest(BaseModel):
    email: str


class OrgAdminRequest(BaseModel):
    email: str
    organizationId: str


class CreateOrganizationRequest(BaseModel):
    name: str
    domain: Optional[str] = None


class CoachSettingsRequest(BaseModel):
    dailyExchangeLimit: int


class CoachPromptRequest(BaseModel):
    content: str


class ContentRequest(BaseModel):
    contentType: str
    category: str
    status: str
    titleEn: str
    titleSv: Optional[str] = None
    purpose: Optional[str] = None
    outcome: Optional[str] = None
    lengthMinutes: Optional[float] = None
    relatedFramework: Optional[str] = None
    coachTopics: Optional[list] = None
    coachPriority: Optional[int] = 0
    coachEnabled: Optional[bool] = True
    textContentEn: Optional[str] = None
    textContentSv: Optional[str] = None
    videoUrl: Optional[str] = None
    videoEmbedCode: Optional[str] = None
    videoAvailableInEn: Optional[bool] = False
    videoAvailableInSv: Optional[bool] = False
    voiceoverScriptEn: Optional[str] = None
    voiceoverScriptSv: Optional[str] = None
    ttsSpeed: Optional[float] = 1.0
    ttsVoice: Optional[str] = "Aria"


# Hub Admins
@app.get("/api/hub/admins")
async def get_hub_admins(authorization: Optional[str] = Header(None)):
    return {"success": True, "data": {"admins": MOCK_HUB_ADMINS}}


@app.post("/api/hub/admins")
async def add_hub_admin(request: HubAdminRequest, authorization: Optional[str] = Header(None)):
    new_admin = {
        "email": request.email,
        "addedBy": "admin@example.com",
        "addedAt": datetime.now(timezone.utc).isoformat(),
    }
    MOCK_HUB_ADMINS.append(new_admin)
    return {"success": True, "data": {"admin": new_admin}}


@app.delete("/api/hub/admins/{email}")
async def remove_hub_admin(email: str, authorization: Optional[str] = Header(None)):
    return {"success": True}


# Organizations
@app.get("/api/hub/organizations")
async def get_organizations(authorization: Optional[str] = Header(None)):
    return {"success": True, "data": {"organizations": MOCK_ORGANIZATIONS}}


@app.post("/api/hub/organizations")
async def create_organization(request: CreateOrganizationRequest, authorization: Optional[str] = Header(None)):
    new_org = {
        "id": f"org_{len(MOCK_ORGANIZATIONS) + 1}",
        "name": request.name,
        "domain": request.domain,
        "memberCount": 0,
    }
    MOCK_ORGANIZATIONS.append(new_org)
    return {"success": True, "data": {"organization": new_org}}


# Org Admins
@app.get("/api/hub/org-admins")
async def get_org_admins(authorization: Optional[str] = Header(None)):
    return {"success": True, "data": {"admins": MOCK_ORG_ADMINS}}


@app.post("/api/hub/org-admins")
async def add_org_admin(request: OrgAdminRequest, authorization: Optional[str] = Header(None)):
    org = next((o for o in MOCK_ORGANIZATIONS if o["id"] == request.organizationId), None)
    if not org:
        raise HTTPException(status_code=404, detail={"message": "Organization not found"})

    existing = next((a for a in MOCK_ORG_ADMINS if a["email"] == request.email), None)
    if existing:
        existing["organizations"].append({
            "id": org["id"],
            "name": org["name"],
            "membershipId": f"mem_{secrets.token_hex(4)}",
        })
    else:
        MOCK_ORG_ADMINS.append({
            "email": request.email,
            "name": request.email.split("@")[0].replace(".", " ").title(),
            "organizations": [{
                "id": org["id"],
                "name": org["name"],
                "membershipId": f"mem_{secrets.token_hex(4)}",
            }],
        })
    return {"success": True}


@app.delete("/api/hub/org-admins/{membership_id}")
async def remove_org_admin(membership_id: str, authorization: Optional[str] = Header(None)):
    return {"success": True}


# Coach Settings
@app.get("/api/hub/settings/coach")
async def get_coach_settings(authorization: Optional[str] = Header(None)):
    return {"success": True, "data": {"dailyExchangeLimit": 15}}


@app.put("/api/hub/settings/coach")
async def update_coach_settings(request: CoachSettingsRequest, authorization: Optional[str] = Header(None)):
    return {"success": True, "data": {"dailyExchangeLimit": request.dailyExchangeLimit}}


# Coach Config
@app.get("/api/hub/coach/config")
async def get_coach_config(authorization: Optional[str] = Header(None)):
    return {"success": True, "data": MOCK_COACH_CONFIG}


# Coach Prompts
@app.get("/api/hub/coach/prompts")
async def get_coach_prompts(authorization: Optional[str] = Header(None)):
    return {"success": True, "data": {"prompts": MOCK_COACH_PROMPTS}}


@app.put("/api/hub/coach/prompts/{language}/{prompt_name}")
async def update_coach_prompt(
    language: str,
    prompt_name: str,
    request: CoachPromptRequest,
    authorization: Optional[str] = Header(None)
):
    if language in MOCK_COACH_PROMPTS and prompt_name in MOCK_COACH_PROMPTS[language]:
        MOCK_COACH_PROMPTS[language][prompt_name] = request.content
    return {"success": True}


# Content Library
@app.get("/api/hub/content")
async def get_content(
    category: Optional[str] = None,
    contentType: Optional[str] = None,
    status: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    items = MOCK_CONTENT_ITEMS
    if category:
        items = [i for i in items if i["category"] == category]
    if contentType:
        items = [i for i in items if i["contentType"] == contentType]
    if status:
        items = [i for i in items if i["status"] == status]
    return {"success": True, "data": {"items": items}}


@app.get("/api/hub/content/{content_id}")
async def get_content_item(content_id: str, authorization: Optional[str] = Header(None)):
    item = next((i for i in MOCK_CONTENT_ITEMS if i["id"] == content_id), None)
    if not item:
        raise HTTPException(status_code=404, detail={"message": "Content not found"})
    return {"success": True, "data": {"item": item}}


@app.post("/api/hub/content")
async def create_content(request: ContentRequest, authorization: Optional[str] = Header(None)):
    new_item = {
        "id": f"cnt_{len(MOCK_CONTENT_ITEMS) + 1}",
        **request.model_dump(),
    }
    MOCK_CONTENT_ITEMS.append(new_item)
    return {"success": True, "data": {"item": new_item}}


@app.put("/api/hub/content/{content_id}")
async def update_content(content_id: str, request: ContentRequest, authorization: Optional[str] = Header(None)):
    for i, item in enumerate(MOCK_CONTENT_ITEMS):
        if item["id"] == content_id:
            MOCK_CONTENT_ITEMS[i] = {"id": content_id, **request.model_dump()}
            return {"success": True, "data": {"item": MOCK_CONTENT_ITEMS[i]}}
    raise HTTPException(status_code=404, detail={"message": "Content not found"})


@app.delete("/api/hub/content/{content_id}")
async def delete_content(content_id: str, authorization: Optional[str] = Header(None)):
    return {"success": True}


@app.post("/api/hub/content/{content_id}/audio/{lang}")
async def upload_audio(content_id: str, lang: str, authorization: Optional[str] = Header(None)):
    return {"success": True, "data": {"audioUrl": f"/audio/{content_id}-{lang}.mp3"}}


@app.delete("/api/hub/content/{content_id}/audio/{lang}")
async def remove_audio(content_id: str, lang: str, authorization: Optional[str] = Header(None)):
    return {"success": True}


# Compliance
@app.get("/api/hub/compliance/stats")
async def get_compliance_stats(authorization: Optional[str] = Header(None)):
    return {
        "success": True,
        "data": {
            "totalUsers": 150,
            "pendingDeletions": 2,
            "auditLogCount": 4523,
            "activeSessions": 87,
        },
    }


@app.get("/api/hub/compliance/user/{email}")
async def get_compliance_user(email: str, authorization: Optional[str] = Header(None)):
    return {
        "success": True,
        "data": {
            "id": "usr_mock123",
            "email": email,
            "organization": "Acme Corp",
            "status": "active",
            "createdAt": "2024-01-15T10:30:00Z",
            "lastLoginAt": "2025-01-10T14:22:00Z",
            "sessionCount": 45,
            "checkInCount": 120,
            "consents": {
                "termsOfService": {"accepted": True, "acceptedAt": "2024-01-15T10:30:00Z"},
                "privacyPolicy": {"accepted": True, "acceptedAt": "2024-01-15T10:30:00Z"},
            },
        },
    }


@app.post("/api/hub/compliance/export/{user_id}")
async def export_user_data(user_id: str, authorization: Optional[str] = Header(None)):
    return {
        "success": True,
        "data": {
            "user": {"id": user_id, "email": "user@example.com"},
            "checkins": [{"date": "2025-01-10", "mood": 4, "stress": 3}],
            "conversations": [{"id": "conv_1", "messageCount": 12}],
            "exportedAt": datetime.now(timezone.utc).isoformat(),
        },
    }


@app.post("/api/hub/compliance/delete/{user_id}")
async def delete_user_account(user_id: str, authorization: Optional[str] = Header(None)):
    return {"success": True, "message": "Account scheduled for deletion"}


@app.get("/api/hub/compliance/pending-deletions")
async def get_pending_deletions(authorization: Optional[str] = Header(None)):
    return {
        "success": True,
        "data": {
            "users": [
                {
                    "id": "usr_del1",
                    "email": "leaving@acme.com",
                    "deletion": {
                        "requestedAt": "2025-01-01T00:00:00Z",
                        "scheduledFor": "2025-01-31T00:00:00Z",
                    },
                },
            ]
        },
    }


@app.post("/api/hub/compliance/cleanup-sessions")
async def cleanup_sessions(authorization: Optional[str] = Header(None)):
    return {"success": True, "data": {"deletedCount": 23}}


@app.get("/api/hub/compliance/security-config")
async def get_security_config(authorization: Optional[str] = Header(None)):
    return {
        "success": True,
        "data": {
            "sessionTimeout": 3600,
            "maxLoginAttempts": 5,
            "passwordMinLength": 12,
            "requireMFA": False,
            "allowedDomains": ["*"],
            "rateLimits": {
                "login": "10/minute",
                "api": "100/minute",
            },
        },
    }


# =============================================================================
# LEARNING ENDPOINTS
# =============================================================================


@app.get("/api/learning/modules")
async def learning_modules(authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return {
        "success": True,
        "data": {
            "modules": [
                {
                    "id": "mod_123",
                    "title": "Time Ninja: Mastering Your Schedule",
                    "titleSv": "Tidsninja: Bemästra ditt schema",
                    "description": "Learn effective time management techniques",
                    "descriptionSv": "Lär dig effektiva tidshanteringstekniker",
                    "type": "audio",
                    "duration": 15,
                    "thumbnail": "/images/modules/time-ninja.jpg",
                    "progress": 45,
                },
                {
                    "id": "mod_456",
                    "title": "Stress Management Basics",
                    "titleSv": "Grundläggande stresshantering",
                    "description": "Techniques for managing daily stress",
                    "descriptionSv": "Tekniker för att hantera daglig stress",
                    "type": "video",
                    "duration": 20,
                    "thumbnail": None,
                    "progress": 0,
                },
                {
                    "id": "mod_789",
                    "title": "Delegation Done Right",
                    "titleSv": "Delegera rätt",
                    "description": "How to delegate effectively and build trust",
                    "descriptionSv": "Hur man delegerar effektivt och bygger förtroende",
                    "type": "article",
                    "duration": 10,
                    "thumbnail": "/images/modules/delegation.jpg",
                    "progress": 100,
                },
                {
                    "id": "mod_101",
                    "title": "Building Psychological Safety",
                    "titleSv": "Bygga psykologisk trygghet",
                    "description": "Create an environment where your team thrives",
                    "descriptionSv": "Skapa en miljö där ditt team blomstrar",
                    "type": "exercise",
                    "duration": 25,
                    "thumbnail": None,
                    "progress": 30,
                },
            ]
        },
    }


# =============================================================================
# PROFILE ENDPOINTS
# =============================================================================


@app.put("/api/profile")
async def update_profile(
    request: ProfileUpdateRequest, authorization: Optional[str] = Header(None)
):
    user = require_auth(authorization)
    return {
        "success": True,
        "data": {
            "user": {
                "id": user["id"],
                "firstName": request.firstName or user["firstName"],
                "lastName": request.lastName or user["lastName"],
                "email": user["email"],
                "organization": request.organization or user["profile"].get("organization"),
                "role": request.role or user["profile"].get("jobTitle"),
                "bio": request.bio or "Passionate about building great teams",
            }
        },
    }


@app.post("/api/profile/avatar")
async def upload_avatar(authorization: Optional[str] = Header(None)):
    user = require_auth(authorization)
    return {
        "success": True,
        "data": {"avatarUrl": f"/uploads/avatars/{user['id']}.jpg"},
    }


@app.put("/api/profile/avatar")
async def remove_avatar(
    _request: AvatarRemoveRequest, authorization: Optional[str] = Header(None)
):
    require_auth(authorization)
    return {"success": True}


# =============================================================================
# PROGRESS ENDPOINTS
# =============================================================================


@app.get("/api/progress/stats")
async def progress_stats(authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return {
        "success": True,
        "data": {"streak": 12, "checkins": 45, "lessons": 8, "sessions": 23},
    }


@app.get("/api/progress/insights")
async def progress_insights(authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return {
        "success": True,
        "data": {
            "insights": [
                {
                    "title": "Thursday Stress Pattern",
                    "titleSv": "Torsdagens stressmönster",
                    "description": "Your stress tends to spike on Thursdays. Consider blocking 30 minutes before your afternoon meetings for preparation.",
                    "descriptionSv": "Din stress tenderar att toppa på torsdagar. Överväg att blockera 30 minuter före dina eftermiddagsmöten för förberedelse.",
                },
                {
                    "title": "Morning Energy Peak",
                    "titleSv": "Morgonens energitopp",
                    "description": "You report highest energy levels between 9-11am. Schedule your most demanding tasks during this window.",
                    "descriptionSv": "Du rapporterar högst energinivåer mellan 9-11. Schemalägg dina mest krävande uppgifter under detta fönster.",
                },
                {
                    "title": "Consistent Sleep Pattern",
                    "titleSv": "Konsekvent sömnmönster",
                    "description": "Your sleep quality has been stable this week. Keep up the good routine!",
                    "descriptionSv": "Din sömnkvalitet har varit stabil denna vecka. Fortsätt med den goda rutinen!",
                },
            ]
        },
    }


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5002)

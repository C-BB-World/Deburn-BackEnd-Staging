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
        raise HTTPException(status_code=401, detail="Unauthorized")
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
# CIRCLES ENDPOINTS
# =============================================================================


@app.get("/api/circles/groups")
async def circles_groups(authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return {
        "success": True,
        "data": {
            "groups": [
                {
                    "id": "grp_123",
                    "name": "Engineering Leaders",
                    "nameSv": "Ingenjörsledare",
                    "memberCount": 6,
                    "members": [
                        {"name": "Anna S.", "avatar": "/avatars/anna.jpg"},
                        {"name": "Erik L.", "avatar": None},
                        {"name": "Maria K.", "avatar": "/avatars/maria.jpg"},
                    ],
                    "nextMeeting": "Mon, Jan 13, 3:00 PM",
                },
                {
                    "id": "grp_456",
                    "name": "Product Managers Circle",
                    "nameSv": "Produktchefscirkel",
                    "memberCount": 4,
                    "members": [
                        {"name": "Johan B.", "avatar": None},
                        {"name": "Lisa T.", "avatar": "/avatars/lisa.jpg"},
                    ],
                    "nextMeeting": "Wed, Jan 15, 2:00 PM",
                },
            ],
            "upcomingMeetings": [
                {
                    "id": "mtg_123",
                    "title": "Weekly Sync",
                    "titleSv": "Veckomöte",
                    "groupName": "Engineering Leaders",
                    "date": "2025-01-13T15:00:00Z",
                },
                {
                    "id": "mtg_456",
                    "title": "Sprint Review",
                    "titleSv": "Sprintgranskning",
                    "groupName": "Product Managers Circle",
                    "date": "2025-01-15T14:00:00Z",
                },
            ],
        },
    }


@app.get("/api/circles/invitations")
async def circles_invitations(authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return {
        "success": True,
        "data": {
            "invitations": [
                {
                    "id": "inv_123",
                    "groupName": "Product Managers Circle",
                    "groupNameSv": "Produktchefscirkel",
                    "invitedBy": "Maria K.",
                },
            ]
        },
    }


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
# HUB ENDPOINTS
# =============================================================================


@app.get("/api/hub/organization")
async def hub_organization(authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return {
        "success": True,
        "data": {
            "id": "org_123",
            "name": "Acme Corporation",
            "memberCount": 45,
            "activeUsers": 32,
            "completedLessons": 234,
            "avgEngagement": 78,
        },
    }


@app.get("/api/hub/members")
async def hub_members(authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    return {
        "success": True,
        "data": {
            "members": [
                {
                    "id": "usr_123",
                    "name": "John Doe",
                    "email": "john@acme.com",
                    "role": "admin",
                },
                {
                    "id": "usr_456",
                    "name": "Jane Smith",
                    "email": "jane@acme.com",
                    "role": "member",
                },
                {
                    "id": "usr_789",
                    "name": "Erik Johansson",
                    "email": "erik@acme.com",
                    "role": "member",
                },
            ]
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

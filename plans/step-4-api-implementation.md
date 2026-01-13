# Step 4: Create api.py

## Overview

Create the main FastAPI application that implements all API endpoints with full business logic. This uses the generic `common/` library and BrainBank-specific code in `app/`.

## Objective

- Implement all 25 API endpoints matching mock_api.py paths exactly
- Use `common/` library for infrastructure (database, auth, ai, i18n)
- Put BrainBank-specific code in `app/` (models, services, config)
- Support SSE streaming for coach endpoints
- Support switchable auth (JWT/Firebase) and AI (Claude/OpenAI)

---

## Endpoint Specifications

### 1. GET /health

**Purpose**: Health check endpoint

**Common Tools**:
- `common/database/mongodb.py` → `MongoDB.is_connected`
- `common/utils/responses.py` → `success_response()`

**Response**:
```json
{
  "success": true,
  "data": {
    "status": "ok",
    "database": true
  }
}
```

**Implementation**:
```python
@app.get("/health")
async def health():
    return success_response({
        "status": "ok",
        "database": main_db.is_connected
    })
```

---

### 2. POST /api/auth/register

**Purpose**: Create new user account

**Common Tools**:
- `common/auth/dependencies.py` → `get_auth_provider()`
- `common/auth/jwt_auth.py` → `JWTAuth.hash_password()`
- `common/utils/password.py` → `validate_password()`
- `common/utils/responses.py` → `success_response()`, `error_response()`
- `common/i18n/service.py` → `I18nService.t()` for error messages

**Request**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "organization": "Acme Corp",
  "country": "SE",
  "firstName": "John",
  "lastName": "Doe"
}
```

**Response (201)**:
```json
{
  "success": true,
  "message": "Registration successful. Please check your email to verify your account.",
  "data": {
    "user": {
      "id": "507f1f77bcf86cd799439011",
      "email": "user@example.com",
      "organization": "Acme Corp",
      "country": "SE",
      "profile": {
        "firstName": "John",
        "lastName": "Doe"
      },
      "status": "pending_verification"
    }
  }
}
```

**Error Response (409)**:
```json
{
  "success": false,
  "error": {
    "code": "EMAIL_EXISTS",
    "message": "This email is already registered"
  }
}
```

**Implementation Flow**:
1. `validate_password(password)` - Check password strength
2. `User.find_one(User.email == email)` - Check if email exists
3. `auth.hash_password(password)` - Hash password
4. `User.insert()` - Create user document with status="pending_verification"
5. `auth.send_verification_email(email)` - Send verification email
6. Return `success_response(user.to_public_json())`

---

### 3. POST /api/auth/login

**Purpose**: Authenticate user and return tokens

**Common Tools**:
- `common/auth/dependencies.py` → `get_auth_provider()`
- `common/auth/jwt_auth.py` → `JWTAuth.verify_password()`, `JWTAuth.create_token()`
- `common/utils/responses.py` → `success_response()`
- `common/utils/exceptions.py` → `UnauthorizedException`

**Request**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "rememberMe": false
}
```

**Response (200)**:
```json
{
  "success": true,
  "message": "Signed in successfully",
  "data": {
    "user": {
      "id": "507f1f77bcf86cd799439011",
      "email": "user@example.com",
      "organization": "Acme Corp",
      "country": "SE",
      "profile": {
        "firstName": "John",
        "lastName": "Doe",
        "preferredLanguage": "en"
      },
      "displayName": "John Doe",
      "status": "active"
    },
    "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

**Error Response (401)**:
```json
{
  "success": false,
  "error": {
    "code": "LOGIN_FAILED",
    "message": "Invalid email or password"
  }
}
```

**Implementation Flow**:
1. `User.find_one(User.email == email)` - Find user
2. Check `user.status == "active"` - Reject if not active
3. `auth.verify_password(password, user.password_hash)` - Verify password
4. `auth.create_token(str(user.id))` - Create JWT token
5. Update `user.last_login_at` - Track login time
6. Return `success_response({user, accessToken})`

---

### 4. POST /api/auth/forgot-password

**Purpose**: Request password reset email

**Common Tools**:
- `common/auth/jwt_auth.py` → `JWTAuth.create_token()` (for reset token)
- `common/utils/responses.py` → `success_response()`

**Request**:
```json
{
  "email": "user@example.com"
}
```

**Response (200)** - Always success to prevent email enumeration:
```json
{
  "success": true,
  "message": "If this email is registered, we've sent password reset instructions."
}
```

**Implementation Flow**:
1. `User.find_one(User.email == email)` - Find user (silently fail if not found)
2. Generate reset token with expiry (1 hour)
3. Store token hash in `user.password_reset.token`
4. `email_service.send_password_reset_email(email, token)` - Send email
5. Return success response (regardless of user existence)

---

### 5. POST /api/auth/reset-password

**Purpose**: Set new password using reset token

**Common Tools**:
- `common/auth/jwt_auth.py` → `JWTAuth.hash_password()`
- `common/utils/password.py` → `validate_password()`
- `common/utils/responses.py` → `success_response()`

**Request**:
```json
{
  "token": "reset-token-from-email",
  "password": "NewSecurePass456!"
}
```

**Response (200)**:
```json
{
  "success": true,
  "message": "Password has been reset successfully. You can now sign in."
}
```

**Error Response (400)**:
```json
{
  "success": false,
  "error": {
    "code": "RESET_FAILED",
    "message": "Invalid or expired reset token"
  }
}
```

**Implementation Flow**:
1. `validate_password(password)` - Check password strength
2. Find user by `password_reset.token` and check expiry
3. `auth.hash_password(password)` - Hash new password
4. Update `user.password_hash`, clear `password_reset`
5. Return success response

---

### 6. POST /api/auth/verify-email

**Purpose**: Verify email address with token

**Common Tools**:
- `common/utils/responses.py` → `success_response()`

**Request**:
```json
{
  "token": "verification-token-from-email"
}
```

**Response (200)**:
```json
{
  "success": true,
  "message": "Email verified successfully",
  "data": {
    "user": {
      "id": "507f1f77bcf86cd799439011",
      "email": "user@example.com",
      "status": "active"
    }
  }
}
```

**Implementation Flow**:
1. Find user by `email_verification.token`
2. Check token expiry
3. Update `user.status = "active"`, `email_verification.verified_at = now()`
4. Return success with user data

---

### 7. POST /api/auth/resend-verification

**Purpose**: Resend email verification link

**Common Tools**:
- `common/utils/responses.py` → `success_response()`

**Request**:
```json
{
  "email": "user@example.com"
}
```

**Response (200)** - Always success to prevent enumeration:
```json
{
  "success": true,
  "message": "If this email is registered and unverified, we've sent a new verification link."
}
```

**Implementation Flow**:
1. Find user by email with `status == "pending_verification"`
2. Generate new verification token
3. Send verification email
4. Return success (regardless of user existence)

---

### 8. POST /api/auth/logout

**Purpose**: Sign out and invalidate session

**Common Tools**:
- `common/auth/dependencies.py` → `get_current_user()`
- `common/utils/responses.py` → `success_response()`

**Request**: No body (uses Authorization header)

**Response (200)**:
```json
{
  "success": true,
  "message": "Signed out successfully"
}
```

**Implementation Flow**:
1. `get_current_user()` - Verify auth token
2. Remove session from `user.sessions` array (if tracking)
3. Return success response

---

### 9. GET /api/admin/stats

**Purpose**: Get admin statistics (organization admin only)

**Common Tools**:
- `common/auth/dependencies.py` → `get_current_user()`
- `common/utils/responses.py` → `success_response()`

**Response (200)**:
```json
{
  "success": true,
  "data": {
    "totalUsers": 150,
    "activeUsers": 142,
    "totalCheckIns": 3500,
    "averageStreak": 12.5
  }
}
```

**Implementation Flow**:
1. Verify user is organization admin via `OrganizationMember.role == "admin"`
2. Aggregate user counts, check-in counts for organization
3. Return stats

---

### 10. POST /api/checkin

**Purpose**: Submit daily wellness check-in

**Common Tools**:
- `common/auth/dependencies.py` → `get_current_user()`
- `common/database/base_document.py` → timestamps
- `common/utils/responses.py` → `success_response()`

**Request**:
```json
{
  "mood": 4,
  "physicalEnergy": 7,
  "mentalEnergy": 6,
  "sleep": 4,
  "stress": 5,
  "notes": "Had a productive meeting this morning"
}
```

**Response (201)**:
```json
{
  "success": true,
  "message": "Check-in saved successfully",
  "data": {
    "checkIn": {
      "id": "507f1f77bcf86cd799439011",
      "date": "2024-01-15",
      "timestamp": "2024-01-15T09:30:00Z",
      "metrics": {
        "mood": 4,
        "physicalEnergy": 7,
        "mentalEnergy": 6,
        "sleep": 4,
        "stress": 5
      },
      "notes": "Had a productive meeting this morning"
    },
    "streak": {
      "current": 7,
      "longest": 21
    },
    "isRetake": false
  }
}
```

**Implementation Flow**:
1. `get_current_user()` - Get authenticated user
2. Get today's date in YYYY-MM-DD format
3. `CheckIn.find_one(user_id, date)` - Check if already checked in today
4. Upsert check-in document
5. `CheckIn.calculate_streak(user_id)` - Calculate streak
6. Return check-in with streak data

---

### 11. GET /api/checkin/trends

**Purpose**: Get check-in trends over time period

**Common Tools**:
- `common/auth/dependencies.py` → `get_current_user()`
- `common/utils/responses.py` → `success_response()`

**Query Parameters**:
- `period`: Number of days (7, 30, 90) - default 30

**Response (200)**:
```json
{
  "success": true,
  "data": {
    "period": 30,
    "dataPoints": 25,
    "mood": {
      "values": [{"date": "2024-01-01", "value": 4}, ...],
      "average": 3.8,
      "trend": "improving",
      "change": 5.2
    },
    "physicalEnergy": {
      "values": [...],
      "average": 6.5,
      "trend": "stable",
      "change": 1.1
    },
    "mentalEnergy": {...},
    "sleep": {...},
    "stress": {...}
  }
}
```

**Implementation Flow**:
1. `get_current_user()` - Get authenticated user
2. Parse period from query (default 30, max 90)
3. `CheckIn.get_trends(user_id, days)` - Get trend data
4. Return trends

---

### 12. GET /api/circles/groups

**Purpose**: Get user's peer support groups

**Common Tools**:
- `common/auth/dependencies.py` → `get_current_user()`
- `common/utils/responses.py` → `success_response()`

**Response (200)**:
```json
{
  "success": true,
  "data": {
    "groups": [
      {
        "id": "507f1f77bcf86cd799439011",
        "name": "Leadership Circle Alpha",
        "topic": "Delegation & Empowerment",
        "memberCount": 4,
        "cadence": "biweekly",
        "nextMeetingAt": "2024-01-20T14:00:00Z",
        "status": "active"
      }
    ]
  }
}
```

**Implementation Flow**:
1. `get_current_user()` - Get authenticated user
2. `CircleGroup.find(members__contains=user_id)` - Find groups user is in
3. Return formatted group list

---

### 13. GET /api/circles/invitations

**Purpose**: Get pending circle invitations for user

**Common Tools**:
- `common/auth/dependencies.py` → `get_current_user()`
- `common/utils/responses.py` → `success_response()`

**Response (200)**:
```json
{
  "success": true,
  "data": {
    "invitations": [
      {
        "id": "507f1f77bcf86cd799439011",
        "poolName": "Q1 Leadership Development",
        "topic": "Stress Management",
        "invitedBy": "admin@company.com",
        "invitedAt": "2024-01-10T10:00:00Z",
        "expiresAt": "2024-01-17T10:00:00Z",
        "status": "pending"
      }
    ]
  }
}
```

**Implementation Flow**:
1. `get_current_user()` - Get authenticated user
2. `CircleInvitation.find(email=user.email, status="pending")` - Find pending invitations
3. Return formatted invitation list

---

### 14. POST /api/coach/chat

**Purpose**: Non-streaming AI coaching conversation

**Common Tools**:
- `common/auth/dependencies.py` → `get_current_user()`
- `common/ai/base.py` → `AIProvider.chat()`
- `common/i18n/service.py` → `I18nService.t()`
- `common/utils/responses.py` → `success_response()`

**Request**:
```json
{
  "message": "How can I better manage stress during busy periods?",
  "conversationId": "conv_12345",
  "language": "en",
  "context": {
    "recentCheckin": {
      "mood": 3,
      "energy": 5,
      "stress": 7,
      "streak": 5
    }
  }
}
```

**Response (200)**:
```json
{
  "success": true,
  "response": {
    "text": "I understand managing stress during busy periods can be challenging...",
    "conversationId": "conv_12345",
    "topics": ["stress", "time_management"],
    "suggestedActions": [
      {"type": "setGoal", "label": "Set a stress management goal"},
      {"type": "openLearning", "label": "Explore stress resources"}
    ]
  },
  "quotaExceeded": false
}
```

**Quota Exceeded Response**:
```json
{
  "success": true,
  "quotaExceeded": true,
  "response": {
    "text": "You've reached your daily conversation limit of 15 messages...",
    "isSystemMessage": true
  },
  "conversationId": "conv_12345"
}
```

**Implementation Flow**:
1. `get_current_user()` - Get authenticated user
2. `check_quota(user_id)` - Check daily exchange limit
3. If quota exceeded, return quota message
4. `coach_service.check_safety(message)` - Safety check for crisis keywords
5. Build user context (name, role, organization, wellbeing)
6. `coach_service.chat(message, conversation_id, user_context, language)` - Get AI response
7. `increment_exchange_count(user_id)` - Increment quota
8. Return response with topics and suggested actions

---

### 15. POST /api/coach/stream (SSE)

**Purpose**: Streaming AI coaching conversation

**Common Tools**:
- `common/auth/dependencies.py` → `get_current_user()`
- `common/ai/base.py` → `AIProvider.stream_chat()` (async generator)
- `common/i18n/service.py` → `I18nService.t()`

**Request**: Same as `/api/coach/chat`

**SSE Response Stream**:
```
data: {"type": "text", "content": "I understand "}

data: {"type": "text", "content": "managing stress "}

data: {"type": "text", "content": "can be challenging..."}

data: {"type": "metadata", "content": {"conversationId": "conv_12345", "topics": ["stress"]}}

data: {"type": "done"}

data: [DONE]
```

**Quota Exceeded SSE**:
```
data: {"type": "quotaExceeded", "content": "You've reached your daily limit...", "conversationId": "conv_12345"}

data: [DONE]
```

**Implementation Flow**:
1. `get_current_user()` - Get authenticated user
2. `check_quota(user_id)` - Check daily exchange limit
3. If quota exceeded, stream quota message and return
4. Set SSE headers: `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `X-Accel-Buffering: no`
5. `coach_service.stream_chat(...)` - Get async generator
6. `async for chunk in stream:` yield SSE events
7. `increment_exchange_count(user_id)` - Increment quota after complete
8. Yield `data: [DONE]`

**FastAPI Implementation**:
```python
@router.post("/stream")
async def stream_chat(request: ChatRequest, user: User = Depends(get_current_user)):
    async def event_generator():
        async for chunk in coach_service.stream_chat(...):
            yield f"data: {json.dumps(chunk)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
```

---

### 16. GET /api/coach/starters

**Purpose**: Get conversation starters based on user context

**Common Tools**:
- `common/auth/dependencies.py` → `get_current_user()`
- `common/i18n/service.py` → `I18nService.t()`
- `common/utils/responses.py` → `success_response()`

**Query Parameters**:
- `language`: "en" | "sv" (default: user's preferred language)
- `includeWellbeing`: "true" | "false"
- `mood`: 1-5 (optional)
- `energy`: 1-10 (optional)
- `stress`: 1-10 (optional)

**Response (200)**:
```json
{
  "success": true,
  "starters": [
    {
      "id": "stress_management",
      "text": "How can I manage stress better?",
      "category": "wellness"
    },
    {
      "id": "goal_setting",
      "text": "I need help setting goals",
      "category": "goals"
    },
    {
      "id": "leadership",
      "text": "How can I improve my leadership style?",
      "category": "leadership"
    },
    {
      "id": "overwhelmed",
      "text": "I'm feeling overwhelmed at work",
      "category": "work"
    }
  ]
}
```

**Implementation Flow**:
1. `get_current_user()` - Get authenticated user
2. Get language from query or user profile
3. `coach_service.get_conversation_starters(context, language)` - Get starters
4. Return starters

---

### 17. GET /api/dashboard

**Purpose**: Get aggregated dashboard data

**Common Tools**:
- `common/auth/dependencies.py` → `get_current_user()`
- `common/utils/responses.py` → `success_response()`

**Response (200)**:
```json
{
  "success": true,
  "data": {
    "user": {
      "firstName": "John",
      "displayName": "John Doe"
    },
    "checkin": {
      "hasCheckedInToday": true,
      "streak": {
        "current": 7,
        "longest": 21
      },
      "recentMood": 4
    },
    "coach": {
      "exchangesRemaining": 12,
      "dailyLimit": 15
    },
    "circles": {
      "activeGroups": 1,
      "pendingInvitations": 0
    }
  }
}
```

**Implementation Flow**:
1. `get_current_user()` - Get authenticated user
2. Parallel queries:
   - `CheckIn.find_one(user_id, today)` - Today's check-in
   - `CheckIn.calculate_streak(user_id)` - Streak data
   - `User.coach_exchanges` - Remaining quota
   - `CircleGroup.count(user_id)` - Active groups
   - `CircleInvitation.count(email, status="pending")` - Pending invitations
3. Return aggregated data

---

### 18. GET /api/hub/organization

**Purpose**: Get organization details (hub admin or org admin)

**Common Tools**:
- `common/auth/dependencies.py` → `get_current_user()`
- `common/utils/responses.py` → `success_response()`

**Response (200)**:
```json
{
  "success": true,
  "data": {
    "organization": {
      "id": "507f1f77bcf86cd799439011",
      "name": "Acme Corporation",
      "domain": "acme.com",
      "memberCount": 150,
      "createdAt": "2023-06-15T10:00:00Z"
    }
  }
}
```

**Implementation Flow**:
1. `get_current_user()` - Get authenticated user
2. Find organization where user is admin
3. Get member count
4. Return organization data

---

### 19. GET /api/hub/members

**Purpose**: Get organization members (hub admin or org admin)

**Common Tools**:
- `common/auth/dependencies.py` → `get_current_user()`
- `common/utils/responses.py` → `success_response()`

**Query Parameters**:
- `limit`: Number of members (default 50)
- `offset`: Pagination offset (default 0)
- `status`: Filter by status ("active", "invited", etc.)

**Response (200)**:
```json
{
  "success": true,
  "data": {
    "members": [
      {
        "id": "507f1f77bcf86cd799439011",
        "email": "user@acme.com",
        "name": "John Doe",
        "role": "member",
        "status": "active",
        "joinedAt": "2023-08-01T10:00:00Z"
      }
    ],
    "pagination": {
      "total": 150,
      "limit": 50,
      "offset": 0,
      "hasMore": true
    }
  }
}
```

**Implementation Flow**:
1. `get_current_user()` - Get authenticated user
2. Verify user is org admin
3. `OrganizationMember.find(organization_id).skip(offset).limit(limit)` - Get members
4. Return paginated member list

---

### 20. GET /api/learning/modules

**Purpose**: Get available learning modules

**Common Tools**:
- `common/auth/dependencies.py` → `get_current_user()`
- `common/i18n/service.py` → Localize content
- `common/utils/responses.py` → `success_response()`

**Query Parameters**:
- `language`: "en" | "sv"
- `category`: Filter by category

**Response (200)**:
```json
{
  "success": true,
  "data": {
    "modules": [
      {
        "id": "mod_stress_101",
        "title": "Understanding Stress",
        "description": "Learn about the science of stress and its effects",
        "category": "wellness",
        "contentType": "audio",
        "lengthMinutes": 15,
        "status": "active"
      }
    ]
  }
}
```

**Implementation Flow**:
1. `get_current_user()` - Get authenticated user
2. Get language from query or user profile
3. `ContentItem.find(status="active")` - Get active content
4. Localize titles based on language
5. Return modules

---

### 21. PUT /api/profile

**Purpose**: Update user profile

**Common Tools**:
- `common/auth/dependencies.py` → `get_current_user()`
- `common/utils/responses.py` → `success_response()`

**Request**:
```json
{
  "firstName": "John",
  "lastName": "Doe",
  "jobTitle": "Engineering Manager",
  "leadershipLevel": "mid",
  "preferredLanguage": "en",
  "timezone": "Europe/Stockholm"
}
```

**Response (200)**:
```json
{
  "success": true,
  "message": "Profile updated successfully",
  "data": {
    "user": {
      "id": "507f1f77bcf86cd799439011",
      "email": "user@example.com",
      "profile": {
        "firstName": "John",
        "lastName": "Doe",
        "jobTitle": "Engineering Manager",
        "leadershipLevel": "mid",
        "preferredLanguage": "en",
        "timezone": "Europe/Stockholm"
      }
    }
  }
}
```

**Implementation Flow**:
1. `get_current_user()` - Get authenticated user
2. Validate allowed fields
3. `user.profile.update(fields)` - Update profile
4. `user.save()` - Save changes
5. Return updated user

---

### 22. POST /api/profile/avatar

**Purpose**: Upload profile avatar

**Common Tools**:
- `common/auth/dependencies.py` → `get_current_user()`
- `common/utils/responses.py` → `success_response()`

**Request**: `multipart/form-data` with `avatar` file

**Response (200)**:
```json
{
  "success": true,
  "message": "Avatar uploaded successfully",
  "data": {
    "avatarUrl": "https://storage.example.com/avatars/507f1f77bcf86cd799439011.jpg"
  }
}
```

**Implementation Flow**:
1. `get_current_user()` - Get authenticated user
2. Validate file type (jpg, png, gif)
3. Validate file size (< 5MB)
4. Upload to storage (FAL.ai or local)
5. Update `user.profile.avatar_url`
6. Return avatar URL

---

### 23. PUT /api/profile/avatar (remove)

**Purpose**: Remove profile avatar

**Common Tools**:
- `common/auth/dependencies.py` → `get_current_user()`
- `common/utils/responses.py` → `success_response()`

**Request**: Empty body

**Response (200)**:
```json
{
  "success": true,
  "message": "Avatar removed successfully"
}
```

**Implementation Flow**:
1. `get_current_user()` - Get authenticated user
2. Delete file from storage if exists
3. Set `user.profile.avatar_url = None`
4. Return success

---

### 24. GET /api/progress/stats

**Purpose**: Get progress statistics

**Common Tools**:
- `common/auth/dependencies.py` → `get_current_user()`
- `common/utils/responses.py` → `success_response()`

**Response (200)**:
```json
{
  "success": true,
  "data": {
    "streak": {
      "current": 7,
      "longest": 21
    },
    "totalCheckIns": 156,
    "averages": {
      "mood": 3.8,
      "physicalEnergy": 6.5,
      "mentalEnergy": 6.2,
      "sleep": 3.9,
      "stress": 5.1
    },
    "trends": {
      "mood": "improving",
      "energy": "stable",
      "stress": "declining"
    },
    "coachingStats": {
      "totalConversations": 45,
      "topTopics": ["stress", "delegation", "communication"]
    }
  }
}
```

**Implementation Flow**:
1. `get_current_user()` - Get authenticated user
2. `progress_service.get_stats(user_id)` - Get calculated stats
3. Return stats

---

### 25. GET /api/progress/insights

**Purpose**: Get AI-generated insights

**Common Tools**:
- `common/auth/dependencies.py` → `get_current_user()`
- `common/ai/base.py` → `AIProvider.chat()` (for generating insights)
- `common/i18n/service.py` → Localize insights
- `common/utils/responses.py` → `success_response()`

**Query Parameters**:
- `generate`: "true" | "false" - Generate new insights (default true)
- `limit`: Number of insights (default 10, max 20)

**Response (200)**:
```json
{
  "success": true,
  "data": {
    "insights": [
      {
        "id": "507f1f77bcf86cd799439011",
        "type": "pattern",
        "trigger": "sleep_impact",
        "title": "Sleep Affects Your Energy",
        "body": "We noticed that on days when you rate your sleep higher, your energy levels are 40% better. Consider prioritizing sleep this week.",
        "isRead": false,
        "createdAt": "2024-01-15T08:00:00Z"
      }
    ],
    "unreadCount": 3
  }
}
```

**Implementation Flow**:
1. `get_current_user()` - Get authenticated user
2. `progress_service.get_insights(user_id, generate_new, limit)` - Get insights
3. `progress_service.get_unread_count(user_id)` - Get unread count
4. Return insights with unread count

---

## Common Tools Usage Summary

| Common Module | Used By Endpoints |
|---------------|-------------------|
| `common/auth/dependencies.py` | 24 endpoints (all except /health) |
| `common/auth/jwt_auth.py` | register, login, forgot-password, reset-password |
| `common/ai/base.py` | coach/chat, coach/stream, progress/insights |
| `common/i18n/service.py` | register, coach/*, learning/modules, progress/insights |
| `common/utils/responses.py` | All 25 endpoints |
| `common/utils/exceptions.py` | Auth endpoints, validation errors |
| `common/utils/password.py` | register, reset-password |
| `common/database/mongodb.py` | health, all DB operations |

---

## Pydantic Request/Response Models

### Auth Models
```python
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    organization: str = Field(min_length=2, max_length=100)
    country: str = Field(pattern=r'^[A-Z]{2}$')
    firstName: Optional[str] = Field(None, max_length=50)
    lastName: Optional[str] = Field(None, max_length=50)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    rememberMe: bool = False

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(min_length=8)

class VerifyEmailRequest(BaseModel):
    token: str

class ResendVerificationRequest(BaseModel):
    email: EmailStr
```

### CheckIn Models
```python
class CheckInRequest(BaseModel):
    mood: int = Field(ge=1, le=5)
    physicalEnergy: int = Field(ge=1, le=10)
    mentalEnergy: int = Field(ge=1, le=10)
    sleep: int = Field(ge=1, le=5)
    stress: int = Field(ge=1, le=10)
    notes: Optional[str] = Field(None, max_length=500)

class CheckInMetrics(BaseModel):
    mood: int
    physicalEnergy: int
    mentalEnergy: int
    sleep: int
    stress: int

class CheckInResponse(BaseModel):
    id: str
    date: str
    timestamp: datetime
    metrics: CheckInMetrics
    notes: Optional[str]
```

### Coach Models
```python
class WellbeingContext(BaseModel):
    mood: Optional[int] = None
    energy: Optional[int] = None
    stress: Optional[int] = None
    streak: Optional[int] = None

class CoachContext(BaseModel):
    recentCheckin: Optional[WellbeingContext] = None

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)
    conversationId: Optional[str] = None
    language: Optional[str] = Field(None, pattern=r'^(en|sv)$')
    context: Optional[CoachContext] = None

class SuggestedAction(BaseModel):
    type: str
    label: str

class ChatResponse(BaseModel):
    text: str
    conversationId: str
    topics: List[str]
    suggestedActions: Optional[List[SuggestedAction]] = None
```

### Profile Models
```python
class ProfileUpdateRequest(BaseModel):
    firstName: Optional[str] = Field(None, max_length=50)
    lastName: Optional[str] = Field(None, max_length=50)
    jobTitle: Optional[str] = Field(None, max_length=100)
    leadershipLevel: Optional[str] = Field(None, pattern=r'^(new|mid|senior|executive)$')
    preferredLanguage: Optional[str] = Field(None, pattern=r'^(en|sv)$')
    timezone: Optional[str] = None
```

---

## File Structure

```
back-end/
├── api.py                      # FastAPI entry point
├── common/                     # GENERIC LIBRARY (from Step 3)
│   ├── database/
│   ├── auth/
│   ├── ai/
│   ├── i18n/
│   ├── utils/
│   └── config/
└── app/                        # BRAINBANK-SPECIFIC
    ├── config.py
    ├── models/
    │   ├── user.py
    │   ├── checkin.py
    │   ├── organization.py
    │   ├── circle.py
    │   └── content.py
    ├── routers/
    │   ├── auth.py
    │   ├── admin.py
    │   ├── checkin.py
    │   ├── circles.py
    │   ├── coach.py
    │   ├── dashboard.py
    │   ├── hub.py
    │   ├── learning.py
    │   ├── profile.py
    │   └── progress.py
    ├── services/
    │   ├── coach_service.py
    │   ├── progress_service.py
    │   └── email_service.py
    ├── schemas/                # Pydantic request/response models
    │   ├── auth.py
    │   ├── checkin.py
    │   ├── coach.py
    │   └── profile.py
    ├── dependencies.py         # FastAPI dependencies
    ├── locales/
    │   ├── en/
    │   └── sv/
    └── prompts/
        ├── en/
        └── sv/
```

---

## Implementation Order

1. **api.py** - Main FastAPI app with lifespan, CORS, routers
2. **app/schemas/** - All Pydantic request/response models
3. **app/models/** - Beanie document models
4. **app/dependencies.py** - Auth, AI provider dependencies
5. **app/routers/auth.py** - Auth endpoints (8 endpoints)
6. **app/routers/checkin.py** - Check-in endpoints (2 endpoints)
7. **app/routers/coach.py** - Coach endpoints with streaming (3 endpoints)
8. **app/routers/profile.py** - Profile endpoints (3 endpoints)
9. **app/routers/progress.py** - Progress endpoints (2 endpoints)
10. **app/routers/dashboard.py** - Dashboard endpoint (1 endpoint)
11. **app/routers/circles.py** - Circle endpoints (2 endpoints)
12. **app/routers/hub.py** - Hub admin endpoints (2 endpoints)
13. **app/routers/admin.py** - Admin endpoints (1 endpoint)
14. **app/routers/learning.py** - Learning endpoints (1 endpoint)

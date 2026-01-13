# Step 2: Create mock_api.py

## Overview

Create a FastAPI application that serves mock JSON responses matching the API documentation. This mock server allows frontend development and testing without requiring the full backend infrastructure (MongoDB, Firebase, Claude API).

## Objective

- Serve mock responses for all documented API endpoints
- Match paths exactly as documented in `back-end/docs/architecture/api/`
- Implement SSE streaming simulation for `/api/coach/stream`
- Simulate session/token authentication behavior
- Include Swedish translations for i18n testing
- No database or external service dependencies

## Files to Reference

### API Documentation (JSON structures)
- `back-end/docs/architecture/api/auth.md` - 7 endpoints
- `back-end/docs/architecture/api/admin.md` - 1 endpoint
- `back-end/docs/architecture/api/checkin.md` - 2 endpoints
- `back-end/docs/architecture/api/circles.md` - 2 endpoints
- `back-end/docs/architecture/api/coach.md` - 3 endpoints (includes streaming)
- `back-end/docs/architecture/api/dashboard.md` - 1 endpoint
- `back-end/docs/architecture/api/hub.md` - 2 endpoints
- `back-end/docs/architecture/api/learning.md` - 1 endpoint
- `back-end/docs/architecture/api/profile.md` - 3 endpoints
- `back-end/docs/architecture/api/progress.md` - 2 endpoints

### Streaming Implementation Reference
- `routes/coach.js` - SSE headers and format
- `services/coachService.js` - Chunk types (text, actions, quickReplies, metadata, done)

## Output Structure

```
back-end/
  mock_api.py           # Single file with all mocks and routes
```

## Implementation Details

### 1. FastAPI Application Setup
- Create FastAPI app with CORS middleware
- Configure to run on port 5002 (to avoid conflict with Express on 5001)
- Add health check endpoint

### 2. Mock Data
- Define mock responses as Python dictionaries directly in `mock_api.py`
- No separate JSON files needed
- Include both English and Swedish content where applicable

### 3. Mock Authentication
- Simulate token-based auth with a simple in-memory token store
- Generate mock tokens on login
- Validate tokens on protected endpoints
- Return 401 for invalid/missing tokens

### 4. Route Implementation
For each documented endpoint:
- Create route matching exact path
- Return mock dictionary responses
- Include appropriate status codes
- Check auth token for protected routes

### 5. SSE Streaming Simulation
For `/api/coach/stream`:
- Use `StreamingResponse` from FastAPI
- Yield chunks with ~50-100ms delays between text chunks
- Format: `data: {json}\n\n`
- End with `data: [DONE]\n\n`

## Endpoints to Implement

| Method | Path | Mock Response |
|--------|------|---------------|
| POST | /api/auth/login | User object with session |
| POST | /api/auth/register | Success message |
| POST | /api/auth/forgot-password | Success acknowledgment |
| POST | /api/auth/reset-password | Success acknowledgment |
| POST | /api/auth/verify-email | Success acknowledgment |
| POST | /api/auth/resend-verification | Success acknowledgment |
| POST | /api/auth/logout | Success acknowledgment |
| GET | /api/admin/stats | Platform statistics |
| POST | /api/checkin | Streak and insight |
| GET | /api/checkin/trends | Trend data arrays |
| GET | /api/circles/groups | Groups and meetings |
| GET | /api/circles/invitations | Pending invitations |
| POST | /api/coach/stream | SSE stream simulation |
| POST | /api/coach/chat | Non-streaming response |
| GET | /api/coach/starters | Conversation starters |
| GET | /api/dashboard | Dashboard overview |
| GET | /api/hub/organization | Organization details |
| GET | /api/hub/members | Member list |
| GET | /api/learning/modules | Module list with progress |
| PUT | /api/profile | Updated user profile |
| POST | /api/profile/avatar | Avatar URL |
| PUT | /api/profile/avatar | Success (remove) |
| GET | /api/progress/stats | User statistics |
| GET | /api/progress/insights | AI insights array |

## Dependencies (requirements.txt additions)

```
fastapi
uvicorn[standard]
python-multipart  # For file uploads
```

## Decisions Made

1. Mock authentication will simulate token behavior (generate on login, validate on protected routes)
2. Mock data will include Swedish translations for i18n testing
3. Streaming simulation will use ~50-100ms delays between text chunks

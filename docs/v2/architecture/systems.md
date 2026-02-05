# BrainBank Backend Systems Documentation

This document describes all backend systems, their components, data flows, and interdependencies.

---

## Table of Contents

1. [Authentication & Session System](#1-authentication--session-system)
2. [User Management System](#2-user-management-system)
3. [Check-in System](#3-check-in-system)
4. [AI Coaching System](#4-ai-coaching-system)
5. [Circles & Groups System](#5-circles--groups-system)
6. [Organization System](#6-organization-system)
7. [Calendar Integration System](#7-calendar-integration-system)
8. [Content & Learning System](#8-content--learning-system)
9. [Progress & Insights System](#9-progress--insights-system)
10. [Email System](#10-email-system)
11. [Media Services System](#11-media-services-system)
12. [Internationalization System](#12-internationalization-system)

---

## 1. Authentication & Session System

### Description

Handles user authentication, session management, and security. Implements JWT-based authentication with refresh tokens stored in cookies. Supports multiple concurrent sessions per user with device tracking. Includes GDPR-compliant audit logging for all authentication events.

### Functions

- Register new users with email verification
- Verify email addresses via token
- Login with email/password credentials
- Logout and invalidate sessions
- Refresh access tokens
- Request and complete password reset
- Manage multiple active sessions (view, revoke individually, revoke all)
- Track login attempts and device information
- Rate limit authentication endpoints
- Audit log all authentication events

### Tech Stack

- **JWT**: jsonwebtoken for token generation/verification
- **Bcrypt**: Password hashing (12 salt rounds)
- **Crypto**: SHA-256 for token hashing, random bytes for token generation
- **Express Middleware**: Custom auth middleware chain
- **MongoDB**: Session storage within User document

### Data Flow

```
Registration:
Client → POST /api/auth/register → validateRegistration middleware → authService.register()
→ Hash password (bcrypt) → Create User (pending_verification) → Generate verification token
→ emailService.sendVerificationEmail() → Return success

Login:
Client → POST /api/auth/login → validateLogin middleware → loginLimiter
→ authService.login() → Verify password (bcrypt) → Check account status
→ Create session record → tokenService.generateTokenPair() → Set cookie
→ AuditLog.log('login') → Return tokens + user data

Protected Request:
Client → Request with cookie/header → requireAuth middleware → Extract token
→ tokenService.verifyRefreshToken() → Hash token → Find matching session in User.sessions
→ Check session not expired → Update lastActivityAt → Attach user to req → Next handler
```

### Dependencies

- **User Model**: Stores sessions array, password hash, verification tokens
- **AuditLog Model**: Records all auth events (90-day TTL)
- **Email System**: Sends verification, welcome, password reset emails
- **Token Service**: Generates and validates JWTs

### Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Auth Routes | routes/auth.js | HTTP endpoints |
| Auth Service | services/authService.js | Business logic |
| Token Service | services/tokenService.js | JWT management |
| Auth Middleware | middleware/auth.js | Request authentication |
| Rate Limiter | middleware/rateLimiter.js | Brute force protection |
| Validator | middleware/validator.js | Input validation |
| User Model | models/User.js | Data persistence |
| AuditLog Model | models/AuditLog.js | Event logging |

---

## 2. User Management System

### Description

Manages user profiles, account status, and GDPR compliance features. Handles the user lifecycle from registration through deletion, including consent tracking and data portability.

### Functions

- Store and update user profiles (name, job title, leadership level, timezone, language)
- Track account status (pending_verification, active, suspended, deleted)
- Manage user consents with version tracking
- Handle account deletion with 30-day grace period
- Export user data (GDPR data portability)
- Anonymize user data on deletion
- Track daily coaching exchange quotas

### Tech Stack

- **MongoDB/Mongoose**: User document storage with virtuals and methods
- **Bcrypt**: Password storage
- **Express**: Profile update endpoints

### Data Flow

```
Profile Update:
Client → PUT /api/profile → requireAuth → Validate input → User.findByIdAndUpdate()
→ AuditLog.log('profile_updated') → Return updated profile

Account Deletion:
Client → POST /api/auth/delete-account → requireAuth → sensitiveOpLimiter
→ authService.requestAccountDeletion() → Set deletion.scheduledFor (30 days)
→ emailService.sendDeletionConfirmationEmail() → AuditLog.log('account_deletion_requested')

Deletion Cancellation (on login):
Login attempt → Check user.isPendingDeletion() → If true, cancel deletion
→ Clear deletion fields → AuditLog.log('account_deletion_cancelled')
```

### Dependencies

- **Authentication System**: Provides user identity
- **Email System**: Sends deletion confirmation
- **Audit Log**: Records profile and deletion events

### Components

| Component | Location | Purpose |
|-----------|----------|---------|
| User Model | models/User.js | Core user data storage |
| Auth Service | services/authService.js | Deletion, export logic |
| Profile endpoints | routes/auth.js | Profile HTTP endpoints |

---

## 3. Check-in System

### Description

Daily wellness tracking system that captures mood, energy levels, sleep quality, and stress. Supports streak tracking, historical analysis, and trend detection to help users understand their wellbeing patterns over time.

### Functions

- Submit daily check-in with multiple metrics
- Retrieve today's check-in status
- View check-in history with date filtering and pagination
- Calculate current and longest streaks
- Generate trend analysis (improving, declining, stable)
- Enforce one check-in per user per day

### Tech Stack

- **MongoDB/Mongoose**: Check-in document storage with aggregation pipelines
- **Express**: RESTful endpoints

### Data Flow

```
Submit Check-in:
Client → POST /api/checkin → requireAuth → Validate metrics
→ CheckIn.create({ userId, date, metrics }) → Compound index ensures uniqueness
→ Trigger insight generation (if streak milestone) → Return check-in data

Get Trends:
Client → GET /api/checkin/trends?period=30 → requireAuth
→ CheckIn.getTrends(userId, period) → Aggregate pipeline calculates averages
→ Compare recent vs earlier periods → Return trend direction per metric

Calculate Streak:
CheckIn.calculateStreak(userId) → Find all check-ins sorted by date
→ Iterate checking consecutive days → Return { current, longest }
```

### Dependencies

- **Authentication System**: User identity for ownership
- **Insights System**: Triggers streak/pattern insights
- **User Model**: Links check-ins to users

### Components

| Component | Location | Purpose |
|-----------|----------|---------|
| CheckIn Model | models/CheckIn.js | Data storage, calculations |
| CheckIn Routes | routes/checkin.js | HTTP endpoints |

### Metrics Tracked

| Metric | Range | Description |
|--------|-------|-------------|
| mood | 1-5 | Overall mood rating |
| physicalEnergy | 1-10 | Physical energy level |
| mentalEnergy | 1-10 | Mental energy level |
| sleep | 1-5 | Sleep quality |
| stress | 1-10 | Stress level (higher = more stress) |

---

## 4. AI Coaching System

### Description

AI-powered coaching using Claude (Anthropic) for personalized guidance. Manages coaching conversations, extracts micro-commitments for follow-up, and tracks commitment completion. Supports streaming responses for real-time conversation experience.

### Functions

- Send messages to Claude AI and receive responses
- Stream AI responses for real-time display
- Extract micro-commitments from coaching conversations
- Track commitment status (active, completed, expired, dismissed)
- Schedule automatic follow-ups (14 days default)
- Record reflection notes and helpfulness ratings
- Categorize commitments by topic (delegation, stress, communication, etc.)
- Track daily coaching exchange quotas per user

### Tech Stack

- **Anthropic SDK**: Claude API integration (claude-sonnet-4-5-20250929)
- **AsyncGenerator**: Streaming response handling
- **MongoDB**: Commitment and conversation storage

### Data Flow

```
Coaching Conversation:
Client → POST /api/chat → requireAuth → Check daily quota
→ claudeService.sendMessage(message, systemPrompt) → Anthropic API call
→ Parse response for commitments → CoachCommitment.createCommitment()
→ Increment user.coachExchanges.count → Return AI response

Streaming Response:
Client → POST /api/chat/stream → requireAuth
→ claudeService.streamMessage(message, systemPrompt) → AsyncGenerator
→ Yield chunks as Server-Sent Events → Client renders progressively

Commitment Follow-up:
Scheduled job or next conversation → CoachCommitment.getDueFollowUps(userId)
→ Surface commitments in conversation context → User marks completed
→ CoachCommitment.markCompleted(rating, notes) → Update stats
```

### Dependencies

- **Authentication System**: User identity
- **User Model**: Daily quota tracking (coachExchanges)
- **External**: Anthropic Claude API

### Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Claude Service | services/claudeService.js | API integration |
| Coach Service | services/coachService.js | Business logic |
| CoachCommitment Model | models/CoachCommitment.js | Commitment storage |
| Coach Routes | routes/coach.js | HTTP endpoints |
| Chat Routes | routes/api.js | Chat endpoints |

### Commitment Topics

- delegation
- stress
- team_dynamics
- communication
- leadership
- time_management
- work_life_balance
- decision_making
- conflict_resolution
- other

---

## 5. Circles & Groups System

### Description

Leadership circles for peer group discussions. Manages the full lifecycle from pool creation, member invitation, group assignment, to meeting scheduling. Designed for cohort-based learning with small groups (3-4 members).

### Functions

- Create and manage circle pools (cohorts)
- Send bulk invitations via CSV upload
- Track invitation status (pending, accepted, declined, expired)
- Automatically assign accepted members to groups
- Generate group names (Circle A, Circle B, etc.)
- Schedule meetings with calendar integration
- Track meeting attendance
- Record meeting notes
- Calculate group and pool statistics

### Tech Stack

- **MongoDB/Mongoose**: Pool, group, invitation, meeting storage
- **Express**: RESTful endpoints
- **Crypto**: Secure invitation token generation

### Data Flow

```
Pool Creation:
Admin → POST /api/circles/pools → requireAuth → Validate org membership
→ CirclePool.create({ organizationId, name, topic, targetGroupSize })
→ Status: 'draft' → Return pool

Invitation Flow:
Admin → POST /api/circles/pools/:id/invitations → Parse CSV or JSON
→ For each email: CircleInvitation.create({ token, email, poolId })
→ emailService.sendCircleInvitation() → Update pool stats (totalInvited)

Acceptance Flow:
Invitee → GET /api/circles/invitations/:token → Validate token not expired
→ POST /api/circles/invitations/:token/accept → CircleInvitation.accept(userId)
→ Increment pool.stats.totalAccepted

Group Assignment:
Admin → POST /api/circles/pools/:id/assign → Verify pool.canAssign()
→ Get all accepted invitations → circleService.assignGroups()
→ Algorithm creates balanced groups → CircleGroup.create() for each
→ Pool status → 'active'

Meeting Scheduling:
Member → POST /api/circles/groups/:id/meetings → Validate membership
→ CircleMeeting.create({ groupId, scheduledAt, duration })
→ For each member: googleCalendarService.createEvent()
→ Store calendarEvents[] with eventIds
```

### Dependencies

- **Authentication System**: User identity, org membership
- **Organization System**: Pool belongs to organization
- **Calendar System**: Meeting scheduling, availability
- **Email System**: Invitation emails

### Components

| Component | Location | Purpose |
|-----------|----------|---------|
| CirclePool Model | models/CirclePool.js | Cohort management |
| CircleGroup Model | models/CircleGroup.js | Group storage |
| CircleInvitation Model | models/CircleInvitation.js | Invitation tracking |
| CircleMeeting Model | models/CircleMeeting.js | Meeting scheduling |
| Circle Service | services/circleService.js | Business logic |
| Circles Routes | routes/circles.js | HTTP endpoints |

### Pool Status Lifecycle

```
draft → inviting → assigning → active → completed
                                    ↓
                               cancelled
```

---

## 6. Organization System

### Description

Multi-tenant organization management. Users belong to organizations, which own circle pools and manage member access. Supports admin and member roles with domain-based organization matching.

### Functions

- Create organizations with initial admin
- Add and remove organization members
- Assign admin roles
- Track member status (active, inactive, removed)
- Match organizations by email domain
- Manage organization settings (timezone, meeting defaults)

### Tech Stack

- **MongoDB/Mongoose**: Organization and membership storage
- **Express**: RESTful endpoints

### Data Flow

```
Organization Creation:
User → POST /api/organizations → requireAuth → Validate input
→ Organization.create({ name, createdBy })
→ OrganizationMember.create({ role: 'admin', userId, organizationId })

Member Addition:
Admin → POST /api/organizations/:id/members → Verify isUserOrgAdmin()
→ OrganizationMember.create({ role: 'member', invitedBy })
→ Return member record

Access Check:
Any org endpoint → OrganizationMember.isUserOrgMember(userId, orgId)
→ Returns boolean for authorization
```

### Dependencies

- **Authentication System**: User identity
- **Circles System**: Pools belong to organizations

### Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Organization Model | models/Organization.js | Org data storage |
| OrganizationMember Model | models/OrganizationMember.js | Membership join table |
| Organization Service | services/organizationService.js | Business logic |
| Organizations Routes | routes/organizations.js | HTTP endpoints |

---

## 7. Calendar Integration System

### Description

Google Calendar OAuth integration for meeting scheduling and availability detection. Stores encrypted OAuth tokens and manages calendar events for circle meetings.

### Functions

- OAuth 2.0 flow with Google Calendar
- Store encrypted access and refresh tokens
- Create calendar events with Google Meet links
- Update and delete calendar events
- Detect user availability from calendar
- Find common availability across group members
- Track user weekly availability preferences

### Tech Stack

- **Google Calendar API**: Calendar operations
- **OAuth 2.0**: Authentication flow
- **AES-256-CBC**: Token encryption with random IV
- **MongoDB**: Token and availability storage

### Data Flow

```
OAuth Connection:
User → GET /api/calendar/auth/google → Generate OAuth URL with state
→ Redirect to Google → User consents → Google redirects to callback

OAuth Callback:
Google → GET /api/calendar/auth/google/callback → Exchange code for tokens
→ CalendarConnection.upsertConnection() → Encrypt tokens (AES-256-CBC)
→ Store encrypted tokens → Redirect to success page

Event Creation:
Meeting scheduled → googleCalendarService.createEvent(connection, meeting)
→ Decrypt tokens → Google API call → Return eventId and meetLink
→ CircleMeeting.addCalendarEvent({ userId, eventId })

Availability Check:
Schedule meeting → googleCalendarService.getFreeBusy(connection, timeRange)
→ Returns busy slots → UserAvailability.findCommonAvailability(userIds)
→ Intersect with weekly preferences → Return available slots
```

### Dependencies

- **Authentication System**: User identity
- **Circles System**: Meeting creation triggers calendar events
- **External**: Google Calendar API

### Components

| Component | Location | Purpose |
|-----------|----------|---------|
| CalendarConnection Model | models/CalendarConnection.js | Token storage |
| UserAvailability Model | models/UserAvailability.js | Weekly preferences |
| Google Calendar Service | services/googleCalendarService.js | API integration |
| Calendar Routes | routes/calendar.js | HTTP endpoints |

---

## 8. Content & Learning System

### Description

Microlearning content management for leadership development. Hub admins manage global content that users consume. Includes audio generation for content items.

### Functions

- Create and manage learning content
- Publish/unpublish content items
- List available content with filtering
- Retrieve individual content details
- Generate and serve audio versions (TTS)
- Track content versions and migrations

### Tech Stack

- **MongoDB**: Content storage (hub database)
- **Express**: RESTful endpoints
- **TTS Service**: Audio generation

### Data Flow

```
Content Creation (Hub Admin):
Hub Admin → POST /api/hub/content → requireHubAdmin
→ ContentItem.create({ title, body, status: 'draft' })
→ Return content item

Content Publishing:
Hub Admin → PUT /api/hub/content/:id/publish → Update status: 'published'
→ Content now visible to users

Content Retrieval:
User → GET /api/learning/content → requireAuth
→ ContentItem.find({ status: 'published' }) → Return content list

Audio Generation:
User → GET /api/audio/:contentId/:lang → Check cache
→ If not cached: ttsService.generateAudio(text, lang)
→ Store audio file → Stream audio response
```

### Dependencies

- **Hub Auth System**: Admin access control
- **TTS Service**: Audio generation
- **Internationalization**: Multi-language support

### Components

| Component | Location | Purpose |
|-----------|----------|---------|
| ContentItem Model | models/hub/ContentItem.js | Content storage |
| HubSettings Model | models/hub/HubSettings.js | Global settings |
| HubAdmin Model | models/hub/HubAdmin.js | Admin identification |
| Hub Routes | routes/hub.js | Admin endpoints |
| Learning endpoints | routes/api.js | User endpoints |
| TTS Service | services/ttsService.js | Audio generation |

---

## 9. Progress & Insights System

### Description

Analytics and insights generation for user progress. Creates AI-generated and rule-based insights based on user activity patterns, streaks, and trends.

### Functions

- Generate streak milestone insights
- Detect activity patterns and trends
- Create personalized recommendations
- Track insight read status
- Auto-expire old insights (TTL)
- Calculate progress metrics
- Prevent duplicate insights

### Tech Stack

- **MongoDB**: Insight storage with TTL index
- **Express**: RESTful endpoints

### Data Flow

```
Insight Generation (Rule-based):
Check-in submitted → Check for streak milestones
→ If milestone: Insight.hasRecentInsight(trigger) → If not recent:
→ Insight.create({ type: 'streak', trigger, title, body, expiresAt })

Insight Retrieval:
User → GET /api/insights → requireAuth → Insight.getActiveInsights(userId)
→ Filter by not expired, not read (optional) → Return insights

Mark Read:
User → PUT /api/insights/:id/read → Insight.markAsRead()
→ Set isRead: true → Return updated insight
```

### Dependencies

- **Check-in System**: Triggers streak insights
- **Coaching System**: May trigger recommendation insights
- **Authentication System**: User identity

### Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Insight Model | models/Insight.js | Insight storage |
| Progress Service | services/progressService.js | Analytics logic |
| Progress Routes | routes/progress.js | HTTP endpoints |

### Insight Types

| Type | Trigger Example | Description |
|------|-----------------|-------------|
| streak | 7-day streak | Milestone achievements |
| pattern | consistent morning check-ins | Behavioral patterns |
| trend | mood improving | Metric trends |
| recommendation | coaching suggestion | AI recommendations |

---

## 10. Email System

### Description

Transactional email delivery supporting multiple providers. Sends authentication emails, notifications, and circle invitations with Nordic-inspired design.

### Functions

- Send email verification links
- Send welcome emails after verification
- Send password reset links
- Send password change confirmations
- Send account deletion confirmations
- Send circle pool invitations
- Send meeting notifications
- Support multiple transport modes (console, Resend API, SMTP)
- Generate HTML and plain text versions

### Tech Stack

- **Resend API**: Primary production email delivery
- **SMTP**: Legacy/fallback transport
- **Console**: Development mode logging
- **HTML/CSS**: Email templating

### Data Flow

```
Send Email:
Trigger (registration, reset, etc.) → emailService.sendXxxEmail(email, data)
→ Load email translations (i18n) → Render HTML template
→ Select transport based on EMAIL_MODE → Send via Resend API or SMTP
→ Return success/failure

Email Transport Selection:
EMAIL_MODE=console → Log to console (development)
EMAIL_MODE=resend → HTTP POST to Resend API
EMAIL_MODE=smtp → SMTP transport with TLS
```

### Dependencies

- **Internationalization System**: Email translations
- **Authentication System**: Triggers auth emails
- **Circles System**: Triggers invitation emails
- **External**: Resend API or SMTP server

### Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Email Service | services/emailService.js | All email logic |
| Email Translations | locales/emails/{lang}.json | Translated content |

### Email Types

| Email | Trigger | Purpose |
|-------|---------|---------|
| Verification | Registration | Confirm email ownership |
| Welcome | Email verified | Onboard new user |
| Password Reset | Forgot password | Reset credentials |
| Password Changed | Reset complete | Security notification |
| Deletion Confirmation | Deletion request | Confirm 30-day grace |
| Circle Invitation | Pool invitation | Join leadership circle |
| Meeting Scheduled | Meeting created | Calendar notification |

---

## 11. Media Services System

### Description

AI-powered media generation including images (FAL.ai) and text-to-speech audio. Supports content enhancement and accessibility features.

### Functions

- Generate images from text prompts
- Fast image generation mode
- Transform existing images
- Provide image size presets
- Generate audio from text (TTS)
- Cache generated audio files
- Support multiple languages for TTS

### Tech Stack

- **FAL.ai SDK**: Image generation API
- **TTS Service**: Text-to-speech (provider TBD)
- **File System**: Audio file caching

### Data Flow

```
Image Generation:
User → POST /api/image/generate → requireAuth
→ imageService.generateImage(prompt, options) → FAL.ai API call
→ Return image URL

Fast Generation:
User → POST /api/image/generate-fast → imageService.generateFast(prompt)
→ Optimized FAL.ai call → Return image URL

Audio Generation:
Request → GET /api/audio/:contentId/:lang → Check cache
→ If cached: stream file → If not: ttsService.generate(text, lang)
→ Save to cache → Stream audio
```

### Dependencies

- **Authentication System**: User identity
- **Content System**: Content for audio generation
- **External**: FAL.ai API, TTS provider

### Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Image Service | services/imageService.js | FAL.ai integration |
| TTS Service | services/ttsService.js | Audio generation |
| Media endpoints | routes/api.js | HTTP endpoints |

---

## 12. Internationalization System

### Description

Multi-language support for the application. Manages translations, language detection, and provides middleware for request-scoped translation functions.

### Functions

- Load translation files from JSON
- Translate keys with dot notation access
- Support variable interpolation ({{varName}})
- Detect language from user profile or Accept-Language header
- Provide request-scoped translation function (req.t())
- Support pluralization
- Fallback to default language for missing translations

### Tech Stack

- **Express Middleware**: Language detection and injection
- **JSON Files**: Translation storage
- **Node.js**: File system for loading translations

### Data Flow

```
Middleware Setup:
Request → i18nService.middleware() → getLanguageFromRequest(req)
→ Priority: user.profile.preferredLanguage > Accept-Language > 'en'
→ Attach req.language and req.t() → Next handler

Translation:
Handler code → req.t('validation.email.required', { field: 'email' })
→ Load translation file for req.language → Traverse dot notation path
→ Interpolate variables → Return translated string

Email Translation:
emailService → Load locales/emails/{lang}.json
→ Access keys like 'verification.subject' → Return translated content
```

### Dependencies

- **User Model**: Stores preferredLanguage in profile
- **All Systems**: Use translations for user-facing content

### Components

| Component | Location | Purpose |
|-----------|----------|---------|
| i18n Service | services/i18nService.js | Translation logic |
| UI Translations | public/locales/{lang}/*.json | Frontend strings |
| Email Translations | locales/emails/{lang}.json | Email content |

### Supported Languages

| Code | Language |
|------|----------|
| en | English (default) |
| sv | Swedish |

---

## System Interdependencies

```
                    ┌─────────────────────────────────────┐
                    │      Authentication System          │
                    │  (auth, tokens, sessions, audit)    │
                    └─────────────────┬───────────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
              ▼                       ▼                       ▼
    ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
    │  User Management │     │  Organization   │     │   Hub Admin     │
    │     System       │     │     System      │     │    System       │
    └────────┬────────┘     └────────┬────────┘     └────────┬────────┘
             │                       │                       │
             │              ┌────────┴────────┐              │
             │              │                 │              │
             ▼              ▼                 ▼              ▼
    ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
    │   Check-in      │  │    Circles      │  │    Content      │
    │    System       │  │    System       │  │    System       │
    └────────┬────────┘  └────────┬────────┘  └────────┬────────┘
             │                    │                    │
             │           ┌────────┴────────┐           │
             │           │                 │           │
             ▼           ▼                 ▼           ▼
    ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
    │   Insights      │  │    Calendar     │  │     Media       │
    │    System       │  │    System       │  │    Services     │
    └─────────────────┘  └─────────────────┘  └─────────────────┘

                    ┌─────────────────────────────────────┐
                    │         AI Coaching System          │
                    │    (Claude, commitments, follow-up) │
                    └─────────────────────────────────────┘
                              Consumes: User, Check-in data
                              Produces: Commitments, Insights

    ┌──────────────────────────────────────────────────────────┐
    │               Cross-Cutting Systems                       │
    ├─────────────────┬─────────────────┬──────────────────────┤
    │  Email System   │   i18n System   │   Rate Limiting      │
    │ (notifications) │ (translations)  │   (security)         │
    └─────────────────┴─────────────────┴──────────────────────┘
```

---

## External Service Dependencies

| Service | System | Purpose |
|---------|--------|---------|
| MongoDB (Primary) | All | Main data storage |
| MongoDB (Hub) | Hub/Content | Admin data storage |
| Anthropic Claude | AI Coaching | Conversation AI |
| FAL.ai | Media Services | Image generation |
| Google Calendar | Calendar | Meeting scheduling |
| Resend/SMTP | Email | Email delivery |
| TTS Provider | Media Services | Audio generation |

---

## Configuration Summary

### Required Environment Variables

| Variable | System | Purpose |
|----------|--------|---------|
| MONGODB_URI | All | Primary database |
| JWT_SECRET | Authentication | Token signing |
| CLAUDE_API_KEY | AI Coaching | Anthropic API |
| EMAIL_MODE | Email | Transport selection |

### Optional Environment Variables

| Variable | System | Default |
|----------|--------|---------|
| HUB_MONGODB_URI | Hub/Content | Falls back to primary |
| PORT | Server | 5001 |
| BCRYPT_SALT_ROUNDS | Auth | 12 |
| JWT_ACCESS_EXPIRES | Auth | 15m |
| JWT_REFRESH_EXPIRES | Auth | 7d |
| RESEND_API_KEY | Email | Required if mode=resend |
| GOOGLE_CALENDAR_CLIENT_ID | Calendar | Required for calendar |
| CALENDAR_ENCRYPTION_KEY | Calendar | Required for calendar |

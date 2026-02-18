# Backend Refactor Brainstorm

## 1. Common Components (Shared Infrastructure)

These are patterns/utilities used across multiple systems that could be consolidated.

### 1.1 Database Layer
- **MongoDB connections** - Two separate connections (main + hub) with similar config
- **Mongoose model patterns** - Every model uses: virtuals, instance methods, static methods, indexes
- **Common model behaviors** - `toPublicJSON()`, `isActive()`, status enums, timestamps
- **TTL indexes** - Used in AuditLog (90 days), Insight (variable)

### 1.2 Authentication & Authorization
- **Token generation** - JWT access/refresh, verification tokens, reset tokens, invitation tokens
- **Token hashing** - SHA-256 pattern repeated
- **Auth middleware chain** - requireAuth → requireVerified → requireActive
- **Session management** - Stored in User.sessions array

### 1.3 Rate Limiting
- **Multiple limiters** with same structure but different values
- **Key generators** - by email, by IP, by user ID
- All defined in one file but could be more configurable

### 1.4 Input Validation
- **Validation functions** - Similar patterns for email, password, strings
- **Sanitization** - HTML entity escaping, length limits
- **Error message formatting** - Repeated across validators

### 1.5 API Response Patterns
- **Success format**: `{ success: true, data, message }`
- **Error format**: `{ success: false, error, code }`
- **Status codes** - Manually set in each route

### 1.6 Email Delivery
- **Template rendering** - HTML generation with similar structure
- **Transport abstraction** - console/resend/smtp switching
- **Translation loading** - i18n for email content

### 1.7 Audit Logging
- **AuditLog.log()** - Called from auth events, profile updates, etc.
- **Metadata extraction** - IP, user agent, device info
- **Action types** - Enum of 16 actions

### 1.8 Encryption
- **AES-256-CBC** - Used for calendar tokens
- **bcrypt** - Used for passwords
- **crypto.randomBytes** - Used for token generation

### 1.9 Error Handling
- **Try/catch patterns** - Repeated in every route handler
- **Error codes** - Semantic codes like EMAIL_EXISTS, INVALID_TOKEN
- **Logging** - console.error with context

---

## 2. Long Pipelines (Multi-Step Workflows)

These are complex flows that span multiple systems and could benefit from explicit orchestration.

### 2.1 User Registration Pipeline
```
Register Request
    → Validate input (email, password, consents)
    → Check email not taken
    → Hash password (bcrypt)
    → Create User (pending_verification)
    → Generate verification token
    → Send verification email
    → Log audit event
    → Return success

Email Verification
    → Validate token
    → Update status → active
    → Clear verification fields
    → Send welcome email
    → Log audit event
```
**Systems involved**: Auth, User, Email, Audit

### 2.2 Password Reset Pipeline
```
Reset Request
    → Validate email format
    → Find user by email
    → Generate reset token (1h expiry)
    → Hash and store token
    → Send reset email
    → Log audit event

Reset Completion
    → Validate token not expired
    → Hash new password
    → Clear reset fields
    → Invalidate ALL sessions (security)
    → Send password changed email
    → Log audit event
```
**Systems involved**: Auth, User, Email, Audit

### 2.3 Account Deletion Pipeline (GDPR)
```
Deletion Request
    → Schedule deletion (30 days)
    → Send confirmation email
    → Log audit event

Grace Period
    → If user logs in → Cancel deletion, log event

After 30 Days
    → Export data (if requested)
    → Anonymize audit logs
    → Delete user document
    → Log final audit event
```
**Systems involved**: Auth, User, Email, Audit

### 2.4 Circle Pool Lifecycle Pipeline
```
Creation
    → Create pool (draft status)
    → Set invitation settings

Invitation Phase
    → Bulk import emails (CSV/JSON)
    → Generate unique tokens per invitation
    → Send invitation emails
    → Track invitation stats
    → Handle accepts/declines
    → Update pool stats

Assignment Phase
    → Verify minimum accepted
    → Run group assignment algorithm
    → Create CircleGroup records
    → Notify members of groups
    → Update pool status → active

Active Phase
    → Schedule meetings
    → Track attendance
    → Record notes

Completion
    → Mark pool as completed
    → Generate summary stats
```
**Systems involved**: Circles, Organization, Email, Calendar

### 2.5 Meeting Scheduling Pipeline
```
Schedule Request
    → Validate user is group member
    → Check group availability (UserAvailability)
    → Check calendar availability (Google Calendar)
    → Create CircleMeeting record

Calendar Sync (for each member)
    → Check CalendarConnection exists
    → Decrypt OAuth tokens
    → Create Google Calendar event
    → Store eventId in meeting.calendarEvents[]
    → Generate Google Meet link

Notifications
    → Send meeting scheduled emails
    → Update meeting attendance records
```
**Systems involved**: Circles, Calendar, Email

### 2.6 Coaching Conversation Pipeline
```
Message Received
    → Validate user quota
    → Build conversation context
    → Send to Claude API
    → Parse response

Commitment Extraction
    → Identify micro-commitments in response
    → Create CoachCommitment records
    → Set 14-day follow-up dates
    → Categorize by topic

Follow-up Flow
    → Surface due commitments in next conversation
    → User marks complete/dismissed
    → Record reflection notes
    → Update completion stats
```
**Systems involved**: Coaching, AI (Claude), User

### 2.7 Check-in → Insights Pipeline
```
Check-in Submission
    → Validate metrics
    → Store check-in
    → Calculate streak

Insight Generation
    → Check streak milestones (7, 14, 30, etc.)
    → Analyze trends (compare periods)
    → Detect patterns
    → Create Insight records if warranted
    → Prevent duplicate insights
```
**Systems involved**: Check-in, Insights

### 2.8 Calendar OAuth Connection Pipeline
```
Initiate OAuth
    → Generate state parameter
    → Build OAuth URL with scopes
    → Redirect to Google

OAuth Callback
    → Validate state parameter
    → Exchange code for tokens
    → Encrypt tokens (AES-256-CBC)
    → Upsert CalendarConnection
    → Redirect to success page

Token Refresh (when expired)
    → Decrypt refresh token
    → Request new access token
    → Re-encrypt and store
    → Update expiry
```
**Systems involved**: Calendar, Encryption

### 2.9 Content Publishing Pipeline
```
Content Creation
    → Hub admin creates item (draft)
    → Add translations
    → Preview content

Publishing
    → Update status → published
    → Content visible to users

Audio Generation (on demand)
    → Check audio cache
    → If not cached: TTS generation
    → Store audio file
    → Serve to user
```
**Systems involved**: Content, Media (TTS), Hub Auth

---

## 3. Simplification Opportunities

### 3.1 Consolidate Common Patterns

| Pattern | Current State | Could Be |
|---------|---------------|----------|
| Token generation | Scattered across services | Single TokenFactory |
| API responses | Manual in each route | Response helper middleware |
| Error handling | Try/catch in every handler | Error boundary middleware |
| Audit logging | Direct calls | Decorator/middleware pattern |
| Model methods | Repeated (toPublicJSON, isActive) | Base model class or mixin |

### 3.2 Extract Reusable Modules

- **CryptoModule** - Token generation, hashing, encryption in one place
- **ResponseModule** - Success/error response builders
- **ValidationModule** - Common validators with consistent error formats
- **PaginationModule** - Offset/limit patterns used in history queries

### 3.3 Pipeline Orchestration

Some pipelines are implicitly defined across multiple files. Could benefit from:
- Explicit workflow definitions
- State machine for status transitions (pool lifecycle, user lifecycle)
- Event-driven architecture (emit events, listeners react)

---

## 4. Questions for Discussion

1. **Should pipelines be explicit?**
   - Currently, pipelines are implicit (spread across routes → services → models)
   - Could use saga pattern, workflow engine, or event sourcing

2. **How to handle dual databases?**
   - Main DB for user data, Hub DB for admin content
   - Could this be simplified to one DB with collections?

3. **Service vs Route responsibility?**
   - Some business logic is in routes, some in services
   - Clear boundary needed

4. **Model complexity?**
   - User model is very large (sessions, consents, verification, deletion, profile)
   - Could split into UserAuth, UserProfile, UserPreferences?

5. **Rate limiting configuration?**
   - Currently hardcoded values
   - Should be configurable per environment?

---

## 5. Next Steps (Not code yet!)

- [ ] Decide on common component extraction strategy
- [ ] Decide which pipelines need explicit orchestration
- [ ] Decide on model simplification approach
- [ ] Decide on service/route boundary rules
- [ ] Prioritize refactoring order

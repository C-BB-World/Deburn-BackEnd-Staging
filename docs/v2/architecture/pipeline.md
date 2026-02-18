# API Pipeline Reference

Maps each documented API endpoint to the class → method chain with parameters and return types.

---

## Auth System

### POST /api/auth/register

```
AuthService.register(
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    organization: str,
    country: str,
    consents: dict
) → User

    → UserService.create_user(email, hashed_password, profile_data) → User
    → TokenService.generate_verification_token(user_id) → str
    → EmailQueue.enqueue(type="verification", to=email, token=token) → None
    → AuditLog.log(action="REGISTER", user_id, metadata) → None

Returns: { success: bool, message: str }
```

### POST /api/auth/login

```
AuthService.login(
    email: str,
    password: str,
    remember_me: bool = False
) → AuthResult

    → UserService.get_by_email(email) → User | None
    → PasswordService.verify(password, user.hashed_password) → bool
    → UserService.check_status(user) → None  # raises if not active
    → SessionService.create_session(user_id, remember_me) → Session
    → AuditLog.log(action="LOGIN", user_id, metadata) → None

Returns: { success: bool, data: { user: UserPublic } }
```

### POST /api/auth/logout

```
AuthService.logout(
    user_id: str,
    session_id: str
) → None

    → SessionService.destroy_session(user_id, session_id) → None
    → AuditLog.log(action="LOGOUT", user_id, metadata) → None

Returns: { success: bool }
```

### POST /api/auth/verify-email

```
AuthService.verify_email(
    token: str
) → None

    → TokenService.validate_verification_token(token) → user_id
    → UserService.activate_user(user_id) → User
    → EmailQueue.enqueue(type="welcome", to=user.email) → None
    → AuditLog.log(action="EMAIL_VERIFIED", user_id) → None

Returns: { success: bool }
```

### POST /api/auth/resend-verification

```
AuthService.resend_verification(
    email: str
) → None

    → UserService.get_by_email(email) → User | None
    → TokenService.generate_verification_token(user_id) → str
    → EmailQueue.enqueue(type="verification", to=email, token=token) → None

Returns: { success: bool }
```

### POST /api/auth/forgot-password

```
AuthService.forgot_password(
    email: str
) → None

    → UserService.get_by_email(email) → User | None
    → TokenService.generate_reset_token(user_id) → str
    → EmailQueue.enqueue(type="password_reset", to=email, token=token) → None
    → AuditLog.log(action="PASSWORD_RESET_REQUESTED", user_id) → None

Returns: { success: bool }
```

### POST /api/auth/reset-password

```
AuthService.reset_password(
    token: str,
    password: str
) → None

    → TokenService.validate_reset_token(token) → user_id
    → PasswordService.hash(password) → str
    → UserService.update_password(user_id, hashed_password) → None
    → SessionService.destroy_all_sessions(user_id) → None
    → EmailQueue.enqueue(type="password_changed", to=user.email) → None
    → AuditLog.log(action="PASSWORD_RESET", user_id) → None

Returns: { success: bool }
```

---

## Profile System

### PUT /api/profile

```
UserService.update_profile(
    user_id: str,
    first_name: str | None,
    last_name: str | None,
    organization: str | None,
    role: str | None,
    bio: str | None
) → User

    → AuditLog.log(action="PROFILE_UPDATED", user_id, changes) → None

Returns: { success: bool, data: { user: UserPublic } }
```

### POST /api/profile/avatar

```
MediaService.upload_avatar(
    user_id: str,
    file: UploadFile
) → str

    → MediaService.validate_image(file) → None
    → MediaService.resize_image(file, max_size=200) → bytes
    → MediaService.save_avatar(user_id, image_data) → str
    → UserService.update_avatar_url(user_id, url) → None

Returns: { success: bool, data: { avatarUrl: str } }
```

### PUT /api/profile/avatar

```
MediaService.remove_avatar(
    user_id: str
) → None

    → MediaService.delete_avatar(user_id) → None
    → UserService.update_avatar_url(user_id, None) → None

Returns: { success: bool }
```

---

## Check-in System

### POST /api/checkin

```
submit_checkin_pipeline(
    user_id: str,
    mood: int,
    physical_energy: int,
    mental_energy: int,
    sleep: int,
    stress: int
) → CheckInResult

    → MetricsValidator.validate(metrics) → None
    → CheckInService.submit_checkin(user_id, metrics) → CheckIn
    → CheckInAnalytics.calculate_streak(user_id) → int
    → CheckinInsightGenerator.generate(user_id, checkin) → CheckinInsight

Returns: { success: bool, data: { streak: int, insight: str, tip: str } }
```

### GET /api/checkin/trends

```
CheckInAnalytics.get_trends(
    user_id: str,
    period: int = 30
) → TrendData

Returns: { success: bool, data: { dataPoints: int, moodValues: list, moodChange: int, energyValues: list, energyChange: int, stressValues: list, stressChange: int } }
```

---

## Progress & Insights System

### GET /api/progress/stats

```
ProgressStatsService.get_summary(
    user_id: str
) → ProgressSummary

    → CheckInAnalytics.calculate_streak(user_id) → int
    → CheckInService.get_total_count(user_id) → int
    → LearningProgressService.get_completed_count(user_id) → int
    → ConversationService.get_session_count(user_id) → int

Returns: { success: bool, data: { streak: int, checkins: int, lessons: int, sessions: int } }
```

### GET /api/progress/insights

```
InsightService.get_user_insights(
    user_id: str
) → list[Insight]

Returns: { success: bool, data: { insights: list[{ title: str, description: str }] } }
```

---

## Content & Learning System

### GET /api/learning/modules

```
get_content_with_progress_pipeline(
    user_id: str
) → list[ContentWithProgress]

    → ContentService.get_published() → list[ContentItem]
    → LearningProgressService.get_user_progress(user_id) → dict[str, int]
    → merge_content_with_progress(content, progress) → list[ContentWithProgress]

Returns: { success: bool, data: { modules: list[{ id, title, description, type, duration, thumbnail, progress }] } }
```

---

## AI Coaching System

### POST /api/coach/stream

```
CoachService.chat(
    user_id: str,
    message: str,
    conversation_id: str | None,
    language: str = "en",
    stream: bool = True
) → Iterator[CoachResponseChunk]

    → CoachService._check_daily_limit(user_id) → bool
    → SafetyChecker.check(message) → SafetyResult
    → [If Level 3] → SafetyChecker.get_crisis_response(language) → CrisisResponse
    → ConversationService.get_or_create(conversation_id, user_id) → Conversation
    → CommitmentService.get_due_followups(user_id) → list[Commitment]
    → CoachService._build_context(user_id, conversation, language) → CoachingContext
    → Agent.generate_coaching_response(context, message, stream=True) → Iterator[str]
    → Agent.extract_topics(message) → list[str]
    → ContentService.get_for_coach(topics, limit=2) → list[ContentItem]
    → CommitmentExtractor.extract(response) → CommitmentData | None
    → [If commitment] → CommitmentService.create_commitment(...) → Commitment
    → ConversationService.add_message(conversation_id, role, content) → None
    → UserService.increment_exchange_count(user_id) → None

Returns: SSE stream { type: "metadata"|"text"|"quickReplies", content }
```

### POST /api/coach/chat

```
CoachService.chat(
    user_id: str,
    message: str,
    conversation_id: str | None,
    language: str = "en",
    stream: bool = False
) → CoachResponse

    # Same pipeline as /stream but returns complete response

Returns: { success: bool, data: { message: str, conversationId: str, quickReplies: list[str] } }
```

### GET /api/coach/starters

```
CoachService.get_starters(
    user_id: str,
    language: str = "en",
    include_wellbeing: bool = True,
    mood: int | None = None,
    energy: int | None = None,
    stress: int | None = None
) → list[ConversationStarter]

    → [If include_wellbeing] → CheckInService.get_today_checkin(user_id) → CheckIn | None

Returns: { success: bool, data: { starters: list[{ key: str, text: str }] } }
```

---

## Circles & Groups System

### GET /api/circles/groups

```
get_user_circles_pipeline(
    user_id: str
) → UserCirclesData

    → GroupService.get_groups_for_user(user_id) → list[CircleGroup]
    → MeetingService.get_meetings_for_user(user_id, upcoming=True) → list[CircleMeeting]

Returns: { success: bool, data: { groups: list[{ id, name, memberCount, members, nextMeeting }], upcomingMeetings: list[{ id, title, groupName, date }] } }
```

### GET /api/circles/invitations

```
InvitationService.get_invitations_for_user(
    email: str
) → list[CircleInvitation]

Returns: { success: bool, data: { invitations: list[{ id, groupName, invitedBy }] } }
```

---

## Dashboard System

### GET /api/dashboard

```
get_dashboard_pipeline(
    user_id: str
) → DashboardData

    → CheckInService.get_today_checkin(user_id) → CheckIn | None
    → CheckInAnalytics.calculate_streak(user_id) → int
    → InsightService.get_unread_count(user_id) → int
    → LearningProgressService.get_current_focus(user_id) → ContentProgress | None
    → MeetingService.get_next_meeting_for_user(user_id) → CircleMeeting | None

Returns: { success: bool, data: { todaysCheckin: CheckIn | null, streak: int, insightsCount: int, todaysFocus: { title, progress } | null, nextCircle: { date } | null } }
```

---

## Organization Hub System

### GET /api/hub/organization

```
OrganizationService.get_organization_with_stats(
    organization_id: str,
    user_id: str
) → OrganizationWithStats

    → OrganizationService._verify_admin(organization_id, user_id) → None
    → OrganizationService.get_organization(organization_id) → Organization
    → OrganizationService.get_member_count(organization_id) → int
    → OrganizationService.get_active_user_count(organization_id) → int
    → LearningProgressService.get_org_completed_count(organization_id) → int
    → OrganizationService.get_engagement_rate(organization_id) → int

Requires: Org Admin
Returns: { success: bool, data: { id, name, memberCount, activeUsers, completedLessons, avgEngagement } }
```

### GET /api/hub/members

```
OrganizationService.get_members(
    organization_id: str,
    user_id: str
) → list[OrganizationMember]

    → OrganizationService._verify_admin(organization_id, user_id) → None

Requires: Org Admin
Returns: { success: bool, data: { members: list[{ id, name, email, role }] } }
```

---

## Admin System

### GET /api/admin/stats

```
AdminStatsService.get_platform_stats() → PlatformStats

    → UserService.count_all() → int
    → UserService.count_active() → int
    → CheckInService.count_all() → int
    → ConversationService.count_all() → int

Requires: isAdmin = true
Returns: { success: bool, data: { totalUsers: int, activeUsers: int, totalCheckins: int, totalSessions: int } }
```

---

## Summary

| System | Endpoints |
|--------|-----------|
| Auth | 7 |
| Profile | 3 |
| Check-in | 2 |
| Progress & Insights | 2 |
| Content & Learning | 1 |
| AI Coaching | 3 |
| Circles & Groups | 2 |
| Dashboard | 1 |
| Organization Hub | 2 |
| Admin | 1 |
| **Total** | **24** |

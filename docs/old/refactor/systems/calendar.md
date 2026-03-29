# Calendar Integration System

## Description

The Calendar Integration System provides calendar connectivity for scheduling circle meetings. It handles OAuth authentication with calendar providers, availability calculation across timezones, and bi-directional synchronization of calendar events.

**Responsibilities:**
- OAuth connection with Google Calendar (Outlook/Microsoft planned for future)
- Fetch free/busy data from connected calendars
- Calculate availability within user-defined working hours
- Find common availability across group members with timezone support
- Create and manage calendar events with Google Meet links
- Sync changes from external calendars via webhooks
- Fallback to manual availability when calendar not connected
- Support multiple calendars per user

**Tech Stack:**
- **Google Calendar API** - Calendar data and event management
- **Google OAuth 2.0** - Authentication with offline access
- **Google Meet** - Auto-generated video meeting links
- **MongoDB** - Connection tokens, meetings, manual availability
- **Webhooks** - Real-time calendar change notifications

**Supported Providers:**
| Provider | Status | Features |
|----------|--------|----------|
| Google Calendar | Supported | Full (OAuth, free/busy, events, Meet links, webhooks) |
| Microsoft Outlook | Planned | - |

---

## Pipelines

### Pipeline 1: Connect/Disconnect Calendar

OAuth flow to connect user's calendar and token revocation for disconnection.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CONNECT CALENDAR PIPELINE                            │
└─────────────────────────────────────────────────────────────────────────────┘

Frontend                         Backend                           Google
────────                         ───────                           ──────
    │                                │                                 │
    │  1. GET /api/calendar/auth/google                                │
    │───────────────────────────────>│                                 │
    │                                │                                 │
    │                                │  2. Generate OAuth URL          │
    │                                │     - Include user ID in state  │
    │                                │     - Request offline access    │
    │                                │     - Scopes: calendar.readonly,│
    │                                │       calendar.events,          │
    │                                │       userinfo.email            │
    │                                │                                 │
    │  3. Return { authUrl }         │                                 │
    │<───────────────────────────────│                                 │
    │                                │                                 │
    │  4. Redirect to Google         │                                 │
    │─────────────────────────────────────────────────────────────────>│
    │                                │                                 │
    │                                │                    5. User signs│
    │                                │                       in/consents
    │                                │                                 │
    │  6. Redirect to callback       │                                 │
    │     /api/calendar/auth/google/callback?code=...&state=...        │
    │<─────────────────────────────────────────────────────────────────│
    │                                │                                 │
    │───────────────────────────────>│                                 │
    │                                │  7. Exchange code for tokens    │
    │                                │─────────────────────────────────>
    │                                │                                 │
    │                                │  8. Receive tokens              │
    │                                │     - access_token              │
    │                                │     - refresh_token             │
    │                                │     - expiry_date               │
    │                                │<─────────────────────────────────
    │                                │                                 │
    │                                │  9. Get user email from Google  │
    │                                │─────────────────────────────────>
    │                                │<─────────────────────────────────
    │                                │                                 │
    │                                │  10. Encrypt & save tokens      │
    │                                │      CalendarConnection.upsert()│
    │                                │                                 │
    │                                │  11. Setup webhook for calendar │
    │                                │      (watch for changes)        │
    │                                │─────────────────────────────────>
    │                                │                                 │
    │  12. Redirect to app           │                                 │
    │      /circles?calendar_connected=true                            │
    │<───────────────────────────────│                                 │
    │                                │                                 │


┌─────────────────────────────────────────────────────────────────────────────┐
│                       DISCONNECT CALENDAR PIPELINE                           │
└─────────────────────────────────────────────────────────────────────────────┘

Frontend                         Backend                           Google
────────                         ───────                           ──────
    │                                │                                 │
    │  1. DELETE /api/calendar/connection                              │
    │───────────────────────────────>│                                 │
    │                                │                                 │
    │                                │  2. Find CalendarConnection     │
    │                                │                                 │
    │                                │  3. Stop webhook (if active)    │
    │                                │─────────────────────────────────>
    │                                │                                 │
    │                                │  4. Revoke tokens with Google   │
    │                                │─────────────────────────────────>
    │                                │                                 │
    │                                │  5. Mark connection as revoked  │
    │                                │     (keep record for audit)     │
    │                                │                                 │
    │  6. Return success             │                                 │
    │<───────────────────────────────│                                 │
    │                                │                                 │
```

**Connect Steps:**
1. Frontend requests OAuth URL from backend
2. Backend generates Google OAuth URL with state (user ID, return URL)
3. User redirected to Google, signs in, grants permissions
4. Google redirects back with authorization code
5. Backend exchanges code for access + refresh tokens
6. Backend fetches user's Google email for display
7. Tokens encrypted (AES-256-CBC) and saved to CalendarConnection
8. Webhook channel created for real-time sync
9. User redirected back to app

**Disconnect Steps:**
1. User requests disconnection
2. Stop any active webhook channels
3. Revoke tokens with Google API
4. Mark CalendarConnection as revoked (preserve for audit)
5. Return success

**Error Cases:**
- User denies OAuth consent → Redirect with error
- Invalid/expired code → 400 Bad Request
- Token exchange fails → 500 Internal Server Error
- Already connected → Update existing connection

---

### Pipeline 2: Get Availability

Fetches availability for a single user or finds common slots for a group.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      GET USER AVAILABILITY PIPELINE                          │
└─────────────────────────────────────────────────────────────────────────────┘

Frontend                         Backend                           Google
────────                         ───────                           ──────
    │                                │                                 │
    │  GET /api/calendar/availability                                  │
    │  ?startDate=...&endDate=...    │                                 │
    │───────────────────────────────>│                                 │
    │                                │                                 │
    │                                │  1. Get user's calendar connection
    │                                │                                 │
    │                                │     [If connected:]             │
    │                                │                                 │
    │                                │  2. Check token expiry          │
    │                                │     → Refresh if needed         │
    │                                │─────────────────────────────────>
    │                                │                                 │
    │                                │  3. Query free/busy for each    │
    │                                │     connected calendar          │
    │                                │─────────────────────────────────>
    │                                │                                 │
    │                                │  4. Merge busy times from all   │
    │                                │     calendars                   │
    │                                │                                 │
    │                                │     [If not connected:]         │
    │                                │                                 │
    │                                │  2b. Load UserAvailability      │
    │                                │      (manual weekly slots)      │
    │                                │                                 │
    │                                │  5. Get user's working hours    │
    │                                │     from profile settings       │
    │                                │                                 │
    │                                │  6. Calculate free slots        │
    │                                │     ┌─────────────────────────┐ │
    │                                │     │ For each day in range:  │ │
    │                                │     │ - Start at working hour │ │
    │                                │     │ - Skip weekends         │ │
    │                                │     │ - Subtract busy times   │ │
    │                                │     │ - Filter by min duration│ │
    │                                │     └─────────────────────────┘ │
    │                                │                                 │
    │                                │  7. Convert to user's timezone  │
    │                                │                                 │
    │  8. Return { slots: [...] }    │                                 │
    │<───────────────────────────────│                                 │
    │                                │                                 │


┌─────────────────────────────────────────────────────────────────────────────┐
│                     GET GROUP AVAILABILITY PIPELINE                          │
└─────────────────────────────────────────────────────────────────────────────┘

Frontend                         Backend                           Google
────────                         ───────                           ──────
    │                                │                                 │
    │  GET /api/calendar/groups/:groupId/availability                  │
    │───────────────────────────────>│                                 │
    │                                │                                 │
    │                                │  1. Verify user has group access│
    │                                │                                 │
    │                                │  2. Get all group members       │
    │                                │                                 │
    │                                │  3. For each member (parallel): │
    │                                │     ┌─────────────────────────┐ │
    │                                │     │ Get availability        │ │
    │                                │     │ (calendar or manual)    │ │
    │                                │     │                         │ │
    │                                │     │ Convert to common       │ │
    │                                │     │ timezone (UTC)          │ │
    │                                │     └─────────────────────────┘ │
    │                                │                                 │
    │                                │  4. Find slot intersections     │
    │                                │     ┌─────────────────────────┐ │
    │                                │     │ For each slot in user1: │ │
    │                                │     │   For each slot in user2│ │
    │                                │     │     Find overlap        │ │
    │                                │     │     If >= minDuration   │ │
    │                                │     │       Add to common     │ │
    │                                │     │ Repeat for all users    │ │
    │                                │     └─────────────────────────┘ │
    │                                │                                 │
    │                                │  5. Score and sort slots        │
    │                                │     - Mid-day preferred (10-14) │
    │                                │     - Earlier in week preferred │
    │                                │     - Longer duration preferred │
    │                                │                                 │
    │                                │  6. Convert back to requester's │
    │                                │     timezone for display        │
    │                                │                                 │
    │  7. Return { slots, stats }    │                                 │
    │<───────────────────────────────│                                 │
    │                                │                                 │
```

**Single User Steps:**
1. Check if user has connected calendar
2. If connected: refresh token if needed, query free/busy from Google
3. If not connected: load manual availability slots (UserAvailability)
4. Get user's working hours from profile (default 9-18)
5. Calculate free slots within working hours, skipping weekends
6. Filter slots by minimum duration
7. Return slots in user's timezone

**Group Availability Steps:**
1. Verify requester has access to group
2. Get all group member IDs
3. Fetch availability for each member (parallel), convert to UTC
4. Calculate intersection of all availability slots
5. Filter by minimum meeting duration
6. Score slots (prefer mid-day, early week, longer duration)
7. Convert back to requester's timezone
8. Return top N slots with stats (users with calendar, total found)

**Cross-Timezone Calculation:**
```
User A (Stockholm, UTC+1): Available 10:00-12:00 local = 09:00-11:00 UTC
User B (London, UTC+0):    Available 09:00-11:00 local = 09:00-11:00 UTC
User C (New York, UTC-5):  Available 05:00-07:00 local = 10:00-12:00 UTC

Intersection in UTC: 10:00-11:00 UTC
Display to User A: 11:00-12:00 Stockholm
Display to User B: 10:00-11:00 London
Display to User C: 05:00-06:00 New York
```

**Error Cases:**
- Calendar not connected → Use manual availability
- Token refresh fails → Mark connection as error, use manual fallback
- No common slots found → Return empty with stats
- Group not found → 404

---

### Pipeline 3: Schedule Meeting

Creates a meeting with conflict detection and calendar events for all participants.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SCHEDULE MEETING PIPELINE                             │
└─────────────────────────────────────────────────────────────────────────────┘

Frontend                         Backend                           Google
────────                         ───────                           ──────
    │                                │                                 │
    │  POST /api/circles/groups/:groupId/meetings                      │
    │  { scheduledAt, duration, title, topic, recurring }              │
    │───────────────────────────────>│                                 │
    │                                │                                 │
    │                                │  1. Verify user can schedule    │
    │                                │     (is group member)           │
    │                                │                                 │
    │                                │  2. Re-check availability       │
    │                                │     ┌─────────────────────────┐ │
    │                                │     │ For each member:        │ │
    │                                │     │ - Get current free/busy │ │
    │                                │     │ - Check slot still free │ │
    │                                │     └─────────────────────────┘ │
    │                                │                                 │
    │                                │     [If conflict detected:]     │
    │                                │     → Return 409 with conflicts │
    │                                │                                 │
    │                                │  3. Create CircleMeeting record │
    │                                │     - status: "scheduled"       │
    │                                │     - attendance: all "pending" │
    │                                │                                 │
    │                                │  4. For each member with        │
    │                                │     connected calendar:         │
    │                                │     ┌─────────────────────────┐ │
    │                                │     │ Create calendar event   │─────>
    │                                │     │ - Title, description    │ │
    │                                │     │ - Add all as attendees  │ │
    │                                │     │ - Generate Meet link    │ │
    │                                │     │ - Set reminders         │ │
    │                                │     │                         │ │
    │                                │     │ Store eventId on meeting│ │
    │                                │     └─────────────────────────┘ │
    │                                │                                 │
    │                                │  5. If recurring:               │
    │                                │     - Create recurrence rule    │
    │                                │     - Generate future instances │
    │                                │                                 │
    │                                │  6. Send notification emails    │
    │                                │     (via Email System)          │
    │                                │                                 │
    │  7. Return meeting details     │                                 │
    │     with meetingLink           │                                 │
    │<───────────────────────────────│                                 │
    │                                │                                 │


┌─────────────────────────────────────────────────────────────────────────────┐
│                         CANCEL MEETING PIPELINE                              │
└─────────────────────────────────────────────────────────────────────────────┘

Frontend                         Backend                           Google
────────                         ───────                           ──────
    │                                │                                 │
    │  DELETE /api/circles/meetings/:meetingId                         │
    │  { reason }                     │                                 │
    │───────────────────────────────>│                                 │
    │                                │                                 │
    │                                │  1. Verify user can cancel      │
    │                                │     (is scheduler or admin)     │
    │                                │                                 │
    │                                │  2. Get meeting with calendar   │
    │                                │     event references            │
    │                                │                                 │
    │                                │  3. For each calendar event:    │
    │                                │     ┌─────────────────────────┐ │
    │                                │     │ Delete event from       │─────>
    │                                │     │ user's Google Calendar  │ │
    │                                │     │ (sends cancellation)    │ │
    │                                │     └─────────────────────────┘ │
    │                                │                                 │
    │                                │  4. Update meeting status       │
    │                                │     - status: "cancelled"       │
    │                                │     - cancelledAt, cancelledBy  │
    │                                │     - cancellationReason        │
    │                                │                                 │
    │                                │  5. If recurring: option to     │
    │                                │     cancel single or all future │
    │                                │                                 │
    │                                │  6. Send cancellation emails    │
    │                                │                                 │
    │  7. Return success             │                                 │
    │<───────────────────────────────│                                 │
    │                                │                                 │
```

**Schedule Steps:**
1. Verify requester is a group member
2. Re-check availability for all members at the requested time
3. If any member has a conflict, return 409 with conflict details
4. Create CircleMeeting record in database
5. For each member with connected calendar, create Google Calendar event
6. First event creation generates Google Meet link, reuse for others
7. Store event IDs on meeting for later updates/deletion
8. If recurring, set recurrence rule (weekly, biweekly, etc.)
9. Queue notification emails via Email System
10. Return meeting with Meet link

**Cancel Steps:**
1. Verify requester is scheduler or group admin
2. Load meeting with all calendar event references
3. Delete calendar event from each member's Google Calendar
4. Update meeting status to cancelled with reason
5. For recurring: prompt for single instance or all future
6. Send cancellation emails
7. Return success

**Recurring Meeting Support:**
```
Recurrence patterns:
- weekly: Every week on same day/time
- biweekly: Every 2 weeks
- monthly: Same day of month

Each instance stored as separate CircleMeeting with:
- recurringId: Links to parent
- recurrenceIndex: Instance number (1, 2, 3...)
```

**Error Cases:**
- Not a group member → 403 Forbidden
- Conflict detected → 409 Conflict with details
- Calendar event creation fails → Continue (meeting still created, log error)
- Meeting not found → 404

---

### Pipeline 4: Sync Calendar Changes

Handles webhook notifications when calendar events change externally.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       SYNC CALENDAR CHANGES PIPELINE                         │
└─────────────────────────────────────────────────────────────────────────────┘

Google                           Backend                           Database
──────                           ───────                           ────────
    │                                │                                 │
    │  POST /api/calendar/webhook    │                                 │
    │  X-Goog-Resource-ID: ...       │                                 │
    │  X-Goog-Channel-ID: ...        │                                 │
    │───────────────────────────────>│                                 │
    │                                │                                 │
    │                                │  1. Validate webhook signature  │
    │                                │     (X-Goog-Channel-Token)      │
    │                                │                                 │
    │                                │  2. Find CalendarConnection     │
    │                                │     by channel ID               │
    │                                │                                 │
    │                                │  3. Get sync token for          │
    │                                │     incremental sync            │
    │                                │                                 │
    │                                │  4. Fetch changed events        │
    │<───────────────────────────────│                                 │
    │  events.list(syncToken)        │                                 │
    │───────────────────────────────>│                                 │
    │                                │                                 │
    │                                │  5. For each changed event:     │
    │                                │     ┌─────────────────────────┐ │
    │                                │     │ Find matching           │ │
    │                                │     │ CircleMeeting by eventId│ │
    │                                │     │                         │ │
    │                                │     │ If deleted in Google:   │ │
    │                                │     │ → Mark meeting cancelled│ │
    │                                │     │ → Notify other members  │ │
    │                                │     │                         │ │
    │                                │     │ If time changed:        │ │
    │                                │     │ → Update scheduledAt    │ │
    │                                │     │ → Re-sync other members'│ │
    │                                │     │   calendar events       │ │
    │                                │     │ → Notify of change      │ │
    │                                │     │                         │ │
    │                                │     │ If attendee responded:  │ │
    │                                │     │ → Update attendance     │ │
    │                                │     └─────────────────────────┘ │
    │                                │                                 │
    │                                │  6. Store new sync token        │
    │                                │                                 │
    │  7. Return 200 OK              │                                 │
    │<───────────────────────────────│                                 │
    │                                │                                 │


                            WEBHOOK SETUP (on connect)
Backend                                                            Google
───────                                                            ──────
    │                                                                 │
    │  POST /calendar/v3/calendars/{calendarId}/events/watch          │
    │  {                                                              │
    │    id: unique_channel_id,                                       │
    │    type: "web_hook",                                            │
    │    address: "https://app.example.com/api/calendar/webhook",     │
    │    token: verification_token,                                   │
    │    expiration: timestamp (max 7 days)                           │
    │  }                                                              │
    │────────────────────────────────────────────────────────────────>│
    │                                                                 │
    │  { resourceId, expiration }                                     │
    │<────────────────────────────────────────────────────────────────│
    │                                                                 │
    │  Store webhook details in CalendarConnection                    │
    │                                                                 │


                            WEBHOOK RENEWAL (cron job)
Scheduler                        Backend                           Google
─────────                        ───────                           ──────
    │                                │                                 │
    │  [Cron: daily]                 │                                 │
    │───────────────────────────────>│                                 │
    │                                │                                 │
    │                                │  1. Find connections where      │
    │                                │     webhook expires in < 2 days │
    │                                │                                 │
    │                                │  2. For each:                   │
    │                                │     - Stop old webhook          │
    │                                │     - Create new webhook        │
    │                                │     - Update connection         │
    │                                │                                 │
```

**Webhook Handler Steps:**
1. Validate webhook authenticity via channel token
2. Find CalendarConnection by channel ID
3. Use sync token for incremental fetch (only changed events)
4. For each changed event:
   - Match to CircleMeeting by stored eventId
   - Handle deletion: mark meeting cancelled, notify
   - Handle time change: update meeting, re-sync others' calendars
   - Handle RSVP: update attendance status
5. Store new sync token for next incremental sync
6. Return 200 immediately (async processing)

**Webhook Lifecycle:**
- Created when user connects calendar
- Expires after max 7 days (Google limit)
- Renewed daily via cron job
- Stopped when user disconnects

**Sync Token Flow:**
```
Initial sync: No token → Full sync → Receive token
Next webhook: Use token → Incremental sync → New token
Token invalid: Full sync again → New token
```

**Error Cases:**
- Invalid webhook signature → 401, ignore
- Connection not found → 200 OK (webhook for deleted connection)
- Sync token expired → Full sync
- Event not found in our system → Ignore (not our event)

---

## Components

### GoogleCalendarService

Handles all Google Calendar API interactions including OAuth, events, and webhooks.

```python
class GoogleCalendarService:
    """
    Google Calendar API client.
    Manages OAuth, calendar operations, and webhook setup.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        webhook_url: str
    ):
        """
        Args:
            client_id: Google OAuth client ID
            client_secret: Google OAuth client secret
            redirect_uri: OAuth callback URL
            webhook_url: URL for calendar webhooks
        """

    def get_auth_url(self, state: str = None) -> str:
        """
        Generate Google OAuth authorization URL.

        Args:
            state: Opaque state value (user ID, return URL)

        Returns:
            Authorization URL to redirect user to

        Scopes requested:
            - calendar.readonly (free/busy)
            - calendar.events (create/delete events)
            - userinfo.email (display connected account)
        """

    def exchange_code(self, code: str) -> dict:
        """
        Exchange authorization code for tokens.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            dict with access_token, refresh_token, expiry_date
        """

    def refresh_token(self, refresh_token: str) -> dict:
        """
        Refresh an expired access token.

        Args:
            refresh_token: Refresh token from initial auth

        Returns:
            dict with new access_token, expiry_date
        """

    def revoke_token(self, access_token: str) -> bool:
        """
        Revoke OAuth tokens with Google.

        Args:
            access_token: Token to revoke

        Returns:
            True if revoked successfully
        """

    def get_user_info(self, access_token: str) -> dict:
        """
        Get user email from Google.

        Args:
            access_token: Valid access token

        Returns:
            dict with email, name
        """

    def get_free_busy(
        self,
        access_token: str,
        calendar_ids: list[str],
        time_min: datetime,
        time_max: datetime
    ) -> list[dict]:
        """
        Query free/busy for calendars.

        Args:
            access_token: Valid access token
            calendar_ids: List of calendar IDs to check
            time_min: Start of range
            time_max: End of range

        Returns:
            List of busy slots: [{ start, end, calendarId }]
        """

    def list_calendars(self, access_token: str) -> list[dict]:
        """
        List user's calendars for multi-calendar support.

        Args:
            access_token: Valid access token

        Returns:
            List of calendars: [{ id, summary, primary }]
        """

    def create_event(
        self,
        access_token: str,
        calendar_id: str,
        event: dict
    ) -> dict:
        """
        Create a calendar event.

        Args:
            access_token: Valid access token
            calendar_id: Calendar to create event in
            event: Event details (summary, start, end, attendees, etc.)

        Returns:
            Created event with id, htmlLink, meetLink
        """

    def update_event(
        self,
        access_token: str,
        calendar_id: str,
        event_id: str,
        updates: dict
    ) -> dict:
        """
        Update an existing event.

        Args:
            access_token: Valid access token
            calendar_id: Calendar containing event
            event_id: Event to update
            updates: Fields to update

        Returns:
            Updated event
        """

    def delete_event(
        self,
        access_token: str,
        calendar_id: str,
        event_id: str,
        send_updates: bool = True
    ) -> bool:
        """
        Delete a calendar event.

        Args:
            access_token: Valid access token
            calendar_id: Calendar containing event
            event_id: Event to delete
            send_updates: Send cancellation to attendees

        Returns:
            True if deleted
        """

    def setup_webhook(
        self,
        access_token: str,
        calendar_id: str,
        channel_id: str,
        token: str,
        expiration: datetime
    ) -> dict:
        """
        Setup push notification webhook for calendar.

        Args:
            access_token: Valid access token
            calendar_id: Calendar to watch
            channel_id: Unique channel identifier
            token: Verification token for webhook
            expiration: When webhook expires

        Returns:
            dict with resourceId, expiration
        """

    def stop_webhook(
        self,
        channel_id: str,
        resource_id: str
    ) -> bool:
        """
        Stop a webhook channel.

        Args:
            channel_id: Channel to stop
            resource_id: Resource ID from setup

        Returns:
            True if stopped
        """

    def sync_events(
        self,
        access_token: str,
        calendar_id: str,
        sync_token: str = None
    ) -> dict:
        """
        Sync calendar events (full or incremental).

        Args:
            access_token: Valid access token
            calendar_id: Calendar to sync
            sync_token: Token for incremental sync (None for full)

        Returns:
            dict with events list and nextSyncToken
        """
```

---

### AvailabilityService

Calculates user availability with timezone support and manual fallback.

```python
class AvailabilityService:
    """
    Calculates availability from calendars or manual slots.
    Handles cross-timezone calculations for groups.
    """

    def __init__(
        self,
        google_calendar: GoogleCalendarService,
        db: Database
    ):
        """
        Args:
            google_calendar: Google Calendar client
            db: Database connection
        """

    def get_user_availability(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        min_duration: int = 60
    ) -> list[dict]:
        """
        Get availability for a single user.

        Args:
            user_id: User's ID
            start_date: Start of range
            end_date: End of range
            min_duration: Minimum slot duration in minutes

        Returns:
            List of free slots: [{ start, end, duration }]

        Logic:
            1. Check if user has connected calendar
            2. If yes: fetch free/busy, calculate free slots
            3. If no: use manual UserAvailability
            4. Apply user's working hours
            5. Filter by min_duration
        """

    def get_user_working_hours(self, user_id: str) -> dict:
        """
        Get user's configured working hours.

        Args:
            user_id: User's ID

        Returns:
            dict with:
                - startHour: int (0-23)
                - endHour: int (0-23)
                - workDays: list[int] (0=Sun, 6=Sat)
                - timezone: str

        Defaults:
            startHour: 9, endHour: 18
            workDays: [1, 2, 3, 4, 5] (Mon-Fri)
            timezone: from user profile
        """

    def get_manual_availability(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> list[dict]:
        """
        Convert manual weekly slots to date-specific slots.

        Args:
            user_id: User's ID
            start_date: Start of range
            end_date: End of range

        Returns:
            List of slots with actual dates
        """

    def find_group_availability(
        self,
        user_ids: list[str],
        start_date: datetime,
        end_date: datetime,
        min_duration: int = 60,
        max_slots: int = 5
    ) -> dict:
        """
        Find common availability across multiple users.

        Args:
            user_ids: List of user IDs
            start_date: Start of range
            end_date: End of range
            min_duration: Minimum slot duration
            max_slots: Maximum slots to return

        Returns:
            dict with:
                - slots: List of common free slots
                - totalFound: Total common slots found
                - usersWithCalendar: Count with connected calendars
                - usersWithManual: Count using manual availability
                - errors: List of users who couldn't be checked
        """

    def intersect_slots(
        self,
        slots_a: list[dict],
        slots_b: list[dict],
        min_duration: int
    ) -> list[dict]:
        """
        Find intersection of two slot lists.

        Args:
            slots_a: First list of slots
            slots_b: Second list of slots
            min_duration: Minimum overlap required

        Returns:
            List of overlapping slots
        """

    def convert_to_timezone(
        self,
        slots: list[dict],
        from_tz: str,
        to_tz: str
    ) -> list[dict]:
        """
        Convert slots between timezones.

        Args:
            slots: Slots with start/end datetimes
            from_tz: Source timezone
            to_tz: Target timezone

        Returns:
            Slots with converted times
        """

    def score_slot(self, slot: dict) -> int:
        """
        Score a slot for sorting preference.

        Args:
            slot: Slot with start, end, duration

        Returns:
            Score (higher = better)

        Scoring:
            +100: Start between 10-14 (mid-day)
            +50: Start between 9-16
            +30: Monday-Wednesday
            +duration: Longer slots preferred
        """

    def check_slot_available(
        self,
        user_id: str,
        start: datetime,
        end: datetime
    ) -> bool:
        """
        Check if a specific slot is still available.
        Used for conflict detection before scheduling.

        Args:
            user_id: User's ID
            start: Slot start time
            end: Slot end time

        Returns:
            True if slot is free
        """
```

---

### MeetingService

Manages meeting lifecycle including scheduling, cancellation, and recurring meetings.

```python
class MeetingService:
    """
    Handles meeting creation, updates, and cancellation.
    Integrates with calendar and email systems.
    """

    def __init__(
        self,
        google_calendar: GoogleCalendarService,
        availability_service: AvailabilityService,
        email_service: EmailService,
        db: Database
    ):
        """
        Args:
            google_calendar: Calendar client for event creation
            availability_service: For conflict checking
            email_service: For notifications
            db: Database connection
        """

    def schedule_meeting(
        self,
        group_id: str,
        scheduled_by: str,
        scheduled_at: datetime,
        duration: int,
        title: str,
        topic: str = None,
        description: str = None,
        recurring: dict = None
    ) -> dict:
        """
        Schedule a new meeting for a group.

        Args:
            group_id: Circle group ID
            scheduled_by: User scheduling the meeting
            scheduled_at: Meeting start time
            duration: Duration in minutes
            title: Meeting title
            topic: Discussion topic
            description: Meeting description
            recurring: Recurrence options (pattern, count)

        Returns:
            Created meeting with meetingLink

        Raises:
            ConflictError: If any member has a conflict
            ForbiddenError: If user can't schedule for group

        Steps:
            1. Verify user is group member
            2. Re-check availability for all members
            3. Create CircleMeeting record
            4. Create calendar events for connected members
            5. Handle recurring if specified
            6. Send notification emails
        """

    def check_conflicts(
        self,
        user_ids: list[str],
        start: datetime,
        end: datetime
    ) -> list[dict]:
        """
        Check for scheduling conflicts.

        Args:
            user_ids: Users to check
            start: Meeting start
            end: Meeting end

        Returns:
            List of conflicts: [{ userId, conflictStart, conflictEnd }]
            Empty list if no conflicts
        """

    def create_calendar_events(
        self,
        meeting: CircleMeeting,
        members: list[dict]
    ) -> str:
        """
        Create calendar events for all members.

        Args:
            meeting: Meeting record
            members: List of group members

        Returns:
            Google Meet link from first event

        Side Effects:
            - Creates event in each member's calendar
            - Stores eventId in meeting.calendarEvents
        """

    def cancel_meeting(
        self,
        meeting_id: str,
        cancelled_by: str,
        reason: str = None,
        cancel_recurring: str = "single"
    ) -> dict:
        """
        Cancel a meeting.

        Args:
            meeting_id: Meeting to cancel
            cancelled_by: User cancelling
            reason: Cancellation reason
            cancel_recurring: "single" or "all_future"

        Returns:
            Cancelled meeting

        Steps:
            1. Verify user can cancel
            2. Delete calendar events
            3. Update meeting status
            4. Handle recurring meetings
            5. Send cancellation emails
        """

    def update_meeting(
        self,
        meeting_id: str,
        updated_by: str,
        updates: dict
    ) -> dict:
        """
        Update meeting details.

        Args:
            meeting_id: Meeting to update
            updated_by: User making update
            updates: Fields to update (time, title, topic)

        Returns:
            Updated meeting

        If time changed:
            - Re-check availability
            - Update all calendar events
            - Notify members
        """

    def create_recurring_meetings(
        self,
        base_meeting: CircleMeeting,
        pattern: str,
        count: int
    ) -> list[dict]:
        """
        Create recurring meeting instances.

        Args:
            base_meeting: First meeting in series
            pattern: "weekly", "biweekly", "monthly"
            count: Number of instances to create

        Returns:
            List of created meetings
        """

    def get_next_occurrence(
        self,
        current_date: datetime,
        pattern: str
    ) -> datetime:
        """
        Calculate next occurrence for recurring meeting.

        Args:
            current_date: Current instance date
            pattern: Recurrence pattern

        Returns:
            Next occurrence datetime
        """

    def handle_calendar_change(
        self,
        user_id: str,
        event_id: str,
        change_type: str,
        new_data: dict = None
    ) -> None:
        """
        Handle change synced from external calendar.

        Args:
            user_id: User whose calendar changed
            event_id: Changed event ID
            change_type: "deleted", "updated", "rsvp"
            new_data: New event data (for updates)

        Actions:
            - deleted: Cancel meeting, notify others
            - updated: Sync time change to meeting
            - rsvp: Update attendance status
        """

    def update_attendance(
        self,
        meeting_id: str,
        user_id: str,
        status: str
    ) -> None:
        """
        Update attendance status for a member.

        Args:
            meeting_id: Meeting ID
            user_id: Member ID
            status: "accepted", "declined", "attended", "no_show"
        """

    def complete_meeting(
        self,
        meeting_id: str,
        notes: str = None
    ) -> dict:
        """
        Mark meeting as completed.

        Args:
            meeting_id: Meeting ID
            notes: Optional meeting notes

        Returns:
            Updated meeting
        """
```

---

## Data Models

### CalendarConnection (Collection)

```python
# calendar_connections collection
{
    "_id": ObjectId,
    "userId": ObjectId,               # User reference
    "provider": str,                  # "google" (future: "outlook")
    "accessTokenEncrypted": str,      # AES-256-CBC encrypted
    "refreshTokenEncrypted": str,     # AES-256-CBC encrypted
    "expiresAt": datetime,            # Token expiry
    "scopes": [str],                  # Granted OAuth scopes
    "calendarIds": [str],             # Connected calendar IDs (multi-calendar)
    "primaryCalendarId": str,         # Default calendar for events
    "providerEmail": str,             # Email from provider
    "status": str,                    # "active", "expired", "revoked", "error"
    "lastError": str | None,          # Last error message
    "webhook": {
        "channelId": str,             # Webhook channel ID
        "resourceId": str,            # Google resource ID
        "token": str,                 # Verification token
        "expiration": datetime        # Webhook expiry
    },
    "syncToken": str | None,          # For incremental sync
    "connectedAt": datetime,
    "lastSyncAt": datetime,
    "createdAt": datetime,
    "updatedAt": datetime
}
```

**Indexes:**
- `{ userId: 1, provider: 1 }` - Unique, one connection per provider per user
- `{ status: 1 }` - For finding active connections
- `{ "webhook.expiration": 1 }` - For webhook renewal

---

### UserAvailability (Collection)

```python
# user_availability collection
{
    "_id": ObjectId,
    "userId": ObjectId,               # User reference (unique)
    "slots": [{
        "day": int,                   # 0-6 (Sunday-Saturday)
        "hour": int                   # 0-23
    }],
    "timezone": str,                  # User's timezone
    "updatedAt": datetime
}
```

**Indexes:**
- `{ userId: 1 }` - Unique

---

### UserWorkingHours (Embedded in User)

```python
# Embedded in user.settings.workingHours
{
    "startHour": int,                 # Default: 9
    "endHour": int,                   # Default: 18
    "workDays": [int],                # Default: [1,2,3,4,5] (Mon-Fri)
    "timezone": str                   # User's timezone
}
```

---

### CircleMeeting (Collection)

```python
# circle_meetings collection
{
    "_id": ObjectId,
    "groupId": ObjectId,              # CircleGroup reference
    "title": str,
    "description": str | None,
    "topic": str | None,              # Discussion topic
    "scheduledAt": datetime,
    "duration": int,                  # Minutes (15-180)
    "timezone": str,
    "meetingLink": str | None,        # Google Meet link
    "calendarEvents": [{
        "userId": ObjectId,
        "eventId": str,               # Google Calendar event ID
        "provider": str               # "google"
    }],
    "status": str,                    # "scheduled", "in_progress", "completed", "cancelled"
    "scheduledBy": ObjectId,
    "attendance": [{
        "userId": ObjectId,
        "status": str,                # "pending", "accepted", "declined", "attended", "no_show"
        "respondedAt": datetime | None
    }],
    "recurring": {
        "parentId": ObjectId | None,  # First meeting in series
        "pattern": str | None,        # "weekly", "biweekly", "monthly"
        "index": int | None           # Instance number (1, 2, 3...)
    } | None,
    "notes": str | None,              # Post-meeting notes
    "cancelledAt": datetime | None,
    "cancelledBy": ObjectId | None,
    "cancellationReason": str | None,
    "createdAt": datetime,
    "updatedAt": datetime
}
```

**Indexes:**
- `{ groupId: 1, scheduledAt: -1 }` - Group meetings by date
- `{ groupId: 1, status: 1 }` - Filter by status
- `{ scheduledAt: 1, status: 1 }` - Upcoming meetings
- `{ "calendarEvents.userId": 1 }` - Find by user's events
- `{ "recurring.parentId": 1 }` - Find recurring instances

---

## Configuration

```python
# Environment variables

# Google OAuth
GOOGLE_CLIENT_ID = "..."
GOOGLE_CLIENT_SECRET = "..."
GOOGLE_REDIRECT_URI = "https://app.example.com/api/calendar/auth/google/callback"

# Webhook
CALENDAR_WEBHOOK_URL = "https://app.example.com/api/calendar/webhook"

# Token encryption
CALENDAR_ENCRYPTION_KEY = "32-byte-hex-key"

# Defaults
DEFAULT_WORKING_HOURS_START = 9
DEFAULT_WORKING_HOURS_END = 18
DEFAULT_TIMEZONE = "Europe/Stockholm"
DEFAULT_MEETING_DURATION = 60

# Availability
AVAILABILITY_LOOKAHEAD_DAYS = 14
MIN_SLOT_DURATION = 30
MAX_SUGGESTED_SLOTS = 5

# Webhook renewal
WEBHOOK_RENEWAL_THRESHOLD_DAYS = 2
```

---

## OAuth Scopes

| Scope | Purpose |
|-------|---------|
| `calendar.readonly` | Read free/busy information |
| `calendar.events` | Create, update, delete events |
| `userinfo.email` | Display connected account email |

---

## Future: Microsoft Outlook Support

Planned interface for Outlook/Microsoft 365:

```python
class OutlookCalendarService:
    """
    Microsoft Graph API client for Outlook calendars.
    Same interface as GoogleCalendarService.
    """

    # OAuth via Microsoft Identity Platform
    # Scopes: Calendars.ReadWrite, User.Read

    def get_auth_url(self, state: str) -> str: ...
    def exchange_code(self, code: str) -> dict: ...
    def get_free_busy(self, ...) -> list[dict]: ...
    def create_event(self, ...) -> dict: ...
    # ... etc
```

Provider abstraction:

```python
class CalendarProvider:
    """Abstract base for calendar providers."""

    def get_auth_url(self, state: str) -> str: ...
    def exchange_code(self, code: str) -> dict: ...
    def get_free_busy(self, ...) -> list[dict]: ...
    def create_event(self, ...) -> dict: ...
    def delete_event(self, ...) -> bool: ...
    def setup_webhook(self, ...) -> dict: ...


# Factory
def get_calendar_provider(provider: str) -> CalendarProvider:
    if provider == "google":
        return GoogleCalendarService()
    elif provider == "outlook":
        return OutlookCalendarService()
    raise ValueError(f"Unknown provider: {provider}")
```

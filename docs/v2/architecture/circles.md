# Circles & Groups System

## Description

The Circles & Groups System facilitates peer-to-peer leadership development through small group discussions. Organization admins create pools, invite participants, and the system automatically assigns them to small groups (circles) for recurring meetings with calendar integration.

**Responsibilities:**
- Create and manage circle pools within organizations
- Send and track invitations to potential participants
- Auto-assign accepted participants to balanced groups
- Schedule and manage group meetings with Google Meet integration
- Track member availability and find common meeting times
- Send email notifications for invitations, assignments, and meetings
- Provide meeting reminders (24 hours and 1 hour before)

**Tech Stack:**
- **MongoDB** - Pool, invitation, group, meeting, and availability storage
- **Google Calendar API** - Calendar events and Meet link generation
- **Email Service** - Uses components from Email System (see email.md)
- **Cron/Scheduler** - Meeting reminders and invitation expiration

**Pool Lifecycle:**
```
draft → inviting → assigning → active → completed
                      ↓
                  cancelled
```

| Status | Description |
|--------|-------------|
| `draft` | Pool created, settings can be modified |
| `inviting` | Accepting invitations, auto-assigning groups |
| `assigning` | Manual group assignment in progress |
| `active` | Groups formed, meetings can be scheduled |
| `completed` | Pool finished, groups disbanded |
| `cancelled` | Pool cancelled, invitations cancelled |

**Key Concepts:**

| Concept | Description |
|---------|-------------|
| **Pool** | A cohort of participants within an organization |
| **Invitation** | Token-based invite to join a pool |
| **Group (Circle)** | Small group of 3-6 members for discussions |
| **Meeting** | Scheduled video call for a group |
| **Availability** | User's weekly time slots for meetings |

---

## Pipelines

### Pipeline 1: Create Pool and Send Invitations

Admin creates a pool and invites participants via email or CSV upload.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CREATE POOL AND SEND INVITATIONS PIPELINE                  │
└─────────────────────────────────────────────────────────────────────────────┘

Admin                            Circle System                      External
─────                            ─────────────                      ────────
    │                                │                                   │
    │  create_pool(                  │                                   │
    │    org_id, name, topic,        │                                   │
    │    target_size, cadence)       │                                   │
    │───────────────────────────────>│                                   │
    │                                │                                   │
    │                                │  1. Verify admin role             │
    │                                │     OrganizationMember.           │
    │                                │       is_user_org_admin()         │
    │                                │                                   │
    │                                │  2. Create pool                   │
    │                                │     CirclePool.create({           │
    │                                │       status: "draft",            │
    │                                │       targetGroupSize,            │
    │                                │       cadence                     │
    │                                │     })                            │
    │                                │                                   │
    │  { pool }                      │                                   │
    │<───────────────────────────────│                                   │
    │                                │                                   │
    │  send_invitations(             │                                   │
    │    pool_id, invitees[], csv)   │                                   │
    │───────────────────────────────>│                                   │
    │                                │                                   │
    │                                │  3. Parse CSV if provided         │
    │                                │     ┌─────────────────────────┐   │
    │                                │     │ email,first,last        │   │
    │                                │     │ john@example.com,John,D │   │
    │                                │     └─────────────────────────┘   │
    │                                │                                   │
    │                                │  4. Update pool status            │
    │                                │     if draft → "inviting"         │
    │                                │                                   │
    │                                │  5. For each invitee:             │
    │                                │     ┌─────────────────────────┐   │
    │                                │     │ Check if already invited│   │
    │                                │     │ Generate unique token   │   │
    │                                │     │ Calculate expiry date   │   │
    │                                │     │ Create CircleInvitation │   │
    │                                │     │ Queue invitation email  │───────>
    │                                │     │   (via Email Service)   │   │
    │                                │     │ Update pool stats       │   │
    │                                │     └─────────────────────────┘   │
    │                                │                                   │
    │  { sent: [], failed: [],       │                                   │
    │    duplicate: [] }             │                                   │
    │<───────────────────────────────│                                   │
    │                                │                                   │
```

**Steps:**
1. Verify requesting user is admin of the organization
2. Create pool in draft status with configurable group size and meeting cadence
3. Parse CSV if bulk invitations provided (format: email,first_name,last_name)
4. Transition pool from draft to inviting status
5. For each invitee:
   - Check for duplicate invitation (same email + pool)
   - Generate unique 64-character token
   - Set expiry date (default: 14 days, configurable)
   - Create CircleInvitation record
   - Queue invitation email via Email Service
   - Increment pool's totalInvited stat
6. Return results with sent, failed, and duplicate counts

**CSV Format:**
```csv
email,first_name,last_name
john.doe@company.com,John,Doe
jane.smith@company.com,Jane,Smith
```

**Error Cases:**
- Not an organization admin → 403 Forbidden
- Invalid email format → Skip, add to failed list
- Already invited (pending) → Skip, add to duplicate list

---

### Pipeline 2: Accept Invitation and Auto-Assign

User accepts invitation and is automatically assigned to a group when enough members are available.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   ACCEPT INVITATION AND AUTO-ASSIGN PIPELINE                  │
└─────────────────────────────────────────────────────────────────────────────┘

User                             Circle System                      External
────                             ─────────────                      ────────
    │                                │                                   │
    │  GET /invitations/:token       │                                   │
    │───────────────────────────────>│                                   │
    │                                │                                   │
    │                                │  1. Find invitation by token      │
    │                                │     Check not expired             │
    │                                │                                   │
    │  { invitation, pool }          │                                   │
    │<───────────────────────────────│                                   │
    │                                │                                   │
    │  accept_invitation(token)      │                                   │
    │───────────────────────────────>│                                   │
    │                                │                                   │
    │                                │  2. Validate invitation           │
    │                                │     - Status = "pending"          │
    │                                │     - Not expired                 │
    │                                │                                   │
    │                                │  3. Update invitation             │
    │                                │     status → "accepted"           │
    │                                │     userId → current user         │
    │                                │     acceptedAt → now              │
    │                                │                                   │
    │                                │  4. Update pool stats             │
    │                                │     totalAccepted++               │
    │                                │                                   │
    │                                │  5. Add to organization           │
    │                                │     (if not already member)       │
    │                                │                                   │
    │                                │  6. Try auto-assign to group      │
    │                                │     ┌─────────────────────────┐   │
    │                                │     │ Find group with room    │   │
    │                                │     │ OR check if enough      │   │
    │                                │     │ unassigned to form new  │   │
    │                                │     └─────────────────────────┘   │
    │                                │                                   │
    │                                │     [If group created/joined]     │
    │                                │     Queue assignment email ───────────>
    │                                │                                   │
    │  { success, group? }           │                                   │
    │<───────────────────────────────│                                   │
    │                                │                                   │
```

**Auto-Assignment Logic:**
1. Check if user is already in a group for this pool
2. Look for existing active group with room (< targetGroupSize members)
3. If found: add user to that group
4. If not found: check if enough unassigned users to form new group
5. If enough unassigned: create new group with targetGroupSize members
6. Send group assignment notification email to all new group members

**Group Formation Algorithm:**
```python
# When forming groups, divide users into balanced groups of 3-6 members
# Prefer groups of target_size (default: 4)
# No group smaller than 3 members
# Shuffle users randomly before assignment for diversity
```

**Error Cases:**
- Token not found → 404 Not Found
- Invitation expired → 410 Gone (update status to "expired")
- Already accepted/declined → 400 Bad Request

---

### Pipeline 3: Schedule Meeting

Group member schedules a meeting with calendar integration and notifications.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SCHEDULE MEETING PIPELINE                            │
└─────────────────────────────────────────────────────────────────────────────┘

Member                           Circle System                      External
──────                           ─────────────                      ────────
    │                                │                                   │
    │  GET /groups/:id/              │                                   │
    │    common-availability         │                                   │
    │───────────────────────────────>│                                   │
    │                                │                                   │
    │                                │  1. Get all members' availability │
    │                                │     UserAvailability.find({       │
    │                                │       userId: { $in: members }    │
    │                                │     })                            │
    │                                │                                   │
    │                                │  2. Calculate intersection        │
    │                                │     Find slots where ALL          │
    │                                │     members are available         │
    │                                │                                   │
    │  { commonSlots,                │                                   │
    │    allMembersSet }             │                                   │
    │<───────────────────────────────│                                   │
    │                                │                                   │
    │  schedule_meeting(             │                                   │
    │    group_id, title, topic,     │                                   │
    │    scheduled_at, duration)     │                                   │
    │───────────────────────────────>│                                   │
    │                                │                                   │
    │                                │  3. Verify group membership       │
    │                                │                                   │
    │                                │  4. Create CircleMeeting          │
    │                                │     - Initialize attendance       │
    │                                │       for all members             │
    │                                │     - Status = "scheduled"        │
    │                                │                                   │
    │                                │  5. Create calendar events        │
    │                                │     For each member with          │
    │                                │     connected calendar:           │
    │                                │     ┌─────────────────────────┐   │
    │                                │     │ GoogleCalendar.create() │──────>
    │                                │     │ - Add attendees         │   │
    │                                │     │ - Generate Meet link    │   │
    │                                │     │ - Store eventId         │   │
    │                                │     └─────────────────────────┘   │
    │                                │                                   │
    │                                │  6. Send notification emails      │
    │                                │     Queue meeting_scheduled ──────────>
    │                                │     email for each member         │
    │                                │                                   │
    │                                │  7. Schedule reminders            │
    │                                │     - 24 hours before             │
    │                                │     - 1 hour before               │
    │                                │                                   │
    │  { meeting, meetingLink }      │                                   │
    │<───────────────────────────────│                                   │
    │                                │                                   │
```

**Steps:**
1. (Optional) Check common availability across all group members
2. Verify user is a member of the group (or org admin)
3. Create meeting with scheduled time, duration, topic
4. Initialize attendance records for all group members (status: "pending")
5. For each member with connected Google Calendar:
   - Create calendar event with all attendees
   - Enable Google Meet link generation
   - Store eventId for later updates/cancellation
6. Use first available Meet link for the meeting
7. Queue meeting notification emails via Email Service
8. Schedule reminder jobs for 24h and 1h before meeting

**Calendar Event Details:**
- Title: Meeting title or "{Group Name} Meeting"
- Description: Topic + pool description
- Attendees: All group members' emails
- Conference: Google Meet (auto-generated)
- Timezone: Per-meeting timezone (default: Europe/Stockholm)

**Error Cases:**
- Not a group member → 403 Forbidden
- Group not active → 400 Bad Request
- Invalid scheduledAt (in past) → 400 Bad Request

---

### Pipeline 4: Manage Groups (Admin)

Admin can view, adjust, and manage groups within a pool.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MANAGE GROUPS PIPELINE (ADMIN)                        │
└─────────────────────────────────────────────────────────────────────────────┘

Admin                            Circle System                      External
─────                            ─────────────                      ────────
    │                                │                                   │
    │  GET /pools/:id/groups         │                                   │
    │───────────────────────────────>│                                   │
    │                                │                                   │
    │                                │  1. Verify admin access           │
    │                                │                                   │
    │                                │  2. Get all groups for pool       │
    │                                │     with member details           │
    │                                │                                   │
    │  { groups: [{                  │                                   │
    │      name, members[], stats    │                                   │
    │    }] }                        │                                   │
    │<───────────────────────────────│                                   │
    │                                │                                   │
    │  move_member(                  │                                   │
    │    member_id, from_group,      │                                   │
    │    to_group)                   │                                   │
    │───────────────────────────────>│                                   │
    │                                │                                   │
    │                                │  3. Verify admin access           │
    │                                │                                   │
    │                                │  4. Remove from source group      │
    │                                │     group.members.pull(userId)    │
    │                                │                                   │
    │                                │  5. Add to target group           │
    │                                │     group.members.push(userId)    │
    │                                │                                   │
    │                                │  6. Notify affected members       │
    │                                │     Queue notification emails ────────>
    │                                │                                   │
    │  { success }                   │                                   │
    │<───────────────────────────────│                                   │
    │                                │                                   │
    │  trigger_manual_assign(        │                                   │
    │    pool_id)                    │                                   │
    │───────────────────────────────>│                                   │
    │                                │                                   │
    │                                │  7. Get all accepted users        │
    │                                │     not yet in groups             │
    │                                │                                   │
    │                                │  8. Shuffle and divide into       │
    │                                │     balanced groups               │
    │                                │                                   │
    │                                │  9. Create CircleGroup records    │
    │                                │     - Names: Circle A, B, C...    │
    │                                │                                   │
    │                                │  10. Update pool status           │
    │                                │      → "active"                   │
    │                                │                                   │
    │                                │  11. Notify all members           │
    │                                │      Queue assignment emails ─────────>
    │                                │                                   │
    │  { groups: [], totalMembers }  │                                   │
    │<───────────────────────────────│                                   │
    │                                │                                   │
```

**Admin Operations:**
1. **View Groups**: See all groups with member details and statistics
2. **Move Member**: Transfer a member between groups
3. **Manual Assignment**: Trigger group formation for all unassigned members
4. **Disband Group**: Mark group as disbanded (soft delete)
5. **Set Leader**: Designate a group leader/facilitator

**Group Balancing Rules:**
- Target size is configurable (default: 4)
- Minimum group size: 3 members
- Maximum group size: 6 members (configurable)
- Groups are named sequentially: Circle A, Circle B, etc.
- Random shuffle before assignment for diversity

**Error Cases:**
- Not an organization admin → 403 Forbidden
- Moving to full group → 400 Bad Request
- Source group would have < 3 members → 400 Bad Request

---

### Pipeline 5: Send Meeting Reminders

Automated reminders sent before scheduled meetings.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       SEND MEETING REMINDERS PIPELINE                         │
└─────────────────────────────────────────────────────────────────────────────┘

Scheduler                        Circle System                      External
─────────                        ─────────────                      ────────
    │                                │                                   │
    │  [Cron: every 15 minutes]      │                                   │
    │───────────────────────────────>│                                   │
    │                                │                                   │
    │                                │  1. Find meetings needing         │
    │                                │     24-hour reminder              │
    │                                │     ┌─────────────────────────┐   │
    │                                │     │ scheduledAt between     │   │
    │                                │     │ now+23h and now+24h     │   │
    │                                │     │ status = "scheduled"    │   │
    │                                │     │ reminder24hSent = false │   │
    │                                │     └─────────────────────────┘   │
    │                                │                                   │
    │                                │  2. For each meeting:             │
    │                                │     - Get group members           │
    │                                │     - Queue reminder email ───────────>
    │                                │     - Set reminder24hSent = true  │
    │                                │                                   │
    │                                │  3. Find meetings needing         │
    │                                │     1-hour reminder               │
    │                                │     ┌─────────────────────────┐   │
    │                                │     │ scheduledAt between     │   │
    │                                │     │ now+45m and now+1h      │   │
    │                                │     │ status = "scheduled"    │   │
    │                                │     │ reminder1hSent = false  │   │
    │                                │     └─────────────────────────┘   │
    │                                │                                   │
    │                                │  4. For each meeting:             │
    │                                │     - Get group members           │
    │                                │     - Queue reminder email ───────────>
    │                                │     - Include Meet link           │
    │                                │     - Set reminder1hSent = true   │
    │                                │                                   │
    │  [Complete]                    │                                   │
    │                                │                                   │
```

**Reminder Schedule:**
| Reminder | Timing | Content |
|----------|--------|---------|
| 24 hours | 23-24h before | Meeting details, topic, attendees |
| 1 hour | 45-60min before | Meeting details + Meet link |

**Reminder Email Content:**
- Meeting title and topic
- Scheduled time (in recipient's timezone)
- Duration
- Other attendees
- Google Meet link (1-hour reminder)
- Link to cancel/reschedule

---

## Components

### PoolService

Manages circle pool lifecycle and settings.

```python
class PoolService:
    """
    Handles circle pool creation, updates, and lifecycle management.
    """

    def __init__(self, db: Database, org_service: OrganizationService):
        """
        Args:
            db: MongoDB database connection
            org_service: For organization membership verification
        """

    def create_pool(
        self,
        organization_id: str,
        name: str,
        created_by: str,
        topic: str = None,
        description: str = None,
        target_group_size: int = 4,
        cadence: str = "biweekly",
        invitation_settings: dict = None
    ) -> CirclePool:
        """
        Create a new circle pool.

        Args:
            organization_id: Organization this pool belongs to
            name: Pool name
            created_by: User ID of creator (must be org admin)
            topic: Discussion topic/theme
            description: Pool description
            target_group_size: Target members per group (3-6)
            cadence: Meeting frequency (weekly, biweekly)
            invitation_settings: Custom invite settings

        Returns:
            Created CirclePool

        Raises:
            PermissionError: If creator is not org admin
        """

    def get_pool(self, pool_id: str) -> CirclePool:
        """Get pool by ID with creator details."""

    def get_pool_with_invitations(self, pool_id: str) -> dict:
        """Get pool with all its invitations."""

    def update_pool(
        self,
        pool_id: str,
        user_id: str,
        updates: dict
    ) -> CirclePool:
        """
        Update pool settings.

        Args:
            pool_id: Pool to update
            user_id: User making update (must be org admin)
            updates: Fields to update

        Note:
            targetGroupSize and cadence can only be updated in draft status
        """

    def start_inviting(self, pool_id: str, user_id: str) -> CirclePool:
        """
        Transition pool from draft to inviting status.

        Raises:
            InvalidStateError: If pool is not in draft status
        """

    def cancel_pool(self, pool_id: str, user_id: str) -> CirclePool:
        """
        Cancel pool and all pending invitations.

        Side Effects:
            - Updates all pending invitations to "cancelled"
            - Optionally notifies invited users
        """

    def get_pools_for_organization(
        self,
        organization_id: str,
        user_id: str,
        status: str = None
    ) -> list[CirclePool]:
        """Get all pools for an organization."""

    def get_pool_stats(self, pool_id: str) -> dict:
        """
        Get pool statistics.

        Returns:
            dict with:
                - invitation counts by status
                - group count
                - can_assign: bool
        """
```

---

### InvitationService

Handles invitation sending, tracking, and acceptance.

```python
class InvitationService:
    """
    Manages circle pool invitations.
    Uses Email Service for sending invitation emails.
    """

    def __init__(
        self,
        db: Database,
        email_queue: EmailQueue,
        template_renderer: EmailTemplateRenderer
    ):
        """
        Args:
            db: MongoDB database connection
            email_queue: From Email System (see email.md)
            template_renderer: From Email System (see email.md)
        """

    def send_invitations(
        self,
        pool_id: str,
        invitees: list[dict],
        invited_by: str
    ) -> dict:
        """
        Send invitations to a list of people.

        Args:
            pool_id: Pool to invite to
            invitees: List of {email, firstName?, lastName?}
            invited_by: User ID sending invitations

        Returns:
            dict with:
                - sent: List of successfully invited
                - failed: List of failed with reasons
                - duplicate: List of already invited
        """

    def parse_invitation_csv(self, csv_content: str) -> dict:
        """
        Parse CSV for bulk invitations.

        Args:
            csv_content: CSV string (email,first_name,last_name)

        Returns:
            dict with:
                - invitees: List of parsed invitees
                - errors: List of parse errors with line numbers
        """

    def get_invitation_by_token(self, token: str) -> CircleInvitation:
        """
        Get invitation by its unique token.

        Raises:
            NotFoundError: If token not found
        """

    def accept_invitation(
        self,
        token: str,
        user_id: str
    ) -> CircleInvitation:
        """
        Accept an invitation.

        Args:
            token: Invitation token
            user_id: User accepting

        Side Effects:
            - Updates invitation status to "accepted"
            - Adds user to organization if not member
            - Triggers auto-assignment to group

        Raises:
            ExpiredError: If invitation expired
            InvalidStateError: If already processed
        """

    def decline_invitation(self, token: str) -> CircleInvitation:
        """Decline an invitation."""

    def get_invitations_for_user(self, email: str) -> list[dict]:
        """Get all invitations for a user's email."""

    def get_invitations_for_pool(
        self,
        pool_id: str,
        status: str = None
    ) -> list[CircleInvitation]:
        """Get invitations for a pool with optional status filter."""

    def cancel_invitation(
        self,
        invitation_id: str,
        user_id: str
    ) -> CircleInvitation:
        """Cancel a pending invitation (admin only)."""

    def resend_invitation(
        self,
        invitation_id: str,
        user_id: str
    ) -> CircleInvitation:
        """Resend invitation email and extend expiry."""

    def expire_old_invitations(self) -> int:
        """
        Mark expired pending invitations.
        Called by cron job.

        Returns:
            Count of invitations expired
        """
```

---

### GroupService

Manages circle groups and member assignments.

```python
class GroupService:
    """
    Handles circle group formation, management, and member operations.
    """

    def __init__(
        self,
        db: Database,
        email_queue: EmailQueue,
        template_renderer: EmailTemplateRenderer
    ):
        """
        Args:
            db: MongoDB database connection
            email_queue: From Email System
            template_renderer: From Email System
        """

    def assign_groups(self, pool_id: str, user_id: str) -> dict:
        """
        Assign all accepted invitees to groups.

        Args:
            pool_id: Pool to assign
            user_id: Admin triggering assignment

        Returns:
            dict with:
                - groups: List of created groups
                - totalMembers: Count of assigned members

        Algorithm:
            1. Get all accepted invitations with user accounts
            2. Shuffle users randomly
            3. Divide into balanced groups (target size, min 3)
            4. Create CircleGroup records
            5. Update pool status to "active"
            6. Send assignment notifications
        """

    def try_auto_assign(self, pool_id: str, user_id: str) -> CircleGroup | None:
        """
        Try to auto-assign a user to a group.
        Called when user accepts invitation.

        Returns:
            Group if assigned, None if waiting for more members
        """

    def divide_into_groups(
        self,
        user_ids: list[str],
        target_size: int,
        min_size: int = 3,
        max_size: int = 6
    ) -> list[list[str]]:
        """
        Divide users into balanced groups.

        Algorithm:
            - Calculate optimal number of groups
            - Distribute extras evenly
            - No group smaller than min_size
        """

    def get_group(self, group_id: str) -> CircleGroup:
        """Get group with full member details."""

    def get_groups_for_pool(
        self,
        pool_id: str,
        user_id: str
    ) -> list[CircleGroup]:
        """Get all groups for a pool."""

    def get_groups_for_user(self, user_id: str) -> list[CircleGroup]:
        """Get user's active groups across all pools."""

    def user_has_group_access(
        self,
        group_id: str,
        user_id: str
    ) -> bool:
        """
        Check if user can access group.
        True if member or org admin.
        """

    def move_member(
        self,
        member_id: str,
        from_group_id: str,
        to_group_id: str,
        admin_id: str
    ) -> None:
        """
        Move a member between groups (admin only).

        Raises:
            ValidationError: If move would leave source group < 3 members
            ValidationError: If target group is full
        """

    def set_leader(
        self,
        group_id: str,
        member_id: str,
        admin_id: str
    ) -> CircleGroup:
        """Designate a group leader/facilitator."""

    def disband_group(
        self,
        group_id: str,
        admin_id: str
    ) -> CircleGroup:
        """Mark group as disbanded (soft delete)."""

    def notify_group_assignment(
        self,
        group: CircleGroup,
        pool: CirclePool
    ) -> None:
        """Send assignment notification to all group members."""
```

---

### MeetingService

Handles meeting scheduling, calendar integration, and notifications.

```python
class MeetingService:
    """
    Manages circle meetings with Google Calendar integration.
    """

    def __init__(
        self,
        db: Database,
        calendar_service: GoogleCalendarService,
        email_queue: EmailQueue,
        template_renderer: EmailTemplateRenderer
    ):
        """
        Args:
            db: MongoDB database connection
            calendar_service: Google Calendar integration
            email_queue: From Email System
            template_renderer: From Email System
        """

    def schedule_meeting(
        self,
        group_id: str,
        scheduled_by: str,
        title: str = None,
        topic: str = None,
        description: str = None,
        scheduled_at: datetime = None,
        duration: int = 60,
        timezone: str = "Europe/Stockholm",
        create_calendar_events: bool = True
    ) -> CircleMeeting:
        """
        Schedule a meeting for a group.

        Args:
            group_id: Group this meeting is for
            scheduled_by: User scheduling (must be member or admin)
            title: Meeting title (default: "{Group Name} Meeting")
            topic: Discussion topic
            description: Additional description
            scheduled_at: When to meet
            duration: Duration in minutes (15-180)
            timezone: Timezone for the meeting
            create_calendar_events: Whether to create calendar events

        Side Effects:
            - Creates calendar events for connected members
            - Generates Google Meet link
            - Queues notification emails
            - Schedules reminder jobs

        Returns:
            Created CircleMeeting with meetingLink
        """

    def create_calendar_events(
        self,
        meeting: CircleMeeting,
        group: CircleGroup
    ) -> str | None:
        """
        Create Google Calendar events for all connected members.

        Returns:
            Google Meet link if generated
        """

    def get_meeting(self, meeting_id: str) -> CircleMeeting:
        """Get meeting with group details."""

    def get_meetings_for_group(
        self,
        group_id: str,
        user_id: str,
        upcoming: bool = True,
        limit: int = 10
    ) -> list[CircleMeeting]:
        """Get meetings for a group."""

    def get_meetings_for_user(
        self,
        user_id: str,
        upcoming: bool = True,
        limit: int = 20
    ) -> list[CircleMeeting]:
        """Get user's meetings across all groups."""

    def get_next_meeting(self, group_id: str) -> CircleMeeting | None:
        """Get next upcoming meeting for a group."""

    def cancel_meeting(
        self,
        meeting_id: str,
        user_id: str,
        reason: str = None
    ) -> CircleMeeting:
        """
        Cancel a meeting.

        Side Effects:
            - Deletes calendar events for all members
            - Sends cancellation notification emails
        """

    def update_attendance(
        self,
        meeting_id: str,
        user_id: str,
        status: str
    ) -> CircleMeeting:
        """
        Update user's attendance status.

        Args:
            status: "accepted" | "declined"
        """

    def complete_meeting(
        self,
        meeting_id: str,
        user_id: str,
        notes: str = None
    ) -> CircleMeeting:
        """Mark meeting as completed with optional notes."""

    def send_reminders(self) -> dict:
        """
        Send meeting reminders (called by cron).

        Returns:
            dict with counts of 24h and 1h reminders sent
        """

    def notify_meeting_scheduled(
        self,
        meeting: CircleMeeting,
        group: CircleGroup,
        pool: CirclePool
    ) -> None:
        """Send meeting scheduled notification to all members."""

    def notify_meeting_cancelled(
        self,
        meeting: CircleMeeting,
        group: CircleGroup,
        reason: str = None
    ) -> None:
        """Send meeting cancellation notification."""
```

---

### AvailabilityService

Manages user availability and finds common meeting times.

```python
class AvailabilityService:
    """
    Handles user availability for circle meetings.
    """

    def __init__(self, db: Database):
        """
        Args:
            db: MongoDB database connection
        """

    def get_availability(self, user_id: str) -> UserAvailability | None:
        """Get user's availability settings."""

    def update_availability(
        self,
        user_id: str,
        slots: list[dict],
        timezone: str = "UTC"
    ) -> UserAvailability:
        """
        Update user's weekly availability.

        Args:
            user_id: User's ID
            slots: List of {day: 0-6, hour: 0-23}
            timezone: User's timezone

        Example slots:
            [
                {"day": 1, "hour": 9},   # Monday 9 AM
                {"day": 1, "hour": 10},  # Monday 10 AM
                {"day": 3, "hour": 14},  # Wednesday 2 PM
            ]
        """

    def find_common_availability(
        self,
        user_ids: list[str]
    ) -> list[dict]:
        """
        Find time slots where ALL users are available.

        Args:
            user_ids: List of user IDs

        Returns:
            List of common slots [{day, hour}]
            Empty if not all users have set availability
        """

    def get_group_availability_status(
        self,
        group_id: str
    ) -> dict:
        """
        Get availability status for a group.

        Returns:
            dict with:
                - commonSlots: Available times for all
                - totalMembers: Group size
                - membersWithAvailability: Count who set availability
                - membersWithoutAvailability: Count who haven't
                - allMembersSet: bool
        """
```

---

## Data Models

### CirclePool (Collection: `circlepools`)

```python
# circlepools collection
{
    "_id": ObjectId,
    "organizationId": ObjectId,    # Organization this pool belongs to
    "name": str,                   # Pool name
    "topic": str,                  # Discussion theme
    "description": str,            # Pool description
    "targetGroupSize": int,        # Target members per group (3-6)
    "cadence": str,                # "weekly" | "biweekly"
    "status": str,                 # draft | inviting | assigning | active | completed | cancelled
    "invitationSettings": {
        "expiryDays": int,         # Days until invite expires (default: 14)
        "customMessage": str       # Custom message in invitation email
    },
    "stats": {
        "totalInvited": int,
        "totalAccepted": int,
        "totalDeclined": int,
        "totalGroups": int
    },
    "createdBy": ObjectId,         # Admin who created
    "assignedAt": datetime,        # When groups were assigned
    "createdAt": datetime,
    "updatedAt": datetime
}
```

**Indexes:**
- `{ organizationId: 1, status: 1 }` - Org pool queries
- `{ organizationId: 1, createdAt: -1 }` - Org pool listing
- `{ status: 1 }` - Status filtering
- `{ createdBy: 1 }` - Creator queries

---

### CircleInvitation (Collection: `circleinvitations`)

```python
# circleinvitations collection
{
    "_id": ObjectId,
    "poolId": ObjectId,            # Pool being invited to
    "email": str,                  # Invitee email (lowercase)
    "firstName": str,              # Optional first name
    "lastName": str,               # Optional last name
    "token": str,                  # Unique 64-char token
    "status": str,                 # pending | accepted | declined | expired | cancelled
    "expiresAt": datetime,         # When invitation expires
    "invitedBy": ObjectId,         # User who sent invitation
    "userId": ObjectId,            # User ID (set on accept)
    "acceptedAt": datetime,
    "declinedAt": datetime,
    "emailSentAt": datetime,       # When email was sent
    "emailSentCount": int,         # Number of emails sent
    "lastReminderAt": datetime,    # Last reminder sent
    "reminderCount": int,          # Reminders sent
    "createdAt": datetime,
    "updatedAt": datetime
}
```

**Indexes:**
- `{ poolId: 1, email: 1 }` - Unique, prevent duplicates
- `{ poolId: 1, status: 1 }` - Pool invitation queries
- `{ email: 1 }` - User invitation lookup
- `{ token: 1 }` - Unique, token lookup
- `{ expiresAt: 1, status: 1 }` - Expiration processing
- `{ userId: 1 }` - Accepted invitation lookup

---

### CircleGroup (Collection)

```python
# circle_groups collection
{
    "_id": ObjectId,
    "poolId": ObjectId,            # Pool this group belongs to
    "name": str,                   # Group name (Circle A, B, etc.)
    "members": [ObjectId],         # Array of user IDs
    "status": str,                 # active | completed | disbanded
    "leaderId": ObjectId,          # Optional designated leader
    "stats": {
        "meetingsHeld": int,
        "totalMeetingMinutes": int,
        "lastMeetingAt": datetime
    },
    "createdAt": datetime,
    "updatedAt": datetime
}
```

**Indexes:**
- `{ poolId: 1 }` - Pool group queries
- `{ poolId: 1, status: 1 }` - Active groups for pool
- `{ members: 1 }` - User's groups lookup
- `{ status: 1 }` - Status filtering

---

### CircleMeeting (Collection)

```python
# circle_meetings collection
{
    "_id": ObjectId,
    "groupId": ObjectId,           # Group this meeting is for
    "title": str,                  # Meeting title
    "description": str,            # Meeting description
    "topic": str,                  # Discussion topic
    "scheduledAt": datetime,       # When meeting starts
    "duration": int,               # Duration in minutes
    "timezone": str,               # Meeting timezone
    "meetingLink": str,            # Google Meet URL
    "status": str,                 # scheduled | in_progress | completed | cancelled
    "scheduledBy": ObjectId,       # User who scheduled
    "calendarEvents": [{
        "userId": ObjectId,
        "eventId": str,            # Google Calendar event ID
        "provider": str            # "google"
    }],
    "attendance": [{
        "userId": ObjectId,
        "status": str,             # pending | accepted | declined | attended | no_show
        "respondedAt": datetime
    }],
    "notes": str,                  # Post-meeting notes
    "reminder24hSent": bool,       # 24-hour reminder sent
    "reminder1hSent": bool,        # 1-hour reminder sent
    "cancelledAt": datetime,
    "cancelledBy": ObjectId,
    "cancellationReason": str,
    "createdAt": datetime,
    "updatedAt": datetime
}
```

**Indexes:**
- `{ groupId: 1, scheduledAt: -1 }` - Group meeting history
- `{ groupId: 1, status: 1 }` - Active meetings for group
- `{ scheduledAt: 1, status: 1 }` - Upcoming meetings
- `{ calendarEvents.userId: 1 }` - User's calendar events
- `{ scheduledAt: 1, reminder24hSent: 1 }` - Reminder processing
- `{ scheduledAt: 1, reminder1hSent: 1 }` - Reminder processing

---

### UserAvailability (Collection)

```python
# user_availability collection
{
    "_id": ObjectId,
    "userId": ObjectId,            # User this availability belongs to
    "slots": [{
        "day": int,                # 0 (Sunday) - 6 (Saturday)
        "hour": int                # 0-23
    }],
    "timezone": str,               # User's timezone
    "createdAt": datetime,
    "updatedAt": datetime
}
```

**Indexes:**
- `{ userId: 1 }` - Unique, one per user

---

## Configuration

### Environment Variables (.env)

```bash
# Group settings (in .env file)
MIN_GROUP_SIZE=3              # Minimum members per group (default: 3)
MAX_GROUP_SIZE=6              # Maximum members per group (default: 6)

# Note: Set MIN_GROUP_SIZE=1 for testing with small numbers of users
```

### Implementation

Group size settings are read from environment variables in `app_v2/services/circles/group_service.py`:

```python
import os

MIN_GROUP_SIZE = int(os.environ.get("MIN_GROUP_SIZE", "3"))
MAX_GROUP_SIZE = int(os.environ.get("MAX_GROUP_SIZE", "6"))
```

### Default Constants

```python
# Invitation settings
INVITATION_EXPIRY_DAYS = 14            # Default invitation expiry
TOKEN_LENGTH = 64                      # Invitation token length

# Meeting settings
DEFAULT_MEETING_DURATION = 60          # Default duration in minutes
DEFAULT_TIMEZONE = "Europe/Stockholm"

# Group naming
GROUP_NAME_PREFIX = "Circle "          # Groups named "Circle A", "Circle B", etc.
```

### Pool Settings (per-pool configuration)

Each pool can have custom settings stored in the pool document:

```python
{
    "targetGroupSize": 4,              # Target members per group (3-6)
    "cadence": "biweekly",             # "weekly" | "biweekly"
    "invitationSettings": {
        "expiryDays": 14,              # Days until invite expires
        "customMessage": "..."         # Custom message in invitation email
    }
}
```

---

## Email Types Reference

| Type | Template | Priority | Description |
|------|----------|----------|-------------|
| `circle_invitation` | Invite to pool | Normal (3) | Initial invitation with accept/decline links |
| `circle_invitation_reminder` | Reminder | Low (4) | Reminder for pending invitation |
| `group_assignment` | Group assigned | Normal (3) | Notification with group members |
| `meeting_scheduled` | Meeting created | High (2) | Meeting details with topic and link |
| `meeting_reminder_24h` | 24h reminder | Normal (3) | Reminder with meeting details |
| `meeting_reminder_1h` | 1h reminder | High (2) | Reminder with Meet link |
| `meeting_cancelled` | Meeting cancelled | High (2) | Cancellation with reason |
| `group_member_added` | New member | Normal (3) | When member joins via admin |
| `group_member_moved` | Member moved | Normal (3) | When admin moves member |

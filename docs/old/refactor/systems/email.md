# Email System

## Description

The Email System handles all outbound email communication including transactional emails, notifications, and automated scheduled emails. It provides reliable delivery through a queue-based architecture with retry logic, rate limiting, and comprehensive logging.

**Responsibilities:**
- Send transactional emails (verification, password reset, welcome)
- Send notification emails (circle invitations, meeting updates)
- Send automated scheduled emails (weekly focus, reminders)
- Queue emails for reliable delivery with retry on failure
- Rate limit emails to prevent abuse
- Log all sent emails for audit and debugging
- Render templates with i18n support

**Tech Stack:**
- **Resend API** - Primary email delivery (HTTP API, cloud-friendly)
- **SMTP/Nodemailer** - Legacy fallback option
- **MongoDB** - Email queue, logs, and template storage
- **i18n Service** - Localized email content from `locales/emails/{lang}.json`
- **Cron/Scheduler** - Automated email triggers

**Email Modes:**
| Mode | Description | Use Case |
|------|-------------|----------|
| `console` | Log to console only | Development |
| `resend` | Resend HTTP API | Production (recommended) |
| `smtp` | SMTP via nodemailer | Legacy/self-hosted |

**Email Categories:**

| Category | Emails |
|----------|--------|
| Auth | Verification, Password Reset, Password Changed, Welcome |
| Account | Deletion Scheduled |
| Circles | Invitation, Group Assignment, Meeting Scheduled, Meeting Cancelled |
| Automated | Weekly Focus, Check-in Reminder, Custom Reminders |

---

## Pipelines

### Pipeline 1: Send Email

Queues an email for delivery with rate limiting and logging.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            SEND EMAIL PIPELINE                               │
└─────────────────────────────────────────────────────────────────────────────┘

Caller                           Email System                        External
──────                           ────────────                        ────────
    │                                │                                   │
    │  send_verification_email(      │                                   │
    │    email, token, name, lang)   │                                   │
    │───────────────────────────────>│                                   │
    │                                │                                   │
    │                                │  1. Check rate limit              │
    │                                │     EmailRateLimiter.check(       │
    │                                │       email, "verification")      │
    │                                │                                   │
    │                                │     [If exceeded → return error]  │
    │                                │                                   │
    │                                │  2. Render template               │
    │                                │     EmailTemplateRenderer.render( │
    │                                │       "verification", lang, data) │
    │                                │                                   │
    │                                │     ┌─────────────────────────┐   │
    │                                │     │ Load i18n translations  │   │
    │                                │     │ OR database template    │   │
    │                                │     │                         │   │
    │                                │     │ Interpolate variables   │   │
    │                                │     │ Generate HTML + text    │   │
    │                                │     └─────────────────────────┘   │
    │                                │                                   │
    │                                │  3. Queue email                   │
    │                                │     EmailQueue.enqueue({          │
    │                                │       to, subject, html, text,    │
    │                                │       template, userId, priority  │
    │                                │     })                            │
    │                                │                                   │
    │                                │  4. Return queued status          │
    │  { queued: true, emailId }     │                                   │
    │<───────────────────────────────│                                   │
    │                                │                                   │
    │                                │  [Background: Queue processor     │
    │                                │   picks up and sends]             │
    │                                │                                   │
```

**Steps:**
1. Check rate limit for this email type and recipient
2. If rate limit exceeded, return error (do not queue)
3. Render email template using i18n translations or database template
4. Interpolate variables (name, token, URLs, etc.)
5. Generate both HTML and plain text versions
6. Add email to queue with priority and metadata
7. Return queued confirmation with email ID
8. Background processor handles actual delivery

**Rate Limits (Default):**
| Email Type | Limit |
|------------|-------|
| verification | 3 per hour |
| password_reset | 3 per hour |
| reminder | 1 per day |
| weekly_focus | 1 per week |

**Error Cases:**
- Rate limit exceeded → 429 Too Many Requests
- Invalid email address → 400 Bad Request
- Template not found → 500 Internal Server Error

---

### Pipeline 2: Process Email Queue

Background worker that processes queued emails with retry logic.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PROCESS EMAIL QUEUE PIPELINE                          │
└─────────────────────────────────────────────────────────────────────────────┘

Scheduler                        Email System                        External
─────────                        ────────────                        ────────
    │                                │                                   │
    │  [Cron: every 30 seconds]      │                                   │
    │───────────────────────────────>│                                   │
    │                                │                                   │
    │                                │  1. Fetch pending emails          │
    │                                │     EmailQueue.get_pending(       │
    │                                │       limit=10, order_by=priority)│
    │                                │                                   │
    │                                │  2. For each email:               │
    │                                │     ┌─────────────────────────┐   │
    │                                │     │ Mark as "processing"    │   │
    │                                │     └─────────────────────────┘   │
    │                                │                                   │
    │                                │  3. Send via provider             │
    │                                │     EmailService.send(email)      │
    │                                │                                   │
    │                                │     ┌─────────────────────────┐   │
    │                                │     │ MODE: resend            │   │
    │                                │     │ POST to Resend API ─────────────>
    │                                │     │                         │   │
    │                                │     │ MODE: smtp              │   │
    │                                │     │ nodemailer.sendMail() ──────────>
    │                                │     │                         │   │
    │                                │     │ MODE: console           │   │
    │                                │     │ console.log()           │   │
    │                                │     └─────────────────────────┘   │
    │                                │                                   │
    │                                │  4. On success:                   │
    │                                │     - Mark as "sent"              │
    │                                │     - Log to EmailLog             │
    │                                │     - Record messageId            │
    │                                │                                   │
    │                                │  5. On failure:                   │
    │                                │     - Increment retryCount        │
    │                                │     - Set nextRetryAt (backoff)   │
    │                                │     - If maxRetries reached:      │
    │                                │       Mark as "failed"            │
    │                                │       Log failure                 │
    │                                │                                   │
    │  [Continue loop]               │                                   │
    │                                │                                   │
```

**Steps:**
1. Cron job triggers queue processor every 30 seconds
2. Fetch pending emails (status = "pending" or "retry"), ordered by priority
3. Mark each email as "processing" to prevent duplicate sends
4. Attempt to send via configured provider (Resend, SMTP, or console)
5. On success: update status to "sent", log to EmailLog, store provider messageId
6. On failure: increment retry count, calculate next retry time with exponential backoff
7. If max retries reached, mark as "failed" and log for admin review

**Retry Strategy:**
| Attempt | Delay |
|---------|-------|
| 1 | Immediate |
| 2 | 5 minutes |
| 3 | 15 minutes |
| 4 | 1 hour |
| 5 | 4 hours (final) |

**Queue Priorities:**
| Priority | Value | Use Case |
|----------|-------|----------|
| Critical | 1 | Password reset, verification |
| High | 2 | Meeting notifications |
| Normal | 3 | Welcome, invitations |
| Low | 4 | Weekly focus, reminders |

---

### Pipeline 3: Send Scheduled Email

Automated emails triggered by cron jobs (weekly focus, reminders).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       SEND SCHEDULED EMAIL PIPELINE                          │
└─────────────────────────────────────────────────────────────────────────────┘

                              WEEKLY FOCUS EMAIL
Scheduler                        Email System                        Database
─────────                        ────────────                        ────────
    │                                │                                   │
    │  [Cron: Monday 9:00 AM]        │                                   │
    │───────────────────────────────>│                                   │
    │                                │                                   │
    │                                │  1. Get eligible users            │
    │                                │     ┌─────────────────────────┐   │
    │                                │     │ Find users where:       │   │
    │                                │     │ - status = "active"     │   │
    │                                │     │ - accountType = "trial" │   │
    │                                │     │ - emailPrefs.weeklyFocus│   │
    │                                │     │   = true                │   │
    │                                │     └─────────────────────────┘   │
    │                                │                                   │
    │                                │  2. For each user:                │
    │                                │     - Get user's language         │
    │                                │     - Generate focus content      │
    │                                │       (based on recent activity)  │
    │                                │                                   │
    │                                │  3. Queue email                   │
    │                                │     send_weekly_focus_email(      │
    │                                │       email, name, lang,          │
    │                                │       focusContent)               │
    │                                │                                   │
    │                                │  4. Log batch completion          │
    │                                │                                   │


                              CHECK-IN REMINDER
Scheduler                        Email System                        Database
─────────                        ────────────                        ────────
    │                                │                                   │
    │  [Cron: Daily 6:00 PM]         │                                   │
    │───────────────────────────────>│                                   │
    │                                │                                   │
    │                                │  1. Get users needing reminder    │
    │                                │     ┌─────────────────────────┐   │
    │                                │     │ Find users where:       │   │
    │                                │     │ - status = "active"     │   │
    │                                │     │ - emailPrefs.reminders  │   │
    │                                │     │   = true                │   │
    │                                │     │ - No check-in today     │   │
    │                                │     │ - Last reminder > 24h   │   │
    │                                │     └─────────────────────────┘   │
    │                                │                                   │
    │                                │  2. For each user:                │
    │                                │     - Check reminder frequency    │
    │                                │     - Get streak info             │
    │                                │                                   │
    │                                │  3. Queue reminder email          │
    │                                │     send_reminder_email(          │
    │                                │       email, name, lang,          │
    │                                │       streakDays)                 │
    │                                │                                   │
    │                                │  4. Update lastReminderSentAt     │
    │                                │                                   │
```

**Weekly Focus Email:**
1. Cron triggers on Monday at 9:00 AM (configurable)
2. Query users: active, trial account, opted-in to weekly emails
3. For each user, generate personalized focus content based on activity
4. Queue email with low priority (batch send)
5. Log batch completion with count sent

**Check-in Reminder:**
1. Cron triggers daily at 6:00 PM (configurable per timezone)
2. Query users: active, opted-in, no check-in today, not recently reminded
3. Include streak information for motivation
4. Queue reminder with low priority
5. Update user's lastReminderSentAt to prevent spam

**Scheduled Email Types:**
| Type | Trigger | Target Users |
|------|---------|--------------|
| Weekly Focus | Monday 9 AM | Trial users, opted-in |
| Check-in Reminder | Daily 6 PM | Active, opted-in, no check-in today |
| Streak Warning | Daily | Users about to lose streak |
| Inactivity | Weekly | Users inactive 7+ days |

---

### Pipeline 4: Get Email Log

Retrieve email history for user or admin audit.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          GET EMAIL LOG PIPELINE                              │
└─────────────────────────────────────────────────────────────────────────────┘

                                USER VIEW
Frontend                         Backend                            Database
────────                         ───────                            ────────
    │                                │                                   │
    │  GET /api/profile/emails       │                                   │
    │  ?page=1&limit=20              │                                   │
    │───────────────────────────────>│                                   │
    │                                │                                   │
    │                                │  1. Get current user ID           │
    │                                │                                   │
    │                                │  2. Query EmailLog                │
    │                                │     { userId, status: "sent" }    │
    │                                │     sort: -sentAt                 │
    │                                │     paginate                      │
    │                                │                                   │
    │                                │  3. Format response               │
    │                                │     (hide internal fields)        │
    │                                │                                   │
    │  { emails: [...],              │                                   │
    │    total, page, pages }        │                                   │
    │<───────────────────────────────│                                   │


                                ADMIN VIEW
Admin                            Backend                            Database
─────                            ───────                            ────────
    │                                │                                   │
    │  GET /admin/emails             │                                   │
    │  ?status=failed&days=7         │                                   │
    │───────────────────────────────>│                                   │
    │                                │                                   │
    │                                │  1. Verify admin role             │
    │                                │                                   │
    │                                │  2. Query EmailLog with filters   │
    │                                │     - status (sent/failed/all)    │
    │                                │     - date range                  │
    │                                │     - email type                  │
    │                                │     - recipient                   │
    │                                │                                   │
    │                                │  3. Include full details          │
    │                                │     - Error messages              │
    │                                │     - Retry attempts              │
    │                                │     - Provider response           │
    │                                │                                   │
    │  { emails: [...],              │                                   │
    │    stats: { sent, failed } }   │                                   │
    │<───────────────────────────────│                                   │
```

**User View:**
- See emails sent to their address
- Limited fields (subject, type, sentAt, status)
- Pagination support

**Admin View:**
- See all emails across system
- Filter by status, type, date range, recipient
- Full details including errors and retries
- Aggregate stats (sent count, failure rate)

---

## Components

### EmailService

Core email sending service with multi-provider support.

```python
class EmailService:
    """
    Handles actual email delivery via configured provider.
    Supports Resend API, SMTP, and console (dev) modes.
    """

    def __init__(
        self,
        mode: str = "console",
        resend_api_key: str = None,
        smtp_config: dict = None,
        from_email: str = "noreply@example.com",
        from_name: str = "Eve"
    ):
        """
        Args:
            mode: "console" | "resend" | "smtp"
            resend_api_key: API key for Resend
            smtp_config: SMTP settings (host, port, user, pass)
            from_email: Sender email address
            from_name: Sender display name
        """

    def send(self, email: dict) -> dict:
        """
        Send an email via configured provider.

        Args:
            email: Dict with keys:
                - to: Recipient email address
                - subject: Email subject
                - html: HTML content
                - text: Plain text content

        Returns:
            dict with keys:
                - success: bool
                - mode: Provider used
                - messageId: Provider's message ID (if success)
                - error: Error message (if failed)
        """

    def send_via_resend(self, email: dict) -> dict:
        """
        Send email using Resend HTTP API.

        Args:
            email: Email data dict

        Returns:
            Result dict with success/error
        """

    def send_via_smtp(self, email: dict) -> dict:
        """
        Send email using SMTP/nodemailer.

        Args:
            email: Email data dict

        Returns:
            Result dict with success/error
        """

    def test_connection(self) -> dict:
        """
        Test email provider connection.

        Returns:
            dict with success bool and message
        """
```

---

### EmailQueue

Manages email queue with priority and retry logic.

```python
class EmailQueue:
    """
    Queue-based email management for reliable delivery.
    Stores pending emails in MongoDB with retry support.
    """

    def __init__(self, db: Database):
        """
        Args:
            db: MongoDB database connection
        """

    def enqueue(
        self,
        to: str,
        subject: str,
        html: str,
        text: str,
        template_type: str,
        user_id: str = None,
        priority: int = 3,
        metadata: dict = None
    ) -> str:
        """
        Add email to queue.

        Args:
            to: Recipient email
            subject: Email subject
            html: HTML content
            text: Plain text content
            template_type: Type of email (verification, reminder, etc.)
            user_id: Associated user ID (optional)
            priority: 1=critical, 2=high, 3=normal, 4=low
            metadata: Additional data for logging

        Returns:
            Queue entry ID
        """

    def get_pending(self, limit: int = 10) -> list[dict]:
        """
        Get pending emails ready to send.

        Args:
            limit: Max emails to fetch

        Returns:
            List of email queue entries, ordered by priority then createdAt

        Query:
            status in ["pending", "retry"]
            AND (nextRetryAt is null OR nextRetryAt <= now)
        """

    def mark_processing(self, email_id: str) -> bool:
        """
        Mark email as being processed (prevents duplicate sends).

        Args:
            email_id: Queue entry ID

        Returns:
            True if marked, False if already processing
        """

    def mark_sent(self, email_id: str, message_id: str) -> None:
        """
        Mark email as successfully sent.

        Args:
            email_id: Queue entry ID
            message_id: Provider's message ID
        """

    def mark_failed(self, email_id: str, error: str) -> None:
        """
        Mark email as permanently failed (max retries reached).

        Args:
            email_id: Queue entry ID
            error: Final error message
        """

    def schedule_retry(self, email_id: str, error: str) -> None:
        """
        Schedule email for retry with exponential backoff.

        Args:
            email_id: Queue entry ID
            error: Error message from this attempt

        Side Effects:
            - Increments retryCount
            - Sets nextRetryAt based on backoff strategy
            - If maxRetries reached, calls mark_failed instead
        """

    def get_retry_delay(self, retry_count: int) -> int:
        """
        Calculate delay for next retry (exponential backoff).

        Args:
            retry_count: Current retry count

        Returns:
            Delay in seconds
            1 → 0, 2 → 300, 3 → 900, 4 → 3600, 5 → 14400
        """

    def cleanup_old_entries(self, days: int = 30) -> int:
        """
        Remove old sent/failed entries from queue.

        Args:
            days: Remove entries older than this

        Returns:
            Count of entries removed
        """
```

---

### EmailTemplateRenderer

Renders email templates with i18n support and variable interpolation.

```python
class EmailTemplateRenderer:
    """
    Renders email templates with localization support.
    Supports code-based templates with optional database override.
    """

    def __init__(
        self,
        i18n_service: I18nService,
        db: Database = None,
        source_mode: str = "code"
    ):
        """
        Args:
            i18n_service: For loading translations
            db: Database connection (for database templates)
            source_mode: "code" or "database"
        """

    def render(
        self,
        template_type: str,
        lang: str,
        data: dict
    ) -> dict:
        """
        Render email template to HTML and text.

        Args:
            template_type: Template name (verification, password_reset, etc.)
            lang: Language code
            data: Variables for interpolation

        Returns:
            dict with keys:
                - subject: Rendered subject line
                - html: Full HTML email
                - text: Plain text version
        """

    def get_template(self, template_type: str, lang: str) -> dict:
        """
        Get template content from source.

        Args:
            template_type: Template name
            lang: Language code

        Returns:
            Template dict with subject, content sections

        Priority:
            1. Database template (if source_mode="database" and exists)
            2. Code-based template with i18n translations
        """

    def render_html(self, content: str, data: dict) -> str:
        """
        Wrap content in HTML email structure.

        Args:
            content: Inner HTML content
            data: Variables for interpolation

        Returns:
            Full HTML email with header, body, footer, styles
        """

    def render_text(self, content: str, data: dict) -> str:
        """
        Generate plain text version.

        Args:
            content: Text content with placeholders
            data: Variables for interpolation

        Returns:
            Plain text email
        """

    def interpolate(self, text: str, data: dict) -> str:
        """
        Replace {{variable}} placeholders with values.

        Args:
            text: Template string
            data: Variable values

        Returns:
            Interpolated string
        """

    def get_styles(self) -> str:
        """
        Get CSS styles for HTML emails.

        Returns:
            CSS string (Nordic/Scandinavian design)
        """
```

---

### EmailLogger

Logs all email activity for audit and debugging.

```python
class EmailLogger:
    """
    Logs sent emails to database for audit trail.
    """

    def __init__(self, db: Database):
        """
        Args:
            db: MongoDB database connection
        """

    def log_sent(
        self,
        to: str,
        subject: str,
        template_type: str,
        user_id: str = None,
        message_id: str = None,
        provider: str = None,
        metadata: dict = None
    ) -> str:
        """
        Log a successfully sent email.

        Args:
            to: Recipient email
            subject: Email subject
            template_type: Type of email
            user_id: Associated user (optional)
            message_id: Provider's message ID
            provider: Email provider used
            metadata: Additional context

        Returns:
            Log entry ID
        """

    def log_failed(
        self,
        to: str,
        subject: str,
        template_type: str,
        error: str,
        user_id: str = None,
        retry_count: int = 0,
        metadata: dict = None
    ) -> str:
        """
        Log a failed email send.

        Args:
            to: Recipient email
            subject: Email subject
            template_type: Type of email
            error: Error message
            user_id: Associated user (optional)
            retry_count: Number of attempts made
            metadata: Additional context

        Returns:
            Log entry ID
        """

    def get_user_emails(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 20
    ) -> dict:
        """
        Get email history for a user.

        Args:
            user_id: User's ID
            page: Page number
            limit: Items per page

        Returns:
            dict with emails list and pagination info
        """

    def get_all_emails(
        self,
        filters: dict = None,
        page: int = 1,
        limit: int = 50
    ) -> dict:
        """
        Get all emails with optional filters (admin).

        Args:
            filters: Optional filters (status, type, dateRange, recipient)
            page: Page number
            limit: Items per page

        Returns:
            dict with emails list, pagination, and stats
        """

    def get_stats(self, days: int = 7) -> dict:
        """
        Get email statistics for period.

        Args:
            days: Period in days

        Returns:
            dict with:
                - totalSent: Count of sent emails
                - totalFailed: Count of failed emails
                - byType: Breakdown by email type
                - failureRate: Percentage failed
        """
```

---

### EmailRateLimiter

Rate limiting to prevent email abuse.

```python
class EmailRateLimiter:
    """
    Rate limits emails per recipient and type.
    Prevents abuse and accidental spam.
    """

    def __init__(self, db: Database):
        """
        Args:
            db: MongoDB database connection
        """

    def check(
        self,
        email: str,
        template_type: str
    ) -> dict:
        """
        Check if email can be sent (rate limit not exceeded).

        Args:
            email: Recipient email address
            template_type: Type of email

        Returns:
            dict with:
                - allowed: bool
                - remaining: Count remaining in window
                - resetAt: When limit resets
        """

    def record(self, email: str, template_type: str) -> None:
        """
        Record an email send for rate limiting.

        Args:
            email: Recipient email address
            template_type: Type of email
        """

    def get_limits(self) -> dict:
        """
        Get configured rate limits.

        Returns:
            dict mapping template_type → { limit, window_seconds }
        """

    def set_limit(
        self,
        template_type: str,
        limit: int,
        window_seconds: int
    ) -> None:
        """
        Configure rate limit for email type.

        Args:
            template_type: Type of email
            limit: Max emails in window
            window_seconds: Time window in seconds
        """
```

**Default Limits:**
```python
{
    "verification": { "limit": 3, "window": 3600 },      # 3 per hour
    "password_reset": { "limit": 3, "window": 3600 },   # 3 per hour
    "reminder": { "limit": 1, "window": 86400 },        # 1 per day
    "weekly_focus": { "limit": 1, "window": 604800 },   # 1 per week
    "circle_invitation": { "limit": 5, "window": 86400 } # 5 per day
}
```

---

### EmailScheduler

Manages scheduled/automated email campaigns.

```python
class EmailScheduler:
    """
    Handles scheduled and automated email sending.
    Triggered by cron jobs for batch email operations.
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
            email_queue: For queueing emails
            template_renderer: For rendering templates
        """

    def send_weekly_focus_emails(self) -> dict:
        """
        Send weekly focus emails to eligible trial users.
        Called by cron (e.g., Monday 9 AM).

        Returns:
            dict with:
                - queued: Count of emails queued
                - skipped: Count skipped (opted out, etc.)
                - errors: List of errors

        Eligible Users:
            - status = "active"
            - accountType = "trial"
            - emailPreferences.weeklyFocus = true
        """

    def send_checkin_reminders(self) -> dict:
        """
        Send check-in reminder emails to users who haven't checked in.
        Called by cron (e.g., daily 6 PM).

        Returns:
            dict with queued, skipped, errors counts

        Eligible Users:
            - status = "active"
            - emailPreferences.reminders = true
            - No check-in today
            - lastReminderSentAt > 24 hours ago
        """

    def send_streak_warnings(self) -> dict:
        """
        Warn users about to lose their streak.
        Called by cron (e.g., daily 8 PM).

        Returns:
            dict with queued, skipped, errors counts

        Eligible Users:
            - Has active streak >= 3 days
            - No check-in today
            - emailPreferences.streakWarnings = true
        """

    def send_inactivity_emails(self) -> dict:
        """
        Re-engage users who have been inactive.
        Called by cron (e.g., weekly).

        Returns:
            dict with queued, skipped, errors counts

        Eligible Users:
            - status = "active"
            - lastActiveAt > 7 days ago
            - emailPreferences.reEngagement = true
            - Not sent inactivity email in last 14 days
        """

    def get_eligible_users(self, criteria: dict) -> list[dict]:
        """
        Query users matching criteria for scheduled emails.

        Args:
            criteria: Query criteria dict

        Returns:
            List of user dicts with email, name, language, etc.
        """

    def generate_focus_content(self, user_id: str) -> dict:
        """
        Generate personalized weekly focus content.

        Args:
            user_id: User's ID

        Returns:
            dict with focus topic, tips, and suggested actions
            based on user's recent activity and progress
        """
```

---

## Data Models

### EmailQueue (Collection)

```python
# email_queue collection
{
    "_id": ObjectId,
    "to": str,                    # Recipient email
    "subject": str,               # Email subject
    "html": str,                  # HTML content
    "text": str,                  # Plain text content
    "templateType": str,          # verification, password_reset, etc.
    "userId": ObjectId | None,    # Associated user
    "priority": int,              # 1=critical, 2=high, 3=normal, 4=low
    "status": str,                # pending, processing, sent, failed, retry
    "retryCount": int,            # Number of retry attempts
    "maxRetries": int,            # Max retries allowed (default: 5)
    "nextRetryAt": datetime | None,  # When to retry
    "error": str | None,          # Last error message
    "messageId": str | None,      # Provider's message ID
    "metadata": dict,             # Additional context
    "createdAt": datetime,
    "updatedAt": datetime,
    "sentAt": datetime | None
}
```

**Indexes:**
- `{ status: 1, priority: 1, createdAt: 1 }` - Queue processing
- `{ status: 1, nextRetryAt: 1 }` - Retry scheduling
- `{ userId: 1, createdAt: -1 }` - User email history
- `{ createdAt: 1 }` - TTL index for cleanup

---

### EmailLog (Collection)

```python
# email_logs collection
{
    "_id": ObjectId,
    "to": str,                    # Recipient email
    "subject": str,               # Email subject
    "templateType": str,          # Type of email
    "userId": ObjectId | None,    # Associated user
    "status": str,                # sent, failed
    "provider": str,              # resend, smtp, console
    "messageId": str | None,      # Provider's message ID
    "error": str | None,          # Error message if failed
    "retryCount": int,            # Attempts made
    "metadata": dict,             # Additional context
    "sentAt": datetime,
    "createdAt": datetime
}
```

**Indexes:**
- `{ userId: 1, sentAt: -1 }` - User email history
- `{ status: 1, sentAt: -1 }` - Admin filtering
- `{ templateType: 1, sentAt: -1 }` - Type filtering
- `{ sentAt: 1 }` - TTL index (90 days retention)

---

### EmailRateLimit (Collection)

```python
# email_rate_limits collection
{
    "_id": ObjectId,
    "email": str,                 # Recipient email (hashed)
    "templateType": str,          # Type of email
    "count": int,                 # Sends in current window
    "windowStart": datetime,      # Current window start
    "expiresAt": datetime         # TTL expiration
}
```

**Indexes:**
- `{ email: 1, templateType: 1 }` - Unique, for lookup
- `{ expiresAt: 1 }` - TTL index for auto-cleanup

---

### EmailTemplate (Collection - Future Database Mode)

```python
# email_templates collection (future)
{
    "_id": ObjectId,
    "templateType": str,          # verification, password_reset, etc.
    "lang": str,                  # Language code
    "subject": str,               # Subject line template
    "htmlContent": str,           # HTML body template
    "textContent": str,           # Plain text template
    "isActive": bool,             # Whether to use (vs code default)
    "createdAt": datetime,
    "updatedAt": datetime,
    "updatedBy": ObjectId         # Admin who last edited
}
```

**Indexes:**
- `{ templateType: 1, lang: 1 }` - Unique, for lookup

---

## Configuration

```python
# Environment variables
EMAIL_MODE = "resend"                    # console | resend | smtp
RESEND_API_KEY = "re_..."                # Resend API key
SMTP_FROM_EMAIL = "noreply@example.com"  # Sender email
SMTP_FROM_NAME = "Eve"                   # Sender name
APP_URL = "https://app.example.com"      # For email links

# SMTP config (legacy)
SMTP_HOST = "smtp.example.com"
SMTP_PORT = 465
SMTP_USERNAME = "user"
SMTP_PASSWORD = "pass"

# Queue settings
EMAIL_QUEUE_BATCH_SIZE = 10              # Emails per queue run
EMAIL_QUEUE_INTERVAL_SECONDS = 30        # Queue processor interval
EMAIL_MAX_RETRIES = 5                    # Max retry attempts

# Scheduled email settings
WEEKLY_FOCUS_DAY = "monday"              # Day to send weekly focus
WEEKLY_FOCUS_HOUR = 9                    # Hour (24h) to send
REMINDER_HOUR = 18                       # Hour for daily reminders

# Rate limiting
EMAIL_RATE_LIMIT_ENABLED = true          # Enable/disable rate limiting
```

---

## Email Types Reference

| Type | Template | Priority | Rate Limit |
|------|----------|----------|------------|
| `verification` | Verify account | Critical (1) | 3/hour |
| `password_reset` | Reset password | Critical (1) | 3/hour |
| `password_changed` | Password changed | High (2) | - |
| `welcome` | Welcome after verify | Normal (3) | 1/user |
| `deletion_scheduled` | Account deletion | High (2) | 1/user |
| `circle_invitation` | Circle invite | Normal (3) | 5/day |
| `group_assignment` | Group assigned | Normal (3) | - |
| `meeting_scheduled` | Meeting created | High (2) | - |
| `meeting_cancelled` | Meeting cancelled | High (2) | - |
| `weekly_focus` | Weekly focus | Low (4) | 1/week |
| `checkin_reminder` | Check-in reminder | Low (4) | 1/day |
| `streak_warning` | Streak at risk | Low (4) | 1/day |
| `inactivity` | Re-engagement | Low (4) | 1/14 days |

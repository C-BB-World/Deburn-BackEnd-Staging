# Hub (Platform Admin) System

Global platform administration for managing hub admins, organizations, content library, AI coach configuration, and GDPR compliance.

> **Note**: Hub uses a **separate MongoDB database** (`HUB_MONGODB_URI`) isolated from the main application data.

---

## Pipelines

### 1. Manage Hub Admins

```
┌─────────────────────────────────────────────────────────────────┐
│                     MANAGE HUB ADMINS                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────┐    ┌──────────────┐    ┌─────────────────────┐    │
│  │ Request │───>│ HubAdminSvc  │───>│ HubAdmin Collection │    │
│  └─────────┘    └──────────────┘    └─────────────────────┘    │
│       │                                       │                 │
│       │         Actions:                      │                 │
│       │         • List active admins          │                 │
│       │         • Add admin (by email)        │                 │
│       │         • Remove admin (soft delete)  │                 │
│       │         • Reactivate removed admin    │                 │
│       │                                       │                 │
│       │              ┌────────────────────────┘                 │
│       │              │                                          │
│       v              v                                          │
│  ┌─────────────────────┐                                        │
│  │      Response       │                                        │
│  └─────────────────────┘                                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Add Hub Admin**: Validates email, checks if already exists. If previously removed, reactivates. Otherwise creates new admin record with `addedBy` tracking.

**Remove Hub Admin**: Soft delete - sets `status: 'removed'`, records `removedBy` and `removedAt`. Cannot remove self.

---

### 2. Manage Content Library

```
┌─────────────────────────────────────────────────────────────────┐
│                   MANAGE CONTENT LIBRARY                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────┐    ┌─────────────┐    ┌───────────────────────┐   │
│  │ Request │───>│ ContentSvc  │───>│ ContentItem Collection│   │
│  └─────────┘    └─────────────┘    └───────────────────────┘   │
│       │                │                                        │
│       │                │  Content Types:                        │
│       │                │  • text_article                        │
│       │                │  • audio_article                       │
│       │                │  • audio_exercise                      │
│       │                │  • video_link                          │
│       │                │  • (future: interactive_quiz, pdf)     │
│       │                │                                        │
│       │                │  Status Flow:                          │
│       │                │  draft → in_review → published         │
│       │                │                  ↓                     │
│       │                │              archived                  │
│       │                │                                        │
│  ┌────┴────┐           │                                        │
│  │  Audio  │───────────┘                                        │
│  │ Upload  │  Binary stored in MongoDB (up to 50MB)             │
│  └─────────┘  Streamed via /api/audio/:id/:lang                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Content CRUD**: Create, read, update, delete content items with i18n support (English/Swedish). Filter by `contentType`, `status`, `category`.

**Audio Upload**: Audio files stored as binary data in MongoDB. Supports MP3, WAV, OGG, M4A up to 50MB. Served via streaming endpoint.

**Coach Integration**: Content items can be tagged with `coachTopics` for AI coach recommendations, with `coachPriority` for ranking.

---

### 3. Configure AI Coach

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONFIGURE AI COACH                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Configuration Areas                   │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │                                                          │   │
│  │  ┌──────────────┐  System prompts stored as .md files   │   │
│  │  │   Prompts    │  in prompts/system/{en,sv}/           │   │
│  │  │  (per lang)  │  Read/write via filesystem            │   │
│  │  └──────────────┘                                        │   │
│  │                                                          │   │
│  │  ┌──────────────┐  Exercises and modules stored in      │   │
│  │  │  Exercises   │  knowledge-base/exercises/            │   │
│  │  │  & Modules   │  as JSON file                         │   │
│  │  └──────────────┘                                        │   │
│  │                                                          │   │
│  │  ┌──────────────┐  Platform-wide settings               │   │
│  │  │   Settings   │  • dailyExchangeLimit (1-100)         │   │
│  │  │ (HubSettings)│  Stored in hub database               │   │
│  │  └──────────────┘                                        │   │
│  │                                                          │   │
│  │  ┌──────────────┐  Safety Escalation (3 levels):        │   │
│  │  │   Safety     │  L1: Soft (continue with caution)     │   │
│  │  │  Keywords    │  L2: Professional referral            │   │
│  │  │  (read-only) │  L3: Crisis (stop immediately)        │   │
│  │  └──────────────┘                                        │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Prompts**: System prompts for AI coach stored as markdown files, editable per language.

**Settings**: Global coach settings (e.g., `dailyExchangeLimit`) stored in HubSettings collection.

**Safety Keywords**: Three-tier escalation system for detecting user distress. Currently read-only (hardcoded in service).

---

### 4. GDPR Compliance

```
┌─────────────────────────────────────────────────────────────────┐
│                     GDPR COMPLIANCE                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Compliance Operations                   │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │                                                          │   │
│  │  Dashboard Stats:                                        │   │
│  │  • Total users                                           │   │
│  │  • Pending deletions                                     │   │
│  │  • Audit log entries                                     │   │
│  │  • Active sessions                                       │   │
│  │                                                          │   │
│  │  ┌──────────────┐    Article 20 - Data Portability      │   │
│  │  │ Data Export  │    Exports: profile, check-ins,       │   │
│  │  │              │    sessions, audit logs               │   │
│  │  └──────────────┘    Returns JSON for download          │   │
│  │                                                          │   │
│  │  ┌──────────────┐    Article 17 - Right to Erasure      │   │
│  │  │   Account    │    Cascade deletes check-ins,         │   │
│  │  │  Deletion    │    anonymizes audit logs,             │   │
│  │  └──────────────┘    removes user record                │   │
│  │                                                          │   │
│  │  ┌──────────────┐    Grace period before deletion       │   │
│  │  │   Pending    │    (configurable, default 30 days)    │   │
│  │  │  Deletions   │    List/process pending requests      │   │
│  │  └──────────────┘                                        │   │
│  │                                                          │   │
│  │  ┌──────────────┐    Remove expired sessions            │   │
│  │  │   Session    │    from all users                     │   │
│  │  │   Cleanup    │                                        │   │
│  │  └──────────────┘                                        │   │
│  │                                                          │   │
│  │  ┌──────────────┐    View security settings             │   │
│  │  │   Security   │    (token expiry, CORS, data          │   │
│  │  │   Config     │    retention - read-only)             │   │
│  │  └──────────────┘                                        │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Data Export**: Compiles all user data (profile, check-ins, sessions, audit logs) into portable JSON format per GDPR Article 20.

**Account Deletion**: Permanently removes user and all associated data. Audit logs are anonymized (PII removed) but retained for compliance.

**Session Cleanup**: Bulk removal of expired sessions across all users.

---

## Components

### HubAdminService

```python
class HubAdminService:
    """
    Manages platform-level super admins.
    Uses separate hub database connection.
    """

    def __init__(self, hub_db: HubDatabase):
        self.hub_db = hub_db

    def is_hub_admin(self, email: str) -> bool:
        """Check if email is an active hub admin."""

    def get_active_admins(self) -> list[HubAdmin]:
        """List all active hub admins."""

    def add_admin(self, email: str, added_by: str) -> HubAdmin:
        """
        Add new hub admin or reactivate removed one.

        Raises:
            AlreadyExistsError: If email is already active admin
        """

    def remove_admin(self, email: str, removed_by: str) -> HubAdmin:
        """
        Soft-delete hub admin.

        Raises:
            NotFoundError: If admin not found
            ValidationError: If trying to remove self
        """

    def seed_initial_admin(self, email: str = "aurora@brainbank.world") -> None:
        """Create initial admin if none exist."""
```

---

### ContentService

```python
class ContentService:
    """
    Manages content library items.
    Supports multiple content types with i18n.
    """

    def __init__(self, hub_db: HubDatabase):
        self.hub_db = hub_db

    def get_all(
        self,
        content_type: str | None = None,
        status: str | None = None,
        category: str | None = None
    ) -> list[ContentItem]:
        """Get content items with optional filters."""

    def get_by_id(self, content_id: str) -> ContentItem | None:
        """Get single content item by ID."""

    def get_published(self) -> list[ContentItem]:
        """Get all published content for users."""

    def get_for_coach(self, topics: list[str]) -> list[ContentItem]:
        """
        Get content matching coach topics.
        Sorted by coachPriority descending.
        Only returns coachEnabled=True items.
        """

    def create(self, data: ContentItemCreate) -> ContentItem:
        """Create new content item."""

    def update(self, content_id: str, data: ContentItemUpdate) -> ContentItem | None:
        """Update existing content item."""

    def delete(self, content_id: str) -> bool:
        """Delete content item."""

    def upload_audio(
        self,
        content_id: str,
        language: str,  # 'en' or 'sv'
        audio_data: bytes,
        mime_type: str
    ) -> str:
        """
        Upload audio file for content item.
        Returns streaming URL.
        Max size: 50MB.
        """

    def remove_audio(self, content_id: str, language: str) -> bool:
        """Remove audio file from content item."""
```

---

### CoachConfigService

```python
class CoachConfigService:
    """
    Manages AI coach configuration.
    Prompts stored in filesystem, settings in database.
    """

    def __init__(self, hub_db: HubDatabase, prompts_dir: str):
        self.hub_db = hub_db
        self.prompts_dir = prompts_dir

    def get_prompts(self) -> dict[str, dict[str, str]]:
        """
        Get all system prompts by language.
        Returns: {'en': {'prompt_name': 'content'}, 'sv': {...}}
        """

    def update_prompt(self, language: str, prompt_name: str, content: str) -> None:
        """
        Update a system prompt file.

        Raises:
            NotFoundError: If prompt file doesn't exist
            ValidationError: If invalid language
        """

    def get_exercises(self) -> dict:
        """Get exercises and modules from JSON file."""

    def update_exercises(self, exercises: list, modules: list) -> None:
        """Update exercises and modules JSON file."""

    def get_coach_settings(self) -> CoachSettings:
        """Get coach settings (creates default if none)."""

    def update_coach_settings(
        self,
        daily_exchange_limit: int,
        admin_email: str
    ) -> CoachSettings:
        """
        Update coach settings.

        Args:
            daily_exchange_limit: 1-100 exchanges per user per day
            admin_email: Who made the change
        """

    def get_safety_config(self) -> SafetyConfig:
        """
        Get safety keyword configuration (read-only).
        Returns escalation levels and keywords.
        """
```

---

### ComplianceService

```python
class ComplianceService:
    """
    GDPR compliance operations.
    Handles data export, deletion, and session management.
    """

    def __init__(
        self,
        user_repo: UserRepository,
        checkin_repo: CheckInRepository,
        audit_log: AuditLog,
        settings_service: HubSettingsService
    ):
        self.user_repo = user_repo
        self.checkin_repo = checkin_repo
        self.audit_log = audit_log
        self.settings_service = settings_service

    def get_stats(self) -> ComplianceStats:
        """
        Get compliance dashboard statistics.
        Returns: total_users, pending_deletions, audit_log_count, active_sessions
        """

    def get_user_compliance_data(self, email: str) -> UserComplianceData | None:
        """Get user data for compliance review."""

    def export_user_data(self, user_id: str, exported_by: str) -> dict:
        """
        Export all user data (GDPR Article 20).
        Includes: profile, check-ins, sessions, audit logs.
        Logs the export action.
        """

    def delete_user_account(self, user_id: str, deleted_by: str) -> DeletionResult:
        """
        Permanently delete user account (GDPR Article 17).
        - Deletes all check-ins
        - Anonymizes audit logs (removes PII, keeps entries)
        - Deletes user record
        Returns: counts of deleted/anonymized records
        """

    def get_pending_deletions(self) -> list[PendingDeletion]:
        """Get users with pending deletion requests."""

    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions from all users. Returns count."""

    def get_security_config(self) -> SecurityConfig:
        """Get current security configuration (read-only)."""

    def get_deletion_grace_period(self) -> int:
        """Get configurable grace period in days (default: 30)."""

    def set_deletion_grace_period(self, days: int, admin_email: str) -> None:
        """Update deletion grace period."""
```

---

## Data Models

### HubAdmin (MongoDB - Hub Database)

```javascript
{
  _id: ObjectId,
  email: String,           // lowercase, unique
  addedBy: String,         // email of admin who added
  addedAt: Date,
  status: "active" | "removed",
  removedAt: Date,         // if removed
  removedBy: String,       // if removed
  createdAt: Date,
  updatedAt: Date
}
```

### HubSettings (MongoDB - Hub Database)

```javascript
{
  _id: ObjectId,
  key: "coachSettings",    // unique key for settings group
  dailyExchangeLimit: Number,  // 1-100, default: 15
  deletionGracePeriodDays: Number,  // default: 30
  updatedAt: Date,
  updatedBy: String,       // admin email
  createdAt: Date
}
```

### ContentItem (MongoDB - Hub Database)

```javascript
{
  _id: ObjectId,
  contentType: "text_article" | "audio_article" | "audio_exercise" | "video_link",
  status: "draft" | "in_review" | "published" | "archived",

  // i18n content
  titleEn: String,
  titleSv: String,
  textContentEn: String,   // text_article only
  textContentSv: String,

  // Audio (audio_article, audio_exercise)
  audioFileEn: String,     // streaming URL
  audioFileSv: String,
  audioDataEn: Buffer,     // binary data
  audioDataSv: Buffer,
  audioMimeTypeEn: String,
  audioMimeTypeSv: String,

  // Video (video_link only)
  videoUrl: String,
  videoEmbedCode: String,
  videoAvailableInEn: Boolean,
  videoAvailableInSv: Boolean,

  // Metadata
  lengthMinutes: Number,
  purpose: String,
  outcome: String,
  relatedFramework: String,
  category: "featured" | "leadership" | "breath" | "meditation" | "burnout" | "wellbeing" | "other",
  sortOrder: Number,

  // Coach integration
  coachTopics: [String],   // enum of coaching topics
  coachPriority: Number,   // higher = more likely to recommend
  coachEnabled: Boolean,   // default: true

  // TTS settings
  ttsSpeed: Number,        // 0.7-1.2, default: 1.0
  ttsVoice: String,        // default: "Aria"

  // Production
  voiceoverScriptEn: String,
  voiceoverScriptSv: String,
  backgroundMusicTrack: String,
  productionNotes: String,

  createdAt: Date,
  updatedAt: Date
}
```

---

## Safety Escalation Levels

| Level | Name | Action | Example Keywords (EN) |
|-------|------|--------|----------------------|
| 0 | Normal | Continue coaching | (default) |
| 1 | Soft Escalation | Continue with caution | "exhausted", "overwhelmed", "can't sleep" |
| 2 | Professional Referral | Redirect to expert | "legal rights", "medical symptoms", "financial stress" |
| 3 | Crisis | Stop coaching immediately | "suicide", "self-harm", "panic attack", "abuse" |

---

## Hard Boundaries

The AI coach will **never** provide advice on:
- Medical advice
- Legal advice
- Financial advice
- Mental health diagnosis

# Content & Learning System

## Description

The Content & Learning System manages all learning content (articles, audio, video, exercises) and tracks user progress. It supports dual-source loading (file-based or database) for flexibility during migration.

**Responsibilities:**
- Serve learning content from file or database
- Track user completion progress
- Provide content recommendations for coach
- Admin CRUD operations (database mode)
- Multi-language content support (EN/SV)

**Tech Stack:**
- **MongoDB** - Content storage (future), user progress tracking
- **File System** - Content storage (current)
- **Express** - RESTful API endpoints
- **Auth Middleware** - All endpoints require authentication

---

## Pipelines

### Pipeline 1: Get Content List

Retrieves all published content with user's progress merged in.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       GET CONTENT LIST PIPELINE                              │
└─────────────────────────────────────────────────────────────────────────────┘

Frontend                         Backend
────────                         ───────
    │                                │
    │  1. GET /api/learning/content  │
    │     ?category=leadership       │
    │     &contentType=audio_article │
    │     Authorization: Bearer <token>
    │───────────────────────────────>│
    │                                │
    │                                │  2. ContentService
    │                                │     .get_published()
    │                                │     (from file or DB)
    │                                │
    │                                │  3. LearningProgressService
    │                                │     .get_user_progress()
    │                                │
    │                                │  4. Merge content + progress
    │                                │
    │  5. Return content list        │
    │     with progress per item     │
    │<───────────────────────────────│
    │                                │
```

**Steps:**
1. Frontend requests content list with optional filters
2. Call `ContentService.get_published()` to load content (from file or database)
3. Call `LearningProgressService.get_user_progress()` to get completion data
4. Merge progress into content items
5. Return content list with `progress` field per item

**Error Cases:**
- Server error → 500 FETCH_FAILED

---

### Pipeline 2: Get Content Item

Retrieves a single content item by ID.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       GET CONTENT ITEM PIPELINE                              │
└─────────────────────────────────────────────────────────────────────────────┘

Frontend                         Backend
────────                         ───────
    │                                │
    │  1. GET /api/learning/         │
    │     content/:id                │
    │     Authorization: Bearer <token>
    │───────────────────────────────>│
    │                                │
    │                                │  2. ContentService
    │                                │     .get_by_id()
    │                                │
    │                                │  3. LearningProgressService
    │                                │     .get_item_progress()
    │                                │
    │  4. Return content item        │
    │     with user's progress       │
    │<───────────────────────────────│
    │                                │
```

**Steps:**
1. Frontend requests specific content item
2. Call `ContentService.get_by_id()` to load content
3. Call `LearningProgressService.get_item_progress()` for user's progress on this item
4. Return content with progress

**Error Cases:**
- Content not found → 404 NOT_FOUND
- Server error → 500 FETCH_FAILED

---

### Pipeline 3: Mark Content Complete

Records that a user has completed a content item.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     MARK CONTENT COMPLETE PIPELINE                           │
└─────────────────────────────────────────────────────────────────────────────┘

Frontend                         Backend
────────                         ───────
    │                                │
    │  1. POST /api/learning/        │
    │     content/:id/complete       │
    │     {progress: 100}            │
    │     Authorization: Bearer <token>
    │───────────────────────────────>│
    │                                │
    │                                │  2. Validate content exists
    │                                │     ContentService.get_by_id()
    │                                │
    │                                │  3. LearningProgressService
    │                                │     .update_progress()
    │                                │
    │  4. Return updated progress    │
    │<───────────────────────────────│
    │                                │
```

**Steps:**
1. Frontend sends completion with progress percentage
2. Validate content exists via `ContentService.get_by_id()`
3. Call `LearningProgressService.update_progress()` to record completion
4. Return updated progress

**Error Cases:**
- Content not found → 404 NOT_FOUND
- Server error → 500 UPDATE_FAILED

---

### Pipeline 4: Get Recommended Content

Retrieves content recommendations for coach based on conversation topics.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    GET RECOMMENDED CONTENT PIPELINE                          │
└─────────────────────────────────────────────────────────────────────────────┘

Coach System                     Content System
────────────                     ──────────────
    │                                │
    │  1. Get recommendations        │
    │     for topics: [stress,       │
    │     burnout, resilience]       │
    │───────────────────────────────>│
    │                                │
    │                                │  2. ContentService
    │                                │     .get_for_coach()
    │                                │     - Filter by coachTopics
    │                                │     - Filter coachEnabled
    │                                │     - Sort by coachPriority
    │                                │
    │  3. Return top N content       │
    │     items matching topics      │
    │<───────────────────────────────│
    │                                │
```

**Steps:**
1. Coach system requests content for detected topics
2. Call `ContentService.get_for_coach()` which:
   - Filters by `coachTopics` matching any provided topic
   - Filters only `coachEnabled: true`
   - Sorts by `coachPriority` descending
   - Limits to N items (default 2)
3. Return matching content items

**Error Cases:**
- No matches → Return empty array (not an error)
- Server error → 500 FETCH_FAILED

---

### Pipeline 5: Admin Create Content

Creates a new content item (database mode only).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      ADMIN CREATE CONTENT PIPELINE                           │
└─────────────────────────────────────────────────────────────────────────────┘

Admin Frontend                   Backend
──────────────                   ───────
    │                                │
    │  1. POST /api/hub/content      │
    │     {contentType, titleEn,     │
    │      category, ...}            │
    │     Authorization: Bearer <token>
    │───────────────────────────────>│
    │                                │
    │                                │  2. Validate admin permissions
    │                                │
    │                                │  3. Validate required fields
    │                                │
    │                                │  4. ContentService
    │                                │     .create()
    │                                │     (database mode only)
    │                                │
    │  5. Return created item        │
    │<───────────────────────────────│
    │                                │
```

**Steps:**
1. Admin submits new content data
2. Validate admin permissions
3. Validate required fields (contentType, titleEn)
4. Call `ContentService.create()` to insert into database
5. Return created content item

**Error Cases:**
- Not in database mode → 400 FILE_MODE_READ_ONLY
- Missing required fields → 400 VALIDATION_ERROR
- Server error → 500 CREATE_FAILED

---

### Pipeline 6: Admin Update Content

Updates an existing content item (database mode only).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      ADMIN UPDATE CONTENT PIPELINE                           │
└─────────────────────────────────────────────────────────────────────────────┘

Admin Frontend                   Backend
──────────────                   ───────
    │                                │
    │  1. PUT /api/hub/content/:id   │
    │     {titleEn, status, ...}     │
    │     Authorization: Bearer <token>
    │───────────────────────────────>│
    │                                │
    │                                │  2. Validate admin permissions
    │                                │
    │                                │  3. ContentService
    │                                │     .update()
    │                                │
    │  4. Return updated item        │
    │<───────────────────────────────│
    │                                │
```

**Steps:**
1. Admin submits updated content data
2. Validate admin permissions
3. Call `ContentService.update()` to update in database
4. Return updated content item

**Error Cases:**
- Not in database mode → 400 FILE_MODE_READ_ONLY
- Content not found → 404 NOT_FOUND
- Server error → 500 UPDATE_FAILED

---

### Pipeline 7: Admin Delete Content

Deletes a content item (database mode only).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      ADMIN DELETE CONTENT PIPELINE                           │
└─────────────────────────────────────────────────────────────────────────────┘

Admin Frontend                   Backend
──────────────                   ───────
    │                                │
    │  1. DELETE /api/hub/content/:id│
    │     Authorization: Bearer <token>
    │───────────────────────────────>│
    │                                │
    │                                │  2. Validate admin permissions
    │                                │
    │                                │  3. ContentService
    │                                │     .delete()
    │                                │
    │  4. Return success             │
    │<───────────────────────────────│
    │                                │
```

**Steps:**
1. Admin requests content deletion
2. Validate admin permissions
3. Call `ContentService.delete()` to remove from database
4. Return success

**Error Cases:**
- Not in database mode → 400 FILE_MODE_READ_ONLY
- Content not found → 404 NOT_FOUND
- Server error → 500 DELETE_FAILED

---

## Components

### ContentService

Manages content with dual-source support (file or database).

```python
class ContentService:
    """
    Handles content retrieval and management.
    Supports loading from file (current) or database (future).
    """

    def __init__(self, source_type: str, filepath: str = None, db: Database = None):
        """
        Args:
            source_type: 'file' or 'database'
            filepath: Path to content file if source_type is 'file'
            db: MongoDB connection if source_type is 'database'
        """

    # --- Read Operations (both modes) ---

    def get_all(self, filters: dict = None) -> list[dict]:
        """
        Get all content items with optional filters.

        Args:
            filters: Optional dict with contentType, status, category

        Returns:
            List of content items

        File mode: Loads from filepath, filters in memory
        Database mode: Queries MongoDB with filters
        """

    def get_published(self, filters: dict = None) -> list[dict]:
        """
        Get only published content items.

        Args:
            filters: Optional dict with contentType, category

        Returns:
            List of published content items
        """

    def get_by_id(self, content_id: str) -> dict | None:
        """
        Get a single content item by ID.

        Args:
            content_id: Content item ID

        Returns:
            Content item dict or None
        """

    def get_for_coach(self, topics: list[str], limit: int = 2) -> list[dict]:
        """
        Get content recommendations for coach.

        Args:
            topics: List of topic strings to match
            limit: Max items to return

        Returns:
            List of matching content items sorted by priority

        Filters:
            - coachTopics contains any of provided topics
            - coachEnabled is True
            - status is 'published'
        """

    # --- Write Operations (database mode only) ---

    def create(self, data: dict) -> dict:
        """
        Create a new content item.

        Args:
            data: Content item data

        Returns:
            Created content item

        Raises:
            NotSupportedError: If in file mode
        """

    def update(self, content_id: str, data: dict) -> dict | None:
        """
        Update a content item.

        Args:
            content_id: Content item ID
            data: Fields to update

        Returns:
            Updated content item or None if not found

        Raises:
            NotSupportedError: If in file mode
        """

    def delete(self, content_id: str) -> bool:
        """
        Delete a content item.

        Args:
            content_id: Content item ID

        Returns:
            True if deleted, False if not found

        Raises:
            NotSupportedError: If in file mode
        """

    # --- Internal Methods ---

    def _load_from_file(self) -> list[dict]:
        """
        Load content from filepath.

        Returns:
            List of content items from file
        """

    def _is_database_mode(self) -> bool:
        """
        Check if service is in database mode.

        Returns:
            True if database mode, False if file mode
        """
```

---

### LearningProgressService

Tracks user completion of content items.

```python
class LearningProgressService:
    """
    Tracks user progress through learning content.
    Stores completion data in MongoDB.
    """

    def __init__(self, db: Database):
        """
        Args:
            db: MongoDB database connection
        """

    def get_user_progress(self, user_id: str) -> dict[str, int]:
        """
        Get progress for all content items a user has interacted with.

        Args:
            user_id: MongoDB user ID

        Returns:
            Dict mapping content_id to progress percentage
            Example: {"content_123": 100, "content_456": 45}
        """

    def get_item_progress(self, user_id: str, content_id: str) -> int:
        """
        Get user's progress for a specific content item.

        Args:
            user_id: MongoDB user ID
            content_id: Content item ID

        Returns:
            Progress percentage (0-100), 0 if not started
        """

    def update_progress(
        self,
        user_id: str,
        content_id: str,
        progress: int,
        content_type: str = None
    ) -> dict:
        """
        Update user's progress for a content item.

        Args:
            user_id: MongoDB user ID
            content_id: Content item ID
            progress: Progress percentage (0-100)
            content_type: Optional content type for stats

        Returns:
            Updated progress record
        """

    def mark_complete(self, user_id: str, content_id: str, content_type: str = None) -> dict:
        """
        Mark content as complete (100% progress).

        Args:
            user_id: MongoDB user ID
            content_id: Content item ID
            content_type: Optional content type for stats

        Returns:
            Updated progress record
        """

    def get_completion_stats(self, user_id: str) -> dict:
        """
        Get user's overall learning statistics.

        Args:
            user_id: MongoDB user ID

        Returns:
            dict with keys:
                - totalCompleted: int
                - byType: dict mapping content type to count
                - lastCompletedAt: datetime or None
        """

    def get_completed_count(self, user_id: str) -> int:
        """
        Get count of completed content items.

        Args:
            user_id: MongoDB user ID

        Returns:
            Number of items with 100% progress
        """
```

---

## Data Models

### ContentItem Document

```python
{
    "_id": ObjectId,

    # --- Identifiers ---
    "contentType": str,           # 'text_article' | 'audio_article' | 'audio_exercise' | 'video_link' | 'exercise'
    "status": str,                # 'draft' | 'in_review' | 'published' | 'archived'
    "category": str,              # 'featured' | 'leadership' | 'breath' | 'meditation' | 'burnout' | 'wellbeing' | 'other'
    "sortOrder": int,             # Sort within category

    # --- Display Content (multi-language) ---
    "titleEn": str,               # English title (max 500 chars)
    "titleSv": str | None,        # Swedish title
    "lengthMinutes": int | None,  # Duration in minutes

    # --- Text Content (text_article) ---
    "textContentEn": str | None,
    "textContentSv": str | None,

    # --- Audio Content (audio_article, audio_exercise) ---
    "audioFileEn": str | None,    # File path (legacy)
    "audioFileSv": str | None,
    "audioDataEn": bytes | None,  # Binary data (production)
    "audioDataSv": bytes | None,
    "audioMimeTypeEn": str | None,
    "audioMimeTypeSv": str | None,

    # --- Video Content (video_link) ---
    "videoUrl": str | None,
    "videoEmbedCode": str | None,
    "videoAvailableInEn": bool,
    "videoAvailableInSv": bool,

    # --- Exercise Content (exercise type) ---
    "steps": list[str] | None,    # Step-by-step instructions
    "closing": str | None,        # Closing message
    "framework": dict | None,     # Framework details (name, steps)

    # --- Internal/Admin ---
    "purpose": str | None,
    "outcome": str | None,
    "relatedFramework": str | None,
    "voiceoverScriptEn": str | None,
    "voiceoverScriptSv": str | None,
    "ttsSpeed": float,            # Default 1.0 (0.7-1.2)
    "ttsVoice": str,              # Default 'Aria'
    "backgroundMusicTrack": str | None,
    "productionNotes": str | None,

    # --- Coach Integration ---
    "coachTopics": list[str],     # Topics that trigger recommendation
    "coachPriority": int,         # Higher = more likely to recommend
    "coachEnabled": bool,         # Whether coach can recommend

    # --- Timestamps ---
    "createdAt": datetime,
    "updatedAt": datetime
}
```

**Content Types:**

| Type | Description | Key Fields |
|------|-------------|------------|
| `text_article` | Written article | textContentEn/Sv |
| `audio_article` | Audio/podcast | audioFileEn/Sv or audioDataEn/Sv |
| `audio_exercise` | Guided audio | audioFileEn/Sv, voiceoverScript |
| `video_link` | Video embed | videoUrl, videoEmbedCode |
| `exercise` | Step-by-step guide | steps, closing, framework |

**Categories:**

| Category | Description |
|----------|-------------|
| `featured` | Highlighted content |
| `leadership` | Leadership skills |
| `breath` | Breathing exercises |
| `meditation` | Meditation content |
| `burnout` | Burnout prevention |
| `wellbeing` | General wellbeing |
| `other` | Uncategorized |

**Coach Topics:**

```python
[
    'delegation', 'stress', 'team_dynamics', 'communication',
    'leadership', 'time_management', 'conflict', 'burnout',
    'motivation', 'decision_making', 'mindfulness', 'resilience'
]
```

**Indexes:**
- `contentType`
- `status`
- `(category, sortOrder)`
- `(coachTopics, coachEnabled, coachPriority)`

---

### UserLearningProgress Document

```python
{
    "_id": ObjectId,
    "userId": ObjectId,           # Reference to User (indexed)
    "contentId": str,             # Content item ID (indexed)
    "contentType": str,           # Content type for stats
    "progress": int,              # 0-100 percentage
    "completedAt": datetime | None,  # When reached 100%
    "lastAccessedAt": datetime,   # Last interaction
    "createdAt": datetime,
    "updatedAt": datetime
}
```

**Indexes:**
- `userId` - For user-specific queries
- `(userId, contentId)` - Compound unique index
- `(userId, progress)` - For completion queries

---

## Integration Points

### With Progress System

Progress System fetches learning stats:

```python
# ProgressStatsService uses LearningProgressService
lessons_count = learning_progress_service.get_completed_count(user_id)
```

### With Coach System

Coach System gets content recommendations:

```python
# Coach requests recommendations for detected topics
recommendations = content_service.get_for_coach(
    topics=['stress', 'burnout'],
    limit=2
)
```

### With Auth System

All endpoints require authentication:

```python
# User endpoints require auth
@require_auth
def get_content_handler(request):
    user_id = request.user.id
    ...

# Admin endpoints require admin role
@require_admin
def create_content_handler(request):
    ...
```

---

## Configuration

### Configurable Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `content_source_type` | 'file' or 'database' | 'file' |
| `content_filepath` | Path to content file | Dynamic |
| `default_coach_limit` | Max recommendations | 2 |

### File Format (when source_type is 'file')

```python
{
    "content": [
        {
            "id": "burnout-prevention",
            "contentType": "text_article",
            "status": "published",
            "category": "burnout",
            "titleEn": "Burnout Prevention: Thrive, Don't Just Survive",
            "titleSv": "Förebyggande av Utbrändhet",
            "lengthMinutes": 5,
            "textContentEn": "## Purpose\n...",
            "coachTopics": ["burnout", "stress", "resilience"],
            "coachPriority": 10,
            "coachEnabled": true
        },
        {
            "id": "box-breathing",
            "contentType": "exercise",
            "status": "published",
            "category": "breath",
            "titleEn": "Box Breathing Exercise",
            "lengthMinutes": 4,
            "steps": [
                "Sit upright in a comfortable position.",
                "Exhale completely through your mouth.",
                "Inhale through your nose for 4 counts.",
                "Hold your breath for 4 counts.",
                "Exhale through your mouth for 4 counts.",
                "Hold for 4 counts before inhaling again.",
                "Repeat for 4 cycles."
            ],
            "closing": "With practice, box breathing becomes a powerful tool.",
            "coachTopics": ["stress", "mindfulness"],
            "coachEnabled": true
        }
    ]
}
```

# Progress & Insights System

## Description

The Progress & Insights System aggregates user statistics from multiple sources and generates personalized insights based on check-in patterns. It provides analytics, pattern detection, and AI-enhanced recommendations.

**Responsibilities:**
- Aggregate progress stats from multiple systems
- Detect patterns in check-in data
- Generate insights based on configurable triggers
- Manage insight lifecycle (create, read, expire)
- Provide unread insight counts for notifications

**Tech Stack:**
- **MongoDB** - Insight documents, trigger configuration
- **Claude API** - AI enhancement for recommendations
- **Express** - RESTful API endpoints
- **Auth Middleware** - All endpoints require authentication

---

## Pipelines

### Pipeline 1: Get Stats

Aggregates user statistics from multiple data sources.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           GET STATS PIPELINE                                 │
└─────────────────────────────────────────────────────────────────────────────┘

Frontend                         Backend
────────                         ───────
    │                                │
    │  1. GET /api/progress/stats    │
    │     Authorization: Bearer <token>
    │───────────────────────────────>│
    │                                │
    │                                │  2. ProgressStatsService
    │                                │     .get_stats()
    │                                │
    │                                │  3. Fetch from sources:
    │                                │     - streak: CheckInAnalytics
    │                                │     - checkins: CheckInService
    │                                │     - lessons: 0 (not implemented)
    │                                │     - sessions: User.coachExchanges
    │                                │
    │  4. Return aggregated stats    │
    │<───────────────────────────────│
    │                                │
```

**Steps:**
1. Frontend requests user stats
2. Call `ProgressStatsService.get_stats()` to aggregate data
3. Fetch from multiple sources:
   - `streak` → CheckInAnalytics.calculate_streak()
   - `checkins` → CheckInService.get_total_count()
   - `lessons` → 0 (not implemented yet)
   - `sessions` → User document `coachExchanges.count`
4. Return aggregated stats object

**API Response:**
```python
{
    "success": True,
    "data": {
        "streak": 12,
        "checkins": 45,
        "lessons": 0,
        "sessions": 23
    }
}
```

**Error Cases:**
- Server error → 500 FETCH_FAILED

---

### Pipeline 2: Get Insights

Detects patterns, generates new insights if warranted, and returns the insight list.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GET INSIGHTS PIPELINE                                │
└─────────────────────────────────────────────────────────────────────────────┘

Frontend                         Backend
────────                         ───────
    │                                │
    │  1. GET /api/progress/insights │
    │     Authorization: Bearer <token>
    │───────────────────────────────>│
    │                                │
    │                                │  2. InsightEngine
    │                                │     .generate_insights()
    │                                │     - Detects patterns
    │                                │     - Checks triggers from DB
    │                                │     - Creates new insights
    │                                │
    │                                │  3. InsightService
    │                                │     .get_active_insights()
    │                                │
    │  4. Return insights list       │
    │     [{title, description}]     │
    │<───────────────────────────────│
    │                                │
```

**Steps:**
1. Frontend requests insights
2. Call `InsightEngine.generate_insights()` which:
   - Analyzes recent check-in data for patterns
   - Loads triggers from database
   - Checks each trigger condition against detected patterns
   - Skips if recent insight exists for same trigger (duplicate prevention)
   - Creates new insight documents if conditions met
   - Optionally enhances with AI for recommendation type
3. Call `InsightService.get_active_insights()` to return non-expired insights
4. Return insights array with `title` and `description`

**API Response:**
```python
{
    "success": True,
    "data": {
        "insights": [
            {
                "title": "Thursday Stress Pattern",
                "description": "Your stress tends to spike on Thursdays. Consider blocking 30 minutes before your afternoon meetings for preparation."
            },
            {
                "title": "Morning Energy Peak",
                "description": "You report highest energy levels between 9-11am. Schedule your most demanding tasks during this window."
            }
        ]
    }
}
```

**Error Cases:**
- Server error → 500 FETCH_FAILED

---

### Pipeline 3: Mark Insight Read

Marks a specific insight as read.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       MARK INSIGHT READ PIPELINE                             │
└─────────────────────────────────────────────────────────────────────────────┘

Frontend                         Backend
────────                         ───────
    │                                │
    │  1. POST /api/progress/        │
    │     insights/:id/read          │
    │     Authorization: Bearer <token>
    │───────────────────────────────>│
    │                                │
    │                                │  2. InsightService
    │                                │     .mark_as_read()
    │                                │
    │                                │  3. Verify ownership
    │                                │     (insight.userId == user)
    │                                │
    │                                │  4. Update isRead = true
    │                                │
    │  5. Return success             │
    │<───────────────────────────────│
    │                                │
```

**Steps:**
1. Frontend sends read confirmation with insight ID
2. Call `InsightService.mark_as_read()` with insight ID and user ID
3. Verify the insight belongs to the requesting user
4. Update `isRead` to true
5. Return success

**Error Cases:**
- Insight not found → 404 NOT_FOUND
- Server error → 500 UPDATE_FAILED

---

### Pipeline 4: Get Unread Count

Returns the count of unread insights for notification badges.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       GET UNREAD COUNT PIPELINE                              │
└─────────────────────────────────────────────────────────────────────────────┘

Frontend                         Backend
────────                         ───────
    │                                │
    │  1. GET /api/progress/         │
    │     insights/count             │
    │     Authorization: Bearer <token>
    │───────────────────────────────>│
    │                                │
    │                                │  2. InsightService
    │                                │     .get_unread_count()
    │                                │
    │  3. Return count               │
    │<───────────────────────────────│
    │                                │
```

**Steps:**
1. Frontend requests unread count (for badge display)
2. Call `InsightService.get_unread_count()` to count unread, non-expired insights
3. Return count

**Error Cases:**
- Server error → 500 FETCH_FAILED

---

## Components

### ProgressStatsService

Aggregates statistics from multiple data sources.

```python
class ProgressStatsService:
    """
    Aggregates user progress stats from multiple systems.
    """

    def __init__(
        self,
        checkin_service: CheckInService,
        checkin_analytics: CheckInAnalytics,
        user_service: UserService
    ):
        """
        Args:
            checkin_service: For check-in count
            checkin_analytics: For streak calculation
            user_service: For user document access (coachExchanges)
        """

    def get_stats(self, user_id: str) -> dict:
        """
        Aggregate stats from all sources.

        Args:
            user_id: MongoDB user ID

        Returns:
            dict with keys:
                - streak: int (current check-in streak)
                - checkins: int (total check-in count)
                - lessons: int (completed lessons count, 0 for now)
                - sessions: int (coach conversation count)
        """

    def _get_lessons_count(self, user_id: str) -> int:
        """
        Get completed lessons count.

        Returns:
            0 (not implemented yet)
        """

    def _get_sessions_count(self, user_id: str) -> int:
        """
        Get coach sessions count from user document.

        Returns:
            User.coachExchanges.count value
        """
```

---

### InsightEngine

Detects patterns and generates insights. Combines pattern detection and insight generation into a single component.

```python
class InsightEngine:
    """
    Analyzes check-in data for patterns and generates insights.
    Handles the full flow: detect patterns → match triggers → create insights.
    """

    def __init__(
        self,
        checkin_service: CheckInService,
        insight_service: InsightService,
        ai_client,
        config: dict
    ):
        """
        Args:
            checkin_service: For fetching check-in data
            insight_service: For creating insights and loading triggers
            ai_client: Claude API client for AI enhancement
            config: Configuration with 'detection_period_days' etc.
        """

    def generate_insights(self, user_id: str, use_ai: bool = True) -> list[dict]:
        """
        Detect patterns and generate new insights.

        Args:
            user_id: MongoDB user ID
            use_ai: Whether to enhance recommendations with AI

        Returns:
            List of newly created insight documents

        Algorithm:
            1. Detect patterns in check-in data
            2. Load triggers from database
            3. For each trigger:
               - Check if condition matches patterns
               - Check if recent insight exists (duplicate prevention)
               - Build content from template
               - Optionally enhance with AI
               - Create insight document
        """

    def detect_patterns(self, user_id: str) -> dict | None:
        """
        Analyze check-in data and detect patterns.

        Args:
            user_id: MongoDB user ID

        Returns:
            dict with detected patterns, or None if insufficient data

        Pattern dict keys:
            - streak: dict with 'current' count
            - morningCheckIns: int (count before 9am)
            - stressDayPattern: dict with 'weekday', 'count' or None
            - moodChange: int (percentage) or None
            - stressChange: int (percentage) or None
            - lowEnergyDays: int (consecutive days)
            - sleepMoodCorrelation: float (0-1)

        Requires minimum 5 check-ins for analysis.
        """

    def _count_morning_checkins(self, checkins: list[dict]) -> int:
        """
        Count check-ins submitted before 9am.
        """

    def _detect_stress_day_pattern(self, checkins: list[dict]) -> dict | None:
        """
        Find day of week with highest stress frequency.

        Returns:
            dict with 'weekday' and 'count' if pattern found (>=3 occurrences)
        """

    def _calculate_metric_change(self, checkins: list[dict], metric: str) -> int | None:
        """
        Calculate percentage change between first and second half.
        """

    def _count_low_energy_streak(self, checkins: list[dict]) -> int:
        """
        Count consecutive recent days with low energy (avg < 5).
        """

    def _calculate_sleep_mood_correlation(self, checkins: list[dict]) -> float:
        """
        Calculate simple correlation between sleep quality and mood.
        """

    def _build_content(self, trigger: dict, patterns: dict) -> tuple[str, str]:
        """
        Build title and description from trigger template.

        Returns:
            tuple of (title, description) with variables substituted
        """

    def _enhance_with_ai(self, description: str, patterns: dict) -> str:
        """
        Enhance description using Claude API.

        Only used for 'recommendation' type triggers.
        Falls back to original description on error.
        """
```

---

### InsightService

CRUD operations for insight documents and trigger loading.

```python
class InsightService:
    """
    Handles insight document storage, retrieval, and trigger configuration.
    """

    def __init__(self, db: Database):
        """
        Args:
            db: MongoDB database connection
        """

    # --- Insight CRUD ---

    def create_insight(
        self,
        user_id: str,
        type: str,
        trigger: str,
        title: str,
        description: str,
        metrics: dict = None,
        expires_at: datetime = None
    ) -> dict:
        """
        Create a new insight document.

        Args:
            user_id: MongoDB user ID
            type: Insight type ('streak', 'pattern', 'trend', 'recommendation')
            trigger: Trigger ID that created this insight
            title: Display title (max 100 chars)
            description: Display description (max 500 chars)
            metrics: Optional supporting data
            expires_at: Optional expiration datetime

        Returns:
            Created insight document
        """

    def get_active_insights(self, user_id: str, limit: int = 10) -> list[dict]:
        """
        Get non-expired insights for a user.

        Args:
            user_id: MongoDB user ID
            limit: Maximum insights to return

        Returns:
            List of insight dicts sorted by createdAt descending
        """

    def mark_as_read(self, insight_id: str, user_id: str) -> dict:
        """
        Mark an insight as read.

        Args:
            insight_id: Insight document ID
            user_id: MongoDB user ID (for ownership verification)

        Returns:
            Updated insight document

        Raises:
            NotFoundError: Insight not found or doesn't belong to user
        """

    def get_unread_count(self, user_id: str) -> int:
        """
        Count unread, non-expired insights.
        """

    def has_recent_insight(self, user_id: str, trigger: str, days_back: int = 7) -> bool:
        """
        Check if insight with trigger exists within time window.
        """

    # --- Trigger Configuration ---

    def get_all_triggers(self) -> list[dict]:
        """
        Get all active insight triggers from database.

        Returns:
            List of trigger configurations

        Trigger dict structure:
            {
                "_id": str,
                "triggerId": str,
                "type": str,
                "condition": str,
                "title": str,
                "template": str,
                "isActive": bool,
                "duplicateWindowDays": int,
                "useAiEnhancement": bool
            }
        """

    def get_trigger_by_id(self, trigger_id: str) -> dict | None:
        """
        Get a specific trigger by ID.
        """
```

---

## Data Models

### Insight Document

```python
{
    "_id": ObjectId,
    "userId": ObjectId,           # Reference to User (indexed)
    "type": str,                  # 'streak' | 'pattern' | 'trend' | 'recommendation'
    "trigger": str,               # Trigger ID that created this (indexed)
    "title": str,                 # Display title (max 100 chars)
    "description": str,           # Display description (max 500 chars)
    "metrics": dict,              # Supporting pattern data
    "isRead": bool,               # Read status (default: False)
    "expiresAt": datetime | None, # Optional TTL expiration
    "createdAt": datetime,        # Auto-managed
    "updatedAt": datetime         # Auto-managed
}
```

**Indexes:**
- `userId` - For user-specific queries
- `(userId, createdAt)` - For sorted retrieval
- `(userId, trigger)` - For duplicate checking
- `expiresAt` - TTL index for auto-deletion

### Insight Trigger Document

```python
{
    "_id": ObjectId,
    "triggerId": str,             # Unique identifier (e.g., 'streak_milestone_7')
    "type": str,                  # 'streak' | 'pattern' | 'trend' | 'recommendation'
    "condition": str,             # Condition expression
    "title": str,                 # Title template
    "template": str,              # Description template with {{variables}}
    "isActive": bool,             # Whether trigger is active
    "duplicateWindowDays": int,   # Days to prevent duplicates (default: 7)
    "useAiEnhancement": bool,     # Whether to enhance with AI
    "createdAt": datetime,
    "updatedAt": datetime
}
```

**Example Triggers:**

| triggerId | type | condition | title |
|-----------|------|-----------|-------|
| `streak_milestone_7` | streak | `streak.current == 7` | "One Week Strong!" |
| `streak_milestone_14` | streak | `streak.current == 14` | "Two Weeks of Dedication" |
| `streak_milestone_30` | streak | `streak.current == 30` | "A Full Month!" |
| `morning_pattern` | pattern | `morningCheckIns >= 5` | "Morning Reflection Habit" |
| `stress_day_pattern` | pattern | `stressDayPattern != None and stressDayPattern.count >= 3` | "{{weekday}} Stress Pattern" |
| `mood_improvement` | trend | `moodChange >= 15` | "Mood on the Rise" |
| `stress_reduction` | trend | `stressChange <= -15` | "Stress Decreasing" |
| `energy_dip` | recommendation | `lowEnergyDays >= 3` | "Energy Check-In" |
| `sleep_correlation` | pattern | `sleepMoodCorrelation >= 0.6` | "Sleep-Mood Connection" |

### Insight Types

| Type | Description | AI Enhanced |
|------|-------------|-------------|
| `streak` | Milestone achievements | No |
| `pattern` | Behavioral patterns detected | No |
| `trend` | Metric trends over time | No |
| `recommendation` | Actionable suggestions | Yes |

---

## Integration Points

### With Check-in System

Progress System depends on Check-in System for data:

```python
# InsightEngine uses CheckInService
checkins = checkin_service.get_checkins_for_period(user_id, detection_period_days)

# ProgressStatsService uses CheckInAnalytics
streak = checkin_analytics.calculate_streak(user_id)
checkins_count = checkin_service.get_total_count(user_id)
```

### With User System

For coach sessions count:

```python
# ProgressStatsService fetches from User document
user = user_service.get_user(user_id)
sessions = user.get("coachExchanges", {}).get("count", 0)
```

### With Auth System

All endpoints require authentication:

```python
# All routes use require_auth middleware
@require_auth
def get_stats_handler(request):
    user_id = request.user.id
    ...
```

---

## Configuration

### Configurable Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `detection_period_days` | Days of check-in data to analyze | 30 |
| `min_checkins_for_patterns` | Minimum check-ins required | 5 |
| `duplicate_window_days` | Days to prevent duplicate insights | 7 |

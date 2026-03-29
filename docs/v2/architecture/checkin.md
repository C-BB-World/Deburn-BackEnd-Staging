# Check-in System

## Description

The Check-in System enables daily wellness tracking by capturing mood, energy levels, sleep quality, and stress. It provides data storage, retrieval, and analytics for trend visualization.

**Responsibilities:**
- Daily check-in submission (one per user per day)
- Check-in history retrieval with pagination
- Streak calculation (consecutive days)
- Trend data formatting for graphs
- Triggering insight generation (via InsightGenerator)

**Tech Stack:**
- **MongoDB** - Check-in document storage with compound indexes
- **Express** - RESTful API endpoints
- **Auth Middleware** - All endpoints require authentication

---

## Pipelines

### Pipeline 1: Submit Check-in

Creates a new check-in for today or updates an existing one (retake). Returns streak and AI-generated insight/tip.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SUBMIT CHECK-IN PIPELINE                              │
└─────────────────────────────────────────────────────────────────────────────┘

Frontend                         Backend
────────                         ───────
    │                                │
    │  1. POST /api/checkin          │
    │     Authorization: Bearer <token>
    │     {mood, physicalEnergy,     │
    │      mentalEnergy, sleep,      │
    │      stress}                   │
    │───────────────────────────────>│
    │                                │
    │                                │  2. Validate metrics
    │                                │
    │                                │  3. CheckInService
    │                                │     .submit_checkin()
    │                                │     (upsert for today)
    │                                │
    │                                │  4. CheckInAnalytics
    │                                │     .calculate_streak()
    │                                │
    │                                │  5. InsightGenerator
    │                                │     .generate_insight()
    │                                │     (AI-generated)
    │                                │
    │  6. Return {streak, insight,   │
    │             tip}               │
    │<───────────────────────────────│
    │                                │
```

**Steps:**
1. User submits check-in data via POST `/api/checkin`
2. Validate all required metrics (mood, physicalEnergy, mentalEnergy, sleep, stress)
3. Call `CheckInService.submit_checkin()` to upsert today's check-in
4. Call `CheckInAnalytics.calculate_streak()` to get current streak count
5. Call `InsightGenerator.generate_insight()` to create AI-generated insight and tip
6. Return response with `streak` (number), `insight` (string), `tip` (string)

**API Response:**
```python
{
    "success": True,
    "data": {
        "streak": 5,
        "insight": "Your stress tends to spike on Thursdays...",
        "tip": "Try the 2-minute breathing exercise before your 10am call"
    }
}
```

**Error Cases:**
- Missing required metrics → 400 MISSING_FIELDS
- Validation error (out of range values) → 400 VALIDATION_ERROR
- Server error → 500 CHECKIN_SAVE_FAILED

---

### Pipeline 2: Get Today's Check-in

Retrieves today's check-in status to determine if user has already checked in.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      GET TODAY'S CHECK-IN PIPELINE                           │
└─────────────────────────────────────────────────────────────────────────────┘

Frontend                         Backend
────────                         ───────
    │                                │
    │  1. GET /api/checkin/today     │
    │     Authorization: Bearer <token>
    │───────────────────────────────>│
    │                                │
    │                                │  2. CheckInService
    │                                │     .get_today_checkin()
    │                                │
    │  3. Return check-in data       │
    │     + hasCheckedInToday flag   │
    │<───────────────────────────────│
    │                                │
```

**Steps:**
1. Frontend requests today's check-in status
2. Call `CheckInService.get_today_checkin()` to find check-in for user + today's date
3. Return check-in data (or null) and boolean `hasCheckedInToday` flag

**Error Cases:**
- Server error → 500 FETCH_FAILED

---

### Pipeline 3: Get History

Retrieves historical check-ins with pagination and optional date filtering.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GET HISTORY PIPELINE                                 │
└─────────────────────────────────────────────────────────────────────────────┘

Frontend                         Backend
────────                         ───────
    │                                │
    │  1. GET /api/checkin/history   │
    │     ?startDate=YYYY-MM-DD      │
    │     &endDate=YYYY-MM-DD        │
    │     &limit=30&offset=0         │
    │     Authorization: Bearer <token>
    │───────────────────────────────>│
    │                                │
    │                                │  2. CheckInService
    │                                │     .get_history()
    │                                │
    │                                │  3. CheckInService
    │                                │     .get_total_count()
    │                                │
    │  4. Return check-ins list      │
    │     + pagination metadata      │
    │<───────────────────────────────│
    │                                │
```

**Steps:**
1. Frontend requests history with optional filters
2. Call `CheckInService.get_history()` with date range and pagination params
3. Call `CheckInService.get_total_count()` for pagination metadata
4. Return check-ins array with pagination (`total`, `limit`, `offset`, `hasMore`)

**Error Cases:**
- Server error → 500 FETCH_FAILED

---

### Pipeline 4: Get Streak

Retrieves current streak count.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          GET STREAK PIPELINE                                 │
└─────────────────────────────────────────────────────────────────────────────┘

Frontend                         Backend
────────                         ───────
    │                                │
    │  1. GET /api/checkin/streak    │
    │     Authorization: Bearer <token>
    │───────────────────────────────>│
    │                                │
    │                                │  2. CheckInAnalytics
    │                                │     .calculate_streak()
    │                                │
    │  3. Return streak count        │
    │<───────────────────────────────│
    │                                │
```

**Steps:**
1. Frontend requests streak information
2. Call `CheckInAnalytics.calculate_streak()` to compute consecutive days
3. Return current streak as a number

**Streak Logic:**
- Current streak starts only if most recent check-in is today or yesterday
- If there's a gap greater than 1 day, current streak resets to 0
- Counts consecutive days backward from today/yesterday

**Error Cases:**
- Server error → 500 FETCH_FAILED

---

### Pipeline 5: Get Trends

Returns formatted trend data for graph visualization.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          GET TRENDS PIPELINE                                 │
└─────────────────────────────────────────────────────────────────────────────┘

Frontend                         Backend
────────                         ───────
    │                                │
    │  1. GET /api/checkin/trends    │
    │     ?period=30                 │
    │     Authorization: Bearer <token>
    │───────────────────────────────>│
    │                                │
    │                                │  2. CheckInAnalytics
    │                                │     .get_trends(period)
    │                                │
    │                                │  3. Format response:
    │                                │     - Flat value arrays
    │                                │     - Percentage changes
    │                                │     - Energy = avg(physical, mental)
    │                                │
    │  4. Return formatted trends    │
    │<───────────────────────────────│
    │                                │
```

**Steps:**
1. Frontend requests trends for a period (7, 30, or 90 days)
2. Call `CheckInAnalytics.get_trends()` to fetch and format data
3. Format response with flat arrays and percentage changes
4. Return formatted trend data for graphs

**API Response:**
```python
{
    "success": True,
    "data": {
        "dataPoints": 7,
        "moodValues": [4, 5, 4, 3, 4, 5, 4],
        "moodChange": 12,
        "energyValues": [6, 7, 5, 6, 7, 6, 7],
        "energyChange": 5,
        "stressValues": [4, 3, 5, 4, 3, 3, 2],
        "stressChange": -15
    }
}
```

**Energy Calculation:**
- `energyValues[i] = (physicalEnergy[i] + mentalEnergy[i]) / 2`

**Trend Detection:**
- Requires at least 4 data points to calculate change percentage
- Compares first half average to second half average
- Change = `((secondHalfAvg - firstHalfAvg) / firstHalfAvg) * 100`

**Error Cases:**
- Server error → 500 FETCH_FAILED

---

## Components

### CheckInService

Pure CRUD operations for check-in data.

```python
class CheckInService:
    """
    Handles check-in storage and retrieval.
    Pure CRUD - no analytics or business logic.
    """

    def __init__(self, db: Database):
        """
        Args:
            db: MongoDB database connection
        """

    def submit_checkin(
        self,
        user_id: str,
        metrics: dict,
        notes: str | None = None
    ) -> dict:
        """
        Create or update today's check-in for a user.

        Args:
            user_id: MongoDB user ID
            metrics: dict with mood, physicalEnergy, mentalEnergy, sleep, stress
            notes: Optional text notes (max 500 chars)

        Returns:
            Saved check-in document

        Raises:
            ValidationError: Metrics out of valid ranges
        """

    def get_today_checkin(self, user_id: str) -> dict | None:
        """
        Get today's check-in for a user if it exists.

        Args:
            user_id: MongoDB user ID

        Returns:
            Check-in dict or None
        """

    def get_history(
        self,
        user_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 30,
        offset: int = 0
    ) -> list[dict]:
        """
        Get paginated check-in history.

        Args:
            user_id: MongoDB user ID
            start_date: Optional YYYY-MM-DD start filter
            end_date: Optional YYYY-MM-DD end filter
            limit: Max records to return (capped at 90)
            offset: Number of records to skip

        Returns:
            List of check-in dicts sorted by date descending
        """

    def get_total_count(self, user_id: str) -> int:
        """
        Get total number of check-ins for a user.

        Args:
            user_id: MongoDB user ID

        Returns:
            Total count
        """

    def get_checkins_for_period(self, user_id: str, days: int) -> list[dict]:
        """
        Get all check-ins for a user within the last N days.
        Used by CheckInAnalytics for trend calculation.

        Args:
            user_id: MongoDB user ID
            days: Number of days to look back

        Returns:
            List of check-in dicts sorted by date ascending
        """
```

---

### CheckInAnalytics

Combines streak calculation and trend formatting.

```python
class CheckInAnalytics:
    """
    Analytics and data formatting for check-ins.
    Handles streak calculation and trend data formatting for graphs.
    """

    def __init__(self, checkin_service: CheckInService):
        """
        Args:
            checkin_service: For fetching check-in data
        """

    def calculate_streak(self, user_id: str) -> int:
        """
        Calculate current streak for a user.

        Args:
            user_id: MongoDB user ID

        Returns:
            Current streak count (consecutive days from today/yesterday)

        Algorithm:
            1. Get all check-ins sorted by date descending
            2. If most recent is not today or yesterday, return 0
            3. Count consecutive days backward
        """

    def get_trends(self, user_id: str, period: int = 30) -> dict:
        """
        Get formatted trend data for graphs.

        Args:
            user_id: MongoDB user ID
            period: Number of days (7, 30, or 90)

        Returns:
            dict with keys:
                - dataPoints: int (number of check-ins in period)
                - moodValues: list[int] (flat array)
                - moodChange: int (percentage)
                - energyValues: list[float] (flat array, averaged)
                - energyChange: int (percentage)
                - stressValues: list[int] (flat array)
                - stressChange: int (percentage)
        """

    def _calculate_energy_average(self, physical: int, mental: int) -> float:
        """
        Calculate combined energy value.

        Args:
            physical: Physical energy (1-10)
            mental: Mental energy (1-10)

        Returns:
            Average of both values
        """

    def _calculate_change_percentage(self, values: list) -> int | None:
        """
        Calculate percentage change between first and second half.

        Args:
            values: List of numeric values

        Returns:
            Percentage change as int, or None if < 4 data points
        """

    def _is_consecutive(self, date1: str, date2: str) -> bool:
        """
        Check if two dates are consecutive (1 day apart).

        Args:
            date1: Earlier date in YYYY-MM-DD format
            date2: Later date in YYYY-MM-DD format

        Returns:
            True if dates are exactly 1 day apart
        """
```

---

### InsightGenerator

AI-generated insights and tips after check-in submission.

```python
class InsightGenerator:
    """
    Generates AI-powered insights and tips based on check-in data.
    Called after check-in submission to provide immediate feedback.
    """

    def __init__(self, ai_client, checkin_service: CheckInService):
        """
        Args:
            ai_client: AI service client (Claude API)
            checkin_service: For fetching historical data
        """

    def generate_insight(self, user_id: str, current_checkin: dict) -> dict:
        """
        Generate insight and tip for a check-in.

        Args:
            user_id: MongoDB user ID
            current_checkin: The just-submitted check-in data

        Returns:
            dict with keys:
                - insight: str (pattern observation)
                - tip: str (actionable recommendation)

        Note: Implementation details TBD (AI-generated)
        """
```

---

### MetricsValidator

Validates check-in metric values.

```python
class MetricsValidator:
    """
    Validates check-in metric values against allowed ranges.
    """

    METRIC_RANGES = {
        "mood": (1, 5),
        "physicalEnergy": (1, 10),
        "mentalEnergy": (1, 10),
        "sleep": (1, 5),
        "stress": (1, 10),
    }

    def validate(self, metrics: dict) -> tuple[bool, str | None]:
        """
        Validate all metrics are present and within valid ranges.

        Args:
            metrics: dict with metric values

        Returns:
            tuple of (is_valid, error_message)
        """

    def validate_notes(self, notes: str | None) -> tuple[bool, str | None]:
        """
        Validate optional notes field.

        Args:
            notes: Optional notes string

        Returns:
            tuple of (is_valid, error_message)

        Rules:
            - Max 500 characters
            - Trimmed whitespace
        """
```

---

## Data Models

### CheckIn Document

```python
{
    "_id": ObjectId,
    "userId": ObjectId,           # Reference to User (indexed)
    "date": str,                  # YYYY-MM-DD format
    "timestamp": datetime,        # When check-in was submitted
    "metrics": {
        "mood": int,              # 1-5 (1=struggling, 5=great)
        "physicalEnergy": int,    # 1-10
        "mentalEnergy": int,      # 1-10
        "sleep": int,             # 1-5 (1=poor, 5=great)
        "stress": int             # 1-10 (1=low, 10=high)
    },
    "notes": str | None,          # Optional, max 500 chars
    "createdAt": datetime,        # Auto-managed
    "updatedAt": datetime         # Auto-managed
}
```

**Indexes:**
- `userId` - For user-specific queries
- `(userId, date)` - Compound unique index (one check-in per user per day)
- `(userId, timestamp)` - Compound index for trend queries

### Metric Scales

| Metric | Range | Scale Description |
|--------|-------|-------------------|
| mood | 1-5 | 1=struggling, 2=low, 3=neutral, 4=good, 5=great |
| physicalEnergy | 1-10 | 1=exhausted, 10=energized |
| mentalEnergy | 1-10 | 1=foggy, 10=sharp |
| sleep | 1-5 | 1=poor, 2=fair, 3=ok, 4=good, 5=great |
| stress | 1-10 | 1=calm, 10=overwhelmed |

---

## Integration Points

### Route Handler Orchestration

The route handler orchestrates calls to multiple components:

```python
# POST /api/checkin handler (pseudocode)
def submit_checkin_handler(request):
    user_id = request.user.id
    metrics = request.body

    # 1. Validate
    is_valid, error = MetricsValidator.validate(metrics)
    if not is_valid:
        return error_response(400, error)

    # 2. Save (CRUD)
    checkin = CheckInService.submit_checkin(user_id, metrics)

    # 3. Calculate streak (Analytics)
    streak = CheckInAnalytics.calculate_streak(user_id)

    # 4. Generate insight (AI)
    insight_data = InsightGenerator.generate_insight(user_id, checkin)

    # 5. Return combined response
    return success_response({
        "streak": streak,
        "insight": insight_data["insight"],
        "tip": insight_data["tip"]
    })
```

### With Auth System
- All endpoints require valid session via `require_auth` middleware
- User ID extracted from authenticated session

### With Progress System
- Progress System calls `CheckInAnalytics.calculate_streak()` for stats
- Progress System uses check-in data for pattern detection
- Insights list comes from Progress System, not Check-in System

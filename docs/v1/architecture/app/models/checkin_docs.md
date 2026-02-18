# CheckIn Model

CheckIn model for BrainBank. Stores daily wellness check-in data.

---

## Classes

### CheckInMetrics

Embedded wellness metrics.

**Properties:**

- `mood` (int): Mood rating 1-5 (1=struggling, 5=great)
- `physical_energy` (int): Physical energy 1-10
- `mental_energy` (int): Mental energy 1-10
- `sleep` (int): Sleep quality 1-5 (1=poor, 5=great)
- `stress` (int): Stress level 1-10 (1=low, 10=high)

---

### CheckIn

CheckIn document for BrainBank. Extends BaseDocument.

**Properties:**

- `user_id` (PydanticObjectId): Reference to User document (indexed)
- `date` (str): Date of check-in in YYYY-MM-DD format (indexed)
- `timestamp` (datetime): When check-in was submitted
- `metrics` (CheckInMetrics): Wellness metrics
- `notes` (Optional[str]): User notes (max 500 chars)

**Methods:**

#### to_public_dict

- **Outputs:** (dict) Public JSON format with id, date, timestamp, metrics (camelCase), notes, createdAt
- **Description:** Convert to public JSON format.

#### get_history (classmethod)

- **Inputs:**
  - `user_id` (PydanticObjectId): User's ID
  - `start_date` (Optional[str]): Start date filter (YYYY-MM-DD)
  - `end_date` (Optional[str]): End date filter (YYYY-MM-DD)
  - `limit` (int): Max results. Default: 90
  - `offset` (int): Results offset. Default: 0
- **Outputs:** (List[CheckIn]) List of check-ins sorted by date descending
- **Description:** Get check-ins for a user within a date range.

#### calculate_streak (classmethod)

- **Inputs:**
  - `user_id` (PydanticObjectId): User's ID
- **Outputs:** (Dict[str, int]) {"current": int, "longest": int}
- **Description:** Calculate current and longest check-in streaks for a user.

#### get_trends (classmethod)

- **Inputs:**
  - `user_id` (PydanticObjectId): User's ID
  - `days` (int): Number of days to analyze. Default: 30
- **Outputs:** (Dict[str, Any]) Trend data with period, dataPoints, and per-metric stats (values, average, trend, change)
- **Description:** Get trend data for a period. Calculates averages and trends ("improving", "stable", "declining") for each metric.

#### get_total_count (classmethod)

- **Inputs:**
  - `user_id` (PydanticObjectId): User's ID
- **Outputs:** (int) Total check-in count
- **Description:** Get total check-in count for user.

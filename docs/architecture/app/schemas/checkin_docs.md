# CheckIn Schemas

Check-in request/response schemas.

---

## Classes

### CheckInRequest

Daily check-in request.

**Properties:**

- `mood` (int): Mood rating 1-5
- `physicalEnergy` (int): Physical energy 1-10
- `mentalEnergy` (int): Mental energy 1-10
- `sleep` (int): Sleep quality 1-5
- `stress` (int): Stress level 1-10
- `notes` (Optional[str]): Notes (max 500 chars)

---

### CheckInMetrics

Check-in metrics in response.

**Properties:**

- `mood` (int)
- `physicalEnergy` (int)
- `mentalEnergy` (int)
- `sleep` (int)
- `stress` (int)

---

### CheckInResponse

Check-in data in response.

**Properties:**

- `id` (str): Check-in ID
- `date` (str): Date (YYYY-MM-DD)
- `timestamp` (datetime): Submission timestamp
- `metrics` (CheckInMetrics): Wellness metrics
- `notes` (Optional[str]): User notes

---

### StreakResponse

Streak data in response.

**Properties:**

- `current` (int): Current streak days
- `longest` (int): Longest streak days

---

### MetricDataPoint

Single data point for a metric.

**Properties:**

- `date` (str): Date (YYYY-MM-DD)
- `value` (int): Metric value

---

### MetricTrend

Trend data for a single metric.

**Properties:**

- `values` (List[MetricDataPoint]): List of data points
- `average` (Optional[float]): Average value
- `trend` (Optional[str]): "improving", "stable", or "declining"
- `change` (Optional[float]): Percentage change

---

### TrendsResponse

Check-in trends response.

**Properties:**

- `period` (int): Number of days
- `dataPoints` (int): Number of check-ins
- `mood` (MetricTrend): Mood trend data
- `physicalEnergy` (MetricTrend): Physical energy trend
- `mentalEnergy` (MetricTrend): Mental energy trend
- `sleep` (MetricTrend): Sleep trend
- `stress` (MetricTrend): Stress trend

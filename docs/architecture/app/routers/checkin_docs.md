# CheckIn Router

Daily wellness check-in endpoints.

---

## Functions

### get_today_date

- **Outputs:** (str) Today's date in YYYY-MM-DD format (UTC)
- **Description:** Get today's date string.

### checkin_to_response

- **Inputs:**
  - `checkin` (CheckIn): CheckIn model
- **Outputs:** (dict) Response dictionary with camelCase metrics
- **Description:** Convert CheckIn model to response dictionary.

### calculate_streak

- **Inputs:**
  - `user_id` (str): User's ID
- **Outputs:** (dict) {current: int, longest: int}
- **Description:** Calculate user's current and longest check-in streaks.

---

## Endpoints

### POST /api/checkin

- **Inputs:**
  - Header: Authorization (Bearer token)
  - Body: `CheckInRequest` (mood, physicalEnergy, mentalEnergy, sleep, stress, notes?)
- **Outputs:** (dict) {checkIn: CheckInResponse, streak: StreakResponse, isRetake: bool}
- **Description:** Submit or update today's daily check-in. If check-in exists for today, updates it. Returns streak data and whether this was a retake.

---

### GET /api/checkin/trends

- **Inputs:**
  - Header: Authorization (Bearer token)
  - Query: `period` (int, 7-90, default 30) - Number of days
- **Outputs:** (dict) {period, dataPoints, mood, physicalEnergy, mentalEnergy, sleep, stress}
- **Description:** Get check-in trends over the specified period. Each metric includes values (data points), average, trend (improving/stable/declining), and change percentage.

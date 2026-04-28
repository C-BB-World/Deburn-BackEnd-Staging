# Dashboard Router

Aggregated dashboard data endpoint.

---

## Functions

### calculate_streak

- **Inputs:**
  - `user_id` (str): User's ID
- **Outputs:** (dict) {current: int, longest: int}
- **Description:** Calculate the user's current and longest check-in streak.

---

## Endpoints

### GET /api/dashboard

- **Inputs:**
  - Header: Authorization (Bearer token)
- **Outputs:** (dict) Dashboard data with user, checkin, coach, and circles info
- **Description:** Get aggregated dashboard data including:
  - user: {firstName, displayName}
  - checkin: {hasCheckedInToday, streak: {current, longest}, recentMood}
  - coach: {exchangesRemaining, dailyLimit}
  - circles: {activeGroups, pendingInvitations}

# Progress Router

User progress and statistics endpoints.

---

## Endpoints

### GET /api/progress/stats

- **Inputs:**
  - Header: Authorization (Bearer token)
- **Outputs:** (dict) {totalCheckIns, streak: {current, longest}, lastCheckIn: date|null}
- **Description:** Get progress statistics including total check-ins, current/longest streak, and date of last check-in.

---

### GET /api/progress/insights

- **Inputs:**
  - Header: Authorization (Bearer token)
  - Query:
    - `period` (int, 7-90, default 30) - Analysis period in days
- **Outputs:** (dict) {period, insights: List[Insight], summary: string}
- **Description:** Get AI-generated insights based on check-in data. Each insight has type, title, description, and optional action.

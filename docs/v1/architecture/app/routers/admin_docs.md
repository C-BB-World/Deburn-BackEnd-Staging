# Admin Router

Admin statistics and management endpoints.

---

## Endpoints

### GET /api/admin/stats

- **Inputs:**
  - Header: Authorization (Bearer token)
- **Outputs:** (dict) {totalUsers, activeUsers, totalCheckIns, averageStreak}
- **Description:** Get admin statistics for the user's organization. Requires admin access. Returns:
  - totalUsers: Total users in organization
  - activeUsers: Users with status "active"
  - totalCheckIns: Total check-ins from org users
  - averageStreak: Average streak (simplified calculation)

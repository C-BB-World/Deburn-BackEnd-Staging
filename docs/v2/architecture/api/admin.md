## API Description

Admin endpoints for platform statistics and management. Requires admin role.

---

## GET /api/admin/stats

Fetches platform-wide statistics.

**Frontend Input** (src/pages/Admin.jsx):
No request body.

**Response:**
```json
{
  "success": true,
  "data": {
    "totalUsers": 150,
    "activeUsers": 87,
    "totalCheckins": 4523,
    "totalSessions": 892
  }
}
```

**Response Types:**
```typescript
{
  success: boolean,
  data: {
    totalUsers: number,      // Total registered users
    activeUsers: number,     // Users active in last 30 days
    totalCheckins: number,   // Total check-ins submitted
    totalSessions: number    // Total coaching sessions
  }
}
```

**Error (403):**
```json
{
  "success": false,
  "error": {
    "message": "Admin access required",
    "code": "FORBIDDEN"
  }
}
```

## API Description

Admin endpoints for platform statistics and management. Requires admin role.

---

## GET /api/admin/stats

Fetches platform-wide statistics.

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

## API Description

Endpoints for managing user notifications. Notifications are created automatically by the system when certain events occur (e.g., group assignment, meeting scheduled, member moved).

---

## GET /api/notifications

Fetches notifications for the current user with pagination.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 20 | Maximum notifications to return |
| `offset` | int | 0 | Number of notifications to skip |

**Response:**
```json
{
  "success": true,
  "data": {
    "notifications": [
      {
        "id": "notif_123",
        "type": "group_assignment",
        "title": "Assigned to Circle A",
        "message": "You have been assigned to Circle A in the Q1 Leadership pool.",
        "metadata": {
          "poolId": "pool_123",
          "groupId": "grp_123"
        },
        "read": false,
        "readAt": null,
        "createdAt": "2026-01-27T10:30:00Z"
      }
    ],
    "total": 15,
    "hasMore": true
  }
}
```

---

## GET /api/notifications/count

Gets the count of unread notifications for the current user.

**Response:**
```json
{
  "success": true,
  "data": {
    "unread": 3
  }
}
```

---

## POST /api/notifications/:notificationId/read

Marks a single notification as read.

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Notification marked as read"
  }
}
```

**Error Responses:**
| Code | HTTP Status | Description |
|------|-------------|-------------|
| `NOT_FOUND` | 404 | Notification does not exist |

---

## POST /api/notifications/read-all

Marks all notifications as read for the current user.

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "All notifications marked as read",
    "count": 5
  }
}
```

---

## Notification Types

| Type | Description | Metadata |
|------|-------------|----------|
| `invitation` | User accepted a circle invitation | `poolId` |
| `group_assignment` | User was assigned to a group | `poolId`, `groupId` |
| `meeting_scheduled` | A meeting was scheduled for user's group | `meetingId`, `groupId` |
| `meeting_reminder` | Reminder for upcoming meeting | `meetingId`, `groupId` |
| `user_moved` | User was moved to a different group | `poolId`, `fromGroupId`, `toGroupId` |

---

## MongoDB Schema

**Collection:** `notifications`

```json
{
  "_id": "ObjectId",
  "userId": "ObjectId",
  "type": "group_assignment",
  "title": "Assigned to Circle A",
  "message": "You have been assigned to Circle A in Leadership Development pool",
  "metadata": {
    "poolId": "ObjectId",
    "groupId": "ObjectId"
  },
  "read": false,
  "readAt": null,
  "createdAt": "2026-01-27T10:30:00Z",
  "updatedAt": "2026-01-27T10:30:00Z"
}
```

**Indexes:**
- `{ userId: 1, read: 1, createdAt: -1 }` - For fetching user notifications
- `{ userId: 1, read: 1 }` - For counting unread

---

## Implementation Status

| Endpoint | Status | File | Line |
|----------|--------|------|------|
| `GET /api/notifications` | ✅ Complete | `app_v2/routers/notifications.py` | 15-35 |
| `GET /api/notifications/count` | ✅ Complete | `app_v2/routers/notifications.py` | 38-48 |
| `POST /api/notifications/:id/read` | ✅ Complete | `app_v2/routers/notifications.py` | 51-65 |
| `POST /api/notifications/read-all` | ✅ Complete | `app_v2/routers/notifications.py` | 68-80 |

### Services Used

| Service | File | Key Methods |
|---------|------|-------------|
| `NotificationService` | `app_v2/services/notifications/notification_service.py` | `get_notifications()`, `get_unread_count()`, `mark_as_read()`, `mark_all_as_read()`, `create_notification()` |

### Notification Creation Triggers

Notifications are created automatically by other services:

| Event | Service | Method |
|-------|---------|--------|
| Group assignment | `GroupService` | `assign_groups()` |
| Member moved | `circles.py` router | `move_member()` |
| Meeting scheduled | `MeetingService` | `schedule_meeting()` |

---

## Added: 2026-01-27

Implemented as part of the Think Tanks notification system feature.

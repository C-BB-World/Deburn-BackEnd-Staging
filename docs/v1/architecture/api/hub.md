## API Description

Organization hub endpoints for managing organization members and settings.

---

## GET /api/hub/organization

Fetches organization details.

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "org_123",
    "name": "Acme Corporation",
    "memberCount": 45,
    "activeUsers": 32,
    "completedLessons": 234,
    "avgEngagement": 78
  }
}
```

---

## GET /api/hub/members

Fetches organization members.

**Response:**
```json
{
  "success": true,
  "data": {
    "members": [
      {
        "id": "usr_123",
        "name": "John Doe",
        "email": "john@acme.com",
        "role": "admin"
      },
      {
        "id": "usr_456",
        "name": "Jane Smith",
        "email": "jane@acme.com",
        "role": "member"
      }
    ]
  }
}
```

---

## Member Roles

- `admin` - Can manage organization settings and members
- `member` - Regular organization member

## API Description

Endpoints for peer support circles (groups) and meetings.

---

## GET /api/circles/groups

Fetches user's circle groups and upcoming meetings.

**Frontend Input** (src/features/circles/circlesApi.js):
Note: Frontend uses `/api/circles/my-groups` instead.

**Response:**
```json
{
  "success": true,
  "data": {
    "groups": [
      {
        "id": "grp_123",
        "name": "Engineering Leaders",
        "memberCount": 6,
        "members": [
          { "name": "Anna S.", "avatar": "/avatars/anna.jpg" },
          { "name": "Erik L.", "avatar": null }
        ],
        "nextMeeting": "Mon, Jan 13, 3:00 PM"
      }
    ],
    "upcomingMeetings": [
      {
        "id": "mtg_123",
        "title": "Weekly Sync",
        "groupName": "Engineering Leaders",
        "date": "2025-01-13T15:00:00Z"
      }
    ]
  }
}
```

---

## GET /api/circles/my-groups

Fetches user's circle groups with next meeting info.

**Frontend Input** (src/features/circles/circlesApi.js):
No request body.

---

## GET /api/circles/invitations

Fetches pending circle invitations for the user.

**Frontend Input** (src/features/circles/circlesApi.js):
Note: Frontend uses `/api/circles/my-invitations` instead.

**Response:**
```json
{
  "success": true,
  "data": {
    "invitations": [
      {
        "id": "inv_123",
        "groupName": "Product Managers Circle",
        "invitedBy": "Maria K."
      }
    ]
  }
}
```

---

## GET /api/circles/my-invitations

Fetches pending and accepted invitations.

**Frontend Input** (src/features/circles/circlesApi.js):
No request body.

---

## GET /api/circles/availability

Fetches user's availability slots.

**Frontend Input** (src/features/circles/circlesApi.js):
No request body.

---

## PUT /api/circles/availability

Updates user's availability slots.

**Frontend Input** (src/features/circles/circlesApi.js):
```typescript
{
  slots: Array<{
    dayOfWeek: number,   // 0-6 (Sunday-Saturday)
    startTime: string,   // HH:MM format
    endTime: string      // HH:MM format
  }>
}
```

---

## GET /api/circles/groups/:groupId

Fetches group details.

**Frontend Input** (src/features/circles/circlesApi.js):
```typescript
// Path parameter
groupId: string  // Group ID
```
No request body.

---

## GET /api/circles/groups/:groupId/meetings

Fetches group's meetings.

**Frontend Input** (src/features/circles/circlesApi.js):
```typescript
// Path parameter
groupId: string  // Group ID
```
No request body.

---

## GET /api/circles/groups/:groupId/common-availability

Fetches group's common availability.

**Frontend Input** (src/features/circles/circlesApi.js):
```typescript
// Path parameter
groupId: string  // Group ID
```
No request body.

---

## POST /api/circles/groups/:groupId/meetings

Schedules a new meeting for the group.

**Frontend Input** (src/features/circles/circlesApi.js):
```typescript
// Path parameter
groupId: string  // Group ID

// Request body
{
  title: string,           // Meeting title
  description?: string,    // Optional description
  scheduledAt: string,     // ISO 8601 datetime
  duration: number,        // Duration in minutes
  location?: string        // Optional location/link
}
```

---

## GET /api/circles/invitations/:token

Fetches invitation details by token.

**Frontend Input** (src/features/circles/circlesApi.js):
```typescript
// Path parameter
token: string  // Invitation token
```
No request body.

---

## POST /api/circles/invitations/:token/accept

Accepts an invitation.

**Frontend Input** (src/features/circles/circlesApi.js):
```typescript
// Path parameter
token: string  // Invitation token

// Request body
{}  // Empty object
```

---

## POST /api/circles/invitations/:token/decline

Declines an invitation.

**Frontend Input** (src/features/circles/circlesApi.js):
```typescript
// Path parameter
token: string  // Invitation token

// Request body
{}  // Empty object
```

---

## POST /api/circles/meetings/:meetingId/cancel

Cancels a meeting.

**Frontend Input** (src/features/circles/circlesApi.js):
```typescript
// Path parameter
meetingId: string  // Meeting ID

// Request body
{}  // Empty object
```

---

## POST /api/circles/meetings/:meetingId/attendance

Updates meeting attendance.

**Frontend Input** (src/features/circles/circlesApi.js):
```typescript
// Path parameter
meetingId: string  // Meeting ID

// Request body
{
  attending: boolean  // Whether user is attending
}
```

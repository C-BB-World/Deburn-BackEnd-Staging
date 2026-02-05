## API Description

Endpoints for peer support circles (groups) and meetings.

---

## GET /api/circles/groups

Fetches user's circle groups and upcoming meetings.

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

## GET /api/circles/invitations

Fetches pending circle invitations for the user.

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

## API Description

Organization hub endpoints for managing organization members and settings.

---

## GET /api/hub/organization

Fetches organization details.

**Frontend Input** (src/features/hub/hubApi.js):
Note: This endpoint is not implemented in the frontend API file.

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

**Frontend Input** (src/features/hub/hubApi.js):
Note: This endpoint is not implemented in the frontend API file.

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

---

## GET /api/hub/admins

Fetches hub admins.

**Frontend Input** (src/features/hub/hubApi.js):
No request body.

---

## POST /api/hub/admins

Adds a hub admin.

**Frontend Input** (src/features/hub/hubApi.js):
```typescript
{
  email: string  // Email address of user to add as admin
}
```

---

## DELETE /api/hub/admins/:email

Removes a hub admin.

**Frontend Input** (src/features/hub/hubApi.js):
```typescript
// Path parameter
email: string  // URL-encoded email address
```
No request body.

---

## GET /api/hub/org-admins

Fetches organization admins.

**Frontend Input** (src/features/hub/hubApi.js):
No request body.

---

## GET /api/hub/organizations

Fetches all organizations.

**Frontend Input** (src/features/hub/hubApi.js):
No request body.

---

## POST /api/hub/org-admins

Adds an organization admin.

**Frontend Input** (src/features/hub/hubApi.js):
```typescript
{
  email: string,          // Email address of user to add
  organizationId: string  // Organization ID to add them to
}
```

---

## DELETE /api/hub/org-admins/:membershipId

Removes an organization admin.

**Frontend Input** (src/features/hub/hubApi.js):
```typescript
// Path parameter
membershipId: string  // Membership ID to remove
```
No request body.

---

## POST /api/hub/organizations

Creates a new organization.

**Frontend Input** (src/features/hub/hubApi.js):
```typescript
{
  name: string,   // Organization name
  domain: string  // Organization email domain (e.g., "acme.com")
}
```

---

## GET /api/hub/settings/coach

Fetches AI coach settings.

**Frontend Input** (src/features/hub/hubApi.js):
No request body.

---

## PUT /api/hub/settings/coach

Updates AI coach settings.

**Frontend Input** (src/features/hub/hubApi.js):
```typescript
{
  // Settings object - structure depends on coach configuration
  model?: string,           // AI model to use
  temperature?: number,     // Response creativity (0-1)
  maxTokens?: number,       // Max response length
  systemPrompt?: string,    // Custom system prompt
  // ... additional settings
}
```

---

## GET /api/hub/coach/prompts

Fetches coach prompts.

**Frontend Input** (src/features/hub/hubApi.js):
No request body.

---

## PUT /api/hub/coach/prompts/:language/:promptName

Updates a coach prompt.

**Frontend Input** (src/features/hub/hubApi.js):
```typescript
// Path parameters
language: string    // Language code: "en" | "sv"
promptName: string  // Prompt identifier

// Request body
{
  content: string  // New prompt content
}
```

---

## GET /api/hub/coach/exercises

Fetches coach exercises.

**Frontend Input** (src/features/hub/hubApi.js):
No request body.

---

## PUT /api/hub/coach/exercises

Updates coach exercises.

**Frontend Input** (src/features/hub/hubApi.js):
```typescript
{
  exercises: Array<{
    id: string,
    title: string,
    description: string,
    duration: number,      // Duration in minutes
    category: string,
    instructions: string[]
  }>
}
```

---

## GET /api/hub/coach/config

Fetches coach configuration.

**Frontend Input** (src/features/hub/hubApi.js):
No request body.

---

## GET /api/hub/content

Fetches content library items.

**Frontend Input** (src/features/hub/hubApi.js):
```typescript
// Query parameters (all optional)
{
  contentType?: string,  // Filter by type: "video" | "audio" | "article" | "exercise"
  status?: string,       // Filter by status: "draft" | "published" | "archived"
  category?: string      // Filter by category
}
```

---

## GET /api/hub/content/:id

Fetches a single content item.

**Frontend Input** (src/features/hub/hubApi.js):
```typescript
// Path parameter
id: string  // Content ID
```
No request body.

---

## POST /api/hub/content

Creates new content.

**Frontend Input** (src/features/hub/hubApi.js):
```typescript
{
  title: string,
  description: string,
  contentType: string,    // "video" | "audio" | "article" | "exercise"
  category: string,
  duration?: number,      // Duration in minutes
  thumbnail?: string,     // URL to thumbnail image
  status: string,         // "draft" | "published"
  content: object         // Type-specific content data
}
```

---

## PUT /api/hub/content/:id

Updates content.

**Frontend Input** (src/features/hub/hubApi.js):
```typescript
// Path parameter
id: string  // Content ID

// Request body
{
  title?: string,
  description?: string,
  category?: string,
  duration?: number,
  thumbnail?: string,
  status?: string,
  content?: object
}
```

---

## DELETE /api/hub/content/:id

Deletes content.

**Frontend Input** (src/features/hub/hubApi.js):
```typescript
// Path parameter
id: string  // Content ID
```
No request body.

---

## POST /api/hub/content/:contentId/audio/:lang

Uploads audio for content.

**Frontend Input** (src/features/hub/hubApi.js):
```typescript
// Path parameters
contentId: string  // Content ID
lang: string       // Language code: "en" | "sv"

// Request body
FormData {
  audio: File  // Audio file (MP3, WAV, etc.)
}
```

---

## DELETE /api/hub/content/:contentId/audio/:lang

Removes audio from content.

**Frontend Input** (src/features/hub/hubApi.js):
```typescript
// Path parameters
contentId: string  // Content ID
lang: string       // Language code: "en" | "sv"
```
No request body.

---

## GET /api/hub/compliance/stats

Fetches compliance statistics.

**Frontend Input** (src/features/hub/hubApi.js):
No request body.

---

## GET /api/hub/compliance/user/:email

Fetches compliance info for a user.

**Frontend Input** (src/features/hub/hubApi.js):
```typescript
// Path parameter
email: string  // URL-encoded email address
```
No request body.

---

## POST /api/hub/compliance/export/:userId

Exports user data.

**Frontend Input** (src/features/hub/hubApi.js):
```typescript
// Path parameter
userId: string  // User ID

// Request body
{}  // Empty object
```

---

## POST /api/hub/compliance/delete/:userId

Deletes user account.

**Frontend Input** (src/features/hub/hubApi.js):
```typescript
// Path parameter
userId: string  // User ID

// Request body
{}  // Empty object
```

---

## GET /api/hub/compliance/pending-deletions

Fetches pending account deletions.

**Frontend Input** (src/features/hub/hubApi.js):
No request body.

---

## POST /api/hub/compliance/cleanup-sessions

Cleans up expired sessions.

**Frontend Input** (src/features/hub/hubApi.js):
```typescript
{}  // Empty object
```

---

## GET /api/hub/compliance/security-config

Fetches security configuration.

**Frontend Input** (src/features/hub/hubApi.js):
No request body.

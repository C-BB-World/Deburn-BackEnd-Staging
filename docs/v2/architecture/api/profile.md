## API Description

Endpoints for user profile management.

---

## PUT /api/profile

Updates user profile information.

**Request:**
```json
{
  "firstName": "John",
  "lastName": "Doe",
  "organization": "Acme Corp",
  "role": "Engineering Manager",
  "bio": "Passionate about building great teams"
}
```

**Frontend Input** (src/pages/Profile.jsx):
```typescript
{
  firstName: string,    // User's first name
  lastName: string,     // User's last name
  organization: string, // Organization/company name
  role: string,         // Job title/role
  bio: string           // Short biography
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "usr_123",
      "firstName": "John",
      "lastName": "Doe",
      "email": "john@example.com",
      "organization": "Acme Corp",
      "role": "Engineering Manager",
      "bio": "Passionate about building great teams"
    }
  }
}
```

**Response Types:**
```typescript
{
  success: boolean,
  data: {
    user: {
      id: string,
      firstName: string,
      lastName: string,
      email: string,
      organization: string,
      role: string,
      bio: string
    }
  }
}
```

---

## POST /api/profile/avatar

Uploads user avatar image.

**Request:** `multipart/form-data`
- `avatar` (File): Image file (JPG/PNG, max 1MB)

**Frontend Input** (src/pages/Profile.jsx):
```typescript
FormData {
  avatar: File  // Image file (JPEG or PNG only, validated client-side)
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "avatarUrl": "/uploads/avatars/usr_123.jpg"
  }
}
```

**Response Types:**
```typescript
{
  success: boolean,
  data: {
    avatarUrl: string  // URL to uploaded avatar
  }
}
```

---

## PUT /api/profile/avatar

Removes user avatar.

**Request:**
```json
{
  "remove": true
}
```

**Frontend Input** (src/pages/Profile.jsx):
```typescript
{
  remove: boolean  // Must be true to remove avatar
}
```

**Response:**
```json
{
  "success": true
}
```

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

---

## POST /api/profile/avatar

Uploads user avatar image.

**Request:** `multipart/form-data`
- `avatar` (File): Image file (JPG/PNG, max 1MB)

**Response:**
```json
{
  "success": true,
  "data": {
    "avatarUrl": "/uploads/avatars/usr_123.jpg"
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

**Response:**
```json
{
  "success": true
}
```

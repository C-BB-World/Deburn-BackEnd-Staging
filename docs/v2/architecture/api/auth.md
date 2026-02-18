## API Description

Authentication endpoints for login, registration, password reset, and email verification.

---

## POST /api/auth/login

Authenticates user and creates session.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword",
  "rememberMe": true
}
```

**Frontend Input** (src/features/auth/authApi.js → src/pages/auth/Login.jsx):
```typescript
{
  email: string,        // User's email address
  password: string,     // User's password
  rememberMe: boolean   // Extend session duration (default: false)
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "usr_123",
      "email": "user@example.com",
      "firstName": "John",
      "lastName": "Doe",
      "isAdmin": false
    }
  }
}
```

---

## POST /api/auth/register

Creates new user account.

**Request:**
```json
{
  "firstName": "John",
  "lastName": "Doe",
  "email": "user@example.com",
  "password": "securepassword",
  "passwordConfirm": "securepassword",
  "organization": "Acme Corp",
  "country": "SE",
  "consents": {
    "terms": true,
    "privacy": true
  }
}
```

**Frontend Input** (src/features/auth/authApi.js → src/pages/auth/Register.jsx):
```typescript
{
  firstName: string,       // User's first name
  lastName: string,        // User's last name
  email: string,           // User's email address
  password: string,        // User's password
  passwordConfirm: string, // Password confirmation
  organization: string,    // Organization/company name
  country: string,         // ISO 3166-1 alpha-2 country code (e.g., "SE", "US")
  consents: {
    termsOfService: boolean,  // Accepted terms of service
    privacyPolicy: boolean,   // Accepted privacy policy
    dataProcessing: boolean,  // Consent to data processing
    marketing: boolean        // Consent to marketing emails (optional)
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Registration successful. Please verify your email."
}
```

---

## POST /api/auth/forgot-password

Initiates password reset flow.

**Request:**
```json
{
  "email": "user@example.com"
}
```

**Frontend Input** (src/pages/auth/ForgotPassword.jsx):
```typescript
{
  email: string  // User's email address
}
```

**Response:**
```json
{
  "success": true
}
```

---

## POST /api/auth/reset-password

Resets password with token.

**Request:**
```json
{
  "token": "reset_token_abc123",
  "password": "newsecurepassword"
}
```

**Frontend Input** (src/pages/auth/ResetPassword.jsx):
```typescript
{
  token: string,    // Reset token from email link
  password: string  // New password
}
```

**Note:** authApi.js also supports `passwordConfirm: string` field but ResetPassword.jsx does not send it.

**Response:**
```json
{
  "success": true
}
```

**Error Codes:**
- `TOKEN_EXPIRED` - Reset token has expired
- `TOKEN_INVALID` - Reset token is invalid

---

## POST /api/auth/verify-email

Verifies email with token.

**Request:**
```json
{
  "token": "verify_token_abc123"
}
```

**Frontend Input** (src/pages/auth/VerifyEmail.jsx):
```typescript
{
  token: string  // Verification token from email link
}
```

**Response:**
```json
{
  "success": true
}
```

---

## POST /api/auth/resend-verification

Resends verification email.

**Request:**
```json
{
  "email": "user@example.com"
}
```

**Frontend Input** (src/pages/auth/VerifyEmail.jsx):
```typescript
{
  email: string  // User's email address
}
```

**Response:**
```json
{
  "success": true
}
```

---

## POST /api/auth/logout

Logs out user and destroys session.

**Request:** None

**Frontend Input** (src/features/auth/authApi.js):
```typescript
{}  // Empty object
```

**Response:**
```json
{
  "success": true
}
```

---

## GET /api/auth/session

Gets current session info.

**Frontend Input** (src/features/auth/authApi.js):
No request body.

**Response:**
```json
{
  "success": true,
  "data": {
    "user": { ... }
  }
}
```

---

## GET /api/auth/sessions

Gets all active sessions for the user.

**Frontend Input** (src/features/auth/authApi.js):
No request body.

---

## DELETE /api/auth/sessions/:sessionId

Revokes a specific session.

**Frontend Input** (src/features/auth/authApi.js):
```typescript
// Path parameter
sessionId: string  // Session ID to revoke
```
No request body.

---

## DELETE /api/auth/sessions

Revokes all other sessions.

**Frontend Input** (src/features/auth/authApi.js):
No request body.

---

## GET /api/auth/data-export

Exports user data (GDPR).

**Frontend Input** (src/features/auth/authApi.js):
No request body.

---

## POST /api/auth/delete-account

Requests account deletion (GDPR).

**Frontend Input** (src/features/auth/authApi.js):
```typescript
{
  reason: string | null  // Optional reason for deletion
}
```

---

## POST /api/auth/refresh

Refreshes access token.

**Frontend Input** (src/features/auth/authApi.js):
```typescript
{}  // Empty object
```

---

## GET /api/auth/admin-status

Checks if the current user is an organization admin. Used by the frontend to determine whether to show admin UI elements.

**Frontend Input** (src/features/circles/circles-adminApi.js):
No request body.

**Response:**
```json
{
  "success": true,
  "data": {
    "isAdmin": true,
    "organizations": [
      {
        "id": "org_123",
        "name": "Acme Corp",
        "role": "admin"
      }
    ]
  }
}
```

**Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `isAdmin` | boolean | Whether user is admin of any organization |
| `organizations` | array | List of organizations where user is admin |
| `organizations[].id` | string | Organization ID |
| `organizations[].name` | string | Organization name |
| `organizations[].role` | string | User's role (always "admin" in this response) |

**Implementation Notes:**
- Queries `organizationmembers` collection for entries where `userId` matches, `role` = "admin", and `status` = "active"
- Returns empty organizations array if user is not an admin of any organization
- Used by AuthContext to set `isOrgAdmin` flag in user state

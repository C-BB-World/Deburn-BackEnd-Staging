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

**Response:**
```json
{
  "success": true
}
```

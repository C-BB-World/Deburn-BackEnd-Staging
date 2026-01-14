# Auth Schemas

Authentication request/response schemas.

---

## Classes

### RegisterRequest

User registration request.

**Properties:**

- `email` (EmailStr): User's email
- `password` (str): Password (min 8 chars)
- `organization` (str): Organization name (2-100 chars)
- `country` (str): ISO 3166-1 alpha-2 country code (2 uppercase letters)
- `firstName` (Optional[str]): First name (max 50 chars)
- `lastName` (Optional[str]): Last name (max 50 chars)

---

### LoginRequest

User login request.

**Properties:**

- `email` (EmailStr): User's email
- `password` (str): User's password
- `rememberMe` (bool): Extended session. Default: False

---

### ForgotPasswordRequest

Forgot password request.

**Properties:**

- `email` (EmailStr): User's email

---

### ResetPasswordRequest

Reset password request.

**Properties:**

- `token` (str): Password reset token
- `password` (str): New password (min 8 chars)

---

### VerifyEmailRequest

Email verification request.

**Properties:**

- `token` (str): Verification token

---

### ResendVerificationRequest

Resend verification email request.

**Properties:**

- `email` (EmailStr): User's email

---

### UserProfileResponse

User profile in response.

**Properties:**

- `firstName` (Optional[str])
- `lastName` (Optional[str])
- `jobTitle` (Optional[str])
- `leadershipLevel` (Optional[str])
- `preferredLanguage` (str): Default: "en"
- `timezone` (Optional[str])

---

### UserResponse

User data in response.

**Properties:**

- `id` (str): User ID
- `email` (str): User's email
- `organization` (str): Organization name
- `country` (str): Country code
- `profile` (UserProfileResponse): Profile data
- `displayName` (Optional[str]): Display name
- `status` (str): Account status
- `createdAt` (Optional[datetime]): Account creation time

---

### LoginResponse

Login response data.

**Properties:**

- `user` (UserResponse): User data
- `accessToken` (str): JWT access token

# Auth Router

Authentication endpoints for user registration, login, logout, password reset, and email verification.

---

## Functions

### generate_token

- **Outputs:** (str) Secure random URL-safe token
- **Description:** Generate a 32-byte secure random token.

### user_to_response

- **Inputs:**
  - `user` (User): User model
- **Outputs:** (dict) Response dictionary with camelCase keys
- **Description:** Convert User model to response dictionary.

---

## Endpoints

### POST /api/auth/register

- **Inputs:**
  - Body: `RegisterRequest` (email, password, organization, country, firstName?, lastName?)
- **Outputs:** (dict) {user: UserResponse}
- **Description:** Register a new user account. Creates user with pending_verification status, generates verification token, sends verification email. Returns 400 if weak password, 409 if email exists.

---

### POST /api/auth/login

- **Inputs:**
  - Body: `LoginRequest` (email, password, rememberMe?)
- **Outputs:** (dict) {user: UserResponse, accessToken: string}
- **Description:** Authenticate user and return access token. Returns 401 if invalid credentials or account not active. Updates last_login_at.

---

### POST /api/auth/logout

- **Inputs:**
  - Header: Authorization (Bearer token)
- **Outputs:** (dict) {message: string}
- **Description:** Sign out the current user. In stateless JWT, client discards token.

---

### POST /api/auth/forgot-password

- **Inputs:**
  - Body: `ForgotPasswordRequest` (email)
- **Outputs:** (dict) {message: string}
- **Description:** Request password reset email. Always returns success to prevent email enumeration. Generates reset token valid for PASSWORD_RESET_EXPIRE_HOURS.

---

### POST /api/auth/reset-password

- **Inputs:**
  - Body: `ResetPasswordRequest` (token, password)
- **Outputs:** (dict) {message: string}
- **Description:** Reset password using reset token. Returns 400 if token invalid/expired or password weak. Clears reset token after success.

---

### POST /api/auth/verify-email

- **Inputs:**
  - Body: `VerifyEmailRequest` (token)
- **Outputs:** (dict) {user: {id, email, status}}
- **Description:** Verify email address using verification token. Returns 400 if token invalid/expired. Activates user account.

---

### POST /api/auth/resend-verification

- **Inputs:**
  - Body: `ResendVerificationRequest` (email)
- **Outputs:** (dict) {message: string}
- **Description:** Resend verification email. Always returns success to prevent enumeration. Only sends if user exists and is pending_verification.

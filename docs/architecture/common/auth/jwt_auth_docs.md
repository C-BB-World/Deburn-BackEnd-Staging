# JWTAuth

JWT + bcrypt authentication provider implementation.

---

## Classes

### JWTAuth

JWT + bcrypt authentication provider. Handles token creation/verification and password hashing. User storage is handled by callbacks to allow integration with any database.

**Properties:**

- `secret` (str): Secret key for JWT signing
- `algorithm` (str): JWT algorithm (default: HS256)
- `access_token_expire` (timedelta): Token expiration duration
- `reset_token_expire` (timedelta): Password reset token expiration
- `verification_token_expire` (timedelta): Email verification token expiration

**Methods:**

#### __init__

- **Inputs:**
  - `secret` (str): Secret key for JWT signing
  - `algorithm` (str): JWT algorithm. Default: "HS256"
  - `access_token_expire_minutes` (int): Token expiration time. Default: 30
  - `reset_token_expire_hours` (int): Password reset token expiration. Default: 24
  - `verification_token_expire_hours` (int): Email verification expiration. Default: 48
  - `get_user_by_email` (Optional[UserLookupCallback]): Callback to fetch user by email
  - `get_user_by_id` (Optional[Callable]): Callback to fetch user by ID
  - `create_user_in_db` (Optional[UserCreateCallback]): Callback to create user in database
  - `update_user_in_db` (Optional[UserUpdateCallback]): Callback to update user in database
  - `delete_user_in_db` (Optional[UserDeleteCallback]): Callback to delete user from database
- **Outputs:** (JWTAuth) New JWTAuth instance
- **Description:** Initialize JWT auth provider with callbacks for database integration

#### hash_password

- **Inputs:**
  - `password` (str): Plain text password
- **Outputs:** (str) Hashed password using bcrypt
- **Description:** Hash a password using bcrypt

#### verify_password

- **Inputs:**
  - `password` (str): Plain text password
  - `hashed` (str): Hashed password to compare against
- **Outputs:** (bool) True if password matches
- **Description:** Verify a password against its hash

#### create_user

- **Inputs:**
  - `email` (str): User's email
  - `password` (str): User's password
  - `**kwargs` (Any): Additional user data
- **Outputs:** (str) Created user's ID
- **Description:** Create a new user with hashed password. Raises NotImplementedError if callback not provided, ValueError if email exists.

#### verify_credentials

- **Inputs:**
  - `email` (str): User's email
  - `password` (str): User's password
- **Outputs:** (Dict[str, Any]) User info without password_hash
- **Description:** Verify email and password. Raises NotImplementedError if callback not provided, ValueError if invalid.

#### create_token

- **Inputs:**
  - `user_id` (str): User's ID
  - `**claims` (Any): Additional JWT claims
- **Outputs:** (str) JWT token string
- **Description:** Create a JWT token with user_id as subject, expiration, and issued-at claims

#### verify_token

- **Inputs:**
  - `token` (str): JWT token to verify
- **Outputs:** (Dict[str, Any]) Decoded token payload
- **Description:** Verify and decode a JWT token. Raises ValueError if token is revoked or invalid.

#### revoke_token

- **Inputs:**
  - `token` (str): Token to revoke
- **Outputs:** (None)
- **Description:** Add token to in-memory revocation list

#### send_password_reset

- **Inputs:**
  - `email` (str): User's email
- **Outputs:** (str) Reset token (URL-safe random string)
- **Description:** Generate password reset token and store with expiration

#### reset_password

- **Inputs:**
  - `token` (str): Reset token
  - `new_password` (str): New password
- **Outputs:** (None)
- **Description:** Reset password using token. Raises ValueError if token invalid or expired.

#### send_verification_email

- **Inputs:**
  - `email` (str): User's email
- **Outputs:** (str) Verification token (URL-safe random string)
- **Description:** Generate email verification token and store with expiration

#### verify_email

- **Inputs:**
  - `token` (str): Verification token
- **Outputs:** (None)
- **Description:** Verify email using token. Raises ValueError if token invalid or expired.

#### delete_user

- **Inputs:**
  - `user_id` (str): User's ID
- **Outputs:** (None)
- **Description:** Delete user account. Raises NotImplementedError if callback not provided.

#### get_user_by_id

- **Inputs:**
  - `user_id` (str): User's ID
- **Outputs:** (Optional[Dict[str, Any]]) User info or None
- **Description:** Get user by ID. Raises NotImplementedError if callback not provided.

#### update_user

- **Inputs:**
  - `user_id` (str): User's ID
  - `**updates` (Any): Fields to update
- **Outputs:** (Dict[str, Any]) Updated user info
- **Description:** Update user information. Raises NotImplementedError if callback not provided.

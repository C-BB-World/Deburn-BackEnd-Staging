# AuthProvider (Base)

Abstract authentication provider interface. Defines the contract that all auth providers must implement.

---

## Classes

### AuthProvider (ABC)

Abstract authentication provider. Implement this interface for different auth strategies.

**Methods:**

#### create_user

- **Inputs:**
  - `email` (str): User's email address
  - `password` (str): User's password (will be hashed)
  - `**kwargs` (Any): Additional user data (name, etc.)
- **Outputs:** (str) The created user's ID
- **Description:** Create a new user account. Raises ValueError if email already exists or validation fails.

#### verify_credentials

- **Inputs:**
  - `email` (str): User's email address
  - `password` (str): User's password
- **Outputs:** (Dict[str, Any]) Dictionary containing user info (at minimum: user_id, email)
- **Description:** Verify email and password credentials. Raises ValueError if credentials are invalid.

#### create_token

- **Inputs:**
  - `user_id` (str): The user's ID
  - `**claims` (Any): Additional claims to include in the token
- **Outputs:** (str) The authentication token string
- **Description:** Create an authentication token for a user.

#### verify_token

- **Inputs:**
  - `token` (str): The token to verify
- **Outputs:** (Dict[str, Any]) Dictionary containing decoded token claims (at minimum: sub/user_id)
- **Description:** Verify an authentication token. Raises ValueError if token is invalid, expired, or revoked.

#### revoke_token

- **Inputs:**
  - `token` (str): The token to revoke
- **Outputs:** (None)
- **Description:** Revoke/invalidate a token.

#### send_password_reset

- **Inputs:**
  - `email` (str): User's email address
- **Outputs:** (str) Reset token (for testing) or confirmation message
- **Description:** Initiate password reset process. Raises ValueError if email is not found.

#### reset_password

- **Inputs:**
  - `token` (str): Password reset token
  - `new_password` (str): New password to set
- **Outputs:** (None)
- **Description:** Reset password using a reset token. Raises ValueError if token is invalid or expired.

#### send_verification_email

- **Inputs:**
  - `email` (str): User's email address
- **Outputs:** (str) Verification token (for testing)
- **Description:** Send email verification. Raises ValueError if email is not found.

#### verify_email

- **Inputs:**
  - `token` (str): Email verification token
- **Outputs:** (None)
- **Description:** Verify email address using verification token. Raises ValueError if token is invalid or expired.

#### delete_user

- **Inputs:**
  - `user_id` (str): The user's ID to delete
- **Outputs:** (None)
- **Description:** Delete a user account. Raises ValueError if user is not found.

#### get_user_by_id

- **Inputs:**
  - `user_id` (str): The user's ID
- **Outputs:** (Optional[Dict[str, Any]]) User info dict or None if not found
- **Description:** Get user information by ID.

#### update_user

- **Inputs:**
  - `user_id` (str): The user's ID
  - `**updates` (Any): Fields to update
- **Outputs:** (Dict[str, Any]) Updated user info
- **Description:** Update user information. Raises ValueError if user is not found.

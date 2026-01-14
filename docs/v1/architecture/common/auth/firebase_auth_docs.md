# FirebaseAuth

Firebase Admin SDK authentication provider implementation.

---

## Classes

### FirebaseAuth

Firebase Admin SDK authentication provider. Handles user authentication through Firebase.

**Methods:**

#### __init__

- **Inputs:**
  - `credentials_path` (Optional[str]): Path to service account JSON file
  - `credentials_dict` (Optional[Dict[str, Any]]): Service account credentials as dict
  - `project_id` (Optional[str]): Firebase project ID (optional, can be inferred)
- **Outputs:** (FirebaseAuth) New FirebaseAuth instance
- **Description:** Initialize Firebase auth provider. Raises ImportError if firebase-admin not installed.

#### create_user

- **Inputs:**
  - `email` (str): User's email
  - `password` (str): User's password
  - `**kwargs` (Any): Optional: display_name, photo_url, disabled
- **Outputs:** (str) Firebase user UID
- **Description:** Create a new Firebase user. Raises ValueError if email exists or creation fails.

#### verify_credentials

- **Inputs:**
  - `email` (str): User's email
  - `password` (str): User's password
- **Outputs:** (Dict[str, Any]) N/A
- **Description:** Not supported by Firebase Admin SDK. Raises NotImplementedError. Use client-side Firebase SDK for sign-in.

#### create_token

- **Inputs:**
  - `user_id` (str): User's UID
  - `**claims` (Any): Additional custom claims
- **Outputs:** (str) Custom token string
- **Description:** Create a custom token for the user. Raises ValueError if creation fails.

#### verify_token

- **Inputs:**
  - `token` (str): Firebase ID token
- **Outputs:** (Dict[str, Any]) Decoded token with sub field added for compatibility
- **Description:** Verify a Firebase ID token. Raises ValueError if token is revoked, expired, or invalid.

#### revoke_token

- **Inputs:**
  - `token` (str): Firebase ID token
- **Outputs:** (None)
- **Description:** Revoke all refresh tokens for the user. Raises ValueError if revocation fails.

#### send_password_reset

- **Inputs:**
  - `email` (str): User's email
- **Outputs:** (str) Password reset link
- **Description:** Generate password reset link. Returns generic message if user not found (security).

#### reset_password

- **Inputs:**
  - `token` (str): Reset action code
  - `new_password` (str): New password
- **Outputs:** (None)
- **Description:** Not implemented - Firebase handles through action handler. Raises NotImplementedError.

#### send_verification_email

- **Inputs:**
  - `email` (str): User's email
- **Outputs:** (str) Email verification link
- **Description:** Generate email verification link. Raises ValueError if user not found.

#### verify_email

- **Inputs:**
  - `token` (str): Verification action code
- **Outputs:** (None)
- **Description:** Not implemented - Firebase handles through action handler. Raises NotImplementedError.

#### delete_user

- **Inputs:**
  - `user_id` (str): User's UID
- **Outputs:** (None)
- **Description:** Delete a Firebase user. Raises ValueError if user not found.

#### get_user_by_id

- **Inputs:**
  - `user_id` (str): User's UID
- **Outputs:** (Optional[Dict[str, Any]]) User info dict with id, uid, email, email_verified, display_name, photo_url, disabled, provider_data
- **Description:** Get Firebase user by UID. Returns None if not found.

#### update_user

- **Inputs:**
  - `user_id` (str): User's UID
  - `**updates` (Any): Fields: email, password, display_name, photo_url, disabled, email_verified
- **Outputs:** (Dict[str, Any]) Updated user info
- **Description:** Update Firebase user. Raises ValueError if user not found.

#### get_user_by_email

- **Inputs:**
  - `email` (str): User's email
- **Outputs:** (Optional[Dict[str, Any]]) User info dict or None
- **Description:** Get Firebase user by email. Returns None if not found.

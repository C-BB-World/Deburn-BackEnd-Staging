# Auth Dependencies

FastAPI authentication dependency factories.

---

## Functions

### create_auth_dependency

- **Inputs:**
  - `get_auth_provider` (Callable[[], AuthProvider]): Callable that returns the AuthProvider instance
  - `header_name` (str): Header to extract token from. Default: "Authorization"
  - `scheme` (str): Auth scheme prefix. Default: "Bearer"
- **Outputs:** (Callable) FastAPI dependency function that returns user_id (str)
- **Description:** Factory to create FastAPI auth dependencies. Returns a dependency that extracts and verifies user ID from authorization header. Raises HTTPException 401 if token is missing, invalid, or expired.

---

### create_optional_auth_dependency

- **Inputs:**
  - `get_auth_provider` (Callable[[], AuthProvider]): Callable that returns the AuthProvider instance
  - `header_name` (str): Header to extract token from. Default: "Authorization"
  - `scheme` (str): Auth scheme prefix. Default: "Bearer"
- **Outputs:** (Callable) FastAPI dependency function that returns Optional[str] (user_id or None)
- **Description:** Factory to create optional auth dependency. Returns None instead of raising exception when no token is provided. Useful for endpoints that work for both authenticated and anonymous users.

---

### create_admin_dependency

- **Inputs:**
  - `get_auth_provider` (Callable[[], AuthProvider]): Callable that returns the AuthProvider instance
  - `is_admin_check` (Callable[[str], bool]): Callable that checks if user_id is an admin
  - `header_name` (str): Header to extract token from. Default: "Authorization"
  - `scheme` (str): Auth scheme prefix. Default: "Bearer"
- **Outputs:** (Callable) FastAPI dependency function that returns user_id (str) for admin users only
- **Description:** Factory to create admin-only auth dependency. Verifies both authentication and admin status. Raises HTTPException 401 if not authenticated, HTTPException 403 if not an admin.

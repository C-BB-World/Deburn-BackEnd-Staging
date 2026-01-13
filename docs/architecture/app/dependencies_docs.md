# Dependencies

FastAPI dependency injection for authentication, AI providers, and services.

---

## Functions

### get_auth_provider

- **Inputs:** None
- **Outputs:** (AuthProvider) Configured authentication provider (JWTAuth or FirebaseAuth)
- **Description:** Get the configured authentication provider based on settings.AUTH_PROVIDER. Cached with lru_cache. Raises ValueError if required credentials not configured.

---

### get_ai_provider

- **Inputs:** None
- **Outputs:** (AIProvider) Configured AI provider (ClaudeProvider or OpenAIProvider)
- **Description:** Get the configured AI provider based on settings.AI_PROVIDER. Cached with lru_cache. Raises ValueError if required API key not configured.

---

### get_current_user

- **Inputs:**
  - `authorization` (Optional[str]): Authorization header value. Via Header dependency.
  - `auth` (AuthProvider): Auth provider. Via Depends(get_auth_provider).
- **Outputs:** (User) The authenticated user document
- **Description:** Get the current authenticated user from the Authorization header. Raises HTTPException 401 if token missing/invalid/user not found. Raises HTTPException 403 if account not active.

---

### get_optional_user

- **Inputs:**
  - `authorization` (Optional[str]): Authorization header value. Via Header dependency.
  - `auth` (AuthProvider): Auth provider. Via Depends(get_auth_provider).
- **Outputs:** (Optional[User]) The authenticated user or None
- **Description:** Get the current user if authenticated, or None if not. Use for endpoints that work with or without authentication.

---

### require_admin

- **Inputs:**
  - `user` (User): Current user. Via Depends(get_current_user).
- **Outputs:** (User) The authenticated admin user
- **Description:** Require the current user to be an admin. Raises HTTPException 403 if user is not an admin.

---

### get_coach_service

- **Inputs:**
  - `ai` (AIProvider): AI provider. Via Depends(get_ai_provider).
- **Outputs:** (CoachService) Configured coach service instance
- **Description:** Get the coach service instance with injected AI provider and i18n.

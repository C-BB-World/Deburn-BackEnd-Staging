# Profile Router

User profile management endpoints.

---

## Endpoints

### PUT /api/profile

- **Inputs:**
  - Header: Authorization (Bearer token)
  - Body: `ProfileUpdateRequest` (firstName?, lastName?, jobTitle?, leadershipLevel?, preferredLanguage?, timezone?)
- **Outputs:** (dict) {user: UserResponse}
- **Description:** Update current user's profile. Only updates provided fields.

---

### POST /api/profile/avatar

- **Inputs:**
  - Header: Authorization (Bearer token)
  - Body: multipart/form-data with `file` (image)
- **Outputs:** (dict) {avatarUrl: string}
- **Description:** Upload a new avatar image. Validates file type and size. Returns the uploaded avatar URL.

---

### PUT /api/profile/avatar

- **Inputs:**
  - Header: Authorization (Bearer token)
- **Outputs:** (dict) {message: string}
- **Description:** Remove current avatar (reset to default). Sets avatarUrl to null.

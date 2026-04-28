# Hub Router

Organization admin and hub management endpoints.

---

## Functions

### get_user_organization

- **Inputs:**
  - `user` (User): User model
- **Outputs:** (Organization) User's organization
- **Description:** Get the organization where the user is an admin. Raises HTTPException 403 if user is not an org admin.

---

## Endpoints

### GET /api/hub/organization

- **Inputs:**
  - Header: Authorization (Bearer token)
- **Outputs:** (dict) {organization: {id, name, domain, memberCount, createdAt}}
- **Description:** Get organization details for the current user's organization. Requires org admin access.

---

### GET /api/hub/members

- **Inputs:**
  - Header: Authorization (Bearer token)
  - Query:
    - `limit` (int, default 50) - Max results per page
    - `offset` (int, default 0) - Pagination offset
    - `status_filter` (string, optional) - Filter by user status
- **Outputs:** (dict) {members: List[MemberInfo], pagination: {total, limit, offset, hasMore}}
- **Description:** Get members of the current user's organization. Returns paginated list with member info (id, email, name, role, status, joinedAt). Requires org admin access.

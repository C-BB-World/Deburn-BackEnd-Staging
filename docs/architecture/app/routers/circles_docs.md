# Circles Router

Peer support groups and invitations endpoints.

---

## Endpoints

### GET /api/circles/groups

- **Inputs:**
  - Header: Authorization (Bearer token)
- **Outputs:** (dict) {groups: List[CircleGroup]}
- **Description:** Get the user's peer support groups. Returns active groups where user is a member. (Placeholder - returns empty list until CircleGroup model is implemented)

---

### GET /api/circles/invitations

- **Inputs:**
  - Header: Authorization (Bearer token)
- **Outputs:** (dict) {invitations: List[CircleInvitation]}
- **Description:** Get pending circle invitations for the user. Returns invitations where user's email matches and status is pending. (Placeholder - returns empty list until CircleInvitation model is implemented)

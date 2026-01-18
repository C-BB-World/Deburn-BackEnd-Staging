## API Description

Endpoints for organization administrators to manage circle pools, invitations, and groups. These endpoints require the user to be an organization admin (checked via `organizationMembers` collection with `role: "admin"`).

---

## GET /api/auth/admin-status

Checks if the current user is an organization admin.

**Response:**
```json
{
  "success": true,
  "data": {
    "isAdmin": true,
    "organizations": [
      {
        "id": "org_123",
        "name": "Acme Corp",
        "role": "admin"
      }
    ]
  }
}
```

---

## GET /api/circles/pools

Fetches pools for the user's organization. Auto-detects organization if user is admin of one org.

**Query Parameters:**
- `status` (optional): Filter by pool status (`draft`, `inviting`, `active`, `completed`, `cancelled`)

**Response:**
```json
{
  "success": true,
  "data": {
    "pools": [
      {
        "id": "pool_123",
        "name": "Default",
        "topic": "Leadership Development",
        "status": "inviting",
        "targetGroupSize": 4,
        "cadence": "biweekly",
        "stats": {
          "totalInvited": 15,
          "totalAccepted": 8,
          "totalDeclined": 2,
          "pending": 5
        },
        "createdAt": "2026-01-10T10:00:00Z"
      }
    ]
  }
}
```

---

## GET /api/circles/pools/:poolId

Fetches pool details.

**Response:**
```json
{
  "success": true,
  "data": {
    "pool": {
      "id": "pool_123",
      "name": "Default",
      "topic": "Leadership Development",
      "description": "Monthly leadership circles",
      "status": "inviting",
      "targetGroupSize": 4,
      "cadence": "biweekly",
      "organizationId": "org_123",
      "createdBy": "user_456",
      "createdAt": "2026-01-10T10:00:00Z",
      "updatedAt": "2026-01-15T10:00:00Z"
    }
  }
}
```

---

## POST /api/circles/pools/:poolId/invitations

Sends invitations to the specified emails.

**Request Body:**
```json
{
  "invitees": [
    {
      "email": "john@example.com",
      "firstName": "John",
      "lastName": "Doe"
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "sent": [
      { "email": "john@example.com", "token": "abc123..." }
    ],
    "failed": [
      { "email": "invalid-email", "reason": "Invalid email format" }
    ],
    "duplicate": [
      { "email": "existing@example.com" }
    ]
  }
}
```

---

## GET /api/circles/pools/:poolId/invitations

Lists all invitations for a pool (admin only).

**Response:**
```json
{
  "success": true,
  "data": {
    "invitations": [
      {
        "id": "inv_123",
        "email": "john@example.com",
        "firstName": "John",
        "lastName": "Doe",
        "status": "pending",
        "invitedBy": {
          "id": "user_456",
          "email": "admin@example.com",
          "firstName": "Admin",
          "lastName": "User"
        },
        "invitedAt": "2026-01-15T10:00:00Z",
        "acceptedAt": null,
        "declinedAt": null,
        "expiresAt": "2026-01-29T10:00:00Z"
      }
    ],
    "count": 15
  }
}
```

---

## DELETE /api/circles/invitations/:invitationId

Cancels/removes an invitation (admin only).

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Invitation cancelled successfully"
  }
}
```

---

## POST /api/circles/pools/:poolId/assign

Triggers group assignment for accepted members (admin only).

**Response:**
```json
{
  "success": true,
  "message": "Successfully created 2 groups with 8 members",
  "data": {
    "groups": [
      {
        "id": "grp_123",
        "name": "Group 1",
        "members": [
          {
            "id": "user_1",
            "email": "john@example.com",
            "firstName": "John",
            "lastName": "Doe"
          }
        ],
        "memberCount": 4
      }
    ],
    "totalMembers": 8
  }
}
```

---

## GET /api/circles/pools/:poolId/groups

Lists groups for a pool (admin only).

**Response:**
```json
{
  "success": true,
  "data": {
    "groups": [
      {
        "id": "grp_123",
        "name": "Group 1",
        "members": [
          {
            "id": "user_1",
            "email": "john@example.com",
            "firstName": "John",
            "lastName": "Doe"
          }
        ],
        "memberCount": 4,
        "createdAt": "2026-01-18T10:00:00Z"
      }
    ],
    "count": 2
  }
}
```

---

## Error Responses

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message"
  }
}
```

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `NOT_ADMIN` | 403 | User is not an organization admin |
| `ACCESS_DENIED` | 403 | User does not have access to this resource |
| `POOL_NOT_FOUND` | 404 | Pool does not exist |
| `INVITATION_NOT_FOUND` | 404 | Invitation does not exist |
| `NO_INVITEES` | 400 | No valid invitees provided |
| `INSUFFICIENT_MEMBERS` | 400 | Not enough accepted members for group assignment |

---

---

## Implementation Plan

### Overview

The services already exist with full functionality. Only the **router endpoints** need to be added.

### Existing Services (No Changes Needed)

| Service | File | Methods to Use |
|---------|------|----------------|
| `PoolService` | `app_v2/services/circles/pool_service.py` | `get_pools_for_organization()`, `get_pool()`, `get_pool_stats()` |
| `InvitationService` | `app_v2/services/circles/invitation_service.py` | `send_invitations()`, `get_invitations_for_pool()` |
| `GroupService` | `app_v2/services/circles/group_service.py` | `assign_groups()`, `get_groups_for_pool()` |

### Files to Modify

#### 1. `app_v2/routers/auth.py`

Add new endpoint:

```python
@router.get("/admin-status")
async def get_admin_status(
    user: Annotated[dict, Depends(require_auth)],
):
    """Check if current user is an organization admin."""
    # Query organizationMembers for admin role
    org_members_collection = get_db()["organizationMembers"]

    admin_memberships = await org_members_collection.find({
        "userId": ObjectId(user["_id"]),
        "role": "admin",
        "status": "active"
    }).to_list(length=100)

    organizations = []
    if admin_memberships:
        org_ids = [m["organizationId"] for m in admin_memberships]
        orgs = await get_db()["organizations"].find({
            "_id": {"$in": org_ids}
        }).to_list(length=100)

        organizations = [{
            "id": str(org["_id"]),
            "name": org.get("name"),
            "role": "admin"
        } for org in orgs]

    return success_response({
        "isAdmin": len(organizations) > 0,
        "organizations": organizations
    })
```

#### 2. `app_v2/routers/circles.py`

Add new admin endpoints after existing member endpoints:

```python
# ==========================================
# ADMIN ENDPOINTS
# ==========================================

@router.get("/pools")
async def get_pools(
    user: Annotated[dict, Depends(require_auth)],
    status: Optional[str] = None,
):
    """Get pools for organization (admin only)."""
    pool_service = get_pool_service()
    user_id = str(user["_id"])

    pools = await pool_service.get_pools_for_organization(
        organization_id=None,  # Auto-detect
        user_id=user_id,
        status=status
    )

    return success_response({"pools": pools})


@router.get("/pools/{pool_id}")
async def get_pool(
    pool_id: str,
    user: Annotated[dict, Depends(require_auth)],
):
    """Get pool details (admin only)."""
    pool_service = get_pool_service()

    pool = await pool_service.get_pool(pool_id)

    return success_response({"pool": pool})


@router.post("/pools/{pool_id}/invitations")
async def send_invitations(
    pool_id: str,
    body: SendInvitationsRequest,
    user: Annotated[dict, Depends(require_auth)],
):
    """Send invitations to a pool (admin only)."""
    invitation_service = get_invitation_service()
    user_id = str(user["_id"])

    result = await invitation_service.send_invitations(
        pool_id=pool_id,
        invitees=[inv.model_dump() for inv in body.invitees],
        invited_by=user_id
    )

    return success_response(result)


@router.get("/pools/{pool_id}/invitations")
async def get_pool_invitations(
    pool_id: str,
    user: Annotated[dict, Depends(require_auth)],
):
    """Get all invitations for a pool (admin only)."""
    invitation_service = get_invitation_service()

    invitations = await invitation_service.get_invitations_for_pool(pool_id)

    formatted = [{
        "id": str(inv["_id"]),
        "email": inv.get("email"),
        "firstName": inv.get("firstName"),
        "lastName": inv.get("lastName"),
        "status": inv.get("status"),
        "invitedAt": inv.get("createdAt"),
        "acceptedAt": inv.get("acceptedAt"),
        "declinedAt": inv.get("declinedAt"),
        "expiresAt": inv.get("expiresAt"),
    } for inv in invitations]

    return success_response({
        "invitations": formatted,
        "count": len(formatted)
    })


@router.delete("/invitations/{invitation_id}")
async def cancel_invitation(
    invitation_id: str,
    user: Annotated[dict, Depends(require_auth)],
):
    """Cancel/remove an invitation (admin only)."""
    # Need to add cancel_invitation method to InvitationService
    # or update status directly

    return success_response({
        "message": "Invitation cancelled successfully"
    })


@router.post("/pools/{pool_id}/assign")
async def assign_groups(
    pool_id: str,
    user: Annotated[dict, Depends(require_auth)],
):
    """Assign accepted members to groups (admin only)."""
    group_service = get_group_service()
    user_id = str(user["_id"])

    result = await group_service.assign_groups(
        pool_id=pool_id,
        assigned_by=user_id
    )

    return success_response(result)


@router.get("/pools/{pool_id}/groups")
async def get_pool_groups(
    pool_id: str,
    user: Annotated[dict, Depends(require_auth)],
):
    """Get groups for a pool (admin only)."""
    group_service = get_group_service()

    groups = await group_service.get_groups_for_pool(pool_id)

    formatted = [{
        "id": str(g["_id"]),
        "name": g.get("name"),
        "members": [{
            "id": str(m.get("_id", m)),
            "email": m.get("email", ""),
            "firstName": m.get("profile", {}).get("firstName", ""),
            "lastName": m.get("profile", {}).get("lastName", ""),
        } for m in g.get("members", [])],
        "memberCount": len(g.get("members", [])),
        "createdAt": g.get("createdAt"),
    } for g in groups]

    return success_response({
        "groups": formatted,
        "count": len(formatted)
    })
```

#### 3. `app_v2/schemas/circles.py`

Add new request schemas:

```python
class InviteeRequest(BaseModel):
    email: str
    firstName: Optional[str] = None
    lastName: Optional[str] = None

class SendInvitationsRequest(BaseModel):
    invitees: List[InviteeRequest]
```

#### 4. `app_v2/dependencies.py`

Ensure these dependency functions exist:

```python
def get_pool_service() -> PoolService:
    return PoolService(get_db())

def get_invitation_service() -> InvitationService:
    return InvitationService(get_db())

def get_group_service() -> GroupService:
    return GroupService(get_db())
```

### Admin Authorization

Each admin endpoint should verify the user is an org admin for the pool's organization. The `PoolService._is_org_admin()` method already exists for this:

```python
async def _is_org_admin(self, organization_id: str, user_id: str) -> bool:
    member = await self._org_members_collection.find_one({
        "organizationId": ObjectId(organization_id),
        "userId": ObjectId(user_id),
        "role": "admin"
    })
    return member is not None
```

### Testing Checklist

- [ ] `GET /api/auth/admin-status` returns correct admin status
- [ ] `GET /api/circles/pools` returns pools for admin's organization
- [ ] `GET /api/circles/pools/:id` returns pool details
- [ ] `POST /api/circles/pools/:id/invitations` sends invitations
- [ ] `GET /api/circles/pools/:id/invitations` lists invitations
- [ ] `DELETE /api/circles/invitations/:id` cancels invitation
- [ ] `POST /api/circles/pools/:id/assign` assigns groups
- [ ] `GET /api/circles/pools/:id/groups` lists groups
- [ ] Non-admin users get 403 on all admin endpoints

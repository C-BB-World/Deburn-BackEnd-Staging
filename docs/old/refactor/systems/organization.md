# Organization System

## Description

The Organization System manages companies and groups that use the platform. It handles organization creation, member management, and organization-level settings that apply to features like Circles.

**Responsibilities:**
- Create and manage organizations
- Add, remove, and manage organization members
- Handle member roles (admin, member)
- Allow members to leave organizations
- Transfer ownership between admins
- Organization-level settings for Circles

**Tech Stack:**
- **MongoDB** - Organization and membership storage
- **Express Middleware** - Role-based access control

**Roles:**
| Role | Permissions |
|------|-------------|
| `admin` | Full access: update settings, manage members, change roles |
| `member` | Read access: view org details and member list, leave org |

---

## Pipelines

### Pipeline 1: Create Organization

Creates a new organization with the creator as the first admin.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       CREATE ORGANIZATION PIPELINE                           │
└─────────────────────────────────────────────────────────────────────────────┘

Frontend                         Backend                           Database
────────                         ───────                           ────────
    │                                │                                 │
    │  POST /api/organizations       │                                 │
    │  { name, domain, settings }    │                                 │
    │───────────────────────────────>│                                 │
    │                                │                                 │
    │                                │  1. Validate input              │
    │                                │     - name: 2-100 chars         │
    │                                │     - domain: optional          │
    │                                │                                 │
    │                                │  2. If domain provided:         │
    │                                │     Check not already taken     │
    │                                │────────────────────────────────>│
    │                                │                                 │
    │                                │  3. Create Organization         │
    │                                │     ┌─────────────────────────┐ │
    │                                │     │ name: "Acme Corp"       │ │
    │                                │     │ domain: "acme.com"      │ │
    │                                │     │ settings: {...}         │ │
    │                                │     │ status: "active"        │ │
    │                                │     │ createdBy: userId       │ │
    │                                │     └─────────────────────────┘ │
    │                                │────────────────────────────────>│
    │                                │                                 │
    │                                │  4. Create OrganizationMember   │
    │                                │     (creator as admin)          │
    │                                │     ┌─────────────────────────┐ │
    │                                │     │ organizationId: orgId   │ │
    │                                │     │ userId: creatorId       │ │
    │                                │     │ role: "admin"           │ │
    │                                │     │ status: "active"        │ │
    │                                │     │ invitedBy: creatorId    │ │
    │                                │     └─────────────────────────┘ │
    │                                │────────────────────────────────>│
    │                                │                                 │
    │  5. Return organization        │                                 │
    │<───────────────────────────────│                                 │
    │                                │                                 │
```

**Steps:**
1. Validate organization name (2-100 characters)
2. If domain provided, verify it's not already used by another org
3. Create Organization document with provided settings
4. Create OrganizationMember for creator with `role: "admin"`
5. Return created organization

**Default Settings:**
```
{
  defaultMeetingDuration: 60,    // minutes
  defaultGroupSize: 4,          // 3-4 members
  allowMemberPoolCreation: false,
  timezone: "Europe/Stockholm"
}
```

**Error Cases:**
- Name too short/long → 400 Bad Request
- Domain already taken → 400 Bad Request

---

### Pipeline 2: Manage Members

Handles adding, removing, leaving, role changes, and ownership transfer.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ADD MEMBER PIPELINE                                │
└─────────────────────────────────────────────────────────────────────────────┘

Admin                            Backend                           Database
─────                            ───────                           ────────
    │                                │                                 │
    │  POST /api/organizations/:id/members                             │
    │  { userId, role }              │                                 │
    │───────────────────────────────>│                                 │
    │                                │                                 │
    │                                │  1. Verify requester is admin   │
    │                                │────────────────────────────────>│
    │                                │                                 │
    │                                │  2. Check if user already member│
    │                                │────────────────────────────────>│
    │                                │                                 │
    │                                │     [If removed: reactivate]    │
    │                                │     [If active: return error]   │
    │                                │                                 │
    │                                │  3. Create OrganizationMember   │
    │                                │     ┌─────────────────────────┐ │
    │                                │     │ organizationId: orgId   │ │
    │                                │     │ userId: newUserId       │ │
    │                                │     │ role: "member"          │ │
    │                                │     │ invitedBy: adminId      │ │
    │                                │     └─────────────────────────┘ │
    │                                │────────────────────────────────>│
    │                                │                                 │
    │  4. Return membership          │                                 │
    │<───────────────────────────────│                                 │


┌─────────────────────────────────────────────────────────────────────────────┐
│                          REMOVE MEMBER PIPELINE                              │
└─────────────────────────────────────────────────────────────────────────────┘

Admin                            Backend                           Database
─────                            ───────                           ────────
    │                                │                                 │
    │  DELETE /api/organizations/:id/members/:userId                   │
    │───────────────────────────────>│                                 │
    │                                │                                 │
    │                                │  1. Verify requester is admin   │
    │                                │────────────────────────────────>│
    │                                │                                 │
    │                                │  2. Find member                 │
    │                                │────────────────────────────────>│
    │                                │                                 │
    │                                │  3. If member is admin:         │
    │                                │     Check admin count > 1       │
    │                                │────────────────────────────────>│
    │                                │                                 │
    │                                │     [If last admin: error]      │
    │                                │                                 │
    │                                │  4. Set status = "removed"      │
    │                                │────────────────────────────────>│
    │                                │                                 │
    │  5. Return success             │                                 │
    │<───────────────────────────────│                                 │


┌─────────────────────────────────────────────────────────────────────────────┐
│                         LEAVE ORGANIZATION PIPELINE                          │
└─────────────────────────────────────────────────────────────────────────────┘

Member                           Backend                           Database
──────                           ───────                           ────────
    │                                │                                 │
    │  POST /api/organizations/:id/leave                               │
    │───────────────────────────────>│                                 │
    │                                │                                 │
    │                                │  1. Find user's membership      │
    │                                │────────────────────────────────>│
    │                                │                                 │
    │                                │  2. If user is admin:           │
    │                                │     ┌─────────────────────────┐ │
    │                                │     │ Check admin count       │ │
    │                                │     │                         │ │
    │                                │     │ If last admin:          │ │
    │                                │     │ → Must transfer first   │ │
    │                                │     │ → Return 400 with       │ │
    │                                │     │   transfer requirement  │ │
    │                                │     └─────────────────────────┘ │
    │                                │                                 │
    │                                │  3. Set status = "removed"      │
    │                                │────────────────────────────────>│
    │                                │                                 │
    │  4. Return success             │                                 │
    │<───────────────────────────────│                                 │


┌─────────────────────────────────────────────────────────────────────────────┐
│                          CHANGE ROLE PIPELINE                                │
└─────────────────────────────────────────────────────────────────────────────┘

Admin                            Backend                           Database
─────                            ───────                           ────────
    │                                │                                 │
    │  PUT /api/organizations/:id/members/:userId/role                 │
    │  { role: "admin" | "member" }  │                                 │
    │───────────────────────────────>│                                 │
    │                                │                                 │
    │                                │  1. Verify requester is admin   │
    │                                │────────────────────────────────>│
    │                                │                                 │
    │                                │  2. Find target membership      │
    │                                │────────────────────────────────>│
    │                                │                                 │
    │                                │  3. If demoting admin → member: │
    │                                │     Check admin count > 1       │
    │                                │────────────────────────────────>│
    │                                │                                 │
    │                                │     [If last admin: error]      │
    │                                │                                 │
    │                                │  4. Update role                 │
    │                                │────────────────────────────────>│
    │                                │                                 │
    │  5. Return updated membership  │                                 │
    │<───────────────────────────────│                                 │


┌─────────────────────────────────────────────────────────────────────────────┐
│                       TRANSFER OWNERSHIP PIPELINE                            │
└─────────────────────────────────────────────────────────────────────────────┘

Admin                            Backend                           Database
─────                            ───────                           ────────
    │                                │                                 │
    │  POST /api/organizations/:id/transfer-ownership                  │
    │  { newOwnerId }                │                                 │
    │───────────────────────────────>│                                 │
    │                                │                                 │
    │                                │  1. Verify requester is admin   │
    │                                │────────────────────────────────>│
    │                                │                                 │
    │                                │  2. Verify target is member     │
    │                                │────────────────────────────────>│
    │                                │                                 │
    │                                │  3. Promote target to admin     │
    │                                │     (if not already)            │
    │                                │────────────────────────────────>│
    │                                │                                 │
    │                                │  4. Update org.createdBy        │
    │                                │     to new owner                │
    │                                │────────────────────────────────>│
    │                                │                                 │
    │                                │  5. Requester can now leave     │
    │                                │     or demote themselves        │
    │                                │                                 │
    │  6. Return success             │                                 │
    │<───────────────────────────────│                                 │
```

**Add Member Steps:**
1. Verify requester has admin role
2. Check if user is already a member (active or removed)
3. If removed: reactivate membership
4. If new: create OrganizationMember with role
5. Return membership

**Remove Member Steps:**
1. Verify requester has admin role
2. Find target membership
3. If target is admin, ensure at least one admin remains
4. Set membership status to "removed"
5. Return success

**Leave Organization Steps:**
1. Find user's own membership
2. If user is last admin, require ownership transfer first
3. Set membership status to "removed"
4. Return success

**Change Role Steps:**
1. Verify requester has admin role
2. Find target membership
3. If demoting admin, ensure at least one admin remains
4. Update role
5. Return updated membership

**Transfer Ownership Steps:**
1. Verify requester has admin role
2. Verify target is an active member
3. Promote target to admin (if not already)
4. Update organization's createdBy to new owner
5. Requester can now leave or be demoted

**Error Cases:**
- Not an admin → 403 Forbidden
- User not found → 404 Not Found
- Already a member → 400 Bad Request
- Cannot remove last admin → 400 Bad Request
- Must transfer ownership first → 400 Bad Request

---

### Pipeline 3: Update Organization

Updates organization settings and details (admin only).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       UPDATE ORGANIZATION PIPELINE                           │
└─────────────────────────────────────────────────────────────────────────────┘

Admin                            Backend                           Database
─────                            ───────                           ────────
    │                                │                                 │
    │  PUT /api/organizations/:id    │                                 │
    │  { name, domain, settings }    │                                 │
    │───────────────────────────────>│                                 │
    │                                │                                 │
    │                                │  1. Verify requester is admin   │
    │                                │────────────────────────────────>│
    │                                │                                 │
    │                                │  2. If domain changed:          │
    │                                │     Check not already taken     │
    │                                │────────────────────────────────>│
    │                                │                                 │
    │                                │  3. Filter allowed updates:     │
    │                                │     - name                      │
    │                                │     - domain                    │
    │                                │     - settings.*                │
    │                                │                                 │
    │                                │  4. Update organization         │
    │                                │────────────────────────────────>│
    │                                │                                 │
    │  5. Return updated org         │                                 │
    │<───────────────────────────────│                                 │
```

**Allowed Updates:**
- `name` - Organization display name
- `domain` - Email domain for display
- `settings.defaultMeetingDuration` - Default meeting length (15-180 min)
- `settings.defaultGroupSize` - Circle group size (3-4)
- `settings.allowMemberPoolCreation` - Let members create pools
- `settings.timezone` - Organization timezone

**Error Cases:**
- Not an admin → 403 Forbidden
- Invalid settings values → 400 Bad Request
- Domain already taken → 400 Bad Request

---

## Components

### OrganizationService

Handles all organization and membership operations.

```python
class OrganizationService:
    """
    Manages organizations and their memberships.
    """

    def __init__(self, db: Database):
        """
        Args:
            db: MongoDB database connection
        """

    # ─────────────────────────────────────────────────────────────────
    # Organization CRUD
    # ─────────────────────────────────────────────────────────────────

    def create_organization(
        self,
        name: str,
        created_by: str,
        domain: str = None,
        settings: dict = None
    ) -> dict:
        """
        Create a new organization.
        Creator automatically becomes first admin.

        Args:
            name: Organization name (2-100 chars)
            created_by: User ID of creator
            domain: Optional email domain
            settings: Optional settings override

        Returns:
            Created organization dict

        Raises:
            ValidationError: Invalid name
            ConflictError: Domain already taken
        """

    def get_organization(self, organization_id: str) -> dict:
        """
        Get organization by ID.

        Args:
            organization_id: Organization ID

        Returns:
            Organization dict

        Raises:
            NotFoundError: Organization not found
        """

    def get_organization_with_stats(self, organization_id: str) -> dict:
        """
        Get organization with member counts.

        Args:
            organization_id: Organization ID

        Returns:
            Organization dict with memberCount, adminCount
        """

    def update_organization(
        self,
        organization_id: str,
        updates: dict,
        updated_by: str
    ) -> dict:
        """
        Update organization settings.

        Args:
            organization_id: Organization ID
            updates: Fields to update (name, domain, settings)
            updated_by: User making the update

        Returns:
            Updated organization dict

        Raises:
            ForbiddenError: User is not admin
            ConflictError: Domain already taken
        """

    def get_user_organizations(self, user_id: str) -> list[dict]:
        """
        Get all organizations a user belongs to.

        Args:
            user_id: User ID

        Returns:
            List of { organization, role, joinedAt }
        """

    # ─────────────────────────────────────────────────────────────────
    # Member Management
    # ─────────────────────────────────────────────────────────────────

    def add_member(
        self,
        organization_id: str,
        user_id: str,
        role: str = "member",
        invited_by: str = None
    ) -> dict:
        """
        Add a member to the organization.

        Args:
            organization_id: Organization ID
            user_id: User to add
            role: "admin" or "member"
            invited_by: Admin who added them

        Returns:
            Created membership dict

        Raises:
            ForbiddenError: Inviter is not admin
            ConflictError: User already a member
        """

    def remove_member(
        self,
        organization_id: str,
        user_id: str,
        removed_by: str
    ) -> bool:
        """
        Remove a member from the organization.

        Args:
            organization_id: Organization ID
            user_id: User to remove
            removed_by: Admin performing removal

        Returns:
            True if removed

        Raises:
            ForbiddenError: Remover is not admin
            ForbiddenError: Cannot remove last admin
            NotFoundError: User not a member
        """

    def leave_organization(
        self,
        organization_id: str,
        user_id: str
    ) -> bool:
        """
        Member leaves the organization voluntarily.

        Args:
            organization_id: Organization ID
            user_id: User leaving

        Returns:
            True if left successfully

        Raises:
            ForbiddenError: Last admin must transfer ownership first
            NotFoundError: User not a member
        """

    def change_member_role(
        self,
        organization_id: str,
        user_id: str,
        new_role: str,
        changed_by: str
    ) -> dict:
        """
        Change a member's role.

        Args:
            organization_id: Organization ID
            user_id: Member to update
            new_role: "admin" or "member"
            changed_by: Admin making the change

        Returns:
            Updated membership dict

        Raises:
            ForbiddenError: Changer is not admin
            ForbiddenError: Cannot demote last admin
            NotFoundError: User not a member
        """

    def transfer_ownership(
        self,
        organization_id: str,
        new_owner_id: str,
        transferred_by: str
    ) -> dict:
        """
        Transfer organization ownership to another member.

        Args:
            organization_id: Organization ID
            new_owner_id: User to become new owner
            transferred_by: Current admin transferring

        Returns:
            Updated organization dict

        Raises:
            ForbiddenError: Transferrer is not admin
            NotFoundError: New owner not a member

        Side Effects:
            - Promotes new owner to admin (if not already)
            - Updates organization.createdBy
        """

    def get_members(
        self,
        organization_id: str,
        role: str = None
    ) -> list[dict]:
        """
        Get organization members.

        Args:
            organization_id: Organization ID
            role: Optional filter by role

        Returns:
            List of member dicts with user details
        """

    # ─────────────────────────────────────────────────────────────────
    # Access Checks
    # ─────────────────────────────────────────────────────────────────

    def is_admin(self, organization_id: str, user_id: str) -> bool:
        """
        Check if user is an admin of the organization.

        Args:
            organization_id: Organization ID
            user_id: User ID

        Returns:
            True if user is active admin
        """

    def is_member(self, organization_id: str, user_id: str) -> bool:
        """
        Check if user is a member of the organization.

        Args:
            organization_id: Organization ID
            user_id: User ID

        Returns:
            True if user is active member (any role)
        """

    def get_membership(
        self,
        organization_id: str,
        user_id: str
    ) -> dict | None:
        """
        Get user's membership in an organization.

        Args:
            organization_id: Organization ID
            user_id: User ID

        Returns:
            Membership dict or None if not a member
        """

    def get_admin_count(self, organization_id: str) -> int:
        """
        Get count of active admins.

        Args:
            organization_id: Organization ID

        Returns:
            Number of active admins
        """
```

---

## Data Models

### Organization (Collection)

```python
# organizations collection
{
    "_id": ObjectId,
    "name": str,                      # 2-100 characters
    "domain": str | None,             # Optional email domain (lowercase)
    "settings": {
        "defaultMeetingDuration": int,  # 15-180 minutes, default: 60
        "defaultGroupSize": int,        # 3-4, default: 4
        "allowMemberPoolCreation": bool, # default: false
        "timezone": str                 # default: "Europe/Stockholm"
    },
    "status": str,                    # "active", "suspended", "deleted"
    "createdBy": ObjectId,            # First admin / current owner
    "createdAt": datetime,
    "updatedAt": datetime
}
```

**Indexes:**
- `{ name: 1 }` - For searching
- `{ domain: 1 }` - Sparse, for domain lookup
- `{ status: 1 }` - For filtering active orgs
- `{ createdAt: 1 }` - For sorting

---

### OrganizationMember (Collection)

```python
# organization_members collection
{
    "_id": ObjectId,
    "organizationId": ObjectId,       # Organization reference
    "userId": ObjectId,               # User reference
    "role": str,                      # "admin" | "member"
    "status": str,                    # "active" | "inactive" | "removed"
    "joinedAt": datetime,
    "invitedBy": ObjectId | None,     # Admin who added them
    "createdAt": datetime,
    "updatedAt": datetime
}
```

**Indexes:**
- `{ organizationId: 1, userId: 1 }` - Unique, one membership per user per org
- `{ organizationId: 1, role: 1 }` - Find admins
- `{ userId: 1 }` - Find user's organizations
- `{ organizationId: 1, status: 1 }` - Find active members

---

## Settings Reference

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `defaultMeetingDuration` | int | 60 | Default meeting length in minutes (15-180) |
| `defaultGroupSize` | int | 4 | Default circle group size (3-4) |
| `allowMemberPoolCreation` | bool | false | Allow non-admins to create circle pools |
| `timezone` | string | "Europe/Stockholm" | Organization default timezone |

---

## Access Control Summary

| Action | Admin | Member |
|--------|-------|--------|
| View organization | ✓ | ✓ |
| View members | ✓ | ✓ |
| Update organization | ✓ | ✗ |
| Add member | ✓ | ✗ |
| Remove member | ✓ | ✗ |
| Change roles | ✓ | ✗ |
| Transfer ownership | ✓ | ✗ |
| Leave organization | ✓ | ✓ |

---

## Business Rules

1. **Creator becomes first admin** - When creating an organization, the creator is automatically added as an admin.

2. **At least one admin** - An organization must always have at least one admin. Operations that would remove the last admin are blocked.

3. **Soft delete for members** - When a member is removed, their status is set to "removed" (not deleted). This preserves audit history and allows reactivation.

4. **Domain uniqueness** - If a domain is specified, it must be unique across all active organizations.

5. **Ownership transfer** - The last admin cannot leave without first transferring ownership to another member.

6. **Reactivation** - If a removed member is added again, their membership is reactivated rather than creating a duplicate.

# Organization Model

Organization model for BrainBank. Represents a company/organization.

---

## Classes

### OrganizationSettings

Embedded organization settings.

**Properties:**

- `default_meeting_duration` (int): Default meeting duration in minutes (15-180). Default: 60
- `default_group_size` (int): Default group size for circles (3-4). Default: 4
- `allow_member_pool_creation` (bool): Allow members to create their own pools. Default: False
- `timezone` (str): Organization-wide timezone. Default: "Europe/Stockholm"

---

### Organization

Organization document for BrainBank. Extends BaseDocument.

**Properties:**

- `name` (str): Organization name (indexed)
- `domain` (Optional[str]): Optional domain for email matching (e.g., "acme.com")
- `settings` (OrganizationSettings): Organization settings
- `status` (str): One of: "active", "suspended", "deleted". Default: "active"
- `created_by` (PydanticObjectId): User ID of first admin

**Methods:**

#### is_active

- **Outputs:** (bool) True if organization is active
- **Description:** Check if organization is active.

#### to_public_dict

- **Outputs:** (dict) Public representation with id, name, domain, settings (camelCase), status, createdAt
- **Description:** Get public representation.

#### find_by_domain (classmethod)

- **Inputs:**
  - `domain` (str): Domain to search (case-insensitive)
- **Outputs:** (Optional[Organization]) Active organization or None
- **Description:** Find active organization by domain.

#### find_active (classmethod)

- **Outputs:** (List[Organization]) All active organizations
- **Description:** Find all active organizations.

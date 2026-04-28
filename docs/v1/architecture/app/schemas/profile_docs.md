# Profile Schemas

Profile request/response schemas.

---

## Classes

### ProfileUpdateRequest

Profile update request.

**Properties:**

- `firstName` (Optional[str]): First name (max 50 chars)
- `lastName` (Optional[str]): Last name (max 50 chars)
- `jobTitle` (Optional[str]): Job title (max 100 chars)
- `leadershipLevel` (Optional[str]): One of: "new", "mid", "senior", "executive"
- `preferredLanguage` (Optional[str]): "en" or "sv"
- `timezone` (Optional[str]): Timezone string

---

### ProfileResponse

User profile response.

**Properties:**

- `firstName` (Optional[str])
- `lastName` (Optional[str])
- `jobTitle` (Optional[str])
- `leadershipLevel` (Optional[str])
- `preferredLanguage` (str): Default: "en"
- `timezone` (Optional[str])
- `avatarUrl` (Optional[str]): Avatar image URL

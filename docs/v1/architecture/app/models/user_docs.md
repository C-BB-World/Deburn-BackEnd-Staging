# User Model

User model for BrainBank.

---

## Classes

### UserConsent

Embedded consent tracking (GDPR compliance).

**Properties:**

- `accepted` (bool): Whether consent is accepted. Default: False
- `accepted_at` (Optional[datetime]): When consent was accepted
- `version` (Optional[str]): Consent version
- `withdrawn_at` (Optional[datetime]): When consent was withdrawn

---

### UserSession

Embedded session tracking.

**Properties:**

- `token_hash` (str): Hashed session token
- `expires_at` (datetime): Session expiration time
- `last_activity_at` (Optional[datetime]): Last activity timestamp
- `ip_address` (Optional[str]): Client IP address
- `user_agent` (Optional[str]): Client user agent
- `device_info` (Optional[str]): Device information

---

### UserProfile

Embedded user profile (optional, populated during onboarding).

**Properties:**

- `first_name` (Optional[str]): First name (max 50 chars)
- `last_name` (Optional[str]): Last name (max 50 chars)
- `job_title` (Optional[str]): Job title (max 100 chars)
- `leadership_level` (Optional[str]): One of: "new", "mid", "senior", "executive"
- `timezone` (str): User timezone. Default: "Europe/Stockholm"
- `preferred_language` (str): "en" or "sv". Default: "en"
- `avatar_url` (Optional[str]): Avatar image URL

---

### User

User document for BrainBank. Extends BaseDocument.

**Properties:**

Core Identity:
- `email` (EmailStr): User's email (unique, indexed)
- `password_hash` (str): Hashed password

Profile (required at registration):
- `organization` (str): Organization name (2-100 chars)
- `country` (str): ISO 3166-1 alpha-2 country code (2 chars)
- `profile` (UserProfile): Embedded profile data

Account Status:
- `status` (str): One of: "pending_verification", "active", "suspended", "deleted"

Email Verification:
- `email_verification_token` (Optional[str]): Verification token
- `email_verification_expires_at` (Optional[datetime]): Token expiration
- `email_verified_at` (Optional[datetime]): When email was verified

Password Reset:
- `password_reset_token` (Optional[str]): Reset token
- `password_reset_expires_at` (Optional[datetime]): Token expiration

GDPR:
- `consents` (dict): Consent tracking for terms_of_service, privacy_policy, data_processing, marketing
- `deletion_requested_at` (Optional[datetime]): When deletion was requested
- `deletion_scheduled_for` (Optional[datetime]): When deletion will occur
- `deletion_completed_at` (Optional[datetime]): When deletion completed
- `deletion_reason` (Optional[str]): Reason for deletion

Coach:
- `coach_exchange_count` (int): Daily exchange count. Default: 0
- `coach_exchange_last_reset` (Optional[datetime]): Last count reset time

Sessions:
- `active_sessions` (List[str]): List of active session token hashes
- `last_login_at` (Optional[datetime]): Last login timestamp

**Methods:**

#### full_name (property)

- **Outputs:** (Optional[str]) User's full name or first name
- **Description:** Get user's full name.

#### display_name (property)

- **Outputs:** (str) Display name (falls back to email prefix)
- **Description:** Get display name.

#### is_verified

- **Outputs:** (bool) True if email is verified
- **Description:** Check if email is verified.

#### is_active

- **Outputs:** (bool) True if account is active
- **Description:** Check if account is active.

#### is_pending_deletion

- **Outputs:** (bool) True if pending deletion
- **Description:** Check if account is pending deletion.

#### to_public_dict

- **Outputs:** (dict) Public profile data safe to return to client
- **Description:** Get public profile with id, email, organization, country, profile, displayName, status, createdAt.

#### find_by_email (classmethod)

- **Inputs:**
  - `email` (str): Email to search (case-insensitive)
- **Outputs:** (Optional[User]) User or None
- **Description:** Find user by email.

#### find_pending_deletion (classmethod)

- **Outputs:** (List[User]) Users pending deletion
- **Description:** Find users whose deletion is scheduled for now or earlier.

#### can_use_coach

- **Inputs:**
  - `daily_limit` (int): Maximum daily exchanges. Default: 15
- **Outputs:** (bool) True if user can use coach
- **Description:** Check if user is within daily coach usage limit.

#### increment_coach_exchange

- **Outputs:** (None)
- **Description:** Increment coach exchange count (resets daily). Saves the user document.

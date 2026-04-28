# User System

## Description

The User System manages user data and lifecycle. It handles profile information, GDPR consent tracking, and account deletion. This system is separate from authentication—it focuses on *what we know about users*, not *who they are*.

**Responsibilities:**
- Create and store user records (linked to Firebase UID)
- Manage user profile data (name, timezone, preferences)
- Track organization and country
- Track GDPR consents with version history
- Manage coaching quotas
- Handle account deletion with 30-day grace period

**Tech Stack:**
- **MongoDB** - User storage (`users` collection)
- **Auth System** - Provides `firebaseUid` linkage, session revocation on deletion

---

## Pipelines

### Pipeline 1: User Creation

Creates a new user record in MongoDB, called during registration after Firebase account creation.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          USER CREATION PIPELINE                              │
└─────────────────────────────────────────────────────────────────────────────┘

Auth System                      User System                       MongoDB
───────────                      ───────────                       ───────
    │                                │                                 │
    │  1. create_user(               │                                 │
    │       firebaseUid,             │                                 │
    │       email,                   │                                 │
    │       organization,            │                                 │
    │       country,                 │                                 │
    │       profile,                 │                                 │
    │       consents                 │                                 │
    │     )                          │                                 │
    │───────────────────────────────>│                                 │
    │                                │                                 │
    │                                │  2. Validate profile data       │
    │                                │     (required fields, formats)  │
    │                                │                                 │
    │                                │  3. Validate consents           │
    │                                │     (required consents present) │
    │                                │                                 │
    │                                │  4. Build user document         │
    │                                │     (init coachExchanges)       │
    │                                │                                 │
    │                                │  5. Insert user                 │
    │                                │─────────────────────────────────>
    │                                │                                 │
    │  6. Return user                │                                 │
    │<───────────────────────────────│                                 │
    │                                │                                 │
```

**Steps:**
1. Auth System calls `UserService.create_user()` after Firebase registration
2. Validate profile data (first name required, valid timezone, etc.)
3. Validate consents (terms of service and privacy policy required)
4. Build user document with timestamps, consent versions, and initial coachExchanges
5. Insert into MongoDB `users` collection
6. Return created user object

**Required Consents at Registration:**
- `termsOfService` - Must be accepted
- `privacyPolicy` - Must be accepted
- `dataProcessing` - Must be accepted
- `marketing` - Optional

**Error Cases:**
- `firebaseUid` already exists → 409 Conflict
- Missing required profile fields → 400 Bad Request
- Missing required consents → 400 Bad Request
- Invalid timezone → 400 Bad Request
- Invalid country code → 400 Bad Request

---

### Pipeline 2: Profile Management

Allows users to view and update their profile information.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       PROFILE MANAGEMENT PIPELINE                            │
└─────────────────────────────────────────────────────────────────────────────┘

                              GET PROFILE
Frontend                         Backend
────────                         ───────
    │                                │
    │  1. GET /user/profile          │
    │───────────────────────────────>│
    │                                │
    │                                │  2. Get userId from
    │                                │     authenticated request
    │                                │
    │                                │  3. Load user from MongoDB
    │                                │
    │                                │  4. Filter to profile fields
    │                                │     (exclude internal data)
    │                                │
    │  5. Return profile             │
    │<───────────────────────────────│
    │                                │


                            UPDATE PROFILE
Frontend                         Backend
────────                         ───────
    │                                │
    │  1. PATCH /user/profile        │
    │     {firstName, lastName,      │
    │      jobTitle, timezone, ...}  │
    │───────────────────────────────>│
    │                                │
    │                                │  2. Validate input
    │                                │     (formats, lengths)
    │                                │
    │                                │  3. Sanitize strings
    │                                │     (prevent XSS)
    │                                │
    │                                │  4. Update user document
    │                                │     (only provided fields)
    │                                │
    │                                │  5. Log audit event
    │                                │     (profile_updated)
    │                                │
    │  6. Return updated profile     │
    │<───────────────────────────────│
    │                                │
```

**Get Profile Steps:**
1. Frontend requests `/user/profile`
2. Extract user ID from authenticated request (set by Auth middleware)
3. Load user document from MongoDB
4. Return only profile fields (not internal auth/deletion state)

**Update Profile Steps:**
1. Frontend sends PATCH with fields to update
2. Validate each field (timezone must be valid, strings within length limits)
3. Sanitize string inputs (escape HTML entities)
4. Update only the provided fields (partial update)
5. Log audit event for compliance
6. Return updated profile

**Editable Profile Fields:**
- `firstName` (string, max 50)
- `lastName` (string, max 50)
- `jobTitle` (string, max 100)
- `leadershipLevel` (enum: individual_contributor, team_lead, manager, director, executive)
- `timezone` (string, valid IANA timezone)
- `preferredLanguage` (enum: en, sv)

**Non-Editable User Fields (set at registration):**
- `organization` (string)
- `country` (string, ISO 3166-1 alpha-2)

**Error Cases:**
- Invalid timezone → 400 Bad Request
- Invalid leadership level → 400 Bad Request
- String too long → 400 Bad Request
- Invalid language code → 400 Bad Request

---

### Pipeline 3: Consent Management

Tracks GDPR consents with version history and allows users to update optional consents.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       CONSENT MANAGEMENT PIPELINE                            │
└─────────────────────────────────────────────────────────────────────────────┘

                              GET CONSENTS
Frontend                         Backend
────────                         ───────
    │                                │
    │  1. GET /user/consents         │
    │───────────────────────────────>│
    │                                │
    │                                │  2. Load user consents
    │                                │
    │                                │  3. Check for outdated
    │                                │     consent versions
    │                                │
    │  4. Return consents with       │
    │     current versions           │
    │<───────────────────────────────│
    │     {consents, needsUpdate}    │


                           UPDATE CONSENT
Frontend                         Backend
────────                         ───────
    │                                │
    │  1. PUT /user/consents/{type}  │
    │     {accepted: bool,           │
    │      version: "1.0"}           │
    │───────────────────────────────>│
    │                                │
    │                                │  2. Validate consent type
    │                                │
    │                                │  3. Validate version matches
    │                                │     current version
    │                                │
    │                                │  4. Update consent record
    │                                │     with timestamp
    │                                │
    │                                │  5. Log audit event
    │                                │     (consent_updated)
    │                                │
    │  6. Return updated consent     │
    │<───────────────────────────────│


                       RE-CONSENT FLOW (Terms Updated)
Frontend                         Backend
────────                         ───────
    │                                │
    │  1. Any protected request      │
    │───────────────────────────────>│
    │                                │
    │                                │  2. Check consent versions
    │                                │
    │                                │  3. If outdated:
    │                                │     Return 451 Unavailable
    │                                │     For Legal Reasons
    │                                │
    │  4. Show consent modal         │
    │<───────────────────────────────│
    │                                │
    │  5. User accepts new terms     │
    │───────────────────────────────>│
    │                                │
    │                                │  6. Update consent
    │                                │     (new version)
    │                                │
    │  7. Continue normal flow       │
    │<───────────────────────────────│
```

**Get Consents Steps:**
1. Frontend requests `/user/consents`
2. Load user's consent records
3. Compare against current consent versions (from config)
4. Return consents with flag indicating if re-consent needed

**Update Consent Steps:**
1. Frontend sends consent update (type, accepted, version)
2. Validate consent type exists
3. Validate version matches current version (can't accept old terms)
4. Store consent with timestamp and version
5. Log audit event
6. Return updated consent

**Re-consent Flow Steps:**
1. User makes request with outdated consent version
2. Backend checks consent versions
3. If outdated required consent, return 451 status
4. Frontend shows consent modal
5. User accepts new terms
6. Backend updates consent with new version
7. User can continue

**Consent Types:**

| Type | Required | Can Withdraw | Description |
|------|----------|--------------|-------------|
| `termsOfService` | Yes | No* | Must accept to use service |
| `privacyPolicy` | Yes | No* | Must accept to use service |
| `dataProcessing` | Yes | No* | GDPR lawful basis |
| `marketing` | No | Yes | Can opt in/out anytime |

*Withdrawing required consents triggers account deletion flow

**Error Cases:**
- Invalid consent type → 400 Bad Request
- Version mismatch → 400 Bad Request (must accept current version)
- Withdrawing required consent → Triggers deletion flow

---

### Pipeline 4: Account Deletion

GDPR-compliant account deletion with 30-day grace period.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       ACCOUNT DELETION PIPELINE                              │
└─────────────────────────────────────────────────────────────────────────────┘

                           REQUEST DELETION
Frontend                         Backend                           External
────────                         ───────                           ────────
    │                                │                                 │
    │  1. POST /user/delete          │                                 │
    │     {reason: "..."}            │                                 │
    │───────────────────────────────>│                                 │
    │                                │                                 │
    │                                │  2. Validate user is active     │
    │                                │                                 │
    │                                │  3. Set deletion state:         │
    │                                │     - requestedAt: now          │
    │                                │     - scheduledFor: now + 30d   │
    │                                │     - reason: user input        │
    │                                │                                 │
    │                                │  4. Update user status:         │
    │                                │     "pendingDeletion"           │
    │                                │                                 │
    │                                │  5. Log audit event             │
    │                                │     (deletion_requested)        │
    │                                │                                 │
    │                                │  6. Send confirmation email     │
    │                                │─────────────────────────────────>
    │                                │                         Email   │
    │  7. Return confirmation        │                                 │
    │<───────────────────────────────│                                 │
    │     {scheduledFor: date}       │                                 │


                         CANCELLATION (via login)
Frontend                         Backend
────────                         ───────
    │                                │
    │  1. User logs in               │
    │     (during grace period)      │
    │───────────────────────────────>│
    │                                │
    │                                │  2. Detect pendingDeletion
    │                                │     status
    │                                │
    │                                │  3. Clear deletion state
    │                                │
    │                                │  4. Set status: "active"
    │                                │
    │                                │  5. Log audit event
    │                                │     (deletion_cancelled)
    │                                │
    │  6. Return success with        │
    │     cancellation notice        │
    │<───────────────────────────────│


                      EXECUTION (after 30 days)
Scheduler                        Backend                           External
─────────                        ───────                           ────────
    │                                │                                 │
    │  1. Cron job triggers          │                                 │
    │───────────────────────────────>│                                 │
    │                                │                                 │
    │                                │  2. Find users where            │
    │                                │     scheduledFor <= now         │
    │                                │                                 │
    │                                │  3. For each user:              │
    │                                │                                 │
    │                                │  4. Revoke all sessions         │
    │                                │     (clear user.sessions[])     │
    │                                │                                 │
    │                                │  5. Revoke Firebase tokens      │
    │                                │─────────────────────────────────>
    │                                │                    Firebase     │
    │                                │                                 │
    │                                │  6. Delete related data:        │
    │                                │     - Check-ins                 │
    │                                │     - Coach commitments         │
    │                                │     - Insights                  │
    │                                │     - Circle memberships        │
    │                                │                                 │
    │                                │  7. Anonymize audit logs        │
    │                                │                                 │
    │                                │  8. Delete user document        │
    │                                │                                 │
    │                                │  9. Log final audit event       │
    │                                │     (account_deleted)           │
    │                                │                                 │
    │                                │  10. Delete Firebase account    │
    │                                │─────────────────────────────────>
    │                                │                    Firebase     │
```

**Request Deletion Steps:**
1. User requests account deletion with optional reason
2. Verify user is active (not already pending deletion)
3. Set deletion state with 30-day grace period
4. Update user status to `pendingDeletion`
5. Log audit event
6. Send confirmation email with cancellation instructions
7. Return scheduled deletion date

**Cancellation Steps:**
1. User logs in during grace period
2. Login flow detects `pendingDeletion` status
3. Clear deletion state
4. Reset status to `active`
5. Log cancellation audit event
6. Inform user their deletion was cancelled

**Execution Steps (Background Job):**
1. Scheduled job runs daily
2. Find all users with `deletion.scheduledFor <= now`
3. For each user:
   - Clear `user.sessions[]` array
   - Call `FirebaseAuthClient.revoke_refresh_tokens(firebaseUid)`
   - Delete user's data from related collections
   - Anonymize audit logs (remove PII, keep event record)
   - Delete user document
   - Log final audit event
   - Delete Firebase account

**Data Deleted:**
- User document
- Check-ins
- Coach commitments
- Insights
- Circle group memberships
- Calendar connections
- User availability

**Data Anonymized (not deleted):**
- Audit logs (PII removed, events preserved for compliance)

**Data Retained:**
- Circle invitations (email anonymized)
- Meeting records (user reference removed)

**Error Cases:**
- Already pending deletion → 400 Bad Request
- User not found → 404 Not Found

---

## Components

### UserService

Main service for user operations.

```python
class UserService:
    """
    Manages user lifecycle and data.
    """

    def __init__(
        self,
        db: Database,
        email_service: EmailService,
        audit_logger: AuditLogger
    ):
        """
        Args:
            db: MongoDB database connection
            email_service: For deletion confirmation emails
            audit_logger: For compliance logging
        """

    def create_user(
        self,
        firebase_uid: str,
        email: str,
        organization: str,
        country: str,
        profile: dict,
        consents: list[dict]
    ) -> dict:
        """
        Create a new user record.

        Args:
            firebase_uid: Firebase user ID (from registration)
            email: User's email address
            organization: User's organization name
            country: User's country code (ISO 3166-1 alpha-2)
            profile: Initial profile data (firstName, lastName, timezone, etc.)
            consents: List of consents accepted at registration

        Returns:
            Created user document

        Raises:
            ConflictError: firebaseUid already exists
            ValidationError: Invalid profile or missing required consents
        """

    def get_user_by_id(self, user_id: str) -> dict | None:
        """
        Load user by MongoDB ID.

        Args:
            user_id: MongoDB ObjectId as string

        Returns:
            User document or None if not found
        """

    def get_user_by_firebase_uid(self, firebase_uid: str) -> dict | None:
        """
        Load user by Firebase UID.

        Args:
            firebase_uid: Firebase user ID

        Returns:
            User document or None if not found
        """

    def request_deletion(
        self,
        user_id: str,
        reason: str = None
    ) -> datetime:
        """
        Initiate account deletion with grace period.

        Args:
            user_id: MongoDB user ID
            reason: Optional reason for deletion

        Returns:
            scheduledFor datetime (30 days from now)

        Side Effects:
            - Sets deletion state on user
            - Updates status to pendingDeletion
            - Logs audit event
            - Sends confirmation email
        """

    def cancel_deletion(self, user_id: str) -> None:
        """
        Cancel pending account deletion.

        Args:
            user_id: MongoDB user ID

        Side Effects:
            - Clears deletion state
            - Sets status back to active
            - Logs audit event
        """

    def execute_deletion(self, user_id: str, firebase_client: FirebaseAuthClient) -> None:
        """
        Permanently delete a user account.
        Called by background job after grace period.

        Args:
            user_id: MongoDB user ID
            firebase_client: For Firebase account deletion

        Side Effects:
            - Clears sessions array
            - Deletes related data
            - Anonymizes audit logs
            - Deletes user document
            - Deletes Firebase account
        """

    def get_pending_deletions(self) -> list[dict]:
        """
        Find users ready for deletion.
        Used by background job.

        Returns:
            List of users where deletion.scheduledFor <= now
        """
```

---

### ProfileService

Handles profile-specific operations.

```python
class ProfileService:
    """
    Manages user profile data.
    """

    def __init__(self, db: Database, audit_logger: AuditLogger):
        """
        Args:
            db: MongoDB database connection
            audit_logger: For compliance logging
        """

    def get_profile(self, user_id: str) -> dict:
        """
        Get user's profile data.

        Args:
            user_id: MongoDB user ID

        Returns:
            dict with profile fields (firstName, lastName, timezone, etc.)
        """

    def update_profile(
        self,
        user_id: str,
        updates: dict
    ) -> dict:
        """
        Update user's profile fields.

        Args:
            user_id: MongoDB user ID
            updates: Dict of fields to update (partial update)
                     Keys should be camelCase (firstName, lastName, etc.)

        Returns:
            Updated profile dict

        Raises:
            ValidationError: Invalid field value

        Side Effects:
            - Validates each field
            - Sanitizes string inputs
            - Updates user.profile in document
            - Logs audit event
        """

    def validate_profile_field(self, field: str, value: any) -> bool:
        """
        Validate a single profile field.

        Args:
            field: Field name (camelCase)
            value: Field value

        Returns:
            True if valid

        Raises:
            ValidationError: If invalid, with reason
        """
```

---

### ConsentService

Manages GDPR consent tracking.

```python
class ConsentService:
    """
    Tracks and manages user consents for GDPR compliance.
    """

    CONSENT_VERSIONS = {
        "termsOfService": "1.0",
        "privacyPolicy": "1.0",
        "dataProcessing": "1.0",
        "marketing": "1.0"
    }

    REQUIRED_CONSENTS = [
        "termsOfService",
        "privacyPolicy",
        "dataProcessing"
    ]

    def __init__(self, db: Database, audit_logger: AuditLogger):
        """
        Args:
            db: MongoDB database connection
            audit_logger: For compliance logging
        """

    def get_consents(self, user_id: str) -> dict:
        """
        Get user's current consents with version check.

        Args:
            user_id: MongoDB user ID

        Returns:
            dict with:
                - consents: user's consent records
                - needsUpdate: bool (if any required consent outdated)
                - outdatedConsents: list of consent types needing update
        """

    def update_consent(
        self,
        user_id: str,
        consent_type: str,
        accepted: bool,
        version: str
    ) -> dict:
        """
        Update a user's consent.

        Args:
            user_id: MongoDB user ID
            consent_type: Type of consent (camelCase)
            accepted: Whether user accepts
            version: Version being accepted (must match current)

        Returns:
            Updated consent record

        Raises:
            ValidationError: Invalid consent type or version mismatch
            DeletionTriggerError: If withdrawing required consent

        Side Effects:
            - Updates consent with timestamp
            - Logs audit event
            - May trigger deletion flow if withdrawing required consent
        """

    def validate_registration_consents(
        self,
        consents: list[dict]
    ) -> bool:
        """
        Validate consents provided at registration.

        Args:
            consents: List of consents from registration

        Returns:
            True if all required consents present and accepted

        Raises:
            ValidationError: Missing or unaccepted required consent
        """

    def check_consent_versions(self, user_id: str) -> list[str]:
        """
        Check which consents are outdated.

        Args:
            user_id: MongoDB user ID

        Returns:
            List of consent types that need re-consent
        """
```

---

### ConsentMiddleware

Middleware to enforce consent requirements.

```python
class ConsentMiddleware:
    """
    Middleware that checks consent versions on requests.
    """

    def __init__(self, consent_service: ConsentService):
        """
        Args:
            consent_service: For consent version checking
        """

    def require_current_consents(self, request: Request) -> None:
        """
        Check user has accepted current consent versions.

        Args:
            request: HTTP request (must have user attached)

        Raises:
            LegalBlockError: If required consent is outdated
                - Returns 451 Unavailable For Legal Reasons
                - Response includes which consents need update
        """
```

---

### DeletionJob

Background job for executing deletions.

```python
class DeletionJob:
    """
    Background job that executes scheduled account deletions.
    Runs daily via cron/scheduler.
    """

    def __init__(
        self,
        user_service: UserService,
        firebase_client: FirebaseAuthClient
    ):
        """
        Args:
            user_service: For finding and deleting users
            firebase_client: For Firebase account deletion
        """

    def run(self) -> dict:
        """
        Execute all pending deletions.

        Returns:
            dict with:
                - processed: int (number of users processed)
                - succeeded: int (number successfully deleted)
                - failed: list of (user_id, error) tuples
        """

    def delete_user_data(self, user_id: str) -> None:
        """
        Delete all data associated with a user.

        Args:
            user_id: MongoDB user ID

        Deletes from:
            - checkIns
            - coachCommitments
            - insights
            - circleGroupMembers
            - calendarConnections
            - userAvailability
        """

    def anonymize_audit_logs(self, user_id: str) -> int:
        """
        Remove PII from user's audit logs.

        Args:
            user_id: MongoDB user ID

        Returns:
            Number of logs anonymized

        Anonymizes:
            - Sets email to "[deleted]"
            - Removes IP addresses
            - Keeps action and timestamp for compliance
        """
```

---

## Data Models

### User Document (MongoDB)

```python
{
    "_id": ObjectId,
    "firebaseUid": str,               # Unique, indexed - Link to Firebase
    "email": str,                     # From Firebase, indexed
    "organization": str,              # User's organization name
    "country": str,                   # ISO 3166-1 alpha-2 (e.g., "GB", "US")
    "status": str,                    # "active" | "pendingDeletion" | "suspended"

    "profile": {
        "firstName": str,
        "lastName": str | None,
        "jobTitle": str | None,
        "leadershipLevel": str | None,    # Enum
        "timezone": str,                   # IANA timezone (e.g., "Europe/Stockholm")
        "preferredLanguage": str           # "en" | "sv"
    },

    "consents": {
        "termsOfService": {
            "accepted": bool,
            "acceptedAt": datetime,
            "version": str
        },
        "privacyPolicy": {
            "accepted": bool,
            "acceptedAt": datetime,
            "version": str
        },
        "dataProcessing": {
            "accepted": bool,
            "acceptedAt": datetime,
            "version": str
        },
        "marketing": {
            "accepted": bool,
            "acceptedAt": datetime | None,
            "version": str | None
        }
    },

    "coachExchanges": {
        "count": int,                 # Daily usage count
        "lastResetDate": datetime     # Date of last reset
    },

    "sessions": list[dict],           # Embedded sessions (managed by Auth System)

    "deletion": {                     # Only present if pending deletion
        "requestedAt": datetime,
        "scheduledFor": datetime,
        "reason": str | None
    },

    "lastLoginAt": datetime,
    "createdAt": datetime,
    "updatedAt": datetime
}
```

**Indexes:**
- `firebaseUid` (unique) - For Firebase → MongoDB lookup
- `email` (unique) - For email lookup
- `status` - For finding active/pending users
- `deletion.scheduledFor` - For deletion job queries
- `sessions.tokenHash` - For session validation (Auth System)

---

### Audit Log Document (MongoDB)

```python
{
    "_id": ObjectId,
    "userId": ObjectId | None,        # None for anonymized logs
    "action": str,                    # Enum of action types
    "metadata": {
        "ipAddress": str | None,      # Anonymized: None
        "userAgent": str | None,
        "email": str | None,          # Anonymized: "[deleted]"
        "consentType": str | None,
        "consentAccepted": bool | None,
        "consentVersion": str | None,
        "reason": str | None
    },
    "timestamp": datetime,
    "expiresAt": datetime             # TTL: 90 days
}
```

**Action Types:**
- `user_created`
- `profile_updated`
- `consent_updated`
- `deletion_requested`
- `deletion_cancelled`
- `account_deleted`

**Indexes:**
- `userId, timestamp` - For user activity lookup
- `action, timestamp` - For action-based queries
- `expiresAt` (TTL) - Auto-delete after 90 days

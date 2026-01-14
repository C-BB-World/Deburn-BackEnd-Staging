# Auth System

## Description

The Auth System handles identity verification and access control. It manages user authentication through Firebase and maintains session state embedded in the User document.

**Responsibilities:**
- User registration (Firebase + MongoDB linking)
- User login and authentication
- Session creation, validation, and revocation
- Multi-device session management

**Tech Stack:**
- **Firebase Auth** - Handles credentials, password reset, email verification
- **MongoDB** - Sessions embedded in `users` collection (`sessions` array)
- **Authorization Header** - Bearer token for API authentication
- **GeoIP** - Location detection from IP address

---

## Pipelines

### Pipeline 1: Registration

Creates a new user account via Firebase and links it to our MongoDB user record.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           REGISTRATION PIPELINE                              │
└─────────────────────────────────────────────────────────────────────────────┘

Frontend                         Backend                           External
────────                         ───────                           ────────
    │                                │                                 │
    │  1. User submits signup form   │                                 │
    │─────────────────────────────────────────────────────────────────>│
    │                                │                    Firebase Auth│
    │                                │                                 │
    │  2. Firebase creates account   │                                 │
    │<─────────────────────────────────────────────────────────────────│
    │     (returns Firebase ID token)│                                 │
    │                                │                                 │
    │  3. POST /auth/register        │                                 │
    │     {firebaseToken, profile,   │                                 │
    │      consents, organization,   │                                 │
    │      country}                  │                                 │
    │───────────────────────────────>│                                 │
    │                                │                                 │
    │                                │  4. Verify Firebase token       │
    │                                │─────────────────────────────────>
    │                                │                                 │
    │                                │  5. Extract firebaseUid         │
    │                                │                                 │
    │                                │  6. Call UserSystem.create_user()
    │                                │     (creates user in MongoDB)   │
    │                                │                                 │
    │                                │  7. Create session              │
    │                                │     (push to user.sessions[])   │
    │                                │                                 │
    │  8. Return user + sessionToken │                                 │
    │<───────────────────────────────│                                 │
    │                                │                                 │
```

**Steps:**
1. User fills registration form on frontend (email, password, profile info, consents, organization, country)
2. Frontend calls Firebase Auth `createUserWithEmailAndPassword()`
3. Firebase returns ID token
4. Frontend sends token + profile + consents + organization + country to backend `/auth/register`
5. Backend verifies Firebase token using Firebase Admin SDK
6. Backend calls User System to create user record in MongoDB
7. Backend creates session by pushing to `user.sessions[]` array
8. Backend returns user data and session token (frontend stores for future requests)

**Error Cases:**
- Firebase token invalid → 401 Unauthorized
- Firebase UID already linked to existing user → 409 Conflict
- Invalid profile data → 400 Bad Request
- Missing required consents → 400 Bad Request

---

### Pipeline 2: Login

Authenticates a returning user and creates a new session.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              LOGIN PIPELINE                                  │
└─────────────────────────────────────────────────────────────────────────────┘

Frontend                         Backend                           External
────────                         ───────                           ────────
    │                                │                                 │
    │  1. User submits login form    │                                 │
    │─────────────────────────────────────────────────────────────────>│
    │                                │                    Firebase Auth│
    │                                │                                 │
    │  2. Firebase authenticates     │                                 │
    │<─────────────────────────────────────────────────────────────────│
    │     (returns Firebase ID token)│                                 │
    │                                │                                 │
    │  3. POST /auth/login           │                                 │
    │     {firebaseToken,            │                                 │
    │      rememberMe: bool}         │                                 │
    │───────────────────────────────>│                                 │
    │                                │                                 │
    │                                │  4. Verify Firebase token       │
    │                                │─────────────────────────────────>
    │                                │                                 │
    │                                │  5. Find user by firebaseUid    │
    │                                │     (MongoDB lookup)            │
    │                                │                                 │
    │                                │  6. Check user status           │
    │                                │     (active? pending deletion?) │
    │                                │                                 │
    │                                │  7. If pending deletion:        │
    │                                │     → Cancel deletion           │
    │                                │                                 │
    │                                │  8. Create session              │
    │                                │     (push to user.sessions[])   │
    │                                │                                 │
    │                                │  9. Detect device & location    │
    │                                │     (User-Agent, IP → GeoIP)    │
    │                                │                                 │
    │                                │  10. Update lastLoginAt         │
    │                                │                                 │
    │  11. Return user + sessionToken│                                 │
    │<───────────────────────────────│                                 │
    │      (7d or 30d if rememberMe) │                                 │
    │                                │                                 │
```

**Steps:**
1. User enters credentials on frontend
2. Frontend calls Firebase Auth `signInWithEmailAndPassword()`
3. Firebase returns ID token
4. Frontend sends token to backend `/auth/login` with optional `rememberMe` flag
5. Backend verifies Firebase token
6. Backend finds user in MongoDB by `firebaseUid`
7. Backend checks user status (active, suspended, pendingDeletion)
8. If pending deletion, cancel it and log the event
9. Create new session with device info and location, push to `user.sessions[]`
10. Update `user.lastLoginAt` timestamp
11. Return user data and session token (expires in 7 days, or 30 days if rememberMe)

**Error Cases:**
- Firebase token invalid → 401 Unauthorized
- User not found in MongoDB → 404 Not Found (should register first)
- User suspended → 403 Forbidden
- User deleted → 410 Gone

---

### Pipeline 3: Logout

Terminates the current session.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              LOGOUT PIPELINE                                 │
└─────────────────────────────────────────────────────────────────────────────┘

Frontend                         Backend
────────                         ───────
    │                                │
    │  1. POST /auth/logout          │
    │     Authorization: Bearer <token>
    │───────────────────────────────>│
    │                                │
    │                                │  2. Extract token from header
    │                                │
    │                                │  3. Hash token, find user
    │                                │     with matching session
    │                                │
    │                                │  4. Pull session from
    │                                │     user.sessions[] array
    │                                │
    │  5. Return success             │
    │<───────────────────────────────│
    │                                │
    │  6. Frontend clears stored     │
    │     token                      │
    │                                │
```

**Steps:**
1. Frontend calls `/auth/logout` with Authorization header
2. Backend extracts session token from header
3. Backend hashes token, finds user document with matching session in `sessions[]`
4. Backend removes (pulls) the session from `user.sessions[]` array
5. Return success response
6. Frontend clears stored token from localStorage/memory

**Error Cases:**
- No token present → 200 OK (already logged out)
- Session not found → 200 OK (already invalidated)

---

### Pipeline 4: Session Validation

Per-request middleware that verifies the user is authenticated.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SESSION VALIDATION PIPELINE                           │
└─────────────────────────────────────────────────────────────────────────────┘

Frontend                         Backend
────────                         ───────
    │                                │
    │  1. ANY protected request      │
    │     Authorization: Bearer <token>
    │───────────────────────────────>│
    │                                │
    │                                │  2. Extract token from
    │                                │     Authorization header
    │                                │
    │                                │  3. Hash token (SHA-256)
    │                                │
    │                                │  4. Find user where
    │                                │     sessions[].tokenHash
    │                                │     matches
    │                                │
    │                                │  5. Check session not
    │                                │     expired (expiresAt)
    │                                │
    │                                │  6. Check user status
    │                                │     (active?)
    │                                │
    │                                │  7. Update session
    │                                │     lastActiveAt
    │                                │
    │                                │  8. Attach user to request
    │                                │     (req.user = user)
    │                                │
    │                                │  9. Continue to handler
    │                                │
```

**Steps:**
1. Any request to protected endpoint includes `Authorization: Bearer <token>` header
2. Middleware extracts session token from header
3. Hash the token with SHA-256 (we never store plain tokens)
4. Find user document where `sessions[].tokenHash` matches the hash
5. Verify session has not expired (`sessions[].expiresAt > now`)
6. Verify user status is active (not suspended/deleted)
7. Update `sessions[].lastActiveAt` timestamp in the matching session
8. Attach user object to request for downstream handlers
9. Call next middleware/handler

**Error Cases:**
- No Authorization header → 401 Unauthorized
- Invalid token format → 401 Unauthorized
- Session not found → 401 Unauthorized
- Session expired → 401 Unauthorized
- User suspended → 403 Forbidden
- User status is pendingDeletion → Allow (they can cancel by logging in)

---

### Pipeline 5: Session Management

Allows users to view and revoke their active sessions across devices.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       SESSION MANAGEMENT PIPELINE                            │
└─────────────────────────────────────────────────────────────────────────────┘

                              VIEW SESSIONS
Frontend                         Backend
────────                         ───────
    │                                │
    │  1. GET /auth/sessions         │
    │     Authorization: Bearer <token>
    │───────────────────────────────>│
    │                                │
    │                                │  2. Get user.sessions[]
    │                                │     from current user
    │                                │
    │                                │  3. Filter out expired
    │                                │
    │                                │  4. Mark current session
    │                                │     (isCurrent: true)
    │                                │
    │  5. Return sessions list       │
    │<───────────────────────────────│
    │     [{id, device, location,    │
    │       lastActiveAt, isCurrent}]│


                             REVOKE SINGLE
Frontend                         Backend
────────                         ───────
    │                                │
    │  1. DELETE /auth/sessions/{id} │
    │     Authorization: Bearer <token>
    │───────────────────────────────>│
    │                                │
    │                                │  2. Find session in
    │                                │     user.sessions[] by id
    │                                │
    │                                │  3. Prevent revoking
    │                                │     current session
    │                                │
    │                                │  4. Pull session from
    │                                │     user.sessions[]
    │                                │
    │  5. Return success             │
    │<───────────────────────────────│


                              REVOKE ALL
Frontend                         Backend
────────                         ───────
    │                                │
    │  1. DELETE /auth/sessions      │
    │     ?exceptCurrent=true        │
    │     Authorization: Bearer <token>
    │───────────────────────────────>│
    │                                │
    │                                │  2. Filter user.sessions[]
    │                                │     to keep only current
    │                                │
    │                                │  3. Update user with
    │                                │     filtered sessions
    │                                │
    │  4. Return count revoked       │
    │<───────────────────────────────│
```

**View Sessions Steps:**
1. Frontend requests `/auth/sessions` with Authorization header
2. Backend reads `user.sessions[]` from authenticated user
3. Filter out expired sessions
4. Mark which session is the current one (matches request token hash)
5. Return list with device, location, last active time, current flag

**Revoke Single Steps:**
1. Frontend requests `DELETE /auth/sessions/{sessionId}` with Authorization header
2. Find the session in `user.sessions[]` by its ID
3. Prevent user from revoking their current session (use logout instead)
4. Pull the session from `user.sessions[]` array
5. Return success

**Revoke All Steps:**
1. Frontend requests `DELETE /auth/sessions?exceptCurrent=true` with Authorization header
2. Filter `user.sessions[]` to keep only the current session
3. Update user document with filtered sessions array
4. Return count of sessions revoked

**Error Cases:**
- Session not found → 404 Not Found
- Trying to revoke current session → 400 Bad Request (use logout)

---

## Components

### FirebaseAuthClient

Handles communication with Firebase Admin SDK for token verification.

```python
class FirebaseAuthClient:
    """
    Wrapper for Firebase Admin SDK operations.
    Initialized once at app startup with service account credentials.
    """

    def __init__(self, credentials_path: str):
        """
        Initialize Firebase Admin SDK.

        Args:
            credentials_path: Path to Firebase service account JSON file
        """

    def verify_token(self, id_token: str) -> dict:
        """
        Verify a Firebase ID token and extract claims.

        Args:
            id_token: Firebase ID token from frontend

        Returns:
            dict with keys: uid, email, emailVerified, etc.

        Raises:
            InvalidTokenError: Token is malformed, expired, or revoked
            FirebaseError: Communication error with Firebase
        """

    def get_user(self, firebase_uid: str) -> dict:
        """
        Get user info from Firebase by UID.

        Args:
            firebase_uid: Firebase user ID

        Returns:
            dict with user info from Firebase

        Raises:
            UserNotFoundError: No user with this UID
        """

    def revoke_refresh_tokens(self, firebase_uid: str) -> None:
        """
        Revoke all Firebase refresh tokens for a user.
        Called when user requests account deletion.

        Args:
            firebase_uid: Firebase user ID
        """
```

---

### SessionManager

Manages session lifecycle within the User document's embedded `sessions` array.

```python
class SessionManager:
    """
    Handles session CRUD operations.
    Sessions are stored as embedded array in user document.
    """

    def __init__(self, db: Database, device_detector: DeviceDetector, geo_service: GeoIPService):
        """
        Args:
            db: MongoDB database connection
            device_detector: Service for parsing User-Agent
            geo_service: Service for IP-to-location lookup
        """

    def create_session(
        self,
        user_id: str,
        ip_address: str,
        user_agent: str,
        remember_me: bool = False
    ) -> tuple[str, datetime]:
        """
        Create a new session for a user.

        Args:
            user_id: MongoDB user ID
            ip_address: Client IP address
            user_agent: Client User-Agent header
            remember_me: If True, session expires in 30 days; else 7 days

        Returns:
            tuple of (session_token, expires_at)

        Side Effects:
            - Generates secure random token
            - Hashes token for storage (SHA-256)
            - Detects device type from user_agent
            - Looks up location from IP
            - Pushes session object to user.sessions[] array
        """

    def validate_session(self, token_hash: str) -> tuple[dict, dict] | None:
        """
        Find user and session by token hash.

        Args:
            token_hash: SHA-256 hash of session token

        Returns:
            tuple of (user_dict, session_dict) if valid, None if not found or expired
        """

    def update_last_active(self, user_id: str, token_hash: str) -> None:
        """
        Update the lastActiveAt timestamp for a session.

        Args:
            user_id: MongoDB user ID
            token_hash: Hash of the session token to update
        """

    def get_user_sessions(self, user_id: str) -> list[dict]:
        """
        Get all active (non-expired) sessions for a user.

        Args:
            user_id: MongoDB user ID

        Returns:
            List of session dicts from user.sessions[], filtered for non-expired
        """

    def revoke_session(self, user_id: str, session_id: str) -> bool:
        """
        Remove a specific session from user.sessions[].

        Args:
            user_id: MongoDB user ID
            session_id: ID of session to remove

        Returns:
            True if removed, False if not found
        """

    def revoke_all_sessions(self, user_id: str, except_token_hash: str = None) -> int:
        """
        Remove all sessions from user.sessions[].

        Args:
            user_id: MongoDB user ID
            except_token_hash: Optional token hash to keep (current session)

        Returns:
            Number of sessions removed
        """

    def cleanup_expired_sessions(self, user_id: str) -> int:
        """
        Remove expired sessions from user.sessions[] array.

        Args:
            user_id: MongoDB user ID

        Returns:
            Number of sessions removed
        """
```

---

### DeviceDetector

Parses User-Agent strings to extract device information.

```python
class DeviceDetector:
    """
    Extracts device type and details from User-Agent header.
    """

    def detect(self, user_agent: str) -> dict:
        """
        Parse User-Agent and return device information.

        Args:
            user_agent: HTTP User-Agent header value

        Returns:
            dict with fields:
                - deviceType: "mobile" | "tablet" | "desktop"
                - os: "iOS" | "Android" | "Windows" | "macOS" | "Linux"
                - browser: "Chrome" | "Safari" | "Firefox" | "Edge" | etc.
                - displayName: Human-readable string, e.g., "Chrome on macOS"
        """
```

---

### GeoIPService

Looks up geographic location from IP addresses.

```python
class GeoIPService:
    """
    IP-to-location lookup service.
    Uses MaxMind GeoLite2 database or similar.
    """

    def __init__(self, database_path: str):
        """
        Args:
            database_path: Path to GeoIP database file
        """

    def lookup(self, ip_address: str) -> dict | None:
        """
        Get location for an IP address.

        Args:
            ip_address: IPv4 or IPv6 address

        Returns:
            dict with fields:
                - city: str | None
                - country: str
                - countryCode: str (ISO 3166-1 alpha-2)
            Returns None for private/localhost IPs
        """
```

---

### TokenHasher

Utility for secure token operations.

```python
class TokenHasher:
    """
    Handles token generation and hashing.
    """

    @staticmethod
    def generate_token(length: int = 32) -> str:
        """
        Generate a cryptographically secure random token.

        Args:
            length: Number of random bytes (output will be hex, so 2x length)

        Returns:
            Hex-encoded random string
        """

    @staticmethod
    def hash_token(token: str) -> str:
        """
        Create SHA-256 hash of a token.
        Used for secure storage (never store plain tokens).

        Args:
            token: Plain token string

        Returns:
            Hex-encoded SHA-256 hash
        """
```

---

### AuthMiddleware

Middleware for protected routes.

```python
class AuthMiddleware:
    """
    Middleware that validates session and attaches user to request.
    """

    def __init__(self, session_manager: SessionManager):
        """
        Args:
            session_manager: For session validation
        """

    def require_auth(self, request: Request) -> dict:
        """
        Validate request is authenticated.

        Args:
            request: HTTP request object

        Returns:
            User dict attached to request

        Raises:
            UnauthorizedError: No header, invalid session, or expired
            ForbiddenError: User is suspended

        Side Effects:
            - Extracts token from Authorization header
            - Updates session.lastActiveAt
            - Attaches user to request.state.user
            - Attaches current session to request.state.session
        """

    def optional_auth(self, request: Request) -> dict | None:
        """
        Attach user if authenticated, but don't require it.

        Args:
            request: HTTP request object

        Returns:
            User dict if authenticated, None otherwise

        Does not raise errors for missing/invalid auth.
        """

    def _extract_token(self, request: Request) -> str | None:
        """
        Extract bearer token from Authorization header.

        Args:
            request: HTTP request object

        Returns:
            Token string if present and valid format, None otherwise

        Expected format: "Authorization: Bearer <token>"
        """
```

---

## Data Models

### Session (Embedded in User Document)

Sessions are stored as an array within the User document:

```python
# user["sessions"][] array element
{
    "_id": ObjectId,              # Unique session ID
    "tokenHash": str,             # SHA-256 hash of session token
    "device": {
        "deviceType": str,        # "mobile" | "tablet" | "desktop"
        "os": str,                # "iOS" | "Android" | "Windows" | "macOS" | "Linux"
        "browser": str,           # "Chrome" | "Safari" | "Firefox" | etc.
        "displayName": str        # "Chrome on macOS"
    },
    "location": {
        "city": str | None,
        "country": str,
        "countryCode": str        # ISO 3166-1 alpha-2
    },
    "ipAddress": str,
    "createdAt": datetime,
    "expiresAt": datetime,
    "lastActiveAt": datetime
}
```

### User Document (Auth-relevant fields)

```python
{
    "_id": ObjectId,
    "firebaseUid": str,           # Link to Firebase account (indexed, unique)
    "email": str,                 # From Firebase
    "status": str,                # "active" | "pendingDeletion" | "suspended"
    "sessions": list[dict],       # Embedded sessions array
    "lastLoginAt": datetime,
    # ... other fields managed by User System
}
```

**Indexes:**
- `firebaseUid` (unique) - For Firebase → MongoDB lookup
- `sessions.tokenHash` - For session validation queries
- `email` (unique) - For email lookup

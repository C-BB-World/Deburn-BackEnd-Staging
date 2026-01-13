"""
JWT + bcrypt authentication provider.

A complete authentication implementation using:
- JWT tokens for stateless authentication
- bcrypt for secure password hashing
- In-memory token revocation (use Redis in production)

Example:
    auth = JWTAuth(
        secret="your-secret-key",
        access_token_expire_minutes=60,
    )

    # Create user and token
    user_id = await auth.create_user("user@example.com", "password123")
    token = await auth.create_token(user_id)

    # Verify token
    claims = await auth.verify_token(token)
    print(claims["sub"])  # user_id
"""

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Callable, Awaitable

import bcrypt as bcrypt_lib
from jose import jwt, JWTError

from common.auth.base import AuthProvider


# Type alias for user lookup callback
UserLookupCallback = Callable[[str, str], Awaitable[Optional[Dict[str, Any]]]]
UserCreateCallback = Callable[[str, str, Dict[str, Any]], Awaitable[str]]
UserUpdateCallback = Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any]]]
UserDeleteCallback = Callable[[str], Awaitable[None]]


class JWTAuth(AuthProvider):
    """
    JWT + bcrypt authentication provider.

    This provider handles token creation/verification and password hashing.
    User storage is handled by callbacks to allow integration with any database.
    """

    def __init__(
        self,
        secret: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        reset_token_expire_hours: int = 24,
        verification_token_expire_hours: int = 48,
        # Callbacks for user storage (integrate with your database)
        get_user_by_email: Optional[UserLookupCallback] = None,
        get_user_by_id: Optional[Callable[[str], Awaitable[Optional[Dict[str, Any]]]]] = None,
        create_user_in_db: Optional[UserCreateCallback] = None,
        update_user_in_db: Optional[UserUpdateCallback] = None,
        delete_user_in_db: Optional[UserDeleteCallback] = None,
    ):
        """
        Initialize JWT auth provider.

        Args:
            secret: Secret key for JWT signing (keep this secure!)
            algorithm: JWT algorithm (default: HS256)
            access_token_expire_minutes: Token expiration time
            reset_token_expire_hours: Password reset token expiration
            verification_token_expire_hours: Email verification expiration
            get_user_by_email: Callback to fetch user by email from database
            get_user_by_id: Callback to fetch user by ID from database
            create_user_in_db: Callback to create user in database
            update_user_in_db: Callback to update user in database
            delete_user_in_db: Callback to delete user from database
        """
        self.secret = secret
        self.algorithm = algorithm
        self.access_token_expire = timedelta(minutes=access_token_expire_minutes)
        self.reset_token_expire = timedelta(hours=reset_token_expire_hours)
        self.verification_token_expire = timedelta(hours=verification_token_expire_hours)

        # User storage callbacks
        self._get_user_by_email = get_user_by_email
        self._get_user_by_id_cb = get_user_by_id
        self._create_user_in_db = create_user_in_db
        self._update_user_in_db = update_user_in_db
        self._delete_user_in_db = delete_user_in_db

        # Token revocation store (use Redis in production)
        self._revoked_tokens: set = set()

        # Pending tokens (reset, verification) - in production use database
        self._reset_tokens: Dict[str, Dict[str, Any]] = {}
        self._verification_tokens: Dict[str, Dict[str, Any]] = {}

    def _prehash_password(self, password: str) -> str:
        """
        Pre-hash password with SHA-256 before bcrypt.

        This handles bcrypt's 72-byte limit and ensures consistent
        behavior across all password lengths.
        """
        sha256_hash = hashlib.sha256(password.encode("utf-8")).digest()
        return base64.b64encode(sha256_hash).decode("utf-8")

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt with SHA-256 pre-hashing."""
        prehashed = self._prehash_password(password)
        salt = bcrypt_lib.gensalt()
        return bcrypt_lib.hashpw(prehashed.encode("utf-8"), salt).decode("utf-8")

    def verify_password(self, password: str, hashed: str) -> bool:
        """
        Verify a password against its hash.

        Supports both new (SHA-256 pre-hashed) and legacy (direct bcrypt) hashes
        for backwards compatibility.
        """
        hashed_bytes = hashed.encode("utf-8")

        # Try new method first (SHA-256 pre-hash)
        prehashed = self._prehash_password(password)
        try:
            if bcrypt_lib.checkpw(prehashed.encode("utf-8"), hashed_bytes):
                return True
        except ValueError:
            pass

        # Fallback to legacy method (direct bcrypt) for old hashes
        try:
            return bcrypt_lib.checkpw(password.encode("utf-8"), hashed_bytes)
        except ValueError:
            # Password too long for direct bcrypt - definitely not a match
            return False

    async def create_user(
        self,
        email: str,
        password: str,
        **kwargs: Any,
    ) -> str:
        """Create a new user with hashed password."""
        if not self._create_user_in_db:
            raise NotImplementedError("create_user_in_db callback not provided")

        # Check if user already exists
        if self._get_user_by_email:
            existing = await self._get_user_by_email(email, "")
            if existing:
                raise ValueError("Email already registered")

        # Hash password and create user
        password_hash = self.hash_password(password)
        user_id = await self._create_user_in_db(email, password_hash, kwargs)
        return user_id

    async def verify_credentials(
        self,
        email: str,
        password: str,
    ) -> Dict[str, Any]:
        """Verify email and password."""
        if not self._get_user_by_email:
            raise NotImplementedError("get_user_by_email callback not provided")

        user = await self._get_user_by_email(email, "password_hash")
        if not user:
            raise ValueError("Invalid email or password")

        password_hash = user.get("password_hash", "")
        if not password_hash or not self.verify_password(password, password_hash):
            raise ValueError("Invalid email or password")

        # Remove password_hash from returned user info
        user_copy = {k: v for k, v in user.items() if k != "password_hash"}
        return user_copy

    async def create_token(
        self,
        user_id: str,
        **claims: Any,
    ) -> str:
        """Create a JWT token for the user."""
        expire = datetime.now(timezone.utc) + self.access_token_expire
        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            **claims,
        }
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode a JWT token."""
        if token in self._revoked_tokens:
            raise ValueError("Token has been revoked")

        try:
            payload = jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm],
            )
            return payload
        except JWTError as e:
            raise ValueError(f"Invalid token: {e}")

    async def revoke_token(self, token: str) -> None:
        """Add token to revocation list."""
        self._revoked_tokens.add(token)

    async def send_password_reset(self, email: str) -> str:
        """Generate password reset token."""
        if self._get_user_by_email:
            user = await self._get_user_by_email(email, "")
            if not user:
                # Don't reveal if email exists - return fake token
                return secrets.token_urlsafe(32)

        token = secrets.token_urlsafe(32)
        expire = datetime.now(timezone.utc) + self.reset_token_expire

        self._reset_tokens[token] = {
            "email": email,
            "expires": expire,
        }

        # In production, send actual email here
        return token

    async def reset_password(
        self,
        token: str,
        new_password: str,
    ) -> None:
        """Reset password using reset token."""
        token_data = self._reset_tokens.get(token)
        if not token_data:
            raise ValueError("Invalid or expired reset token")

        if datetime.now(timezone.utc) > token_data["expires"]:
            del self._reset_tokens[token]
            raise ValueError("Reset token has expired")

        # Update password in database
        if self._get_user_by_email and self._update_user_in_db:
            user = await self._get_user_by_email(token_data["email"], "")
            if user:
                password_hash = self.hash_password(new_password)
                await self._update_user_in_db(
                    user["id"],
                    {"password_hash": password_hash},
                )

        # Invalidate the reset token
        del self._reset_tokens[token]

    async def send_verification_email(self, email: str) -> str:
        """Generate email verification token."""
        token = secrets.token_urlsafe(32)
        expire = datetime.now(timezone.utc) + self.verification_token_expire

        self._verification_tokens[token] = {
            "email": email,
            "expires": expire,
        }

        # In production, send actual email here
        return token

    async def verify_email(self, token: str) -> None:
        """Verify email using verification token."""
        token_data = self._verification_tokens.get(token)
        if not token_data:
            raise ValueError("Invalid or expired verification token")

        if datetime.now(timezone.utc) > token_data["expires"]:
            del self._verification_tokens[token]
            raise ValueError("Verification token has expired")

        # Mark email as verified in database
        if self._get_user_by_email and self._update_user_in_db:
            user = await self._get_user_by_email(token_data["email"], "")
            if user:
                await self._update_user_in_db(
                    user["id"],
                    {"email_verified": True},
                )

        # Invalidate the verification token
        del self._verification_tokens[token]

    async def delete_user(self, user_id: str) -> None:
        """Delete user account."""
        if not self._delete_user_in_db:
            raise NotImplementedError("delete_user_in_db callback not provided")
        await self._delete_user_in_db(user_id)

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        if not self._get_user_by_id_cb:
            raise NotImplementedError("get_user_by_id callback not provided")
        return await self._get_user_by_id_cb(user_id)

    async def update_user(
        self,
        user_id: str,
        **updates: Any,
    ) -> Dict[str, Any]:
        """Update user information."""
        if not self._update_user_in_db:
            raise NotImplementedError("update_user_in_db callback not provided")
        return await self._update_user_in_db(user_id, updates)

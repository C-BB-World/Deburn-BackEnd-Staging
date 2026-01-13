"""
Abstract authentication provider interface.

Defines the contract that all auth providers must implement.
This allows swapping between different auth strategies (JWT, Firebase, etc.)
without changing application code.

Example:
    from common.auth import AuthProvider, JWTAuth, FirebaseAuth

    def get_auth_provider(settings) -> AuthProvider:
        if settings.AUTH_PROVIDER == "firebase":
            return FirebaseAuth(settings.FIREBASE_CREDENTIALS_PATH)
        return JWTAuth(secret=settings.JWT_SECRET)
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class AuthProvider(ABC):
    """
    Abstract authentication provider.

    Implement this interface for different auth strategies.
    All methods are async to support both sync and async implementations.
    """

    @abstractmethod
    async def create_user(
        self,
        email: str,
        password: str,
        **kwargs: Any,
    ) -> str:
        """
        Create a new user account.

        Args:
            email: User's email address
            password: User's password (will be hashed)
            **kwargs: Additional user data (name, etc.)

        Returns:
            The created user's ID

        Raises:
            ValueError: If email already exists or validation fails
        """
        pass

    @abstractmethod
    async def verify_credentials(
        self,
        email: str,
        password: str,
    ) -> Dict[str, Any]:
        """
        Verify email and password credentials.

        Args:
            email: User's email address
            password: User's password

        Returns:
            Dictionary containing user info (at minimum: user_id, email)

        Raises:
            ValueError: If credentials are invalid
        """
        pass

    @abstractmethod
    async def create_token(
        self,
        user_id: str,
        **claims: Any,
    ) -> str:
        """
        Create an authentication token for a user.

        Args:
            user_id: The user's ID
            **claims: Additional claims to include in the token

        Returns:
            The authentication token string
        """
        pass

    @abstractmethod
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify an authentication token.

        Args:
            token: The token to verify

        Returns:
            Dictionary containing decoded token claims (at minimum: sub/user_id)

        Raises:
            ValueError: If token is invalid, expired, or revoked
        """
        pass

    @abstractmethod
    async def revoke_token(self, token: str) -> None:
        """
        Revoke/invalidate a token.

        Args:
            token: The token to revoke
        """
        pass

    @abstractmethod
    async def send_password_reset(self, email: str) -> str:
        """
        Initiate password reset process.

        Args:
            email: User's email address

        Returns:
            Reset token (for testing) or confirmation message

        Raises:
            ValueError: If email is not found
        """
        pass

    @abstractmethod
    async def reset_password(
        self,
        token: str,
        new_password: str,
    ) -> None:
        """
        Reset password using a reset token.

        Args:
            token: Password reset token
            new_password: New password to set

        Raises:
            ValueError: If token is invalid or expired
        """
        pass

    @abstractmethod
    async def send_verification_email(self, email: str) -> str:
        """
        Send email verification.

        Args:
            email: User's email address

        Returns:
            Verification token (for testing)

        Raises:
            ValueError: If email is not found
        """
        pass

    @abstractmethod
    async def verify_email(self, token: str) -> None:
        """
        Verify email address using verification token.

        Args:
            token: Email verification token

        Raises:
            ValueError: If token is invalid or expired
        """
        pass

    @abstractmethod
    async def delete_user(self, user_id: str) -> None:
        """
        Delete a user account.

        Args:
            user_id: The user's ID to delete

        Raises:
            ValueError: If user is not found
        """
        pass

    @abstractmethod
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user information by ID.

        Args:
            user_id: The user's ID

        Returns:
            User info dict or None if not found
        """
        pass

    @abstractmethod
    async def update_user(
        self,
        user_id: str,
        **updates: Any,
    ) -> Dict[str, Any]:
        """
        Update user information.

        Args:
            user_id: The user's ID
            **updates: Fields to update

        Returns:
            Updated user info

        Raises:
            ValueError: If user is not found
        """
        pass

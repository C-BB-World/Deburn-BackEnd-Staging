"""
Firebase Admin SDK authentication provider.

Uses Firebase Authentication for user management and token verification.
Requires firebase-admin package and a service account credentials file.

Example:
    auth = FirebaseAuth(credentials_path="path/to/serviceAccount.json")

    # Create user
    user_id = await auth.create_user("user@example.com", "password123")

    # Verify ID token from client
    claims = await auth.verify_token(id_token)
    print(claims["uid"])  # Firebase user ID
"""

from typing import Dict, Any, Optional
from common.auth.base import AuthProvider


class FirebaseAuth(AuthProvider):
    """
    Firebase Admin SDK authentication provider.

    Handles user authentication through Firebase, which provides:
    - Email/password authentication
    - Email verification
    - Password reset
    - Token verification
    """

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        credentials_dict: Optional[Dict[str, Any]] = None,
        project_id: Optional[str] = None,
    ):
        """
        Initialize Firebase auth provider.

        Args:
            credentials_path: Path to service account JSON file
            credentials_dict: Service account credentials as dict (alternative to path)
            project_id: Firebase project ID (optional, can be inferred from credentials)
        """
        try:
            import firebase_admin
            from firebase_admin import credentials, auth
        except ImportError:
            raise ImportError(
                "firebase-admin package is required for Firebase authentication. "
                "Install with: pip install firebase-admin"
            )

        # Initialize Firebase app if not already done
        if not firebase_admin._apps:
            if credentials_path:
                cred = credentials.Certificate(credentials_path)
            elif credentials_dict:
                cred = credentials.Certificate(credentials_dict)
            else:
                # Use default credentials (for GCP environments)
                cred = credentials.ApplicationDefault()

            options = {}
            if project_id:
                options["projectId"] = project_id

            firebase_admin.initialize_app(cred, options)

        self._auth = auth

    async def create_user(
        self,
        email: str,
        password: str,
        **kwargs: Any,
    ) -> str:
        """Create a new Firebase user."""
        try:
            user_record = self._auth.create_user(
                email=email,
                password=password,
                display_name=kwargs.get("display_name"),
                photo_url=kwargs.get("photo_url"),
                disabled=kwargs.get("disabled", False),
            )
            return user_record.uid
        except self._auth.EmailAlreadyExistsError:
            raise ValueError("Email already registered")
        except Exception as e:
            raise ValueError(f"Failed to create user: {e}")

    async def verify_credentials(
        self,
        email: str,
        password: str,
    ) -> Dict[str, Any]:
        """
        Verify credentials - not directly supported by Firebase Admin SDK.

        Firebase auth is designed for client-side password verification.
        This method is included for interface compatibility but requires
        client-side sign-in and token verification instead.
        """
        # Firebase Admin SDK doesn't support direct password verification
        # In production, clients sign in with Firebase client SDK and send ID token
        raise NotImplementedError(
            "Firebase Admin SDK doesn't support direct password verification. "
            "Use client-side Firebase SDK for sign-in, then verify the ID token."
        )

    async def create_token(
        self,
        user_id: str,
        **claims: Any,
    ) -> str:
        """Create a custom token for the user."""
        try:
            custom_token = self._auth.create_custom_token(
                uid=user_id,
                developer_claims=claims if claims else None,
            )
            # create_custom_token returns bytes, decode to string
            if isinstance(custom_token, bytes):
                return custom_token.decode("utf-8")
            return custom_token
        except Exception as e:
            raise ValueError(f"Failed to create token: {e}")

    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify a Firebase ID token."""
        try:
            decoded = self._auth.verify_id_token(token)
            # Add 'sub' field for compatibility with JWT provider
            decoded["sub"] = decoded.get("uid")
            return decoded
        except self._auth.RevokedIdTokenError:
            raise ValueError("Token has been revoked")
        except self._auth.ExpiredIdTokenError:
            raise ValueError("Token has expired")
        except self._auth.InvalidIdTokenError as e:
            raise ValueError(f"Invalid token: {e}")
        except Exception as e:
            raise ValueError(f"Token verification failed: {e}")

    async def revoke_token(self, token: str) -> None:
        """Revoke all refresh tokens for a user."""
        try:
            # First verify the token to get the user ID
            decoded = self._auth.verify_id_token(token)
            uid = decoded.get("uid")
            if uid:
                self._auth.revoke_refresh_tokens(uid)
        except Exception as e:
            raise ValueError(f"Failed to revoke token: {e}")

    async def send_password_reset(self, email: str) -> str:
        """Generate password reset link."""
        try:
            # Generate a password reset link
            link = self._auth.generate_password_reset_link(email)
            # In production, send this link via email
            # Return the link (or just a confirmation) for now
            return link
        except self._auth.UserNotFoundError:
            # Don't reveal if user exists - return generic response
            return "If the email exists, a reset link will be sent"
        except Exception as e:
            raise ValueError(f"Failed to send password reset: {e}")

    async def reset_password(
        self,
        token: str,
        new_password: str,
    ) -> None:
        """
        Reset password - handled by Firebase's action handler.

        Firebase password reset is handled through Firebase's built-in
        action handler or can be customized with confirm_password_reset.
        """
        # Firebase handles password reset through its action handler
        # The token (action code) is verified and password updated by Firebase
        raise NotImplementedError(
            "Firebase password reset is handled through Firebase's action handler. "
            "Use Firebase client SDK or custom action handler."
        )

    async def send_verification_email(self, email: str) -> str:
        """Generate email verification link."""
        try:
            link = self._auth.generate_email_verification_link(email)
            # In production, send this link via email
            return link
        except self._auth.UserNotFoundError:
            raise ValueError("User not found")
        except Exception as e:
            raise ValueError(f"Failed to send verification email: {e}")

    async def verify_email(self, token: str) -> None:
        """
        Verify email - handled by Firebase's action handler.

        Firebase email verification is handled through Firebase's built-in
        action handler.
        """
        # Firebase handles email verification through its action handler
        raise NotImplementedError(
            "Firebase email verification is handled through Firebase's action handler. "
            "Use Firebase client SDK or custom action handler."
        )

    async def delete_user(self, user_id: str) -> None:
        """Delete a Firebase user."""
        try:
            self._auth.delete_user(user_id)
        except self._auth.UserNotFoundError:
            raise ValueError("User not found")
        except Exception as e:
            raise ValueError(f"Failed to delete user: {e}")

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get Firebase user by UID."""
        try:
            user = self._auth.get_user(user_id)
            return {
                "id": user.uid,
                "uid": user.uid,
                "email": user.email,
                "email_verified": user.email_verified,
                "display_name": user.display_name,
                "photo_url": user.photo_url,
                "disabled": user.disabled,
                "provider_data": [
                    {"provider_id": p.provider_id, "uid": p.uid}
                    for p in user.provider_data
                ],
            }
        except self._auth.UserNotFoundError:
            return None
        except Exception as e:
            raise ValueError(f"Failed to get user: {e}")

    async def update_user(
        self,
        user_id: str,
        **updates: Any,
    ) -> Dict[str, Any]:
        """Update Firebase user."""
        try:
            # Map common field names to Firebase field names
            firebase_updates = {}
            field_mapping = {
                "email": "email",
                "password": "password",
                "display_name": "display_name",
                "photo_url": "photo_url",
                "disabled": "disabled",
                "email_verified": "email_verified",
            }

            for key, value in updates.items():
                if key in field_mapping:
                    firebase_updates[field_mapping[key]] = value

            user = self._auth.update_user(user_id, **firebase_updates)

            return {
                "id": user.uid,
                "uid": user.uid,
                "email": user.email,
                "email_verified": user.email_verified,
                "display_name": user.display_name,
                "photo_url": user.photo_url,
                "disabled": user.disabled,
            }
        except self._auth.UserNotFoundError:
            raise ValueError("User not found")
        except Exception as e:
            raise ValueError(f"Failed to update user: {e}")

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get Firebase user by email."""
        try:
            user = self._auth.get_user_by_email(email)
            return await self.get_user_by_id(user.uid)
        except self._auth.UserNotFoundError:
            return None
        except Exception as e:
            raise ValueError(f"Failed to get user: {e}")

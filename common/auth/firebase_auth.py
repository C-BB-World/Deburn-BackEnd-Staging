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

    # Sign in with email/password (via REST API)
    user = await auth.sign_in_with_password("user@example.com", "password123")
"""

import os
import httpx
from typing import Dict, Any, Optional
from common.auth.base import AuthProvider

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, rely on system environment variables


def _get_firebase_credentials_from_env() -> Optional[Dict[str, Any]]:
    """
    Check if Firebase credentials are present in environment variables.
    Returns credentials dict if all required fields are present, None otherwise.
    """
    required_fields = [
        "PROJECT_ID",
        "PRIVATE_KEY",
        "CLIENT_EMAIL",
    ]

    # Check if required fields are present
    for field in required_fields:
        if not os.environ.get(field):
            return None

    # Build credentials dict from environment variables
    credentials = {
        "type": os.environ.get("TYPE", "service_account").strip('"').strip(","),
        "project_id": os.environ.get("PROJECT_ID", "").strip('"').strip(","),
        "private_key_id": os.environ.get("PRIVATE_KEY_ID", "").strip('"').strip(","),
        "private_key": os.environ.get("PRIVATE_KEY", "").strip('"').strip(","),
        "client_email": os.environ.get("CLIENT_EMAIL", "").strip('"').strip(","),
        "client_id": os.environ.get("CLIENT_ID", "").strip('"').strip(","),
        "auth_uri": os.environ.get("AUTH_URI", "https://accounts.google.com/o/oauth2/auth").strip('"').strip(","),
        "token_uri": os.environ.get("TOKEN_URI", "https://oauth2.googleapis.com/token").strip('"').strip(","),
        "auth_provider_x509_cert_url": os.environ.get("AUTH_PROVIDER_X509_CERT_URL", "https://www.googleapis.com/oauth2/v1/certs").strip('"').strip(","),
        "client_x509_cert_url": os.environ.get("CLIENT_X509_CERT_URL", "").strip('"').strip(","),
        "universe_domain": os.environ.get("UNIVERSE_DOMAIN", "googleapis.com").strip('"').strip(","),
    }

    return credentials


class FirebaseAuth(AuthProvider):
    """
    Firebase Admin SDK authentication provider.

    Handles user authentication through Firebase, which provides:
    - Email/password authentication
    - Email verification
    - Password reset
    - Token verification
    """

    # Firebase REST API base URL
    FIREBASE_AUTH_URL = "https://identitytoolkit.googleapis.com/v1/accounts"

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        credentials_dict: Optional[Dict[str, Any]] = None,
        project_id: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """
        Initialize Firebase auth provider.

        Args:
            credentials_path: Path to service account JSON file
            credentials_dict: Service account credentials as dict (alternative to path)
            project_id: Firebase project ID (optional, can be inferred from credentials)
            api_key: Firebase Web API Key (for REST API authentication)
        """
        try:
            import firebase_admin
            from firebase_admin import credentials, auth
        except ImportError:
            raise ImportError(
                "firebase-admin package is required for Firebase authentication. "
                "Install with: pip install firebase-admin"
            )

        # Get API key from parameter or environment
        self._api_key = api_key or os.environ.get("FIREBASE_API_KEY")

        # Initialize Firebase app if not already done
        if not firebase_admin._apps:
            if credentials_path:
                cred = credentials.Certificate(credentials_path)
            elif credentials_dict:
                cred = credentials.Certificate(credentials_dict)
            else:
                # Check if Firebase credentials are available in environment variables
                env_credentials = _get_firebase_credentials_from_env()
                if env_credentials:
                    cred = credentials.Certificate(env_credentials)
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
        Verify email/password credentials using Firebase REST API.

        Returns user info and tokens if successful.
        """
        return await self.sign_in_with_password(email, password)

    async def sign_in_with_password(
        self,
        email: str,
        password: str,
    ) -> Dict[str, Any]:
        """
        Sign in with email and password using Firebase REST API.

        Args:
            email: User's email address
            password: User's password

        Returns:
            Dict containing uid, email, idToken, refreshToken, etc.

        Raises:
            ValueError: If credentials are invalid or API key is missing
        """
        if not self._api_key:
            raise ValueError(
                "Firebase API key is required for email/password authentication. "
                "Set FIREBASE_API_KEY environment variable."
            )

        url = f"{self.FIREBASE_AUTH_URL}:signInWithPassword?key={self._api_key}"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json={
                    "email": email,
                    "password": password,
                    "returnSecureToken": True,
                },
            )

            if response.status_code != 200:
                error_data = response.json()
                error_message = error_data.get("error", {}).get("message", "Unknown error")

                if error_message in ["EMAIL_NOT_FOUND", "INVALID_PASSWORD", "INVALID_LOGIN_CREDENTIALS"]:
                    raise ValueError("Invalid email or password")
                elif error_message == "USER_DISABLED":
                    raise ValueError("Account has been disabled")
                elif error_message == "TOO_MANY_ATTEMPTS_TRY_LATER":
                    raise ValueError("Too many failed attempts. Please try again later.")
                else:
                    raise ValueError(f"Authentication failed: {error_message}")

            data = response.json()

            return {
                "uid": data.get("localId"),
                "email": data.get("email"),
                "displayName": data.get("displayName"),
                "idToken": data.get("idToken"),
                "refreshToken": data.get("refreshToken"),
                "expiresIn": data.get("expiresIn"),
            }

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

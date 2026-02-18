"""
Token generation and hashing utilities.

Provides secure token operations for session management.
"""

import hashlib
import secrets


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
        return secrets.token_hex(length)

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
        return hashlib.sha256(token.encode()).hexdigest()

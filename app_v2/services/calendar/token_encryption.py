"""
Token encryption service for calendar OAuth tokens.

Uses AES-256-CBC encryption for secure token storage.
"""

import base64
import hashlib
import logging
import os
import secrets
from typing import Optional

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class TokenEncryptionService:
    """
    Encrypts and decrypts OAuth tokens using AES-256-CBC.
    """

    BLOCK_SIZE = 16

    def __init__(self, encryption_key: str):
        """
        Initialize TokenEncryptionService.

        Args:
            encryption_key: 32-byte hex key for AES-256
        """
        key_bytes = bytes.fromhex(encryption_key)
        if len(key_bytes) != 32:
            raise ValueError("Encryption key must be 32 bytes (64 hex characters)")
        self._key = key_bytes

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a token.

        Args:
            plaintext: Token to encrypt

        Returns:
            Base64-encoded encrypted string (IV + ciphertext)
        """
        iv = secrets.token_bytes(self.BLOCK_SIZE)
        cipher = Cipher(
            algorithms.AES(self._key),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()

        padded = self._pad(plaintext.encode("utf-8"))
        ciphertext = encryptor.update(padded) + encryptor.finalize()

        return base64.b64encode(iv + ciphertext).decode("utf-8")

    def decrypt(self, encrypted: str) -> Optional[str]:
        """
        Decrypt a token.

        Args:
            encrypted: Base64-encoded encrypted string

        Returns:
            Decrypted token or None if decryption fails
        """
        try:
            data = base64.b64decode(encrypted)
            iv = data[:self.BLOCK_SIZE]
            ciphertext = data[self.BLOCK_SIZE:]

            cipher = Cipher(
                algorithms.AES(self._key),
                modes.CBC(iv),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()

            padded = decryptor.update(ciphertext) + decryptor.finalize()
            return self._unpad(padded).decode("utf-8")
        except Exception as e:
            logger.error(f"Token decryption failed: {e}")
            return None

    def _pad(self, data: bytes) -> bytes:
        """PKCS7 padding."""
        padding_length = self.BLOCK_SIZE - (len(data) % self.BLOCK_SIZE)
        return data + bytes([padding_length] * padding_length)

    def _unpad(self, data: bytes) -> bytes:
        """Remove PKCS7 padding."""
        padding_length = data[-1]
        return data[:-padding_length]

    @staticmethod
    def generate_key() -> str:
        """Generate a new 32-byte encryption key as hex string."""
        return secrets.token_hex(32)

"""
Memory encryption service.

Uses AES-256-CBC encryption for secure conversation storage.
Key derived from SHA256 hash of encryption key.
"""

import base64
import hashlib
import logging
import secrets
from typing import Optional

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class MemoryEncryptionService:
    """
    Encrypts/decrypts conversation content using AES-256-CBC.
    """

    BLOCK_SIZE = 16

    def __init__(self, encryption_key: str):
        """
        Initialize MemoryEncryptionService.

        Args:
            encryption_key: 32-byte hex key for AES-256, or any string (will be SHA256 hashed)
        """
        try:
            key_bytes = bytes.fromhex(encryption_key)
            if len(key_bytes) != 32:
                raise ValueError("Invalid hex key length")
            self._key = key_bytes
            logger.debug("Using provided 32-byte hex encryption key")
        except ValueError:
            self._key = hashlib.sha256(encryption_key.encode("utf-8")).digest()
            logger.debug("Using SHA256-hashed encryption key")

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt message content.

        Args:
            plaintext: Content to encrypt

        Returns:
            Base64-encoded string (IV + ciphertext)
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
        Decrypt message content.

        Args:
            encrypted: Base64-encoded encrypted string

        Returns:
            Decrypted content or None if decryption fails
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
            logger.error(f"Memory decryption failed: {e}")
            return None

    def hash_for_search(self, text: str) -> str:
        """
        Generate SHA256 hash for content indexing.

        Used for future RAG deduplication and indexing.

        Args:
            text: Content to hash

        Returns:
            SHA256 hex digest
        """
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _pad(self, data: bytes) -> bytes:
        """PKCS7 padding."""
        padding_length = self.BLOCK_SIZE - (len(data) % self.BLOCK_SIZE)
        return data + bytes([padding_length] * padding_length)

    def _unpad(self, data: bytes) -> bytes:
        """Remove PKCS7 padding."""
        padding_length = data[-1]
        return data[:-padding_length]

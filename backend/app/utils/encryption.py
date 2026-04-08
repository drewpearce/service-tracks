"""Fernet symmetric encryption for storing API tokens and secrets at rest.

Usage:
    from app.utils.encryption import encrypt, decrypt

    ciphertext = encrypt("my-api-secret")     # -> bytes (store in BYTEA column)
    plaintext = decrypt(ciphertext)            # -> "my-api-secret"

Generate a new key (run once, store in ENCRYPTION_KEY env var):
    from app.utils.encryption import generate_encryption_key
    print(generate_encryption_key())
"""

from cryptography.fernet import Fernet

from app.config import settings


def generate_encryption_key() -> str:
    """Generate a new Fernet-compatible encryption key.

    Run once, then store the result in the ENCRYPTION_KEY environment variable.
    """
    return Fernet.generate_key().decode()


def _get_fernet() -> Fernet:
    """Return a Fernet instance using the configured encryption key."""
    key = settings.ENCRYPTION_KEY
    if not key:
        raise ValueError(
            "ENCRYPTION_KEY is not configured. "
            "Generate one with: "
            "python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt(plaintext: str) -> bytes:
    """Encrypt a plaintext string. Returns bytes suitable for BYTEA column storage."""
    return _get_fernet().encrypt(plaintext.encode("utf-8"))


def decrypt(ciphertext: bytes) -> str:
    """Decrypt ciphertext bytes back to a plaintext string.

    Raises:
        cryptography.fernet.InvalidToken: If the key is wrong or data is corrupted.
    """
    return _get_fernet().decrypt(ciphertext).decode("utf-8")

"""Unit tests for the Fernet encryption utility."""

import pytest
from cryptography.fernet import InvalidToken

from app.utils.encryption import decrypt, encrypt, generate_encryption_key


@pytest.fixture()
def fernet_key(monkeypatch) -> str:
    """Patch settings.ENCRYPTION_KEY with a freshly generated test key."""
    key = generate_encryption_key()
    from app.config import settings

    monkeypatch.setattr(settings, "ENCRYPTION_KEY", key)
    return key


def test_round_trip(fernet_key):
    """decrypt(encrypt(x)) returns the original plaintext."""
    assert decrypt(encrypt("my-secret")) == "my-secret"


def test_ciphertext_differs_each_call(fernet_key):
    """encrypt() produces different ciphertext on each call (Fernet IV + timestamp)."""
    ct1 = encrypt("same-input")
    ct2 = encrypt("same-input")
    assert ct1 != ct2


def test_wrong_key_raises_invalid_token(monkeypatch):
    """Encrypting with key A and decrypting with key B raises InvalidToken."""
    from app.config import settings

    key_a = generate_encryption_key()
    key_b = generate_encryption_key()

    monkeypatch.setattr(settings, "ENCRYPTION_KEY", key_a)
    ciphertext = encrypt("secret")

    monkeypatch.setattr(settings, "ENCRYPTION_KEY", key_b)
    with pytest.raises(InvalidToken):
        decrypt(ciphertext)


def test_empty_key_raises_value_error(monkeypatch):
    """encrypt() raises ValueError when ENCRYPTION_KEY is not configured."""
    from app.config import settings

    monkeypatch.setattr(settings, "ENCRYPTION_KEY", "")
    with pytest.raises(ValueError, match="ENCRYPTION_KEY"):
        encrypt("test")


def test_return_type_is_bytes(fernet_key):
    """encrypt() returns bytes."""
    result = encrypt("test")
    assert isinstance(result, bytes)


def test_unicode_round_trip(fernet_key):
    """UTF-8 strings (including non-ASCII characters) survive the encrypt/decrypt cycle."""
    original = "caf\u00e9 \u2603"
    assert decrypt(encrypt(original)) == original

"""
core/encryption/__init__.py
────────────────────────────
AES-256 (Fernet) encryption for sensitive data at rest.

Usage:
    from core.encryption import encrypt, decrypt

    encrypted = encrypt("sensitive text")   # returns str
    original  = decrypt(encrypted)          # returns str

The key is read from the ENCRYPTION_KEY environment variable.
In development a fallback key is auto-generated and printed once.
In production always set ENCRYPTION_KEY in your env.
"""
import os
import base64
import logging
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

# ── Key setup ─────────────────────────────────────────────────────────────────

def _get_fernet() -> Fernet:
    raw_key = os.getenv('ENCRYPTION_KEY', '')
    if raw_key:
        # Try 1: use as-is (already a valid Fernet key, i.e. 44-char urlsafe base64)
        try:
            return Fernet(raw_key.encode())
        except Exception:
            pass
        # Try 2: treat as raw 32-byte hex or utf-8, re-encode as Fernet key
        try:
            decoded = base64.urlsafe_b64decode(raw_key + '==')  # padding-safe
            if len(decoded) == 32:
                return Fernet(base64.urlsafe_b64encode(decoded))
        except Exception:
            pass
        # All attempts failed — warn and fall through to generated key
        logger.error(
            "ENCRYPTION_KEY is set but is not a valid Fernet key. "
            "Generate a proper key with: python -c \"from core.encryption import generate_key; print(generate_key())\""
        )

    # Dev fallback — generate once per process
    key = Fernet.generate_key()
    logger.warning(
        "Using a temporary encryption key (data will be unreadable after restart). "
        "Set ENCRYPTION_KEY in .env to a valid Fernet key.\n"
        "Generate one: python -c \"from core.encryption import generate_key; print(generate_key())\""
    )
    return Fernet(key)


_fernet = None  # type: Optional[Fernet]


def _f() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = _get_fernet()
    return _fernet


# ── Public API ────────────────────────────────────────────────────────────────

def encrypt(value: str) -> str:
    """Encrypt a string. Returns a base64 token string."""
    if not value:
        return value
    return _f().encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    """Decrypt a token produced by encrypt(). Returns original string."""
    if not token:
        return token
    try:
        return _f().decrypt(token.encode()).decode()
    except InvalidToken:
        logger.error("Decryption failed — invalid token or wrong key.")
        return ''


def generate_key() -> str:
    """Helper: generate a new Fernet key to put in .env as ENCRYPTION_KEY."""
    return Fernet.generate_key().decode()

"""
core/encryption/fields.py
──────────────────────────
Custom Django model field that transparently encrypts/decrypts text.
Store encrypted data in DB; read plain text in Python.

Usage in model:
    from core.encryption.fields import EncryptedTextField
    notes = EncryptedTextField(blank=True, null=True)
"""
from django.db import models
from . import encrypt, decrypt


class EncryptedTextField(models.TextField):
    """TextField that encrypts before save and decrypts on load."""

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return decrypt(value)

    def to_python(self, value):
        if value is None:
            return value
        # Already decrypted (in-memory)
        return value

    def get_prep_value(self, value):
        if value is None or value == '':
            return value
        # Encrypt only if not already encrypted (avoid double-encrypting)
        try:
            from cryptography.fernet import Fernet
            from . import _f
            _f().decrypt(value.encode())
            return value  # Already encrypted
        except Exception:
            return encrypt(value)

"""Password encryption utility.

Provides simple one-way encryption for passwords using SHA hashing.
"""

from __future__ import annotations

import base64
import hashlib


def encrypt_password(text: str, default_text: str | None = None) -> str:
    """Encrypt a password using SHA hashing and Base64 encoding.

    Parameters
    ----------
    text : str
        Text to encrypt
    default_text : str | None, optional
        Default text to return if encryption fails, by default None
        (uses text if None)

    Returns
    -------
    str
        Encrypted password (Base64-encoded SHA hash), or default_text if
        encryption fails
    """
    if default_text is None:
        default_text = text

    try:
        md = hashlib.sha1()
        md.update(text.encode("utf-8"))
        raw = md.digest()
        # Base64 encode without line breaks
        return base64.b64encode(raw).decode("ascii")
    except Exception:
        return default_text

"""Unique ID generator for form components.

Ensures unique IDs for dynamically generated form elements by maintaining
a set of used IDs and sanitizing input strings.

Converted from org.yawlfoundation.yawl.ui.dynform.IdGenerator
"""

from __future__ import annotations

import threading


class IdGenerator:
    """Thread-safe unique ID generator.

    Generates unique string IDs by sanitizing base strings and appending
    incrementing suffixes. Maintains a set of all used IDs to ensure uniqueness.

    Only letters, digits, underscores, and dashes are allowed in generated IDs.

    Thread Safety
    -------------
    Uses threading.Lock to ensure thread-safe ID generation and tracking.

    Examples
    --------
    >>> IdGenerator.uniquify("user-panel")
    'user-panel1'
    >>> IdGenerator.uniquify("user-panel")
    'user-panel2'
    >>> IdGenerator.uniquify("admin$panel")  # $ sanitized out
    'adminpanel1'
    """

    _used_ids: set[str] = set()
    _lock = threading.Lock()

    @classmethod
    def clear(cls) -> None:
        """Clear all tracked IDs.

        Resets the internal set of used IDs. Useful for test isolation
        or when starting a new form generation context.
        """
        with cls._lock:
            cls._used_ids.clear()

    @classmethod
    def uniquify(cls, base_id: str) -> str:
        """Generate unique ID from base string.

        Sanitizes the input by removing invalid characters, then appends
        an incrementing numeric suffix to ensure uniqueness.

        Parameters
        ----------
        base_id : str
            Base identifier (may contain invalid characters)

        Returns
        -------
        str
            Unique sanitized ID with numeric suffix (e.g., "panel1", "field2")

        Notes
        -----
        Valid characters are: letters, digits, underscores, dashes.
        Invalid characters (including $) are removed during sanitization.
        """
        with cls._lock:
            # Sanitize: only letters, digits, underscore, dash allowed
            # (equivalent to Java's isJavaIdentifierPart but excluding $)
            clean_chars = []
            for char in base_id:
                if char.isalnum() or char in ("_", "-"):
                    clean_chars.append(char)

            clean_id = "".join(clean_chars)

            # Find next available suffix
            suffix = 0
            while True:
                suffix += 1
                candidate = f"{clean_id}{suffix}"
                if candidate not in cls._used_ids:
                    cls._used_ids.add(candidate)
                    return candidate

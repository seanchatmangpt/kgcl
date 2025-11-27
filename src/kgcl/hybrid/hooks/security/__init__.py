"""Security utilities for knowledge hooks.

Provides error sanitization and information disclosure prevention.
"""

from __future__ import annotations

from kgcl.hybrid.hooks.security.error_sanitizer import ErrorSanitizer, SanitizationConfig

__all__ = ["ErrorSanitizer", "SanitizationConfig"]

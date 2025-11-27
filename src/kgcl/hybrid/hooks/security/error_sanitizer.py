"""Innovation #3: Error Sanitizer (UNRDF Port).

Prevents information disclosure in hook error messages by redacting
credentials, file paths, and other sensitive data patterns.

Architecture
------------
Ported from UNRDF JavaScript error handling, adapted for Python:
- Regex-based pattern matching for sensitive data
- Configurable redaction levels
- Stack trace sanitization

Examples
--------
>>> from kgcl.hybrid.hooks.security.error_sanitizer import ErrorSanitizer
>>> sanitizer = ErrorSanitizer()
>>> sanitizer.sanitize("password=secret123")
'password=[REDACTED]'

Database connection strings are redacted:

>>> sanitizer.sanitize("postgres://user:pass@localhost/db")
'postgres://[REDACTED]@localhost/db'
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RedactionLevel(Enum):
    """Levels of error sanitization.

    MINIMAL : Only credentials
    STANDARD : Credentials + file paths
    PARANOID : All potentially sensitive data
    """

    MINIMAL = "minimal"
    STANDARD = "standard"
    PARANOID = "paranoid"


@dataclass(frozen=True)
class SanitizationConfig:
    """Configuration for error sanitization.

    Parameters
    ----------
    level : RedactionLevel
        Redaction aggressiveness
    redact_file_paths : bool
        Whether to redact file paths
    redact_stack_traces : bool
        Whether to sanitize stack traces
    custom_patterns : list
        Additional regex patterns to redact

    Examples
    --------
    >>> config = SanitizationConfig(level=RedactionLevel.STANDARD)
    >>> config.redact_file_paths
    True
    """

    level: RedactionLevel = RedactionLevel.STANDARD
    redact_file_paths: bool = True
    redact_stack_traces: bool = True
    custom_patterns: tuple[str, ...] = ()


@dataclass
class ErrorSanitizer:
    """Sanitizes error messages to prevent information disclosure.

    Applies regex patterns to redact sensitive information from
    error messages before they are logged or returned to users.

    Attributes
    ----------
    config : SanitizationConfig
        Sanitization configuration
    _patterns : dict
        Compiled regex patterns by category

    Examples
    --------
    >>> sanitizer = ErrorSanitizer()
    >>> sanitizer.sanitize("API_KEY=abc123xyz")
    'API_KEY=[REDACTED]'
    """

    config: SanitizationConfig = field(default_factory=SanitizationConfig)

    def __post_init__(self) -> None:
        """Compile regex patterns on initialization."""
        self._patterns: dict[str, list[re.Pattern[str]]] = {
            "credentials": [
                # Key=value patterns
                re.compile(r"(password|api[_-]?key|secret|token|auth)\s*[:=]\s*\S+", re.IGNORECASE),
                # Database connection strings
                re.compile(r"(postgres|mysql|mongodb)://[^:]+:[^@]+@", re.IGNORECASE),
                # AWS credentials
                re.compile(r"AKIA[0-9A-Z]{16}", re.IGNORECASE),
                # Bearer tokens
                re.compile(r"Bearer\s+[A-Za-z0-9\-_.]+", re.IGNORECASE),
                # JWT patterns
                re.compile(r"eyJ[A-Za-z0-9\-_]+\.eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+"),
            ],
            "file_paths": [
                # Absolute paths with line numbers
                re.compile(r"/[a-zA-Z0-9_\-./]+\.py(?::\d+)?"),
                # Windows paths
                re.compile(r"[A-Z]:\\[a-zA-Z0-9_\-\\]+\.py(?::\d+)?"),
                # Home directory paths
                re.compile(r"~[/\\][a-zA-Z0-9_\-./\\]+"),
            ],
            "ip_addresses": [
                # IPv4
                re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
            ],
            "emails": [
                re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
            ],
        }

        # Add custom patterns
        if self.config.custom_patterns:
            self._patterns["custom"] = [re.compile(p) for p in self.config.custom_patterns]

    def sanitize(self, error: Exception | str) -> str:
        """Sanitize error message by redacting sensitive data.

        Parameters
        ----------
        error : Exception | str
            Error to sanitize

        Returns
        -------
        str
            Sanitized error message

        Examples
        --------
        >>> sanitizer = ErrorSanitizer()
        >>> sanitizer.sanitize("password=secret123")
        'password=[REDACTED]'

        >>> sanitizer.sanitize("Connected to postgres://admin:pass@db.example.com/mydb")
        'Connected to postgres://[REDACTED]@db.example.com/mydb'
        """
        message = str(error)
        return self._apply_patterns(message)

    def _apply_patterns(self, message: str) -> str:
        """Apply all relevant patterns based on config level.

        Parameters
        ----------
        message : str
            Message to sanitize

        Returns
        -------
        str
            Sanitized message
        """
        # Always apply credential patterns
        for pattern in self._patterns.get("credentials", []):
            message = self._redact_pattern(pattern, message)

        # Apply file paths at STANDARD and above
        if self.config.level in (RedactionLevel.STANDARD, RedactionLevel.PARANOID):
            if self.config.redact_file_paths:
                for pattern in self._patterns.get("file_paths", []):
                    message = pattern.sub("[PATH]", message)

        # Apply IP/email at PARANOID level
        if self.config.level == RedactionLevel.PARANOID:
            for pattern in self._patterns.get("ip_addresses", []):
                message = pattern.sub("[IP]", message)
            for pattern in self._patterns.get("emails", []):
                message = pattern.sub("[EMAIL]", message)

        # Apply custom patterns
        for pattern in self._patterns.get("custom", []):
            message = pattern.sub("[REDACTED]", message)

        return message

    def _redact_pattern(self, pattern: re.Pattern[str], message: str) -> str:
        """Redact matches while preserving key names.

        Parameters
        ----------
        pattern : re.Pattern
            Pattern to match
        message : str
            Message to redact

        Returns
        -------
        str
            Message with values redacted
        """

        def replace_value(match: re.Match[str]) -> str:
            text = match.group(0)
            # Preserve key name, redact value
            if "=" in text:
                key = text.split("=")[0]
                return f"{key}=[REDACTED]"
            if ":" in text and "@" in text:
                # Database URL - redact credentials portion
                before_at = text.split("@")[0]
                after_at = text.split("@")[1] if "@" in text else ""
                protocol = before_at.split("://")[0] if "://" in before_at else ""
                return f"{protocol}://[REDACTED]@{after_at}"
            return "[REDACTED]"

        return pattern.sub(replace_value, message)

    def sanitize_exception(self, exc: Exception) -> dict[str, Any]:
        """Sanitize exception with traceback.

        Parameters
        ----------
        exc : Exception
            Exception to sanitize

        Returns
        -------
        dict[str, Any]
            Sanitized exception info

        Examples
        --------
        >>> sanitizer = ErrorSanitizer()
        >>> try:
        ...     raise ValueError("password=secret")
        ... except Exception as e:
        ...     result = sanitizer.sanitize_exception(e)
        ...     'REDACTED' in result['message']
        True
        """
        import traceback

        result: dict[str, Any] = {
            "type": type(exc).__name__,
            "message": self.sanitize(str(exc)),
        }

        if self.config.redact_stack_traces:
            tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            result["traceback"] = self._apply_patterns(tb)

        return result

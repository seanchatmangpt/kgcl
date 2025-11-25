"""
Security Module - Error Sanitization.

Ported from UNRDF security/error-sanitizer.mjs.
Provides error sanitization to prevent information disclosure.
"""

import re
from dataclasses import dataclass


@dataclass
class SanitizedError:
    """
    Result of error sanitization.

    Parameters
    ----------
    message : str
        Sanitized error message safe for user display
    code : str
        Error code for debugging (e.g., INTERNAL_ERROR, VALIDATION_ERROR)
    is_user_safe : bool
        Whether this error is safe to display to end users
    """

    message: str
    code: str
    is_user_safe: bool = True


class ErrorSanitizer:
    """
    Sanitizes errors to prevent information disclosure.

    Removes sensitive information from error messages including:
    - File paths (/path/to/file.py)
    - Stack traces (File "...", line N)
    - Function names (in function_name)
    - Local variable references

    Preserves:
    - Error code for debugging
    - User-safe message structure
    """

    # Patterns that may leak sensitive information
    # Order matters: more specific patterns first
    SENSITIVE_PATTERNS = [
        r'File "[^"]+", line \d+',  # Stack traces (most specific first)
        r"/[a-z0-9_\-./]+\.py",  # Python file paths (Unix-style)
        r"/[a-z0-9_\-./]+",  # General Unix paths (includes /etc/passwd, /var/log, etc.)
        r"[A-Z]:[\\\/][a-z0-9_\-\\\/]+",  # Windows file paths
        r"in [a-z_][a-z0-9_]*",  # Function names with "in" prefix
        r"\b[a-z_][a-z0-9_]*\s*=",  # Variable assignments
        r"at line \d+",  # Line number references
        r"line \d+ in",  # Alternative line references
        r"line \d+",  # Standalone line numbers
        r"\bfunction [a-z_][a-z0-9_]*",  # Function names with "function" prefix
        r"\b[a-z_]+_[a-z0-9_]+\s*$",  # Snake_case identifiers at end (likely functions/vars)
    ]

    def sanitize(self, error: Exception) -> SanitizedError:
        """
        Remove sensitive details from error.

        Parameters
        ----------
        error : Exception
            Exception to sanitize

        Returns
        -------
        SanitizedError
            Sanitized error with safe message and error code
        """
        msg = str(error)

        # Apply regex patterns to remove sensitive info
        for pattern in self.SENSITIVE_PATTERNS:
            msg = re.sub(pattern, "[REDACTED]", msg, flags=re.IGNORECASE)

        # Get error code from exception if available
        code = getattr(error, "error_code", "INTERNAL_ERROR")

        # If no custom code, derive from exception type
        if code == "INTERNAL_ERROR":
            error_type = type(error).__name__
            code = error_type.upper().replace("ERROR", "").replace("EXCEPTION", "")
            if not code:
                code = "INTERNAL_ERROR"

        return SanitizedError(message=msg, code=code, is_user_safe=True)

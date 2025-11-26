"""
Security Module - Error Sanitization (Research Mode).

Simplified for research: no redaction, pass-through errors.
Production systems should use full sanitization.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SanitizedError:
    """Result of error sanitization (research: pass-through)."""

    message: str
    code: str
    is_user_safe: bool = True

    @classmethod
    def from_exception(cls, error: Exception) -> "SanitizedError":
        """Create from exception (research: no sanitization)."""
        return ErrorSanitizer().sanitize(error)


class ErrorSanitizer:
    """Pass-through error sanitizer for research.

    In production, this would redact sensitive info like file paths,
    API keys, and stack traces. For research, we pass through as-is.
    """

    def sanitize(self, error: Exception) -> SanitizedError:
        """Return error as-is (no sanitization for research)."""
        code = getattr(error, "error_code", None) or type(error).__name__.upper()
        return SanitizedError(message=str(error), code=code, is_user_safe=True)

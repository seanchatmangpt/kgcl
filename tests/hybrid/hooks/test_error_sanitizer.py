"""Tests for Innovation #3: Error Sanitizer.

Chicago School TDD: Real regex matching, no mocking.
Tests credential redaction, path sanitization, and exception handling.
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.hooks.security.error_sanitizer import (
    ErrorSanitizer,
    RedactionLevel,
    SanitizationConfig,
)


class TestSanitizationConfig:
    """Tests for sanitization configuration."""

    def test_default_config_is_standard(self) -> None:
        """Default config uses STANDARD redaction level."""
        config = SanitizationConfig()

        assert config.level == RedactionLevel.STANDARD
        assert config.redact_file_paths is True
        assert config.redact_stack_traces is True

    def test_custom_config(self) -> None:
        """Custom config values are stored."""
        config = SanitizationConfig(level=RedactionLevel.PARANOID, redact_file_paths=False)

        assert config.level == RedactionLevel.PARANOID
        assert config.redact_file_paths is False


class TestCredentialRedaction:
    """Tests for credential pattern redaction."""

    def test_password_equals_redacted(self) -> None:
        """password=value is redacted."""
        sanitizer = ErrorSanitizer()

        result = sanitizer.sanitize("Error: password=secret123")

        assert "secret123" not in result
        assert "REDACTED" in result

    def test_api_key_colon_redacted(self) -> None:
        """api_key: value is redacted."""
        sanitizer = ErrorSanitizer()

        result = sanitizer.sanitize("Config: api_key: abc123xyz")

        assert "abc123xyz" not in result
        assert "REDACTED" in result

    def test_token_redacted(self) -> None:
        """token=value is redacted."""
        sanitizer = ErrorSanitizer()

        result = sanitizer.sanitize("Auth token=eyJhbGciOiJIUzI1NiJ9")

        assert "eyJhbGciOiJIUzI1NiJ9" not in result

    def test_secret_redacted(self) -> None:
        """secret=value is redacted."""
        sanitizer = ErrorSanitizer()

        result = sanitizer.sanitize("secret=my_super_secret")

        assert "my_super_secret" not in result

    def test_case_insensitive_matching(self) -> None:
        """Credential patterns match case-insensitively."""
        sanitizer = ErrorSanitizer()

        result = sanitizer.sanitize("PASSWORD=secret API_KEY=key123")

        assert "secret" not in result
        assert "key123" not in result


class TestDatabaseConnectionRedaction:
    """Tests for database connection string redaction."""

    def test_postgres_connection_redacted(self) -> None:
        """PostgreSQL connection credentials are redacted."""
        sanitizer = ErrorSanitizer()

        result = sanitizer.sanitize("postgres://admin:password123@db.example.com/mydb")

        assert "password123" not in result
        assert "admin" not in result
        assert "db.example.com" in result  # Host preserved

    def test_mysql_connection_redacted(self) -> None:
        """MySQL connection credentials are redacted."""
        sanitizer = ErrorSanitizer()

        result = sanitizer.sanitize("mysql://root:rootpass@localhost/db")

        assert "rootpass" not in result
        assert "REDACTED" in result


class TestBearerTokenRedaction:
    """Tests for bearer token redaction."""

    def test_bearer_token_redacted(self) -> None:
        """Bearer tokens are redacted."""
        sanitizer = ErrorSanitizer()

        result = sanitizer.sanitize("Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")

        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result


class TestFilePathRedaction:
    """Tests for file path redaction at STANDARD level."""

    def test_python_path_redacted_standard(self) -> None:
        """Python file paths are redacted at STANDARD level."""
        sanitizer = ErrorSanitizer()

        result = sanitizer.sanitize("Error at /home/user/project/main.py:42")

        assert "/home/user/project/main.py" not in result
        assert "[PATH]" in result

    def test_path_not_redacted_minimal(self) -> None:
        """Paths are not redacted at MINIMAL level."""
        config = SanitizationConfig(level=RedactionLevel.MINIMAL)
        sanitizer = ErrorSanitizer(config=config)

        result = sanitizer.sanitize("Error at /home/user/project/main.py:42")

        assert "/home/user/project/main.py" in result


class TestParanoidLevel:
    """Tests for PARANOID redaction level."""

    def test_ip_address_redacted_paranoid(self) -> None:
        """IP addresses are redacted at PARANOID level."""
        config = SanitizationConfig(level=RedactionLevel.PARANOID)
        sanitizer = ErrorSanitizer(config=config)

        result = sanitizer.sanitize("Connected to 192.168.1.100:5432")

        assert "192.168.1.100" not in result
        assert "[IP]" in result

    def test_email_redacted_paranoid(self) -> None:
        """Email addresses are redacted at PARANOID level."""
        config = SanitizationConfig(level=RedactionLevel.PARANOID)
        sanitizer = ErrorSanitizer(config=config)

        result = sanitizer.sanitize("Contact: admin@example.com")

        assert "admin@example.com" not in result
        assert "[EMAIL]" in result


class TestCustomPatterns:
    """Tests for custom redaction patterns."""

    def test_custom_pattern_applied(self) -> None:
        """Custom regex patterns are applied."""
        config = SanitizationConfig(custom_patterns=(r"SSN:\s*\d{3}-\d{2}-\d{4}",))
        sanitizer = ErrorSanitizer(config=config)

        result = sanitizer.sanitize("User SSN: 123-45-6789")

        assert "123-45-6789" not in result


class TestExceptionSanitization:
    """Tests for exception object sanitization."""

    def test_exception_message_sanitized(self) -> None:
        """Exception message is sanitized."""
        sanitizer = ErrorSanitizer()

        try:
            raise ValueError("Connection failed: password=secret123")
        except ValueError as e:
            result = sanitizer.sanitize_exception(e)

        assert "secret123" not in result["message"]
        assert result["type"] == "ValueError"

    def test_exception_traceback_sanitized(self) -> None:
        """Exception traceback is sanitized."""
        sanitizer = ErrorSanitizer()

        try:
            raise ValueError("password=secret")
        except ValueError as e:
            result = sanitizer.sanitize_exception(e)

        assert "traceback" in result
        assert "secret" not in result["traceback"]


class TestSafeMessages:
    """Tests for messages that should not be modified."""

    def test_safe_message_unchanged(self) -> None:
        """Message without sensitive data is unchanged."""
        sanitizer = ErrorSanitizer()

        message = "Task completed successfully"
        result = sanitizer.sanitize(message)

        assert result == message

    def test_normal_error_preserved(self) -> None:
        """Normal error messages are preserved."""
        sanitizer = ErrorSanitizer()

        message = "Invalid input: expected integer"
        result = sanitizer.sanitize(message)

        assert result == message

"""
Comprehensive tests for security module.

Tests ErrorSanitizer, SandboxRestrictions, and lifecycle integration
following Chicago School TDD (no mocking domain objects).
"""

import pytest

from kgcl.hooks.conditions import Condition, ConditionResult
from kgcl.hooks.core import Hook
from kgcl.hooks.lifecycle import HookContext, HookExecutionPipeline
from kgcl.hooks.sandbox import SandboxRestrictions
from kgcl.hooks.security import ErrorSanitizer

# ============================================================================
# ErrorSanitizer Tests
# ============================================================================


def test_sanitize_removes_file_paths():
    """Test that file paths are redacted from error messages."""
    sanitizer = ErrorSanitizer()

    # Unix-style path
    error = Exception("Error in /usr/local/lib/python3.12/site-packages/kgcl/hooks.py")
    result = sanitizer.sanitize(error)

    assert "[REDACTED]" in result.message
    assert "/usr/local/lib" not in result.message
    assert result.is_user_safe


def test_sanitize_removes_windows_paths():
    """Test that Windows file paths are redacted."""
    sanitizer = ErrorSanitizer()

    error = Exception("Error in C:\\Users\\admin\\kgcl\\hooks.py line 42")
    result = sanitizer.sanitize(error)

    assert "[REDACTED]" in result.message
    assert "C:\\Users" not in result.message


def test_sanitize_removes_stack_traces():
    """Test that stack trace information is redacted."""
    sanitizer = ErrorSanitizer()

    error = Exception('File "/path/to/file.py", line 123, in execute_hook')
    result = sanitizer.sanitize(error)

    assert "[REDACTED]" in result.message
    assert '"/path/to/file.py"' not in result.message
    assert "line 123" not in result.message


def test_sanitize_removes_function_names():
    """Test that function names are redacted."""
    sanitizer = ErrorSanitizer()

    error = Exception("Error in execute_handler function")
    result = sanitizer.sanitize(error)

    assert "[REDACTED]" in result.message
    assert "execute_handler" not in result.message


def test_sanitize_preserves_error_code():
    """Test that error codes are preserved."""
    sanitizer = ErrorSanitizer()

    error = ValueError("Invalid input at /tmp/file.py")
    error.error_code = "VALIDATION_ERROR"

    result = sanitizer.sanitize(error)

    assert result.code == "VALIDATION_ERROR"
    assert result.is_user_safe


def test_sanitize_preserves_message_structure():
    """Test that the general message structure remains readable."""
    sanitizer = ErrorSanitizer()

    error = Exception("Hook execution failed: timeout exceeded")
    result = sanitizer.sanitize(error)

    assert "Hook execution failed" in result.message
    assert "timeout exceeded" in result.message


def test_custom_error_code():
    """Test custom error_code attribute."""
    sanitizer = ErrorSanitizer()

    class CustomError(Exception):
        """Test-specific custom error with error_code attribute."""

        def __init__(self, message: str, error_code: str | None = None) -> None:
            """Initialize CustomError.

            Parameters
            ----------
            message : str
                Error message
            error_code : str, optional
                Error code for categorization
            """
            self.error_code = error_code
            super().__init__(message)

    error = CustomError("Something went wrong", error_code="CUSTOM_FAILURE")

    result = sanitizer.sanitize(error)

    assert result.code == "CUSTOM_FAILURE"


def test_unicode_handling():
    """Test that non-ASCII characters are handled correctly."""
    sanitizer = ErrorSanitizer()

    error = Exception("Error: 文件不存在 in /path/to/file.py")
    result = sanitizer.sanitize(error)

    assert "文件不存在" in result.message
    assert "[REDACTED]" in result.message


def test_multiple_sensitive_patterns():
    """Test multiple sensitive patterns in a single error."""
    sanitizer = ErrorSanitizer()

    error = Exception(
        'File "/usr/lib/hooks.py", line 42, in execute_hook: variable_name = invalid_value'
    )
    result = sanitizer.sanitize(error)

    # All sensitive parts should be redacted
    assert "/usr/lib/hooks.py" not in result.message
    assert "line 42" not in result.message
    assert "execute_hook" not in result.message
    assert "variable_name" not in result.message
    assert "[REDACTED]" in result.message


def test_derived_error_code_from_exception_type():
    """Test that error code is derived from exception type if not set."""
    sanitizer = ErrorSanitizer()

    error = ValueError("Invalid value")
    result = sanitizer.sanitize(error)

    # Should derive code from ValueError
    assert result.code == "VALUE"


# ============================================================================
# SandboxRestrictions Tests
# ============================================================================


def test_validate_allowed_path():
    """Test that allowed paths are validated correctly."""
    sandbox = SandboxRestrictions(allowed_paths=["/tmp", "/var/log"])

    assert sandbox.validate_path("/tmp/test.txt")
    assert sandbox.validate_path("/tmp/subdir/file.txt")
    assert sandbox.validate_path("/var/log/app.log")


def test_validate_disallowed_path():
    """Test that disallowed paths are rejected."""
    sandbox = SandboxRestrictions(allowed_paths=["/tmp"])

    assert not sandbox.validate_path("/etc/passwd")
    assert not sandbox.validate_path("/home/user/secrets")
    assert not sandbox.validate_path("/root/.ssh/id_rsa")


def test_validate_path_normalization():
    """Test that different path formats are normalized correctly."""
    sandbox = SandboxRestrictions(allowed_paths=["/tmp"])

    # Various path formats that resolve to same location
    assert sandbox.validate_path("/tmp/./file.txt")
    assert sandbox.validate_path("/tmp//file.txt")

    # Path traversal should not escape allowed path
    assert not sandbox.validate_path("/tmp/../etc/passwd")


def test_validate_restrictions_valid():
    """Test that valid configuration passes validation."""
    sandbox = SandboxRestrictions(
        allowed_paths=["/tmp"],
        memory_limit_mb=512,
        timeout_ms=30000,
        max_open_files=100,
    )

    assert sandbox.validate_restrictions()


def test_validate_restrictions_invalid():
    """Test that invalid configurations fail validation."""
    # No allowed paths
    sandbox = SandboxRestrictions(allowed_paths=[])
    assert not sandbox.validate_restrictions()

    # Invalid memory limit
    sandbox = SandboxRestrictions(allowed_paths=["/tmp"], memory_limit_mb=0)
    assert not sandbox.validate_restrictions()

    # Invalid timeout
    sandbox = SandboxRestrictions(allowed_paths=["/tmp"], timeout_ms=-1)
    assert not sandbox.validate_restrictions()

    # Invalid max_open_files
    sandbox = SandboxRestrictions(allowed_paths=["/tmp"], max_open_files=0)
    assert not sandbox.validate_restrictions()


def test_symlink_handling(tmp_path):
    """Test that symbolic links are handled safely."""
    # Create a symlink in allowed directory pointing to disallowed location
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()

    disallowed_dir = tmp_path / "disallowed"
    disallowed_dir.mkdir()

    symlink = allowed_dir / "link"
    try:
        symlink.symlink_to(disallowed_dir)
    except OSError:
        # Symlink creation might fail on some platforms
        pytest.skip("Symlink creation not supported")

    sandbox = SandboxRestrictions(allowed_paths=[str(allowed_dir)])

    # Symlink should resolve to actual target
    # and be rejected if target is outside allowed paths
    assert not sandbox.validate_path(str(symlink / "secret.txt"))


def test_empty_allowed_paths():
    """Test that empty paths list denies all access."""
    sandbox = SandboxRestrictions(allowed_paths=[])

    assert not sandbox.validate_path("/tmp/file.txt")
    assert not sandbox.validate_path("/any/path")


def test_read_only_flag():
    """Test read-only flag is preserved."""
    sandbox = SandboxRestrictions(allowed_paths=["/tmp"], read_only=True)

    assert sandbox.read_only
    assert sandbox.validate_path("/tmp/file.txt")


def test_network_restrictions():
    """Test network restriction flags."""
    sandbox = SandboxRestrictions(allowed_paths=["/tmp"], no_network=True)
    assert sandbox.no_network

    sandbox_with_network = SandboxRestrictions(allowed_paths=["/tmp"], no_network=False)
    assert not sandbox_with_network.no_network


def test_process_spawn_restrictions():
    """Test process spawn restriction flags."""
    sandbox = SandboxRestrictions(allowed_paths=["/tmp"], no_process_spawn=True)
    assert sandbox.no_process_spawn

    sandbox_with_spawn = SandboxRestrictions(
        allowed_paths=["/tmp"], no_process_spawn=False
    )
    assert not sandbox_with_spawn.no_process_spawn


# ============================================================================
# Lifecycle Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_error_sanitization_on_execute():
    """Test that errors are sanitized during hook execution."""
    pipeline = HookExecutionPipeline()

    # Create a hook that raises an error with sensitive info
    def failing_handler(context):
        raise ValueError("Error in /usr/local/lib/python3.12/hooks.py line 42")

    class AlwaysTrueCondition(Condition):
        async def evaluate(self, context):
            return ConditionResult(triggered=True, metadata={})

    hook = Hook(
        name="test_hook",
        description="Test hook that fails",
        condition=AlwaysTrueCondition(),
        handler=failing_handler,
    )

    receipt = await pipeline.execute(hook, {"data": "test"})

    # Error should be present and sanitized
    assert receipt.error is not None
    assert "[REDACTED]" in receipt.error
    assert "/usr/local/lib" not in receipt.error
    assert "line 42" not in receipt.error


@pytest.mark.asyncio
async def test_execution_id_generation():
    """Test that each execution gets a unique ID."""
    context1 = HookContext(actor="user1")
    context2 = HookContext(actor="user2")

    # Each context should have a unique execution_id
    assert context1.execution_id != context2.execution_id
    assert len(context1.execution_id) > 0
    assert len(context2.execution_id) > 0


@pytest.mark.asyncio
async def test_receipt_contains_sanitized_error():
    """Test that receipts store sanitized errors."""
    pipeline = HookExecutionPipeline()

    def handler_with_path_error(context):
        raise RuntimeError("Failed to read /etc/passwd in function validate_user")

    class AlwaysTrueCondition(Condition):
        async def evaluate(self, context):
            return ConditionResult(triggered=True, metadata={})

    hook = Hook(
        name="secure_hook",
        description="Hook with error sanitization",
        condition=AlwaysTrueCondition(),
        handler=handler_with_path_error,
    )

    receipt = await pipeline.execute(hook, {"data": "test"})

    # Receipt should contain sanitized error
    assert receipt.error is not None
    assert "/etc/passwd" not in receipt.error
    assert "validate_user" not in receipt.error
    assert "[REDACTED]" in receipt.error


@pytest.mark.asyncio
async def test_error_code_preserved_in_receipt():
    """Test that error codes are preserved in receipts."""
    pipeline = HookExecutionPipeline()

    def handler_with_custom_error(context):
        error = ValueError("Invalid input at /tmp/data.json")
        error.error_code = "INVALID_INPUT"
        raise error

    class AlwaysTrueCondition(Condition):
        async def evaluate(self, context):
            return ConditionResult(triggered=True, metadata={})

    hook = Hook(
        name="validation_hook",
        description="Hook with validation error",
        condition=AlwaysTrueCondition(),
        handler=handler_with_custom_error,
    )
    hook.error_code = "VALIDATION_FAILED"

    receipt = await pipeline.execute(hook, {"data": "test"})

    # Error code should be in metadata
    assert "error_code" in receipt.metadata
    assert receipt.metadata["sanitized"] is True


@pytest.mark.asyncio
async def test_stack_trace_removed():
    """Test that stack traces are removed for security."""
    pipeline = HookExecutionPipeline()

    def handler_with_exception(context):
        raise RuntimeError("Critical error in /opt/app/handler.py")

    class AlwaysTrueCondition(Condition):
        async def evaluate(self, context):
            return ConditionResult(triggered=True, metadata={})

    hook = Hook(
        name="failing_hook",
        description="Hook that fails with stack trace",
        condition=AlwaysTrueCondition(),
        handler=handler_with_exception,
    )

    receipt = await pipeline.execute(hook, {"data": "test"})

    # Stack trace should be removed
    assert receipt.stack_trace is None
    assert receipt.error is not None


@pytest.mark.asyncio
async def test_successful_execution_unchanged():
    """Test that successful executions are not affected by sanitization."""
    pipeline = HookExecutionPipeline()

    def successful_handler(context):
        return {"status": "success", "data": context.get("input")}

    class AlwaysTrueCondition(Condition):
        async def evaluate(self, context):
            return ConditionResult(triggered=True, metadata={})

    hook = Hook(
        name="success_hook",
        description="Hook that succeeds",
        condition=AlwaysTrueCondition(),
        handler=successful_handler,
    )

    receipt = await pipeline.execute(hook, {"input": "test_data"})

    # Successful execution should not be affected
    assert receipt.error is None
    assert receipt.handler_result is not None
    assert receipt.handler_result["status"] == "success"
    assert receipt.handler_result["data"] == "test_data"


@pytest.mark.asyncio
async def test_sanitization_metadata_added():
    """Test that sanitization metadata is added to receipts."""
    pipeline = HookExecutionPipeline()

    def failing_handler(context):
        raise ValueError("Error in /var/log/app.log")

    class AlwaysTrueCondition(Condition):
        async def evaluate(self, context):
            return ConditionResult(triggered=True, metadata={})

    hook = Hook(
        name="metadata_hook",
        description="Hook to test metadata",
        condition=AlwaysTrueCondition(),
        handler=failing_handler,
    )

    receipt = await pipeline.execute(hook, {"data": "test"})

    # Sanitization metadata should be present
    assert "sanitized" in receipt.metadata
    assert receipt.metadata["sanitized"] is True
    assert "error_code" in receipt.metadata

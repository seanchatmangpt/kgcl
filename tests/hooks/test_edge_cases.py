"""Tests for edge_cases module."""

import pytest

from kgcl.hooks.edge_cases import EdgeCaseHandler


class TestEdgeCaseHandler:
    """Test EdgeCaseHandler class."""

    def test_initialization(self):
        """Test handler initialization."""
        handler = EdgeCaseHandler()
        assert len(handler.handlers) > 0
        # Check default handlers are registered
        assert "empty_result" in handler.handlers
        assert "null_value" in handler.handlers
        assert "timeout" in handler.handlers
        assert "memory_pressure" in handler.handlers

    def test_register_custom_handler(self):
        """Test registering custom handler."""
        handler = EdgeCaseHandler()

        def custom_handler(context):
            return "custom_result"

        handler.register_handler("custom_case", custom_handler)
        assert handler.has_handler("custom_case")

    def test_unregister_handler(self):
        """Test unregistering handler."""
        handler = EdgeCaseHandler()

        def custom_handler(context):
            return "test"

        handler.register_handler("test_case", custom_handler)
        assert handler.has_handler("test_case")

        removed = handler.unregister_handler("test_case")
        assert removed is True
        assert not handler.has_handler("test_case")

    def test_unregister_nonexistent_handler(self):
        """Test unregistering nonexistent handler."""
        handler = EdgeCaseHandler()
        removed = handler.unregister_handler("nonexistent")
        assert removed is False

    def test_has_handler(self):
        """Test checking if handler exists."""
        handler = EdgeCaseHandler()
        assert handler.has_handler("empty_result") is True
        assert handler.has_handler("nonexistent") is False

    def test_handle_unknown_case(self):
        """Test handling unknown case raises error."""
        handler = EdgeCaseHandler()
        with pytest.raises(ValueError, match="Unknown edge case"):
            handler.handle_case("unknown_case")

    def test_handle_custom_case(self):
        """Test handling custom case."""
        handler = EdgeCaseHandler()

        def custom_handler(context):
            return f"Handled: {context.get('value')}"

        handler.register_handler("custom", custom_handler)
        result = handler.handle_case("custom", {"value": "test"})
        assert result == "Handled: test"

    def test_handle_empty_result(self):
        """Test handling empty result."""
        handler = EdgeCaseHandler()
        result = handler.handle_case("empty_result", {"query": "SELECT * FROM users"})
        assert result is None

    def test_handle_empty_result_with_default(self):
        """Test handling empty result with default value."""
        handler = EdgeCaseHandler()
        result = handler.handle_case(
            "empty_result", {"query": "SELECT * FROM users", "default": []}
        )
        assert result == []

    def test_handle_null_value(self):
        """Test handling null value."""
        handler = EdgeCaseHandler()
        result = handler.handle_case("null_value", {"field": "email"})
        assert result is None

    def test_handle_null_value_with_default(self):
        """Test handling null value with default."""
        handler = EdgeCaseHandler()
        result = handler.handle_case(
            "null_value", {"field": "email", "default": "unknown@example.com"}
        )
        assert result == "unknown@example.com"

    def test_handle_timeout(self):
        """Test handling timeout."""
        handler = EdgeCaseHandler()
        result = handler.handle_case(
            "timeout", {"operation": "database_query", "timeout_seconds": 30}
        )
        assert result is None

    def test_handle_memory_pressure(self):
        """Test handling memory pressure."""
        handler = EdgeCaseHandler()
        result = handler.handle_case(
            "memory_pressure", {"threshold": "80%", "current_usage": "85%"}
        )
        assert result is None

    def test_handle_rate_limit(self):
        """Test handling rate limit."""
        handler = EdgeCaseHandler()
        result = handler.handle_case("rate_limit", {"limit": 100, "window": 60, "retry_after": 30})
        assert isinstance(result, dict)
        assert result["should_retry"] is True
        assert result["retry_after_seconds"] == 30
        assert result["limit"] == 100
        assert result["window"] == 60

    def test_handle_rate_limit_default_retry(self):
        """Test handling rate limit with default retry."""
        handler = EdgeCaseHandler()
        result = handler.handle_case("rate_limit", {"limit": 100, "window": 60})
        assert result["retry_after_seconds"] == 60  # Default

    def test_handle_invalid_input(self):
        """Test handling invalid input."""
        handler = EdgeCaseHandler()
        result = handler.handle_case(
            "invalid_input", {"input": "abc", "expected": "integer", "reason": "not a number"}
        )
        assert result is None

    def test_handle_connection_error(self):
        """Test handling connection error."""
        handler = EdgeCaseHandler()
        result = handler.handle_case(
            "connection_error",
            {"host": "database.example.com", "port": 5432, "error": "Connection refused"},
        )
        assert isinstance(result, dict)
        assert result["should_retry"] is True
        assert result["host"] == "database.example.com"
        assert result["port"] == 5432

    def test_handle_connection_error_custom_retry(self):
        """Test handling connection error with custom retry."""
        handler = EdgeCaseHandler()
        result = handler.handle_case(
            "connection_error",
            {"host": "api.example.com", "port": 443, "error": "Timeout", "retry_after": 10},
        )
        assert result["retry_after_seconds"] == 10

    def test_handle_resource_exhausted(self):
        """Test handling resource exhaustion."""
        handler = EdgeCaseHandler()
        result = handler.handle_case(
            "resource_exhausted", {"resource": "file_descriptors", "limit": 1024, "requested": 1050}
        )
        assert result is None

    def test_handle_case_without_context(self):
        """Test handling case without context."""
        handler = EdgeCaseHandler()
        result = handler.handle_case("empty_result")
        assert result is None

    def test_override_default_handler(self):
        """Test overriding default handler."""
        handler = EdgeCaseHandler()

        def custom_empty_handler(context):
            return "custom_empty"

        handler.register_handler("empty_result", custom_empty_handler)
        result = handler.handle_case("empty_result", {"query": "test"})
        assert result == "custom_empty"

    def test_handler_with_complex_context(self):
        """Test handler with complex context."""
        handler = EdgeCaseHandler()

        def complex_handler(context):
            metrics = context.get("metrics", {})
            threshold = context.get("threshold", 100)
            return sum(metrics.values()) > threshold

        handler.register_handler("check_metrics", complex_handler)
        result = handler.handle_case(
            "check_metrics", {"metrics": {"cpu": 50, "memory": 60}, "threshold": 100}
        )
        assert result is True

    def test_multiple_handlers_registered(self):
        """Test registering multiple custom handlers."""
        handler = EdgeCaseHandler()

        handlers_to_add = {
            "case1": lambda ctx: "result1",
            "case2": lambda ctx: "result2",
            "case3": lambda ctx: "result3",
        }

        for case, func in handlers_to_add.items():
            handler.register_handler(case, func)

        assert handler.handle_case("case1") == "result1"
        assert handler.handle_case("case2") == "result2"
        assert handler.handle_case("case3") == "result3"

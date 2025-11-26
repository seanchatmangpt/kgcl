"""Edge Case Handler - Gracefully handle edge cases.

Provides centralized handling of common edge cases in data processing,
API calls, and system operations.
"""

import logging
from collections.abc import Callable
from typing import Any


class EdgeCaseHandler:
    """Handle edge cases gracefully with configurable handlers.

    Provides default handlers for common edge cases and allows
    registration of custom handlers for application-specific scenarios.
    """

    def __init__(self, log_level: int = logging.WARNING):
        """Initialize edge case handler.

        Args:
            log_level: Default logging level for edge cases
        """
        self.handlers: dict[str, Callable[..., Any]] = {}
        self._logger = logging.getLogger(__name__)
        self._logger.setLevel(log_level)
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Register handlers for common edge cases."""
        self.handlers["empty_result"] = self._handle_empty_result
        self.handlers["null_value"] = self._handle_null_value
        self.handlers["timeout"] = self._handle_timeout
        self.handlers["memory_pressure"] = self._handle_memory_pressure
        self.handlers["rate_limit"] = self._handle_rate_limit
        self.handlers["invalid_input"] = self._handle_invalid_input
        self.handlers["connection_error"] = self._handle_connection_error
        self.handlers["resource_exhausted"] = self._handle_resource_exhausted

    def register_handler(self, case: str, handler: Callable) -> None:
        """Register custom edge case handler.

        Args:
            case: Edge case identifier
            handler: Callable that takes context dict and returns result
        """
        self.handlers[case] = handler
        self._logger.debug(f"Registered handler for edge case: {case}")

    def unregister_handler(self, case: str) -> bool:
        """Unregister an edge case handler.

        Args:
            case: Edge case identifier

        Returns
        -------
            True if handler was found and removed
        """
        if case in self.handlers:
            del self.handlers[case]
            return True
        return False

    def handle_case(self, case: str, context: dict[str, Any] | None = None) -> Any:
        """Handle edge case with context.

        Args:
            case: Edge case identifier
            context: Context dictionary with case-specific data

        Returns
        -------
            Result from handler

        Raises
        ------
            ValueError: If edge case has no registered handler
        """
        if context is None:
            context = {}

        if case not in self.handlers:
            raise ValueError(f"Unknown edge case: {case}")

        return self.handlers[case](context)

    def has_handler(self, case: str) -> bool:
        """Check if handler exists for edge case.

        Args:
            case: Edge case identifier

        Returns
        -------
            True if handler is registered
        """
        return case in self.handlers

    # Default handlers

    def _handle_empty_result(self, context: dict[str, Any]) -> None:
        """Handle empty query result.

        Args:
            context: Should contain 'query' or 'operation' key

        Returns
        -------
            None or default value from context
        """
        operation = context.get("query") or context.get("operation", "unknown")
        self._logger.warning(f"Empty result for: {operation}")
        return context.get("default")

    def _handle_null_value(self, context: dict[str, Any]) -> Any:
        """Handle null/None value.

        Args:
            context: Should contain 'field' and optionally 'default'

        Returns
        -------
            Default value from context or None
        """
        field = context.get("field", "unknown")
        self._logger.warning(f"Null value in field: {field}")
        return context.get("default")

    def _handle_timeout(self, context: dict[str, Any]) -> None:
        """Handle operation timeout.

        Args:
            context: Should contain 'operation' and optionally 'timeout_seconds'

        Returns
        -------
            None
        """
        operation = context.get("operation", "unknown")
        timeout = context.get("timeout_seconds", "unknown")
        self._logger.error(f"Timeout on {operation} (timeout={timeout}s)")

    def _handle_memory_pressure(self, context: dict[str, Any]) -> None:
        """Handle memory pressure situation.

        Args:
            context: Should contain 'threshold' or 'current_usage'

        Returns
        -------
            None
        """
        threshold = context.get("threshold", "unknown")
        current = context.get("current_usage", "unknown")
        self._logger.critical(
            f"Memory pressure detected (current={current}, threshold={threshold})"
        )
        # In real implementation, this would trigger cache cleanup, etc.

    def _handle_rate_limit(self, context: dict[str, Any]) -> dict[str, Any]:
        """Handle rate limit exceeded.

        Args:
            context: Should contain 'limit', 'window', 'retry_after'

        Returns
        -------
            Dictionary with retry information
        """
        limit = context.get("limit", "unknown")
        window = context.get("window", "unknown")
        retry_after = context.get("retry_after", 60)

        self._logger.warning(
            f"Rate limit exceeded (limit={limit}/{window}s), retry after {retry_after}s"
        )

        return {
            "should_retry": True,
            "retry_after_seconds": retry_after,
            "limit": limit,
            "window": window,
        }

    def _handle_invalid_input(self, context: dict[str, Any]) -> None:
        """Handle invalid input data.

        Args:
            context: Should contain 'input', 'expected', 'reason'

        Returns
        -------
            None
        """
        input_val = context.get("input", "unknown")
        expected = context.get("expected", "valid data")
        reason = context.get("reason", "validation failed")

        self._logger.error(
            f"Invalid input: {input_val} (expected {expected}): {reason}"
        )

    def _handle_connection_error(self, context: dict[str, Any]) -> dict[str, Any]:
        """Handle connection error.

        Args:
            context: Should contain 'host', 'port', 'error'

        Returns
        -------
            Dictionary with retry information
        """
        host = context.get("host", "unknown")
        port = context.get("port", "unknown")
        error = context.get("error", "connection failed")

        self._logger.error(f"Connection error to {host}:{port} - {error}")

        return {
            "should_retry": True,
            "retry_after_seconds": context.get("retry_after", 5),
            "host": host,
            "port": port,
            "error": str(error),
        }

    def _handle_resource_exhausted(self, context: dict[str, Any]) -> None:
        """Handle resource exhaustion.

        Args:
            context: Should contain 'resource', 'limit', 'requested'

        Returns
        -------
            None
        """
        resource = context.get("resource", "unknown")
        limit = context.get("limit", "unknown")
        requested = context.get("requested", "unknown")

        self._logger.critical(
            f"Resource exhausted: {resource} (limit={limit}, requested={requested})"
        )

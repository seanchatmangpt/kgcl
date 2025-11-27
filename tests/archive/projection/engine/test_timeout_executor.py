"""Tests for timeout executor - Thread-based query timeout.

Chicago School TDD: Test behavior through state verification.
"""

from __future__ import annotations

import time

import pytest

from kgcl.projection.domain.exceptions import QueryTimeoutError
from kgcl.projection.engine.timeout_executor import execute_with_timeout

# Timeout tests actually wait for timeouts - mark as slow
pytestmark = pytest.mark.slow


class TestExecuteWithTimeout:
    """Tests for execute_with_timeout function."""

    def test_fast_function_returns_result(self) -> None:
        """Fast function returns result within timeout."""
        def fast() -> str:
            return "done"

        result = execute_with_timeout(fast, timeout_seconds=1.0)

        assert result == "done"

    def test_slow_function_raises_timeout(self) -> None:
        """Slow function raises QueryTimeoutError."""
        def slow() -> str:
            time.sleep(1.0)
            return "done"

        with pytest.raises(QueryTimeoutError) as exc:
            execute_with_timeout(slow, timeout_seconds=0.05, query_name="test_query")

        assert exc.value.query_name == "test_query"
        assert exc.value.timeout_seconds == 0.05

    def test_function_just_under_timeout(self) -> None:
        """Function completing just under timeout succeeds."""
        def quick() -> str:
            time.sleep(0.01)
            return "done"

        result = execute_with_timeout(quick, timeout_seconds=0.5)

        assert result == "done"

    def test_function_returning_list(self) -> None:
        """Functions returning complex types work correctly."""
        def returns_list() -> list[dict[str, str]]:
            return [{"name": "Alice"}, {"name": "Bob"}]

        result = execute_with_timeout(returns_list, timeout_seconds=1.0)

        assert len(result) == 2
        assert result[0]["name"] == "Alice"

    def test_function_raising_exception(self) -> None:
        """Exceptions from function propagate correctly."""
        def raises() -> str:
            msg = "Test error"
            raise ValueError(msg)

        with pytest.raises(ValueError, match="Test error"):
            execute_with_timeout(raises, timeout_seconds=1.0)

    def test_default_query_name(self) -> None:
        """Default query_name is 'unnamed'."""
        def slow() -> str:
            time.sleep(1.0)
            return "done"

        with pytest.raises(QueryTimeoutError) as exc:
            execute_with_timeout(slow, timeout_seconds=0.01)

        assert exc.value.query_name == "unnamed"

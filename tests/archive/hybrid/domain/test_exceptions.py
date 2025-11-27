"""Tests for hybrid engine exceptions.

Tests verify exception creation, attributes, and message formatting.
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.domain.exceptions import ConvergenceError, HybridEngineError, ReasonerError, StoreOperationError


class TestHybridEngineError:
    """Tests for base exception class."""

    def test_is_exception(self) -> None:
        """HybridEngineError is an Exception."""
        assert issubclass(HybridEngineError, Exception)

    def test_can_raise(self) -> None:
        """HybridEngineError can be raised and caught."""
        with pytest.raises(HybridEngineError):
            raise HybridEngineError("Test error")

    def test_catches_subclasses(self) -> None:
        """HybridEngineError catches all domain exceptions."""
        with pytest.raises(HybridEngineError):
            raise ConvergenceError(max_ticks=10, final_delta=5)


class TestConvergenceError:
    """Tests for ConvergenceError."""

    def test_stores_max_ticks(self) -> None:
        """ConvergenceError stores max_ticks attribute."""
        exc = ConvergenceError(max_ticks=100, final_delta=5)
        assert exc.max_ticks == 100

    def test_stores_final_delta(self) -> None:
        """ConvergenceError stores final_delta attribute."""
        exc = ConvergenceError(max_ticks=100, final_delta=5)
        assert exc.final_delta == 5

    def test_message_format(self) -> None:
        """ConvergenceError formats message correctly."""
        exc = ConvergenceError(max_ticks=100, final_delta=5)
        message = str(exc)

        assert "100 ticks" in message
        assert "Final delta: 5" in message

    def test_is_hybrid_engine_error(self) -> None:
        """ConvergenceError is a HybridEngineError."""
        assert issubclass(ConvergenceError, HybridEngineError)


class TestReasonerError:
    """Tests for ReasonerError."""

    def test_stores_command(self) -> None:
        """ReasonerError stores command attribute."""
        exc = ReasonerError("Error", command="eye --nope")
        assert exc.command == "eye --nope"

    def test_command_optional(self) -> None:
        """ReasonerError command is optional."""
        exc = ReasonerError("Error")
        assert exc.command is None

    def test_message_preserved(self) -> None:
        """ReasonerError preserves message."""
        exc = ReasonerError("EYE timed out")
        assert "EYE timed out" in str(exc)

    def test_is_hybrid_engine_error(self) -> None:
        """ReasonerError is a HybridEngineError."""
        assert issubclass(ReasonerError, HybridEngineError)


class TestStoreOperationError:
    """Tests for StoreOperationError."""

    def test_stores_operation(self) -> None:
        """StoreOperationError stores operation attribute."""
        exc = StoreOperationError("load", "Invalid syntax")
        assert exc.operation == "load"

    def test_message_includes_operation(self) -> None:
        """StoreOperationError includes operation in message."""
        exc = StoreOperationError("load", "Invalid syntax")
        message = str(exc)

        assert "load" in message
        assert "Invalid syntax" in message

    def test_is_hybrid_engine_error(self) -> None:
        """StoreOperationError is a HybridEngineError."""
        assert issubclass(StoreOperationError, HybridEngineError)

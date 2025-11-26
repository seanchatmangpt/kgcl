"""Tests for monitoring module (Andon signals)."""

from datetime import datetime

import pytest

from kgcl.hooks.monitoring import AndonBoard, AndonSignal, SignalSeverity


class TestAndonSignal:
    """Test AndonSignal class."""

    def test_create_basic_signal(self):
        """Test creating basic signal."""
        signal = AndonSignal(
            severity=SignalSeverity.WARNING,
            message="Test warning",
            source="test_module",
        )
        assert signal.severity == SignalSeverity.WARNING
        assert signal.message == "Test warning"
        assert signal.source == "test_module"
        assert signal.auto_stop is False
        assert isinstance(signal.timestamp, datetime)

    def test_create_signal_with_auto_stop(self):
        """Test creating signal with auto_stop."""
        signal = AndonSignal(
            severity=SignalSeverity.CRITICAL,
            message="Critical error",
            source="database",
            auto_stop=True,
        )
        assert signal.auto_stop is True

    def test_create_signal_with_metadata(self):
        """Test creating signal with metadata."""
        metadata = {"error_code": 500, "retries": 3}
        signal = AndonSignal(
            severity=SignalSeverity.ERROR,
            message="Request failed",
            source="api",
            metadata=metadata,
        )
        assert signal.metadata == metadata

    def test_invalid_severity_raises_error(self):
        """Test that invalid severity raises ValueError."""
        with pytest.raises(ValueError, match="Invalid severity"):
            AndonSignal(
                severity="invalid",  # type: ignore
                message="Test",
                source="test",
            )

    def test_empty_message_raises_error(self):
        """Test that empty message raises ValueError."""
        with pytest.raises(ValueError, match="message cannot be empty"):
            AndonSignal(severity=SignalSeverity.INFO, message="", source="test")

    def test_empty_source_raises_error(self):
        """Test that empty source raises ValueError."""
        with pytest.raises(ValueError, match="source cannot be empty"):
            AndonSignal(severity=SignalSeverity.INFO, message="Test", source="")


class TestAndonBoard:
    """Test AndonBoard class."""

    def test_create_board(self):
        """Test creating Andon board."""
        board = AndonBoard()
        assert len(board.signals) == 0
        assert not board.is_stopped()

    def test_raise_signal(self):
        """Test raising a signal."""
        board = AndonBoard()
        signal = AndonSignal(
            severity=SignalSeverity.INFO, message="Test info", source="test"
        )
        board.raise_signal(signal)
        assert len(board.signals) == 1
        assert board.signals[0] == signal

    def test_raise_multiple_signals(self):
        """Test raising multiple signals."""
        board = AndonBoard()
        for i in range(5):
            signal = AndonSignal(
                severity=SignalSeverity.INFO, message=f"Test {i}", source="test"
            )
            board.raise_signal(signal)
        assert len(board.signals) == 5

    def test_max_signals_limit(self):
        """Test that signals are limited to max_signals."""
        board = AndonBoard(max_signals=10)
        for i in range(15):
            signal = AndonSignal(
                severity=SignalSeverity.INFO, message=f"Test {i}", source="test"
            )
            board.raise_signal(signal)
        assert len(board.signals) == 10
        # Should keep most recent signals
        assert board.signals[0].message == "Test 5"
        assert board.signals[-1].message == "Test 14"

    def test_auto_stop_signal(self):
        """Test that auto_stop signal stops the board."""
        board = AndonBoard()
        signal = AndonSignal(
            severity=SignalSeverity.CRITICAL,
            message="Critical failure",
            source="system",
            auto_stop=True,
        )
        board.raise_signal(signal)
        assert board.is_stopped()

    def test_reset_stop(self):
        """Test resetting stopped state."""
        board = AndonBoard()
        signal = AndonSignal(
            severity=SignalSeverity.CRITICAL,
            message="Critical failure",
            source="system",
            auto_stop=True,
        )
        board.raise_signal(signal)
        assert board.is_stopped()
        board.reset_stop()
        assert not board.is_stopped()

    def test_register_handler(self):
        """Test registering signal handler."""
        board = AndonBoard()
        handler_called = []

        def test_handler(signal):
            handler_called.append(signal)

        board.register_handler(SignalSeverity.WARNING, test_handler)
        signal = AndonSignal(
            severity=SignalSeverity.WARNING, message="Test warning", source="test"
        )
        board.raise_signal(signal)
        assert len(handler_called) == 1
        assert handler_called[0] == signal

    def test_multiple_handlers(self):
        """Test registering multiple handlers for same severity."""
        board = AndonBoard()
        calls = []

        def handler1(signal):
            calls.append("handler1")

        def handler2(signal):
            calls.append("handler2")

        board.register_handler(SignalSeverity.ERROR, handler1)
        board.register_handler(SignalSeverity.ERROR, handler2)

        signal = AndonSignal(
            severity=SignalSeverity.ERROR, message="Test error", source="test"
        )
        board.raise_signal(signal)
        assert len(calls) == 2
        assert "handler1" in calls
        assert "handler2" in calls

    def test_unregister_handler(self):
        """Test unregistering handler."""
        board = AndonBoard()
        calls = []

        def test_handler(signal):
            calls.append(signal)

        board.register_handler(SignalSeverity.INFO, test_handler)
        removed = board.unregister_handler(SignalSeverity.INFO, test_handler)
        assert removed is True

        signal = AndonSignal(
            severity=SignalSeverity.INFO, message="Test", source="test"
        )
        board.raise_signal(signal)
        assert len(calls) == 0

    def test_get_active_signals_all(self):
        """Test getting all active signals."""
        board = AndonBoard()
        for i in range(3):
            signal = AndonSignal(
                severity=SignalSeverity.INFO, message=f"Test {i}", source="test"
            )
            board.raise_signal(signal)
        signals = board.get_active_signals()
        assert len(signals) == 3

    def test_get_active_signals_by_severity(self):
        """Test filtering signals by severity."""
        board = AndonBoard()
        board.raise_signal(AndonSignal(SignalSeverity.INFO, "Info", "test"))
        board.raise_signal(AndonSignal(SignalSeverity.WARNING, "Warn", "test"))
        board.raise_signal(AndonSignal(SignalSeverity.ERROR, "Error", "test"))

        warnings = board.get_active_signals(severity=SignalSeverity.WARNING)
        assert len(warnings) == 1
        assert warnings[0].message == "Warn"

    def test_get_active_signals_by_source(self):
        """Test filtering signals by source."""
        board = AndonBoard()
        board.raise_signal(AndonSignal(SignalSeverity.INFO, "Test", "source1"))
        board.raise_signal(AndonSignal(SignalSeverity.INFO, "Test", "source2"))
        board.raise_signal(AndonSignal(SignalSeverity.INFO, "Test", "source1"))

        source1_signals = board.get_active_signals(source="source1")
        assert len(source1_signals) == 2

    def test_clear_all_signals(self):
        """Test clearing all signals."""
        board = AndonBoard()
        for i in range(5):
            board.raise_signal(AndonSignal(SignalSeverity.INFO, f"Test {i}", "test"))

        count = board.clear_signals()
        assert count == 5
        assert len(board.signals) == 0

    def test_clear_signals_by_severity(self):
        """Test clearing signals by severity."""
        board = AndonBoard()
        board.raise_signal(AndonSignal(SignalSeverity.INFO, "Info", "test"))
        board.raise_signal(AndonSignal(SignalSeverity.WARNING, "Warn", "test"))
        board.raise_signal(AndonSignal(SignalSeverity.ERROR, "Error", "test"))

        count = board.clear_signals(severity=SignalSeverity.WARNING)
        assert count == 1
        assert len(board.signals) == 2

    def test_get_signal_count_by_severity(self):
        """Test getting signal counts by severity."""
        board = AndonBoard()
        board.raise_signal(AndonSignal(SignalSeverity.INFO, "Info1", "test"))
        board.raise_signal(AndonSignal(SignalSeverity.INFO, "Info2", "test"))
        board.raise_signal(AndonSignal(SignalSeverity.WARNING, "Warn", "test"))
        board.raise_signal(AndonSignal(SignalSeverity.ERROR, "Error", "test"))

        counts = board.get_signal_count_by_severity()
        assert counts[SignalSeverity.INFO] == 2
        assert counts[SignalSeverity.WARNING] == 1
        assert counts[SignalSeverity.ERROR] == 1
        assert counts[SignalSeverity.CRITICAL] == 0

    def test_handler_exception_doesnt_break_board(self):
        """Test that handler exception doesn't break the board."""
        board = AndonBoard()

        def bad_handler(signal):
            raise RuntimeError("Handler error")

        board.register_handler(SignalSeverity.ERROR, bad_handler)
        signal = AndonSignal(SignalSeverity.ERROR, "Test", "test")

        # Should not raise exception
        board.raise_signal(signal)
        assert len(board.signals) == 1

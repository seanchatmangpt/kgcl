"""Andon Signals - Production monitoring system.

Manufacturing-inspired visual signal board for production problems.
Implements the Andon system concept for detecting and responding to issues.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class SignalSeverity(Enum):
    """Andon signal severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AndonSignal:
    """Production problem signal (manufacturing quality control concept)."""

    severity: SignalSeverity
    message: str
    source: str
    timestamp: datetime = field(default_factory=datetime.now)
    auto_stop: bool = False  # Should stop operations
    metadata: dict | None = None

    def __post_init__(self) -> None:
        """Validate signal data."""
        if not isinstance(self.severity, SignalSeverity):
            raise ValueError(f"Invalid severity: {self.severity}")
        if not self.message:
            raise ValueError("Signal message cannot be empty")
        if not self.source:
            raise ValueError("Signal source cannot be empty")


class AndonBoard:
    """Visual signal board for production problems.

    Manages system-wide signals, handlers, and automated responses.
    Inspired by manufacturing Andon systems for quality control.
    """

    def __init__(self, max_signals: int = 1000):
        """Initialize Andon board.

        Args:
            max_signals: Maximum number of signals to retain in history
        """
        self.signals: list[AndonSignal] = []
        self.handlers: dict[SignalSeverity, list[Callable]] = {
            severity: [] for severity in SignalSeverity
        }
        self.max_signals = max_signals
        self._stopped = False
        self._logger = logging.getLogger(__name__)

    def raise_signal(self, signal: AndonSignal) -> None:
        """Raise new Andon signal.

        Args:
            signal: AndonSignal to raise
        """
        # Add to history
        self.signals.append(signal)

        # Trim history if needed
        if len(self.signals) > self.max_signals:
            self.signals = self.signals[-self.max_signals :]

        # Trigger all registered handlers for this severity
        if signal.severity in self.handlers:
            for handler in self.handlers[signal.severity]:
                try:
                    handler(signal)
                except Exception as e:
                    self._logger.error(f"Handler error: {e}")

        # Log based on severity
        log_msg = f"[{signal.source}] {signal.message}"
        if signal.severity == SignalSeverity.INFO:
            self._logger.info(log_msg)
        elif signal.severity == SignalSeverity.WARNING:
            self._logger.warning(log_msg)
        elif signal.severity == SignalSeverity.ERROR:
            self._logger.error(log_msg)
        elif signal.severity == SignalSeverity.CRITICAL:
            self._logger.critical(log_msg)

        # Handle auto-stop
        if signal.auto_stop:
            self._stopped = True
            self._logger.critical(f"SYSTEM STOPPED: {signal.message}")

    def register_handler(
        self, severity: SignalSeverity, handler: Callable[[AndonSignal], None]
    ) -> None:
        """Register handler for severity level.

        Args:
            severity: Severity level to handle
            handler: Callback function that takes AndonSignal
        """
        if severity not in self.handlers:
            self.handlers[severity] = []
        self.handlers[severity].append(handler)

    def unregister_handler(
        self, severity: SignalSeverity, handler: Callable[[AndonSignal], None]
    ) -> bool:
        """Unregister a handler.

        Args:
            severity: Severity level
            handler: Handler to remove

        Returns
        -------
            True if handler was found and removed
        """
        if severity in self.handlers and handler in self.handlers[severity]:
            self.handlers[severity].remove(handler)
            return True
        return False

    def get_active_signals(
        self, severity: SignalSeverity | None = None, source: str | None = None
    ) -> list[AndonSignal]:
        """Get active signals with optional filtering.

        Args:
            severity: Filter by severity level
            source: Filter by source

        Returns
        -------
            List of matching signals
        """
        signals = self.signals

        if severity is not None:
            signals = [s for s in signals if s.severity == severity]

        if source is not None:
            signals = [s for s in signals if s.source == source]

        return signals

    def clear_signals(self, severity: SignalSeverity | None = None) -> int:
        """Clear signals.

        Args:
            severity: If provided, only clear signals of this severity

        Returns
        -------
            Number of signals cleared
        """
        if severity is None:
            count = len(self.signals)
            self.signals = []
            return count
        before = len(self.signals)
        self.signals = [s for s in self.signals if s.severity != severity]
        return before - len(self.signals)

    def is_stopped(self) -> bool:
        """Check if system has been stopped by auto_stop signal."""
        return self._stopped

    def reset_stop(self) -> None:
        """Reset the stopped state (use with caution)."""
        self._stopped = False

    def get_signal_count_by_severity(self) -> dict[SignalSeverity, int]:
        """Get count of signals by severity level.

        Returns
        -------
            Dictionary mapping severity to count
        """
        counts = dict.fromkeys(SignalSeverity, 0)
        for signal in self.signals:
            counts[signal.severity] += 1
        return counts

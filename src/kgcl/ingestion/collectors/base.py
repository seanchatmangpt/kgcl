"""Base collector interface and state management."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from kgcl.ingestion.models import AppEvent, BrowserVisit, CalendarBlock


class CollectorState(str, Enum):
    """Collector lifecycle states."""

    INITIALIZED = "initialized"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class BaseCollector(ABC):
    """Base class for event collectors.

    Defines the interface that all collectors must implement.
    """

    def __init__(self, output_path: Path, flush_interval: int = 60, batch_size: int = 100) -> None:
        """Initialize collector.

        Parameters
        ----------
        output_path : Path
            Directory for output files
        flush_interval : int, optional
            Seconds between batch flushes, by default 60
        batch_size : int, optional
            Maximum events per batch, by default 100
        """
        self.output_path = Path(output_path)
        self.flush_interval = flush_interval
        self.batch_size = batch_size
        self.state = CollectorState.INITIALIZED
        self._event_count = 0
        self._error_count = 0
        self._last_flush = datetime.now(UTC).replace(tzinfo=None)

        # Ensure output directory exists
        self.output_path.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def collect(self) -> list[AppEvent | BrowserVisit | CalendarBlock]:
        """Collect events from source.

        Returns
        -------
        list[AppEvent | BrowserVisit | CalendarBlock]
            Collected events
        """
        ...

    @abstractmethod
    def flush(self) -> int:
        """Flush accumulated events to storage.

        Returns
        -------
        int
            Number of events flushed
        """
        ...

    @abstractmethod
    def start(self) -> None:
        """Start the collector."""
        ...

    @abstractmethod
    def stop(self) -> None:
        """Stop the collector."""
        ...

    def pause(self) -> None:
        """Pause event collection."""
        if self.state == CollectorState.RUNNING:
            self.state = CollectorState.PAUSED

    def resume(self) -> None:
        """Resume event collection."""
        if self.state == CollectorState.PAUSED:
            self.state = CollectorState.RUNNING

    def get_stats(self) -> dict[str, Any]:
        """Get collector statistics.

        Returns
        -------
        dict[str, Any]
            Collector statistics
        """
        return {
            "state": self.state.value,
            "event_count": self._event_count,
            "error_count": self._error_count,
            "last_flush": self._last_flush.isoformat(),
            "output_path": str(self.output_path),
        }

    def register_error_handler(self, handler: Callable[[Exception, Any], None]) -> None:
        """Register error handling callback.

        Parameters
        ----------
        handler : Callable[[Exception, Any], None]
            Error handler function
        """
        self._error_handler = handler

    def _handle_error(self, error: Exception, context: Any = None) -> None:
        """Handle collection errors.

        Parameters
        ----------
        error : Exception
            Error that occurred
        context : Any, optional
            Additional error context
        """
        self._error_count += 1
        self.state = CollectorState.ERROR

        if hasattr(self, "_error_handler"):
            self._error_handler(error, context)

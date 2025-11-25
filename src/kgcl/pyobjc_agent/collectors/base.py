"""
Base collector class for continuous event collection.

Provides foundation for sampling capabilities at intervals,
batching events, and outputting JSONL streams.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, TextIO
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
import json
import logging
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)


class CollectorStatus(str, Enum):
    """Status of a collector."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class CollectorConfig:
    """
    Configuration for a collector.

    Attributes:
        name: Collector name
        interval_seconds: Sampling interval
        batch_size: Number of events to batch before flush
        batch_timeout_seconds: Max time to wait before flushing batch
        output_path: Path to JSONL output file
        buffer_size: Max events to buffer in memory
        enable_compression: Whether to compress output
        retry_on_error: Whether to retry on collection errors
        max_retries: Maximum retry attempts
    """
    name: str
    interval_seconds: float = 60.0
    batch_size: int = 100
    batch_timeout_seconds: float = 300.0  # 5 minutes
    output_path: Optional[str] = None
    buffer_size: int = 10000
    enable_compression: bool = False
    retry_on_error: bool = True
    max_retries: int = 3


@dataclass
class CollectedEvent:
    """
    A collected event from a capability.

    Attributes:
        collector_name: Name of collector
        timestamp: Collection timestamp
        data: Event data payload
        metadata: Additional metadata
        sequence_number: Event sequence number
    """
    collector_name: str
    timestamp: str
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    sequence_number: int = 0

    def to_jsonl(self) -> str:
        """Convert event to JSONL format."""
        return json.dumps(asdict(self), separators=(',', ':'))


class BaseCollector(ABC):
    """
    Abstract base class for event collectors.

    Collectors continuously sample capabilities at intervals,
    batch events, and write to JSONL output files.
    """

    def __init__(self, config: CollectorConfig):
        """
        Initialize the collector.

        Args:
            config: Collector configuration
        """
        self.config = config
        self.status = CollectorStatus.STOPPED
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()

        # Event batching
        self._event_buffer: List[CollectedEvent] = []
        self._buffer_lock = threading.Lock()
        self._last_flush_time = time.time()
        self._sequence_number = 0

        # Output file
        self._output_file: Optional[TextIO] = None

        # Statistics
        self._stats = {
            "events_collected": 0,
            "events_written": 0,
            "batches_flushed": 0,
            "errors": 0,
            "started_at": None,
            "last_collection_at": None
        }

        logger.debug(f"Initialized collector: {config.name}")

    @abstractmethod
    def collect_event(self) -> Optional[Dict[str, Any]]:
        """
        Collect a single event.

        Returns:
            Event data dictionary or None if nothing to collect

        Raises:
            Exception: If collection fails
        """
        pass

    @abstractmethod
    def validate_configuration(self) -> bool:
        """
        Validate collector configuration and requirements.

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        pass

    def start(self) -> None:
        """Start the collector in a background thread."""
        if self.status == CollectorStatus.RUNNING:
            logger.warning(f"Collector {self.config.name} already running")
            return

        # Validate configuration
        if not self.validate_configuration():
            raise RuntimeError(f"Invalid configuration for {self.config.name}")

        # Open output file
        self._open_output_file()

        # Start collection thread
        self.status = CollectorStatus.STARTING
        self._stop_event.clear()
        self._pause_event.set()  # Start unpaused
        self._thread = threading.Thread(target=self._collection_loop, daemon=True)
        self._thread.start()

        self._stats["started_at"] = datetime.utcnow().isoformat()
        logger.info(f"Started collector: {self.config.name}")

    def stop(self) -> None:
        """Stop the collector and flush remaining events."""
        if self.status == CollectorStatus.STOPPED:
            logger.warning(f"Collector {self.config.name} already stopped")
            return

        logger.info(f"Stopping collector: {self.config.name}")
        self.status = CollectorStatus.STOPPING

        # Signal thread to stop
        self._stop_event.set()

        # Wait for thread to finish
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10.0)

        # Flush remaining events
        self._flush_buffer(force=True)

        # Close output file
        self._close_output_file()

        self.status = CollectorStatus.STOPPED
        logger.info(f"Stopped collector: {self.config.name}")

    def pause(self) -> None:
        """Pause the collector."""
        if self.status == CollectorStatus.RUNNING:
            self._pause_event.clear()
            self.status = CollectorStatus.PAUSED
            logger.info(f"Paused collector: {self.config.name}")

    def resume(self) -> None:
        """Resume the collector."""
        if self.status == CollectorStatus.PAUSED:
            self._pause_event.set()
            self.status = CollectorStatus.RUNNING
            logger.info(f"Resumed collector: {self.config.name}")

    def _collection_loop(self) -> None:
        """Main collection loop running in background thread."""
        self.status = CollectorStatus.RUNNING
        consecutive_errors = 0

        while not self._stop_event.is_set():
            try:
                # Wait for unpause
                self._pause_event.wait()

                # Check if should stop
                if self._stop_event.is_set():
                    break

                # Collect event
                event_data = self.collect_event()

                if event_data is not None:
                    # Create event
                    event = CollectedEvent(
                        collector_name=self.config.name,
                        timestamp=datetime.utcnow().isoformat(),
                        data=event_data,
                        sequence_number=self._get_next_sequence()
                    )

                    # Add to buffer
                    self._add_to_buffer(event)

                    # Update stats
                    self._stats["events_collected"] += 1
                    self._stats["last_collection_at"] = event.timestamp
                    consecutive_errors = 0

                # Check if should flush
                self._check_and_flush()

                # Sleep until next collection
                self._stop_event.wait(timeout=self.config.interval_seconds)

            except Exception as e:
                logger.error(f"Error in collection loop for {self.config.name}: {e}")
                self._stats["errors"] += 1
                consecutive_errors += 1

                # Handle retries
                if not self.config.retry_on_error or consecutive_errors >= self.config.max_retries:
                    logger.error(
                        f"Max errors reached for {self.config.name}. Stopping collector."
                    )
                    self.status = CollectorStatus.ERROR
                    break

                # Wait before retry
                self._stop_event.wait(timeout=self.config.interval_seconds * 2)

    def _get_next_sequence(self) -> int:
        """Get next sequence number."""
        with self._buffer_lock:
            self._sequence_number += 1
            return self._sequence_number

    def _add_to_buffer(self, event: CollectedEvent) -> None:
        """
        Add event to buffer.

        Args:
            event: Event to add
        """
        with self._buffer_lock:
            # Check buffer size
            if len(self._event_buffer) >= self.config.buffer_size:
                logger.warning(
                    f"Buffer full for {self.config.name}. "
                    f"Flushing {len(self._event_buffer)} events."
                )
                self._flush_buffer(force=True)

            self._event_buffer.append(event)

    def _check_and_flush(self) -> None:
        """Check if buffer should be flushed."""
        with self._buffer_lock:
            should_flush = (
                len(self._event_buffer) >= self.config.batch_size or
                (time.time() - self._last_flush_time) >= self.config.batch_timeout_seconds
            )

            if should_flush:
                self._flush_buffer()

    def _flush_buffer(self, force: bool = False) -> None:
        """
        Flush buffered events to output file.

        Args:
            force: Force flush even if batch size not met
        """
        with self._buffer_lock:
            if not self._event_buffer:
                return

            if not force and len(self._event_buffer) < self.config.batch_size:
                return

            try:
                # Write events
                for event in self._event_buffer:
                    self._write_event(event)

                written_count = len(self._event_buffer)
                self._stats["events_written"] += written_count
                self._stats["batches_flushed"] += 1

                logger.debug(
                    f"Flushed {written_count} events from {self.config.name}"
                )

                # Clear buffer
                self._event_buffer.clear()
                self._last_flush_time = time.time()

            except Exception as e:
                logger.error(f"Error flushing buffer for {self.config.name}: {e}")
                raise

    def _write_event(self, event: CollectedEvent) -> None:
        """
        Write a single event to output file.

        Args:
            event: Event to write
        """
        if self._output_file:
            try:
                jsonl_line = event.to_jsonl()
                self._output_file.write(jsonl_line + '\n')
                self._output_file.flush()  # Ensure written
            except Exception as e:
                logger.error(f"Error writing event: {e}")
                raise

    def _open_output_file(self) -> None:
        """Open output file for writing."""
        if not self.config.output_path:
            logger.warning(f"No output path configured for {self.config.name}")
            return

        try:
            output_path = Path(self.config.output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Open in append mode
            self._output_file = open(output_path, 'a', encoding='utf-8')
            logger.info(f"Opened output file: {output_path}")

        except Exception as e:
            logger.error(f"Failed to open output file {self.config.output_path}: {e}")
            raise

    def _close_output_file(self) -> None:
        """Close output file."""
        if self._output_file:
            try:
                self._output_file.close()
                logger.debug(f"Closed output file for {self.config.name}")
            except Exception as e:
                logger.error(f"Error closing output file: {e}")
            finally:
                self._output_file = None

    def get_stats(self) -> Dict[str, Any]:
        """
        Get collector statistics.

        Returns:
            Statistics dictionary
        """
        with self._buffer_lock:
            return {
                **self._stats,
                "status": self.status.value,
                "buffer_size": len(self._event_buffer),
                "config": asdict(self.config)
            }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.config.name} status={self.status.value}>"

"""Batch event collector with JSONL output and recovery."""

import json
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kgcl.ingestion.collectors.base import BaseCollector, CollectorState
from kgcl.ingestion.config import CollectorConfig
from kgcl.ingestion.models import AppEvent, BrowserVisit, CalendarBlock, EventBatch


class BatchCollector(BaseCollector):
    """Production batch collector with recovery capabilities.

    Features:
    - Configurable batch sizes and flush intervals
    - JSONL output format with schema versioning
    - Automatic recovery from corrupted logs
    - Event filtering and validation
    """

    def __init__(
        self,
        config: CollectorConfig,
        source_fn: Callable[[], list[AppEvent | BrowserVisit | CalendarBlock]] | None = None,
    ) -> None:
        """Initialize batch collector.

        Parameters
        ----------
        config : CollectorConfig
            Collector configuration
        source_fn : Callable, optional
            Function to collect events from source
        """
        super().__init__(
            output_path=config.output_directory,
            flush_interval=config.flush_interval_seconds,
            batch_size=config.batch_size,
        )
        self.config = config
        self.source_fn = source_fn
        self._buffer: list[AppEvent | BrowserVisit | CalendarBlock] = []
        self._current_batch_id: str | None = None

    def collect(self) -> list[AppEvent | BrowserVisit | CalendarBlock]:
        """Collect events from source function.

        Returns
        -------
        list[AppEvent | BrowserVisit | CalendarBlock]
            Collected events

        Raises
        ------
        RuntimeError
            If source function not configured
        """
        if self.source_fn is None:
            msg = "Source function not configured"
            raise RuntimeError(msg)

        try:
            events = self.source_fn()
            self._buffer.extend(events)
            self._event_count += len(events)

            # Auto-flush if batch size reached
            if len(self._buffer) >= self.batch_size:
                self.flush()

            return events

        except Exception as e:
            self._handle_error(e, {"operation": "collect"})
            return []

    def add_event(self, event: AppEvent | BrowserVisit | CalendarBlock) -> None:
        """Add single event to buffer.

        Parameters
        ----------
        event : AppEvent | BrowserVisit | CalendarBlock
            Event to add
        """
        self._buffer.append(event)
        self._event_count += 1

        # Auto-flush if batch size reached
        if len(self._buffer) >= self.batch_size:
            self.flush()

    def add_events(
        self,
        events: list[AppEvent | BrowserVisit | CalendarBlock],
    ) -> None:
        """Add multiple events to buffer.

        Parameters
        ----------
        events : list[AppEvent | BrowserVisit | CalendarBlock]
            Events to add
        """
        self._buffer.extend(events)
        self._event_count += len(events)

        # Auto-flush if batch size reached
        if len(self._buffer) >= self.batch_size:
            self.flush()

    def flush(self) -> int:
        """Flush buffered events to JSONL file.

        Returns
        -------
        int
            Number of events flushed
        """
        if not self._buffer:
            return 0

        try:
            # Create batch
            batch = EventBatch(
                batch_id=self._current_batch_id or self._generate_batch_id(),
                events=self._buffer.copy(),
                metadata={
                    "flush_time": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
                    "collector_state": self.state.value,
                },
            )

            # Write to JSONL
            output_file = self._get_output_file()
            self._write_batch(batch, output_file)

            # Clear buffer
            flushed_count = len(self._buffer)
            self._buffer.clear()
            self._last_flush = datetime.now(timezone.utc).replace(tzinfo=None)
            self._current_batch_id = None

            return flushed_count

        except Exception as e:
            self._handle_error(e, {"operation": "flush", "buffer_size": len(self._buffer)})
            return 0

    def _write_batch(self, batch: EventBatch, output_file: Path) -> None:
        """Write batch to JSONL file.

        Parameters
        ----------
        batch : EventBatch
            Batch to write
        output_file : Path
            Output file path
        """
        with output_file.open("a") as f:
            # Write batch metadata
            batch_line = {
                "type": "batch",
                "batch_id": batch.batch_id,
                "created_at": batch.created_at.isoformat(),
                "event_count": batch.event_count(),
                "events_by_type": batch.events_by_type(),
                "metadata": batch.metadata,
            }
            f.write(json.dumps(batch_line) + "\n")

            # Write events
            for event in batch.events:
                event_line = {
                    "type": "event",
                    "batch_id": batch.batch_id,
                    "event_type": type(event).__name__,
                    "data": event.model_dump(mode="json"),
                }
                f.write(json.dumps(event_line) + "\n")

    def _get_output_file(self) -> Path:
        """Get current output file path.

        Returns
        -------
        Path
            Output file path with date-based naming
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        filename = f"events_{now.strftime('%Y%m%d')}.jsonl"
        return self.output_path / filename

    def _generate_batch_id(self) -> str:
        """Generate unique batch ID.

        Returns
        -------
        str
            Batch identifier
        """
        return f"batch_{uuid.uuid4().hex[:12]}"

    def recover_from_file(self, file_path: Path) -> tuple[int, int]:
        """Recover events from potentially corrupted JSONL file.

        Parameters
        ----------
        file_path : Path
            JSONL file to recover

        Returns
        -------
        tuple[int, int]
            (recovered_events, corrupted_lines)
        """
        if not file_path.exists():
            return 0, 0

        recovered = 0
        corrupted = 0

        try:
            with file_path.open("r") as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        data = json.loads(line.strip())

                        # Skip batch metadata lines
                        if data.get("type") == "batch":
                            continue

                        # Recover event
                        if data.get("type") == "event":
                            event_type = data["event_type"]
                            event_data = data["data"]

                            # Reconstruct event
                            if event_type == "AppEvent":
                                event = AppEvent(**event_data)
                            elif event_type == "BrowserVisit":
                                event = BrowserVisit(**event_data)
                            elif event_type == "CalendarBlock":
                                event = CalendarBlock(**event_data)
                            else:
                                corrupted += 1
                                continue

                            self._buffer.append(event)
                            recovered += 1

                    except (json.JSONDecodeError, KeyError, TypeError) as e:
                        corrupted += 1
                        if self.config.enable_recovery:
                            # Log error and continue
                            self._handle_error(
                                e,
                                {"line_num": line_num, "file": str(file_path)},
                            )
                        else:
                            raise

        except Exception as e:
            self._handle_error(e, {"operation": "recovery", "file": str(file_path)})

        return recovered, corrupted

    def start(self) -> None:
        """Start collector."""
        self.state = CollectorState.RUNNING
        self._current_batch_id = self._generate_batch_id()

    def stop(self) -> None:
        """Stop collector and flush remaining events."""
        if self.state in {CollectorState.RUNNING, CollectorState.PAUSED}:
            self.flush()
            self.state = CollectorState.STOPPED

    def get_stats(self) -> dict[str, Any]:
        """Get collector statistics.

        Returns
        -------
        dict[str, Any]
            Enhanced statistics
        """
        stats = super().get_stats()
        stats.update({
            "buffer_size": len(self._buffer),
            "current_batch_id": self._current_batch_id,
            "batch_size": self.batch_size,
            "flush_interval": self.flush_interval,
        })
        return stats

"""Apple ingest pipeline coordinating all 4 data sources."""

from dataclasses import dataclass
from typing import Any

from rdflib import Graph

from kgcl.ingestion.apple.calendar import CalendarIngestEngine
from kgcl.ingestion.apple.files import FilesIngestEngine
from kgcl.ingestion.apple.mail import MailIngestEngine
from kgcl.ingestion.apple.reminders import RemindersIngestEngine


@dataclass
class PipelineMetrics:
    """Metrics for ingest pipeline."""

    event_count: int = 0
    action_count: int = 0
    message_count: int = 0
    work_count: int = 0
    total_count: int = 0
    error_count: int = 0
    duration_ms: float = 0.0


@dataclass
class PipelineResult:
    """Result of full ingest pipeline."""

    success: bool
    graph: Graph
    receipt_hash: str
    metrics: PipelineMetrics
    validation_report: dict | None
    errors: list[str]
    error_report: dict | None


class AppleIngestPipeline:
    """Orchestrates ingest of all 4 Apple data sources."""

    def __init__(self):
        """Initialize pipeline with all ingest engines."""
        self.calendar_engine = CalendarIngestEngine()
        self.reminders_engine = RemindersIngestEngine()
        self.mail_engine = MailIngestEngine()
        self.files_engine = FilesIngestEngine()
        self.graph = Graph()

    def ingest_all(self, ingest_data: dict[str, list[Any]]) -> PipelineResult:
        """Ingest all data sources together.

        Args:
            ingest_data: Dict with keys:
                - calendar_events: List of EKEvent objects
                - reminders: List of EKReminder objects
                - mail_messages: List of Mail messages
                - files: List of file metadata objects

        Returns
        -------
            PipelineResult with consolidated graph and metrics
        """
        import time

        start_time = time.perf_counter()
        errors = []
        metrics = PipelineMetrics()

        try:
            # Ingest calendar events
            if "calendar_events" in ingest_data:
                try:
                    result = self.calendar_engine.ingest_batch(
                        ingest_data["calendar_events"]
                    )
                    self._merge_graph(result.graph)
                    metrics.event_count = result.items_processed
                    if not result.success:
                        errors.extend(result.errors)
                except Exception as e:
                    errors.append(f"Calendar ingest failed: {e!s}")

            # Ingest reminders
            if "reminders" in ingest_data:
                try:
                    result = self.reminders_engine.ingest_batch(
                        ingest_data["reminders"]
                    )
                    self._merge_graph(result.graph)
                    metrics.action_count = result.items_processed
                    if not result.success:
                        errors.extend(result.errors)
                except Exception as e:
                    errors.append(f"Reminders ingest failed: {e!s}")

            # Ingest mail messages
            if "mail_messages" in ingest_data:
                try:
                    result = self.mail_engine.ingest_batch(ingest_data["mail_messages"])
                    self._merge_graph(result.graph)
                    metrics.message_count = result.items_processed
                    if not result.success:
                        errors.extend(result.errors)
                except Exception as e:
                    errors.append(f"Mail ingest failed: {e!s}")

            # Ingest files
            if "files" in ingest_data:
                try:
                    result = self.files_engine.ingest_batch(ingest_data["files"])
                    self._merge_graph(result.graph)
                    metrics.work_count = result.items_processed
                    if not result.success:
                        errors.extend(result.errors)
                except Exception as e:
                    errors.append(f"Files ingest failed: {e!s}")

            # Calculate totals
            metrics.total_count = (
                metrics.event_count
                + metrics.action_count
                + metrics.message_count
                + metrics.work_count
            )
            metrics.error_count = len(errors)

            # Generate receipt hash
            receipt_hash = self._generate_receipt()

            # Calculate duration
            elapsed = time.perf_counter() - start_time
            metrics.duration_ms = elapsed * 1000

            return PipelineResult(
                success=len(errors) == 0,
                graph=self.graph,
                receipt_hash=receipt_hash,
                metrics=metrics,
                validation_report=None,  # Would be filled by SHACLValidator
                errors=errors,
                error_report=None,
            )

        except Exception as e:
            errors.append(f"Pipeline error: {e!s}")
            elapsed = time.perf_counter() - start_time
            metrics.duration_ms = elapsed * 1000

            return PipelineResult(
                success=False,
                graph=self.graph,
                receipt_hash="",
                metrics=metrics,
                validation_report=None,
                errors=errors,
                error_report=None,
            )

    def _merge_graph(self, source_graph: Graph):
        """Merge source graph into pipeline graph.

        Args:
            source_graph: Graph to merge
        """
        for s, p, o in source_graph:
            self.graph.add((s, p, o))

    def _generate_receipt(self) -> str:
        """Generate SHA256 receipt for idempotency.

        Returns
        -------
            SHA256 hex digest
        """
        import hashlib

        serialized = self.graph.serialize(format="ttl")
        return hashlib.sha256(serialized.encode()).hexdigest()

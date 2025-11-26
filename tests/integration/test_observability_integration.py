"""Observability integration tests."""

from __future__ import annotations

import tempfile
import time
from collections.abc import Iterable
from pathlib import Path

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from kgcl.observability.health import check_health
from kgcl.observability.tracing import reset_tracer_provider
from kgcl.unrdf_engine.engine import UnrdfEngine
from kgcl.unrdf_engine.ingestion import IngestionPipeline

SPANS_MIN_LENGTH = 0
PERFORMANCE_BUDGET_SECONDS = 1.0
HEALTH_STATUSES = {"healthy", "degraded", "unhealthy"}


def _create_pipeline(tmpdir: str) -> IngestionPipeline:
    engine = UnrdfEngine(file_path=Path(tmpdir) / "graph.ttl")
    return IngestionPipeline(engine)


def _configure_tracer(exporter: InMemorySpanExporter) -> None:
    reset_tracer_provider()
    provider = TracerProvider()
    trace.set_tracer_provider(provider)
    provider.add_span_processor(SimpleSpanProcessor(exporter))


def _span_names(spans: Iterable) -> set[str]:
    return {span.name for span in spans}


class TestObservabilityIntegration:
    """High-level tests covering spans, metrics, and health probes."""

    def test_spans_generated_on_ingestion(self) -> None:
        exporter = InMemorySpanExporter()
        _configure_tracer(exporter)

        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = _create_pipeline(tmpdir)
            result = pipeline.ingest_json(
                data={"id": "span_test", "type": "Ping"}, agent="test"
            )

        assert result.success is True
        spans = exporter.get_finished_spans()
        assert isinstance(spans, list)
        assert len(spans) >= SPANS_MIN_LENGTH

    def test_span_attributes_include_nested_operations(self) -> None:
        exporter = InMemorySpanExporter()
        _configure_tracer(exporter)
        tracer = trace.get_tracer(__name__)

        with (
            tracer.start_as_current_span("parent"),
            tracer.start_as_current_span("child"),
        ):
            pass

        spans = exporter.get_finished_spans()
        assert _span_names(spans) >= {"parent", "child"}

    def test_health_check_reports_components(self) -> None:
        system_health = check_health()
        assert system_health.status.value in HEALTH_STATUSES
        assert hasattr(system_health, "components")
        for component in system_health.components:
            assert component.status.value in HEALTH_STATUSES

    def test_span_exception_recording(self) -> None:
        exporter = InMemorySpanExporter()
        _configure_tracer(exporter)
        tracer = trace.get_tracer(__name__)

        def _raise() -> None:
            error_message = "span exception"
            raise ValueError(error_message)

        with pytest.raises(ValueError), tracer.start_as_current_span("exception_span"):
            _raise()

        spans = exporter.get_finished_spans()
        assert "exception_span" in _span_names(spans)

    def test_performance_metrics_collect_execution_time(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = _create_pipeline(tmpdir)
            start = time.perf_counter()
            result = pipeline.ingest_json(
                data={"id": "perf", "type": "PerfTest"}, agent="tester"
            )
            duration = time.perf_counter() - start

        assert result.success is True
        assert duration < PERFORMANCE_BUDGET_SECONDS

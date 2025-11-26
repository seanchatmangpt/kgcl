"""OpenTelemetry observability package for KGCL.

This package provides comprehensive instrumentation for tracing, metrics,
and logging across all KGCL subsystems.
"""

from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter as _OtelInMemorySpanExporter,
)

from kgcl.observability.config import ObservabilityConfig
from kgcl.observability.logging import configure_logging, get_logger
from kgcl.observability.metrics import KGCLMetrics
from kgcl.observability.tracing import configure_tracing, get_tracer

_original_get_finished_spans = _OtelInMemorySpanExporter.get_finished_spans


def _kgcl_get_finished_spans(self):
    """Ensure OpenTelemetry exporter returns a mutable list for compatibility."""
    spans = _original_get_finished_spans(self)
    return list(spans)


if not getattr(_OtelInMemorySpanExporter.get_finished_spans, "_kgcl_patched", False):
    _OtelInMemorySpanExporter.get_finished_spans = _kgcl_get_finished_spans
    _OtelInMemorySpanExporter.get_finished_spans._kgcl_patched = True  # type: ignore[attr-defined]

__all__ = [
    "KGCLMetrics",
    "ObservabilityConfig",
    "configure_logging",
    "configure_tracing",
    "get_logger",
    "get_tracer",
]

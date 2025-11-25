"""OpenTelemetry tracing configuration and utilities.

Provides tracer initialization with support for multiple exporters
and proper sampling configuration.
"""

import logging
from contextlib import contextmanager
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter as OTLPGrpcExporter,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter as OTLPHttpExporter,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SpanExporter
from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio, TraceIdRatioBased
from opentelemetry.trace import Status, StatusCode, Tracer

from kgcl.observability.config import ExporterType, ObservabilityConfig

logger = logging.getLogger(__name__)

_tracer_provider: TracerProvider | None = None
_configured = False


def configure_tracing(config: ObservabilityConfig | None = None) -> TracerProvider | None:
    """Configure OpenTelemetry tracing with the specified configuration.

    Parameters
    ----------
    config : ObservabilityConfig | None
        Observability configuration. If None, loads from environment.

    Returns
    -------
    TracerProvider | None
        Configured tracer provider, or None if tracing is disabled

    """
    global _tracer_provider, _configured

    if _configured:
        logger.warning("Tracing already configured, skipping reconfiguration")
        return _tracer_provider

    if config is None:
        config = ObservabilityConfig.from_env()

    if not config.enable_tracing:
        logger.info("Tracing is disabled")
        _configured = True
        return None

    # Create resource with service information
    resource_attrs = {
        "service.name": config.service_name,
        "service.environment": config.environment.value,
        "service.version": "0.0.0",  # TODO: Get from package metadata
        **config.resource_attributes,
    }
    resource = Resource.create(resource_attrs)

    # Configure sampler based on sampling rate
    if config.sampling_rate >= 1.0:
        sampler = None  # Default always-on sampler
    elif config.sampling_rate <= 0.0:
        sampler = TraceIdRatioBased(0.0)  # Always off
    else:
        sampler = ParentBasedTraceIdRatio(config.sampling_rate)

    # Create tracer provider
    _tracer_provider = TracerProvider(resource=resource, sampler=sampler)

    # Configure exporters
    exporters = _create_exporters(config)
    for exporter in exporters:
        _tracer_provider.add_span_processor(BatchSpanProcessor(exporter))

    # Set as global tracer provider
    trace.set_tracer_provider(_tracer_provider)

    _configured = True
    logger.info(
        "Tracing configured",
        extra={
            "service_name": config.service_name,
            "environment": config.environment.value,
            "exporter": config.trace_exporter.value,
            "sampling_rate": config.sampling_rate,
        },
    )

    return _tracer_provider


def _create_exporters(config: ObservabilityConfig) -> list[SpanExporter]:
    """Create span exporters based on configuration.

    Parameters
    ----------
    config : ObservabilityConfig
        Observability configuration

    Returns
    -------
    list[SpanExporter]
        List of configured span exporters

    """
    exporters: list[SpanExporter] = []

    # Add primary exporter
    if config.trace_exporter == ExporterType.CONSOLE:
        exporters.append(ConsoleSpanExporter())
    elif config.trace_exporter == ExporterType.OTLP_HTTP:
        if not config.otlp_endpoint:
            msg = "OTLP endpoint required for OTLP HTTP exporter"
            raise ValueError(msg)
        exporters.append(
            OTLPHttpExporter(
                endpoint=f"{config.otlp_endpoint}/v1/traces", insecure=config.otlp_insecure
            )
        )
    elif config.trace_exporter == ExporterType.OTLP_GRPC:
        if not config.otlp_endpoint:
            msg = "OTLP endpoint required for OTLP gRPC exporter"
            raise ValueError(msg)
        exporters.append(
            OTLPGrpcExporter(endpoint=config.otlp_endpoint, insecure=config.otlp_insecure)
        )
    elif config.trace_exporter == ExporterType.JAEGER:
        try:
            from opentelemetry.exporter.jaeger.thrift import JaegerExporter

            exporters.append(JaegerExporter())
        except ImportError:
            logger.warning("Jaeger exporter not available, install opentelemetry-exporter-jaeger")
    elif config.trace_exporter == ExporterType.ZIPKIN:
        try:
            from opentelemetry.exporter.zipkin.json import ZipkinExporter

            exporters.append(ZipkinExporter())
        except ImportError:
            logger.warning("Zipkin exporter not available, install opentelemetry-exporter-zipkin")

    # Add console exporter if requested
    if config.console_export and config.trace_exporter != ExporterType.CONSOLE:
        exporters.append(ConsoleSpanExporter())

    return exporters


def get_tracer(name: str) -> Tracer:
    """Get a tracer instance for the specified module.

    Parameters
    ----------
    name : str
        Module name (typically __name__)

    Returns
    -------
    Tracer
        OpenTelemetry tracer instance

    """
    if not _configured:
        configure_tracing()

    return trace.get_tracer(name)


@contextmanager
def traced_operation(
    tracer: Tracer,
    operation_name: str,
    attributes: dict[str, Any] | None = None,
    record_exception: bool = True,
):
    """Context manager for tracing operations with error handling.

    Parameters
    ----------
    tracer : Tracer
        OpenTelemetry tracer instance
    operation_name : str
        Name of the operation being traced
    attributes : dict[str, Any] | None
        Additional span attributes
    record_exception : bool
        Whether to record exceptions in the span

    Yields
    ------
    Span
        Active span for the operation

    Examples
    --------
    >>> tracer = get_tracer(__name__)
    >>> with traced_operation(tracer, "process_data", {"item_count": 10}):
    ...     # Your code here
    ...     pass

    """
    with tracer.start_as_current_span(operation_name) as span:
        if attributes:
            span.set_attributes(attributes)

        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            if record_exception:
                span.record_exception(e)
            raise


def add_span_attributes(span: trace.Span, attributes: dict[str, Any]) -> None:
    """Add multiple attributes to a span safely.

    Parameters
    ----------
    span : Span
        OpenTelemetry span
    attributes : dict[str, Any]
        Attributes to add (non-string values will be converted)

    """
    for key, value in attributes.items():
        if isinstance(value, (str, int, float, bool)):
            span.set_attribute(key, value)
        else:
            span.set_attribute(key, str(value))


def shutdown_tracing() -> None:
    """Shutdown tracing and flush remaining spans."""
    global _tracer_provider, _configured

    if _tracer_provider:
        _tracer_provider.shutdown()
        _tracer_provider = None
        _configured = False
        logger.info("Tracing shutdown completed")

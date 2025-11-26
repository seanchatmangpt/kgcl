"""OpenTelemetry metrics configuration and utilities.

Provides metrics instrumentation for KGCL operations including counters,
histograms, and gauges for monitoring system performance.
"""

import logging
from typing import Any

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
    OTLPMetricExporter as OTLPGrpcMetricExporter,
)
from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
    OTLPMetricExporter as OTLPHttpMetricExporter,
)
from opentelemetry.metrics import Meter, ObservableGauge
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    MetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource

from kgcl.observability.config import ExporterType, ObservabilityConfig

logger = logging.getLogger(__name__)

_meter_provider: MeterProvider | None = None
_configured = False


def configure_metrics(
    config: ObservabilityConfig | None = None,
) -> MeterProvider | None:
    """Configure OpenTelemetry metrics with the specified configuration.

    Parameters
    ----------
    config : ObservabilityConfig | None
        Observability configuration. If None, loads from environment.

    Returns
    -------
    MeterProvider | None
        Configured meter provider, or None if metrics are disabled

    """
    global _meter_provider, _configured

    if _configured:
        logger.warning("Metrics already configured, skipping reconfiguration")
        return _meter_provider

    if config is None:
        config = ObservabilityConfig.from_env()

    if not config.enable_metrics:
        logger.info("Metrics are disabled")
        _configured = True
        return None

    # Create resource with service information
    # Get version from package metadata or environment variable
    try:
        import importlib.metadata

        service_version = importlib.metadata.version("kgcl")
    except Exception:
        service_version = "0.0.0"

    resource_attrs = {
        "service.name": config.service_name,
        "service.environment": config.environment.value,
        "service.version": service_version,
        **config.resource_attributes,
    }
    resource = Resource.create(resource_attrs)

    # Configure exporter
    exporter = _create_metric_exporter(config)
    reader = PeriodicExportingMetricReader(exporter, export_interval_millis=60000)

    # Create meter provider
    _meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(_meter_provider)

    _configured = True
    logger.info(
        "Metrics configured",
        extra={
            "service_name": config.service_name,
            "environment": config.environment.value,
            "exporter": config.metric_exporter.value,
        },
    )

    return _meter_provider


def _create_metric_exporter(config: ObservabilityConfig) -> MetricExporter:
    """Create metric exporter based on configuration.

    Parameters
    ----------
    config : ObservabilityConfig
        Observability configuration

    Returns
    -------
    MetricExporter
        Configured metric exporter

    """
    if config.metric_exporter == ExporterType.CONSOLE:
        return ConsoleMetricExporter()
    if config.metric_exporter == ExporterType.OTLP_HTTP:
        if not config.otlp_endpoint:
            msg = "OTLP endpoint required for OTLP HTTP exporter"
            raise ValueError(msg)
        return OTLPHttpMetricExporter(
            endpoint=f"{config.otlp_endpoint}/v1/metrics", insecure=config.otlp_insecure
        )
    if config.metric_exporter == ExporterType.OTLP_GRPC:
        if not config.otlp_endpoint:
            msg = "OTLP endpoint required for OTLP gRPC exporter"
            raise ValueError(msg)
        return OTLPGrpcMetricExporter(
            endpoint=config.otlp_endpoint, insecure=config.otlp_insecure
        )
    logger.warning(
        f"Unsupported metric exporter: {config.metric_exporter}, using console"
    )
    return ConsoleMetricExporter()


def get_meter(name: str, version: str = "0.0.0") -> Meter:
    """Get a meter instance for the specified module.

    Parameters
    ----------
    name : str
        Module name (typically __name__)
    version : str
        Module version

    Returns
    -------
    Meter
        OpenTelemetry meter instance

    """
    if not _configured:
        configure_metrics()

    return metrics.get_meter(name, version)


class KGCLMetrics:
    """Central metrics registry for KGCL operations.

    Provides pre-configured metrics for common KGCL operations across
    all subsystems.
    """

    def __init__(self, meter: Meter | None = None) -> None:
        """Initialize KGCL metrics.

        Parameters
        ----------
        meter : Meter | None
            OpenTelemetry meter. If None, creates a new meter.

        """
        if meter is None:
            meter = get_meter("kgcl.metrics")

        self._meter = meter

        # Ingestion metrics
        self.events_ingested = meter.create_counter(
            name="kgcl.events.ingested",
            description="Total number of events ingested",
            unit="events",
        )

        self.ingestion_errors = meter.create_counter(
            name="kgcl.ingestion.errors",
            description="Total number of ingestion errors",
            unit="errors",
        )

        self.ingestion_duration = meter.create_histogram(
            name="kgcl.ingestion.duration",
            description="Duration of ingestion operations",
            unit="ms",
        )

        # Graph operations metrics
        self.graph_operations = meter.create_counter(
            name="kgcl.graph.operations",
            description="Total number of graph operations",
            unit="operations",
        )

        self.graph_operation_duration = meter.create_histogram(
            name="kgcl.graph.operation.duration",
            description="Duration of graph operations",
            unit="ms",
        )

        self.graph_query_duration = meter.create_histogram(
            name="kgcl.graph.query.duration",
            description="Duration of graph queries",
            unit="ms",
        )

        # DSPy/LM metrics
        self.lm_calls = meter.create_counter(
            name="kgcl.lm.calls",
            description="Total number of language model calls",
            unit="calls",
        )

        self.lm_tokens_used = meter.create_counter(
            name="kgcl.lm.tokens",
            description="Total number of tokens used",
            unit="tokens",
        )

        self.lm_call_duration = meter.create_histogram(
            name="kgcl.lm.call.duration",
            description="Duration of language model calls",
            unit="ms",
        )

        self.lm_errors = meter.create_counter(
            name="kgcl.lm.errors",
            description="Total number of language model errors",
            unit="errors",
        )

        # Parsing metrics
        self.parse_operations = meter.create_counter(
            name="kgcl.parse.operations",
            description="Total number of parse operations",
            unit="operations",
        )

        self.parse_duration = meter.create_histogram(
            name="kgcl.parse.duration",
            description="Duration of parse operations",
            unit="ms",
        )

        self.parse_errors = meter.create_counter(
            name="kgcl.parse.errors",
            description="Total number of parse errors",
            unit="errors",
        )

        # Cache metrics
        self.cache_hits = meter.create_counter(
            name="kgcl.cache.hits",
            description="Total number of cache hits",
            unit="hits",
        )

        self.cache_misses = meter.create_counter(
            name="kgcl.cache.misses",
            description="Total number of cache misses",
            unit="misses",
        )

        # Feature generation metrics
        self.features_generated = meter.create_counter(
            name="kgcl.features.generated",
            description="Total number of features generated",
            unit="features",
        )

        self.feature_generation_duration = meter.create_histogram(
            name="kgcl.features.generation.duration",
            description="Duration of feature generation",
            unit="ms",
        )

        # Capability crawler metrics
        self.capabilities_discovered = meter.create_counter(
            name="kgcl.capabilities.discovered",
            description="Total number of capabilities discovered",
            unit="capabilities",
        )

        self.crawler_duration = meter.create_histogram(
            name="kgcl.crawler.duration",
            description="Duration of capability crawling",
            unit="ms",
        )

    def record_event_ingestion(
        self, event_type: str, duration_ms: float, success: bool = True
    ) -> None:
        """Record an event ingestion operation.

        Parameters
        ----------
        event_type : str
            Type of event ingested
        duration_ms : float
            Duration in milliseconds
        success : bool
            Whether the ingestion was successful

        """
        attrs = {"event_type": event_type, "success": str(success)}
        self.events_ingested.add(1, attrs)
        self.ingestion_duration.record(duration_ms, attrs)

        if not success:
            self.ingestion_errors.add(1, {"event_type": event_type})

    def record_graph_operation(
        self, operation: str, duration_ms: float, success: bool = True
    ) -> None:
        """Record a graph operation.

        Parameters
        ----------
        operation : str
            Type of graph operation
        duration_ms : float
            Duration in milliseconds
        success : bool
            Whether the operation was successful

        """
        attrs = {"operation": operation, "success": str(success)}
        self.graph_operations.add(1, attrs)
        self.graph_operation_duration.record(duration_ms, attrs)

    def record_lm_call(
        self, model: str, tokens: int, duration_ms: float, success: bool = True
    ) -> None:
        """Record a language model call.

        Parameters
        ----------
        model : str
            Model name
        tokens : int
            Number of tokens used
        duration_ms : float
            Duration in milliseconds
        success : bool
            Whether the call was successful

        """
        attrs = {"model": model, "success": str(success)}
        self.lm_calls.add(1, attrs)
        self.lm_tokens_used.add(tokens, attrs)
        self.lm_call_duration.record(duration_ms, attrs)

        if not success:
            self.lm_errors.add(1, {"model": model})

    def record_parse_operation(
        self, parser: str, duration_ms: float, success: bool = True
    ) -> None:
        """Record a parse operation.

        Parameters
        ----------
        parser : str
            Parser name
        duration_ms : float
            Duration in milliseconds
        success : bool
            Whether the parse was successful

        """
        attrs = {"parser": parser, "success": str(success)}
        self.parse_operations.add(1, attrs)
        self.parse_duration.record(duration_ms, attrs)

        if not success:
            self.parse_errors.add(1, {"parser": parser})

    def record_cache_access(self, cache_name: str, hit: bool) -> None:
        """Record a cache access.

        Parameters
        ----------
        cache_name : str
            Name of the cache
        hit : bool
            Whether it was a cache hit

        """
        attrs = {"cache": cache_name}
        if hit:
            self.cache_hits.add(1, attrs)
        else:
            self.cache_misses.add(1, attrs)

    def create_gauge(
        self, name: str, callback: Any, description: str = "", unit: str = ""
    ) -> ObservableGauge:
        """Create an observable gauge metric.

        Parameters
        ----------
        name : str
            Metric name
        callback : callable
            Callback function to get gauge value
        description : str
            Metric description
        unit : str
            Unit of measurement

        Returns
        -------
        ObservableGauge
            Created gauge metric

        """
        return self._meter.create_observable_gauge(
            name=name, callbacks=[callback], description=description, unit=unit
        )


def shutdown_metrics() -> None:
    """Shutdown metrics and flush remaining data."""
    global _meter_provider, _configured

    if _meter_provider:
        _meter_provider.shutdown()
        _meter_provider = None
        _configured = False
        logger.info("Metrics shutdown completed")

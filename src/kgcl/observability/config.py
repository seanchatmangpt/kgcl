"""Configuration for OpenTelemetry observability.

Supports both local development and production modes with environment-based configuration.
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


class Environment(str, Enum):
    """Deployment environment."""

    LOCAL = "local"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class ExporterType(str, Enum):
    """Telemetry exporter types."""

    CONSOLE = "console"
    OTLP_HTTP = "otlp_http"
    OTLP_GRPC = "otlp_grpc"
    JAEGER = "jaeger"
    ZIPKIN = "zipkin"


@dataclass
class ObservabilityConfig:
    """Configuration for OpenTelemetry observability.

    Attributes
    ----------
    service_name : str
        Name of the service for telemetry identification
    environment : Environment
        Deployment environment (local, development, staging, production)
    enable_tracing : bool
        Enable distributed tracing
    enable_metrics : bool
        Enable metrics collection
    enable_logging : bool
        Enable structured logging
    trace_exporter : ExporterType
        Type of trace exporter to use
    metric_exporter : ExporterType
        Type of metric exporter to use
    otlp_endpoint : str | None
        OTLP collector endpoint (e.g., http://localhost:4318)
    otlp_insecure : bool
        Use insecure connection for OTLP
    sampling_rate : float
        Trace sampling rate (0.0 to 1.0)
    log_level : str
        Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    log_format : Literal["json", "text"]
        Log output format
    console_export : bool
        Also export to console in addition to configured exporter
    resource_attributes : dict[str, str]
        Additional resource attributes for telemetry

    """

    service_name: str = "kgcl"
    environment: Environment = Environment.LOCAL
    enable_tracing: bool = True
    enable_metrics: bool = True
    enable_logging: bool = True
    trace_exporter: ExporterType = ExporterType.CONSOLE
    metric_exporter: ExporterType = ExporterType.CONSOLE
    otlp_endpoint: str | None = None
    otlp_insecure: bool = True
    sampling_rate: float = 1.0
    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "json"
    console_export: bool = False
    resource_attributes: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "ObservabilityConfig":
        """Create configuration from environment variables.

        Environment Variables
        --------------------
        OTEL_SERVICE_NAME : str
            Service name (default: kgcl)
        KGCL_ENVIRONMENT : str
            Environment (local, development, staging, production)
        OTEL_TRACES_ENABLED : bool
            Enable tracing (default: true)
        OTEL_METRICS_ENABLED : bool
            Enable metrics (default: true)
        OTEL_LOGS_ENABLED : bool
            Enable logging (default: true)
        OTEL_TRACES_EXPORTER : str
            Trace exporter type (console, otlp_http, otlp_grpc, jaeger, zipkin)
        OTEL_METRICS_EXPORTER : str
            Metric exporter type
        OTEL_EXPORTER_OTLP_ENDPOINT : str
            OTLP collector endpoint
        OTEL_EXPORTER_OTLP_INSECURE : bool
            Use insecure OTLP connection
        OTEL_TRACES_SAMPLER : str
            Sampling strategy (always_on, always_off, traceidratio)
        OTEL_TRACES_SAMPLER_ARG : float
            Sampling rate for traceidratio sampler (0.0 to 1.0)
        KGCL_LOG_LEVEL : str
            Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        KGCL_LOG_FORMAT : str
            Log format (json, text)
        OTEL_CONSOLE_EXPORT : bool
            Also export to console
        OTEL_RESOURCE_ATTRIBUTES : str
            Comma-separated key=value pairs

        Returns
        -------
        ObservabilityConfig
            Configuration instance populated from environment

        """
        # Parse resource attributes from comma-separated key=value pairs
        resource_attrs = {}
        if attrs_str := os.getenv("OTEL_RESOURCE_ATTRIBUTES", ""):
            for pair in attrs_str.split(","):
                if "=" in pair:
                    key, value = pair.split("=", 1)
                    resource_attrs[key.strip()] = value.strip()

        # Parse sampling rate from sampler configuration
        sampling_rate = 1.0
        sampler = os.getenv("OTEL_TRACES_SAMPLER", "always_on").lower()
        if sampler == "traceidratio":
            sampling_rate = float(os.getenv("OTEL_TRACES_SAMPLER_ARG", "1.0"))
        elif sampler == "always_off":
            sampling_rate = 0.0

        return cls(
            service_name=os.getenv("OTEL_SERVICE_NAME", "kgcl"),
            environment=Environment(
                os.getenv("KGCL_ENVIRONMENT", Environment.LOCAL.value).lower()
            ),
            enable_tracing=os.getenv("OTEL_TRACES_ENABLED", "true").lower() == "true",
            enable_metrics=os.getenv("OTEL_METRICS_ENABLED", "true").lower() == "true",
            enable_logging=os.getenv("OTEL_LOGS_ENABLED", "true").lower() == "true",
            trace_exporter=ExporterType(
                os.getenv("OTEL_TRACES_EXPORTER", ExporterType.CONSOLE.value).lower()
            ),
            metric_exporter=ExporterType(
                os.getenv("OTEL_METRICS_EXPORTER", ExporterType.CONSOLE.value).lower()
            ),
            otlp_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
            otlp_insecure=os.getenv("OTEL_EXPORTER_OTLP_INSECURE", "true").lower() == "true",
            sampling_rate=sampling_rate,
            log_level=os.getenv("KGCL_LOG_LEVEL", "INFO").upper(),
            log_format=os.getenv("KGCL_LOG_FORMAT", "json").lower(),  # type: ignore[arg-type]
            console_export=os.getenv("OTEL_CONSOLE_EXPORT", "false").lower() == "true",
            resource_attributes=resource_attrs,
        )

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == Environment.PRODUCTION

    @property
    def is_local(self) -> bool:
        """Check if running in local development environment."""
        return self.environment == Environment.LOCAL

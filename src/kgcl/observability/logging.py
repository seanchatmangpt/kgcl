"""Structured logging configuration with OpenTelemetry integration.

Provides JSON and text logging with correlation IDs for distributed tracing.
"""

import logging
import logging.config
import sys
import uuid
from contextvars import ContextVar
from typing import Any

from kgcl.observability.config import ObservabilityConfig

# Context variable for correlation ID
_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)

_configured = False


class CorrelationIdFilter(logging.Filter):
    """Logging filter that adds correlation ID to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation ID to the log record.

        Parameters
        ----------
        record : logging.LogRecord
            Log record to filter

        Returns
        -------
        bool
            Always True (doesn't filter out records)

        """
        record.correlation_id = get_correlation_id()  # type: ignore[attr-defined]
        return True


class JsonFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Parameters
        ----------
        record : logging.LogRecord
            Log record to format

        Returns
        -------
        str
            JSON-formatted log message

        """
        import json

        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", None),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in (
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
                "correlation_id",
            ):
                log_data[key] = value

        return json.dumps(log_data)


def configure_logging(config: ObservabilityConfig | None = None) -> None:
    """Configure structured logging with OpenTelemetry integration.

    Parameters
    ----------
    config : ObservabilityConfig | None
        Observability configuration. If None, loads from environment.

    """
    global _configured

    if _configured:
        logging.getLogger(__name__).warning("Logging already configured, skipping")
        return

    if config is None:
        config = ObservabilityConfig.from_env()

    if not config.enable_logging:
        logging.getLogger(__name__).info("Logging is disabled")
        _configured = True
        return

    # Determine formatter based on configuration
    if config.log_format == "json":
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Configure handlers
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(CorrelationIdFilter())

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(config.log_level)
    root_logger.addHandler(handler)

    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("opentelemetry").setLevel(logging.WARNING)

    _configured = True
    logging.getLogger(__name__).info(
        "Logging configured",
        extra={
            "service_name": config.service_name,
            "environment": config.environment.value,
            "log_level": config.log_level,
            "log_format": config.log_format,
        },
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the specified module.

    Parameters
    ----------
    name : str
        Module name (typically __name__)

    Returns
    -------
    logging.Logger
        Logger instance

    """
    if not _configured:
        configure_logging()

    return logging.getLogger(name)


def get_correlation_id() -> str:
    """Get or create a correlation ID for the current context.

    Returns
    -------
    str
        Correlation ID (UUID)

    """
    correlation_id = _correlation_id.get()
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
        _correlation_id.set(correlation_id)
    return correlation_id


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID for the current context.

    Parameters
    ----------
    correlation_id : str
        Correlation ID to set

    """
    _correlation_id.set(correlation_id)


def clear_correlation_id() -> None:
    """Clear the correlation ID for the current context."""
    _correlation_id.set(None)

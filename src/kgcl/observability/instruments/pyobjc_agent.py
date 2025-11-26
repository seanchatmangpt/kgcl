"""OpenTelemetry instrumentation for PyObjC agent subsystem.

Instruments capability crawler and collectors for macOS system interaction.
"""

import functools
import logging
import time
from typing import Any

from opentelemetry.trace import Status, StatusCode

from kgcl.observability.metrics import KGCLMetrics
from kgcl.observability.tracing import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


def instrument_pyobjc_agent(metrics: KGCLMetrics | None = None) -> None:
    """Instrument PyObjC agent subsystem with OpenTelemetry.

    Parameters
    ----------
    metrics : KGCLMetrics | None
        Metrics instance. If None, creates a new instance.

    """
    if metrics is None:
        metrics = KGCLMetrics()

    logger.info("Instrumenting PyObjC agent subsystem")

    # This would be called during module initialization
    # to wrap key functions with instrumentation


def traced_capability_crawler(func: Any) -> Any:
    """Decorator for tracing capability crawler operations.

    Parameters
    ----------
    func : callable
        Function to trace

    Returns
    -------
    callable
        Wrapped function with tracing

    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        with tracer.start_as_current_span(
            f"capability_crawler.{func.__name__}",
            attributes={
                "subsystem": "pyobjc_agent",
                "operation": "capability_discovery",
            },
        ) as span:
            start_time = time.perf_counter()

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000

                # Record metrics
                if hasattr(result, "__len__"):
                    span.set_attribute("capabilities_count", len(result))

                span.set_status(Status(StatusCode.OK))
                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

    return wrapper


def traced_collector(collector_type: str) -> Any:
    """Decorator for tracing collector operations.

    Parameters
    ----------
    collector_type : str
        Type of collector (e.g., 'accessibility', 'window', 'process')

    Returns
    -------
    callable
        Decorator function

    """

    def decorator(func: Any) -> Any:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with tracer.start_as_current_span(
                f"collector.{collector_type}.{func.__name__}",
                attributes={
                    "subsystem": "pyobjc_agent",
                    "collector_type": collector_type,
                    "operation": "collect",
                },
            ) as span:
                start_time = time.perf_counter()

                try:
                    result = func(*args, **kwargs)
                    duration_ms = (time.perf_counter() - start_time) * 1000

                    # Record collection metrics
                    if isinstance(result, (dict, list)):
                        span.set_attribute("items_collected", len(result))

                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        return wrapper

    return decorator


class InstrumentedCapabilityCrawler:
    """Example instrumented capability crawler.

    This demonstrates how to instrument a capability crawler class.
    """

    def __init__(self, metrics: KGCLMetrics | None = None) -> None:
        """Initialize instrumented crawler.

        Parameters
        ----------
        metrics : KGCLMetrics | None
            Metrics instance

        """
        self.metrics = metrics or KGCLMetrics()

    @traced_capability_crawler
    def crawl_applications(self) -> list[dict[str, Any]]:
        """Crawl running applications for capabilities.

        Returns
        -------
        list[dict[str, Any]]
            List of discovered capabilities

        """
        # Implementation would go here
        return []

    @traced_collector("accessibility")
    def collect_accessibility_tree(self, app_name: str) -> dict[str, Any]:
        """Collect accessibility tree for an application.

        Parameters
        ----------
        app_name : str
            Application name

        Returns
        -------
        dict[str, Any]
            Accessibility tree data

        """
        # Implementation would go here
        return {}

    @traced_collector("window")
    def collect_window_info(self) -> list[dict[str, Any]]:
        """Collect window information.

        Returns
        -------
        list[dict[str, Any]]
            Window information

        """
        # Implementation would go here
        return []

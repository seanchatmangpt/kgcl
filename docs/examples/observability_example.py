"""Complete example of KGCL observability usage.

This demonstrates all observability features:
- Distributed tracing
- Metrics recording
- Structured logging
- Health checks
- Custom instrumentation
"""

import time
from typing import Any

from kgcl.observability import (
    ObservabilityConfig,
    configure_logging,
    configure_metrics,
    configure_tracing,
    get_logger,
    get_tracer,
)
from kgcl.observability.health import check_health, register_health_check
from kgcl.observability.logging import set_correlation_id
from kgcl.observability.metrics import KGCLMetrics
from kgcl.observability.tracing import traced_operation


# Initialize observability
def setup_observability() -> tuple[Any, KGCLMetrics, Any]:
    """Initialize all observability features.

    Returns
    -------
    tuple
        (tracer, metrics, logger)

    """
    # Load configuration from environment
    config = ObservabilityConfig.from_env()

    # Initialize all features
    configure_logging(config)
    configure_tracing(config)
    configure_metrics(config)

    # Get instances
    tracer = get_tracer(__name__)
    metrics = KGCLMetrics()
    logger = get_logger(__name__)

    logger.info("Observability initialized", extra={"environment": config.environment.value})

    return tracer, metrics, logger


# Example 1: Basic tracing
def example_basic_tracing(tracer: Any, logger: Any) -> None:
    """Demonstrate basic tracing.

    Parameters
    ----------
    tracer : Tracer
        OpenTelemetry tracer
    logger : Logger
        Python logger

    """
    logger.info("Starting basic tracing example")

    with traced_operation(
        tracer, "example_operation", attributes={"example": "basic_tracing"}
    ) as span:
        logger.info("Performing work inside span")

        # Simulate work
        time.sleep(0.1)

        # Add more attributes
        span.set_attribute("work_completed", True)
        span.set_attribute("items_processed", 10)

        logger.info("Work completed")


# Example 2: Nested spans
def example_nested_spans(tracer: Any, logger: Any) -> None:
    """Demonstrate nested spans.

    Parameters
    ----------
    tracer : Tracer
        OpenTelemetry tracer
    logger : Logger
        Python logger

    """
    logger.info("Starting nested spans example")

    with traced_operation(tracer, "parent_operation") as parent_span:
        parent_span.set_attribute("operation_type", "batch_processing")

        for i in range(3):
            with traced_operation(
                tracer, "child_operation", attributes={"iteration": i}
            ) as child_span:
                logger.info(f"Processing item {i}")
                time.sleep(0.05)
                child_span.set_attribute("result", "success")


# Example 3: Metrics recording
def example_metrics(metrics: KGCLMetrics, logger: Any) -> None:
    """Demonstrate metrics recording.

    Parameters
    ----------
    metrics : KGCLMetrics
        Metrics instance
    logger : Logger
        Python logger

    """
    logger.info("Starting metrics example")

    # Record event ingestion
    start = time.perf_counter()
    # Simulate event processing
    time.sleep(0.02)
    duration_ms = (time.perf_counter() - start) * 1000

    metrics.record_event_ingestion(
        event_type="capability_discovery", duration_ms=duration_ms, success=True
    )

    # Record LM call
    metrics.record_lm_call(model="ollama/llama3.1", tokens=512, duration_ms=150.0, success=True)

    # Record graph operation
    metrics.record_graph_operation(operation="sparql_query", duration_ms=10.5, success=True)

    # Record cache hit
    metrics.record_cache_access(cache_name="template_cache", hit=True)

    # Record cache miss
    metrics.record_cache_access(cache_name="template_cache", hit=False)

    logger.info("Metrics recorded successfully")


# Example 4: Structured logging
def example_structured_logging(logger: Any) -> None:
    """Demonstrate structured logging.

    Parameters
    ----------
    logger : Logger
        Python logger

    """
    # Set correlation ID
    correlation_id = "req-12345"
    set_correlation_id(correlation_id)

    logger.info(
        "Processing capability event",
        extra={
            "event_type": "window_focus",
            "app_name": "Chrome",
            "window_title": "GitHub - KGCL",
            "duration_ms": 25.5,
        },
    )

    logger.warning(
        "Cache miss for template",
        extra={"template_id": "capability_classifier", "cache_name": "template_cache"},
    )

    try:
        # Simulate error
        raise ValueError("Invalid event format")
    except ValueError:
        logger.exception("Failed to process event", extra={"event_id": "evt-789"})


# Example 5: Complete workflow with instrumentation
def example_complete_workflow(tracer: Any, metrics: KGCLMetrics, logger: Any) -> None:
    """Demonstrate complete workflow with all instrumentation.

    Parameters
    ----------
    tracer : Tracer
        OpenTelemetry tracer
    metrics : KGCLMetrics
        Metrics instance
    logger : Logger
        Python logger

    """
    logger.info("Starting complete workflow example")

    with traced_operation(
        tracer,
        "capability_ingestion_workflow",
        attributes={"workflow_version": "1.0", "event_batch_size": 5},
    ):
        # Step 1: Crawl capabilities
        with traced_operation(tracer, "crawl_capabilities") as crawl_span:
            logger.info("Crawling capabilities")
            start = time.perf_counter()

            # Simulate crawling
            capabilities = ["window_focus", "text_selection", "scroll", "click", "keyboard"]
            time.sleep(0.1)

            duration_ms = (time.perf_counter() - start) * 1000
            crawl_span.set_attribute("capabilities_found", len(capabilities))
            metrics.crawler_duration.record(duration_ms, {"type": "accessibility"})

        # Step 2: Parse events
        with traced_operation(tracer, "parse_events"):
            logger.info("Parsing capability events")
            start = time.perf_counter()

            for capability in capabilities:
                # Simulate parsing
                time.sleep(0.01)

            duration_ms = (time.perf_counter() - start) * 1000
            metrics.record_parse_operation(parser="capability_parser", duration_ms=duration_ms)

        # Step 3: Ingest to graph
        with traced_operation(tracer, "ingest_to_graph") as ingest_span:
            logger.info("Ingesting events to graph")

            for i, capability in enumerate(capabilities):
                start = time.perf_counter()

                # Simulate ingestion
                time.sleep(0.02)

                duration_ms = (time.perf_counter() - start) * 1000
                metrics.record_event_ingestion(
                    event_type=capability, duration_ms=duration_ms, success=True
                )

            ingest_span.set_attribute("events_ingested", len(capabilities))

        # Step 4: Generate DSPy features
        with traced_operation(tracer, "generate_features") as gen_span:
            logger.info("Generating DSPy features")
            start = time.perf_counter()

            # Check cache
            cache_hit = False
            metrics.record_cache_access("feature_cache", hit=cache_hit)

            if not cache_hit:
                # Simulate feature generation with LM call
                time.sleep(0.15)
                metrics.record_lm_call(
                    model="ollama/llama3.1", tokens=256, duration_ms=150.0, success=True
                )

            duration_ms = (time.perf_counter() - start) * 1000
            gen_span.set_attribute("features_generated", 5)
            metrics.feature_generation_duration.record(duration_ms, {"generator": "dspy"})

        logger.info("Workflow completed successfully")


# Example 6: Error handling
def example_error_handling(tracer: Any, metrics: KGCLMetrics, logger: Any) -> None:
    """Demonstrate error handling in instrumentation.

    Parameters
    ----------
    tracer : Tracer
        OpenTelemetry tracer
    metrics : KGCLMetrics
        Metrics instance
    logger : Logger
        Python logger

    """
    logger.info("Starting error handling example")

    try:
        with traced_operation(tracer, "operation_with_error") as span:
            logger.info("Attempting operation that will fail")
            start = time.perf_counter()

            # Simulate error
            raise ValueError("Simulated error for demonstration")

    except ValueError:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.exception("Operation failed")

        # Record error metrics
        metrics.record_event_ingestion(
            event_type="test_event", duration_ms=duration_ms, success=False
        )


# Example 7: Custom health check
def example_custom_health_check() -> None:
    """Demonstrate custom health check registration."""

    def check_custom_service() -> tuple[bool, str, dict[str, Any]]:
        """Custom health check.

        Returns
        -------
        tuple
            (is_healthy, message, details)

        """
        try:
            # Simulate service check
            time.sleep(0.01)
            return (True, "Custom service is healthy", {"status": "operational", "uptime": 3600})
        except Exception as e:
            return (False, f"Custom service check failed: {e}", {"error": str(e)})

    # Register the check
    register_health_check("custom_service", check_custom_service)

    # Run health checks
    health = check_health()

    print(f"\nHealth Status: {health.status.value}")
    for component in health.components:
        print(f"  {component.name}: {component.status.value} - {component.message}")


def main() -> None:
    """Run all examples."""
    # Setup
    tracer, metrics, logger = setup_observability()

    print("\n" + "=" * 60)
    print("KGCL Observability Examples")
    print("=" * 60)

    # Run examples
    print("\n1. Basic Tracing")
    example_basic_tracing(tracer, logger)

    print("\n2. Nested Spans")
    example_nested_spans(tracer, logger)

    print("\n3. Metrics Recording")
    example_metrics(metrics, logger)

    print("\n4. Structured Logging")
    example_structured_logging(logger)

    print("\n5. Complete Workflow")
    example_complete_workflow(tracer, metrics, logger)

    print("\n6. Error Handling")
    example_error_handling(tracer, metrics, logger)

    print("\n7. Custom Health Check")
    example_custom_health_check()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()

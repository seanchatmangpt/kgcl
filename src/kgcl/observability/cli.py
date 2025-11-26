"""CLI commands for observability and diagnostics.

Provides health check and diagnostic commands for monitoring KGCL.
"""

import json
import sys

import click

from kgcl.observability.config import ObservabilityConfig
from kgcl.observability.health import check_health
from kgcl.observability.logging import configure_logging
from kgcl.observability.metrics import configure_metrics
from kgcl.observability.tracing import configure_tracing


@click.group()
def cli() -> None:
    """KGCL observability and diagnostics commands."""


@cli.command()
@click.option("--format", type=click.Choice(["json", "text"]), default="text", help="Output format")
def health(format: str) -> None:
    """Check system health and connectivity.

    Checks:
    - Ollama connectivity
    - Graph integrity
    - Observability configuration
    """
    # Configure logging for CLI
    config = ObservabilityConfig.from_env()
    configure_logging(config)

    # Run health checks
    system_health = check_health()

    if format == "json":
        click.echo(json.dumps(system_health.to_dict(), indent=2))
    else:
        # Text format
        status_color = {"healthy": "green", "degraded": "yellow", "unhealthy": "red"}

        click.echo("\n🏥 KGCL System Health Check")
        click.echo("=" * 50)
        click.echo(
            f"Overall Status: {click.style(system_health.status.value.upper(), fg=status_color[system_health.status.value])}"
        )
        click.echo(f"Timestamp: {system_health.timestamp}")
        click.echo()

        for component in system_health.components:
            status_symbol = {"healthy": "✅", "degraded": "⚠️", "unhealthy": "❌"}

            click.echo(f"{status_symbol[component.status.value]} {component.name}")
            click.echo(f"   Status: {component.status.value}")
            click.echo(f"   Message: {component.message}")
            click.echo(f"   Check Duration: {component.check_duration_ms:.2f}ms")

            if component.details:
                click.echo("   Details:")
                for key, value in component.details.items():
                    click.echo(f"      {key}: {value}")

            click.echo()

    # Exit with appropriate code
    sys.exit(0 if system_health.is_healthy else 1)


@cli.command()
def config() -> None:
    """Display current observability configuration."""
    config = ObservabilityConfig.from_env()

    click.echo("\n⚙️  KGCL Observability Configuration")
    click.echo("=" * 50)
    click.echo(f"Service Name: {config.service_name}")
    click.echo(f"Environment: {config.environment.value}")
    click.echo()
    click.echo("Features:")
    click.echo(
        f"  Tracing: {click.style('enabled' if config.enable_tracing else 'disabled', fg='green' if config.enable_tracing else 'red')}"
    )
    click.echo(
        f"  Metrics: {click.style('enabled' if config.enable_metrics else 'disabled', fg='green' if config.enable_metrics else 'red')}"
    )
    click.echo(
        f"  Logging: {click.style('enabled' if config.enable_logging else 'disabled', fg='green' if config.enable_logging else 'red')}"
    )
    click.echo()
    click.echo("Configuration:")
    click.echo(f"  Trace Exporter: {config.trace_exporter.value}")
    click.echo(f"  Metric Exporter: {config.metric_exporter.value}")
    click.echo(f"  OTLP Endpoint: {config.otlp_endpoint or 'not configured'}")
    click.echo(f"  Sampling Rate: {config.sampling_rate}")
    click.echo(f"  Log Level: {config.log_level}")
    click.echo(f"  Log Format: {config.log_format}")
    click.echo()


@cli.command()
@click.option("--duration", type=int, default=60, help="Test duration in seconds")
def test_tracing(duration: int) -> None:
    """Test OpenTelemetry tracing configuration.

    Generates sample traces to verify exporter configuration.
    """
    import time

    from kgcl.observability.tracing import get_tracer, traced_operation

    config = ObservabilityConfig.from_env()
    configure_logging(config)
    configure_tracing(config)

    tracer = get_tracer("kgcl.test")

    click.echo(f"\n🔍 Testing tracing for {duration} seconds...")
    click.echo(f"Exporter: {config.trace_exporter.value}")
    click.echo(f"Endpoint: {config.otlp_endpoint or 'console'}")
    click.echo()

    end_time = time.time() + duration

    try:
        while time.time() < end_time:
            with traced_operation(
                tracer, "test_operation", attributes={"test": "true", "iteration": str(int(time.time()))}
            ):
                time.sleep(1)
                click.echo(".", nl=False)

        click.echo("\n✅ Tracing test completed")
    except KeyboardInterrupt:
        click.echo("\n⚠️  Test interrupted")


@cli.command()
def test_metrics() -> None:
    """Test OpenTelemetry metrics configuration.

    Generates sample metrics to verify exporter configuration.
    """
    import time

    from kgcl.observability.metrics import KGCLMetrics

    config = ObservabilityConfig.from_env()
    configure_logging(config)
    configure_metrics(config)

    metrics = KGCLMetrics()

    click.echo("\n📊 Testing metrics for 60 seconds...")
    click.echo(f"Exporter: {config.metric_exporter.value}")
    click.echo(f"Endpoint: {config.otlp_endpoint or 'console'}")
    click.echo()

    try:
        for i in range(60):
            metrics.record_event_ingestion("test_event", 10.0 + i, success=True)
            metrics.record_lm_call("test_model", 100, 50.0, success=True)
            metrics.record_graph_operation("test_query", 25.0, success=True)

            time.sleep(1)
            click.echo(".", nl=False)

        click.echo("\n✅ Metrics test completed")
    except KeyboardInterrupt:
        click.echo("\n⚠️  Test interrupted")


if __name__ == "__main__":
    cli()

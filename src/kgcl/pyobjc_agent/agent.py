"""
PyObjC Agent main daemon for continuous capability monitoring.

This module provides a daemonizable agent that:
- Manages multiple collectors
- Provides lifecycle management
- Integrates with OpenTelemetry
- Handles graceful shutdown
"""

import logging
import signal
import sys
import time
from pathlib import Path
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from .collectors import (
    BaseCollector,
    create_browser_history_collector,
    create_calendar_collector,
    create_frontmost_app_collector,
)
from .plugins import get_registry, load_builtin_plugins

logger = logging.getLogger(__name__)


class PyObjCAgent:
    """
    Main agent for PyObjC capability monitoring.

    Manages collectors, plugins, and provides daemon functionality.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize the agent.

        Args:
            config: Agent configuration dictionary
        """
        self.config = config or {}
        self._collectors: dict[str, BaseCollector] = {}
        self._running = False
        self._tracer: trace.Tracer | None = None

        # Setup OpenTelemetry if enabled
        if self.config.get("enable_otel", True):
            self._setup_otel()

        logger.info("PyObjC Agent initialized")

    def _setup_otel(self) -> None:
        """Setup OpenTelemetry instrumentation."""
        try:
            # Create resource
            resource = Resource.create(
                {
                    "service.name": "pyobjc-agent",
                    "service.version": "1.0.0",
                    "deployment.environment": self.config.get("environment", "development"),
                }
            )

            # Create tracer provider
            provider = TracerProvider(resource=resource)

            # Add OTLP exporter
            otlp_endpoint = self.config.get("otlp_endpoint", "http://localhost:4317")
            otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

            # Set global tracer provider
            trace.set_tracer_provider(provider)

            # Get tracer
            self._tracer = trace.get_tracer(__name__)

            logger.info(f"OpenTelemetry configured with endpoint: {otlp_endpoint}")

        except Exception as e:
            logger.warning(f"Failed to setup OpenTelemetry: {e}")
            logger.info("Continuing without telemetry")
            self._tracer = None

    def _get_span(self, name: str) -> trace.Span | None:
        """
        Get a new span for tracing.

        Args:
            name: Span name

        Returns
        -------
            Span instance or None if telemetry disabled
        """
        if self._tracer:
            return self._tracer.start_span(name)
        return None

    def initialize(self) -> None:
        """Initialize agent components."""
        with self._get_span("agent.initialize") or trace.get_current_span():
            logger.info("Initializing agent components")

            # Load built-in plugins
            load_builtin_plugins()

            # Create collectors based on configuration
            self._create_collectors()

            logger.info(f"Agent initialized with {len(self._collectors)} collectors")

    def _create_collectors(self) -> None:
        """Create collectors based on configuration."""
        collectors_config = self.config.get("collectors", {})
        data_dir = self.config.get("data_dir", "/Users/sac/dev/kgcl/data")

        # Ensure data directory exists
        Path(data_dir).mkdir(parents=True, exist_ok=True)

        # Frontmost app collector
        if collectors_config.get("frontmost_app", {}).get("enabled", True):
            logger.info("Creating frontmost app collector")
            collector = create_frontmost_app_collector(
                interval_seconds=collectors_config.get("frontmost_app", {}).get("interval", 1.0),
                output_path=f"{data_dir}/frontmost_app.jsonl",
            )
            self._collectors["frontmost_app"] = collector

        # Browser history collector
        if collectors_config.get("browser_history", {}).get("enabled", True):
            logger.info("Creating browser history collector")
            collector = create_browser_history_collector(
                interval_seconds=collectors_config.get("browser_history", {}).get("interval", 300.0),
                output_path=f"{data_dir}/browser_history.jsonl",
            )
            self._collectors["browser_history"] = collector

        # Calendar collector
        if collectors_config.get("calendar", {}).get("enabled", True):
            logger.info("Creating calendar collector")
            collector = create_calendar_collector(
                interval_seconds=collectors_config.get("calendar", {}).get("interval", 300.0),
                output_path=f"{data_dir}/calendar_events.jsonl",
            )
            self._collectors["calendar"] = collector

    def start(self) -> None:
        """Start all collectors."""
        with self._get_span("agent.start") or trace.get_current_span():
            logger.info("Starting PyObjC Agent")

            self._running = True

            # Start all collectors
            for name, collector in self._collectors.items():
                try:
                    logger.info(f"Starting collector: {name}")
                    collector.start()
                except Exception as e:
                    logger.error(f"Failed to start collector {name}: {e}")

            logger.info(f"Started {len(self._collectors)} collectors")

    def stop(self) -> None:
        """Stop all collectors."""
        with self._get_span("agent.stop") or trace.get_current_span():
            logger.info("Stopping PyObjC Agent")

            self._running = False

            # Stop all collectors
            for name, collector in self._collectors.items():
                try:
                    logger.info(f"Stopping collector: {name}")
                    collector.stop()
                except Exception as e:
                    logger.error(f"Error stopping collector {name}: {e}")

            logger.info("Agent stopped")

    def run(self) -> None:
        """
        Run the agent until interrupted.

        This method blocks until a shutdown signal is received.
        """
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Initialize and start
        self.initialize()
        self.start()

        logger.info("Agent running. Press Ctrl+C to stop.")

        # Main loop
        try:
            while self._running:
                time.sleep(1)

                # Log stats periodically
                if int(time.time()) % 60 == 0:  # Every minute
                    self._log_stats()

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")

        finally:
            self.stop()

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}")
        self._running = False

    def _log_stats(self) -> None:
        """Log collector statistics."""
        with self._get_span("agent.log_stats") or trace.get_current_span():
            for name, collector in self._collectors.items():
                stats = collector.get_stats()
                logger.info(
                    f"Collector {name}: "
                    f"collected={stats.get('events_collected', 0)}, "
                    f"written={stats.get('events_written', 0)}, "
                    f"buffer={stats.get('buffer_size', 0)}, "
                    f"status={stats.get('status', 'unknown')}"
                )

    def get_status(self) -> dict[str, Any]:
        """
        Get agent status.

        Returns
        -------
            Status dictionary
        """
        collector_stats = {}
        for name, collector in self._collectors.items():
            collector_stats[name] = collector.get_stats()

        # Get plugin status
        registry = get_registry()
        plugin_ids = registry.list_initialized_plugins()

        return {
            "running": self._running,
            "collectors_count": len(self._collectors),
            "collectors": collector_stats,
            "plugins_loaded": plugin_ids,
            "telemetry_enabled": self._tracer is not None,
            "config": self.config,
        }


def create_default_agent(data_dir: str | None = None) -> PyObjCAgent:
    """
    Create agent with default configuration.

    Args:
        data_dir: Directory for output data

    Returns
    -------
        Configured PyObjCAgent instance
    """
    config = {
        "data_dir": data_dir or "/Users/sac/dev/kgcl/data",
        "enable_otel": True,
        "otlp_endpoint": "http://localhost:4317",
        "environment": "development",
        "collectors": {
            "frontmost_app": {
                "enabled": True,
                "interval": 1.0,  # 1 second
            },
            "browser_history": {
                "enabled": True,
                "interval": 300.0,  # 5 minutes
            },
            "calendar": {
                "enabled": True,
                "interval": 300.0,  # 5 minutes
            },
        },
    }

    return PyObjCAgent(config)


def main():
    """Main entry point for agent daemon."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("/Users/sac/dev/kgcl/logs/pyobjc_agent.log")],
    )

    # Create log directory
    Path("/Users/sac/dev/kgcl/logs").mkdir(parents=True, exist_ok=True)

    # Create and run agent
    agent = create_default_agent()

    try:
        agent.run()
    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

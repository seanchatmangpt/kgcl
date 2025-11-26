"""
CLI entry point for PyObjC Agent.

Provides command-line interface for:
- Starting/stopping the agent
- Running capability discovery
- Aggregating collected data
- Managing configuration
"""

import argparse
import json
import logging
import sys
from pathlib import Path

import yaml

from .agent import PyObjCAgent, create_default_agent
from .aggregators import (
    BrowserHistoryAggregator,
    CalendarAggregator,
    FrontmostAppAggregator,
    aggregate_jsonl_file,
)
from .crawler import FrameworkName, PyObjCFrameworkCrawler
from .plugins import get_registry, load_builtin_plugins

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


def cmd_run(args):
    """Run the agent daemon."""
    logger.info("Starting PyObjC Agent daemon")

    # Load configuration if provided
    config = None
    if args.config:
        config = load_config(args.config)

    # Create agent
    agent = (
        PyObjCAgent(config) if config else create_default_agent(data_dir=args.data_dir)
    )

    # Run agent
    try:
        agent.run()
    except KeyboardInterrupt:
        logger.info("Agent stopped by user")
    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        sys.exit(1)


def cmd_discover(args):
    """Discover available capabilities."""
    logger.info("Discovering PyObjC capabilities")

    crawler = PyObjCFrameworkCrawler(safe_mode=not args.unsafe)

    if args.framework:
        # Crawl specific framework
        try:
            framework = FrameworkName(args.framework)
            capabilities = crawler.crawl_framework(framework)

            # Export
            output_path = (
                args.output
                or f"/Users/sac/dev/kgcl/{args.framework}_capabilities.jsonld"
            )
            crawler.export_capabilities(
                {framework.value: capabilities}, output_path, format="jsonld"
            )

            print(f"\nDiscovered capabilities for {args.framework}:")
            print(f"  Classes: {len(capabilities.classes)}")
            print(f"  Methods: {sum(len(c.methods) for c in capabilities.classes)}")
            print(f"  Output: {output_path}")

        except ValueError:
            logger.error(f"Unknown framework: {args.framework}")
            print(f"Available frameworks: {[f.value for f in FrameworkName]}")
            sys.exit(1)
    else:
        # Crawl all frameworks
        all_capabilities = crawler.crawl_all_frameworks()

        # Export
        output_path = args.output or "/Users/sac/dev/kgcl/capabilities.jsonld"
        crawler.export_capabilities(all_capabilities, output_path, format="jsonld")

        # Print summary
        total_classes = sum(len(cap.classes) for cap in all_capabilities.values())
        total_methods = sum(
            sum(len(cls.methods) for cls in cap.classes)
            for cap in all_capabilities.values()
        )

        print("\n=== Capability Discovery Summary ===")
        print(f"Frameworks: {len(all_capabilities)}")
        print(f"Total classes: {total_classes}")
        print(f"Total methods: {total_methods}")
        print(f"Output: {output_path}")


def cmd_aggregate(args):
    """Aggregate collected event data."""
    logger.info(f"Aggregating data from {args.input}")

    # Determine aggregator type
    if "frontmost_app" in args.input.lower():
        aggregator = FrontmostAppAggregator(window_size_hours=args.window_hours)
    elif "browser" in args.input.lower():
        aggregator = BrowserHistoryAggregator(window_size_hours=args.window_hours)
    elif "calendar" in args.input.lower():
        aggregator = CalendarAggregator(window_size_hours=args.window_hours)
    else:
        logger.error("Cannot determine aggregator type from filename")
        print(
            "Specify aggregator type in filename: frontmost_app, browser, or calendar"
        )
        sys.exit(1)

    # Aggregate
    output_path = args.output or args.input.replace(".jsonl", "_aggregated.json")

    features = aggregate_jsonl_file(args.input, aggregator, output_path)

    print("\n=== Aggregation Summary ===")
    print(f"Input: {args.input}")
    print(f"Features computed: {len(features)}")
    print(f"Output: {output_path}")


def cmd_status(args):
    """Get agent status."""
    logger.info("Checking agent status")

    # Load plugins to check availability
    load_builtin_plugins()
    registry = get_registry()

    print("\n=== PyObjC Agent Status ===")
    print(f"\nRegistered Plugins: {len(registry.list_plugins())}")
    for plugin_id in registry.list_plugins():
        print(f"  - {plugin_id}")

    print(f"\nInitialized Plugins: {len(registry.list_initialized_plugins())}")
    for plugin_id in registry.list_initialized_plugins():
        plugin = registry.get_plugin(plugin_id)
        if plugin:
            status = plugin.get_status()
            print(f"  - {plugin_id}: {status.get('status')}")

    # Check data directory
    data_dir = Path(args.data_dir)
    if data_dir.exists():
        print(f"\nData Directory: {data_dir}")
        jsonl_files = list(data_dir.glob("*.jsonl"))
        print(f"  JSONL files: {len(jsonl_files)}")
        for file in jsonl_files:
            size = file.stat().st_size
            print(f"    - {file.name}: {size:,} bytes")


def cmd_config(args):
    """Generate or validate configuration."""
    if args.generate:
        # Generate default configuration
        config = {
            "data_dir": "/Users/sac/dev/kgcl/data",
            "enable_otel": True,
            "otlp_endpoint": "http://localhost:4317",
            "environment": "development",
            "collectors": {
                "frontmost_app": {
                    "enabled": True,
                    "interval": 1.0,
                    "batch_size": 50,
                    "batch_timeout_seconds": 60.0,
                },
                "browser_history": {
                    "enabled": True,
                    "interval": 300.0,
                    "batch_size": 10,
                    "batch_timeout_seconds": 600.0,
                },
                "calendar": {
                    "enabled": True,
                    "interval": 300.0,
                    "batch_size": 10,
                    "batch_timeout_seconds": 600.0,
                },
            },
        }

        output_path = args.output or "/Users/sac/dev/kgcl/config/pyobjc_agent.yaml"
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)

        print(f"Generated configuration: {output_path}")

    elif args.validate:
        # Validate configuration
        try:
            config = load_config(args.validate)
            print(f"Configuration valid: {args.validate}")
            print(json.dumps(config, indent=2))
        except Exception as e:
            print(f"Configuration invalid: {e}")
            sys.exit(1)


def load_config(config_path: str) -> dict:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to configuration file

    Returns
    -------
        Configuration dictionary
    """
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Override with environment variables
    import os

    if os.getenv("PYOBJC_DATA_DIR"):
        config["data_dir"] = os.getenv("PYOBJC_DATA_DIR")

    if os.getenv("PYOBJC_OTLP_ENDPOINT"):
        config["otlp_endpoint"] = os.getenv("PYOBJC_OTLP_ENDPOINT")

    if os.getenv("PYOBJC_ENVIRONMENT"):
        config["environment"] = os.getenv("PYOBJC_ENVIRONMENT")

    return config


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="PyObjC Agent - macOS capability monitoring and discovery",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run agent daemon
  python -m kgcl.pyobjc_agent run

  # Discover capabilities
  python -m kgcl.pyobjc_agent discover --framework AppKit

  # Aggregate collected data
  python -m kgcl.pyobjc_agent aggregate data/frontmost_app.jsonl

  # Check status
  python -m kgcl.pyobjc_agent status

  # Generate configuration
  python -m kgcl.pyobjc_agent config --generate
        """,
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run the agent daemon")
    run_parser.add_argument("-c", "--config", help="Path to configuration file")
    run_parser.add_argument(
        "-d",
        "--data-dir",
        default="/Users/sac/dev/kgcl/data",
        help="Data directory for output",
    )

    # Discover command
    discover_parser = subparsers.add_parser("discover", help="Discover capabilities")
    discover_parser.add_argument(
        "-f", "--framework", help="Specific framework to discover"
    )
    discover_parser.add_argument("-o", "--output", help="Output file path")
    discover_parser.add_argument(
        "--unsafe", action="store_true", help="Include potentially unsafe methods"
    )

    # Aggregate command
    aggregate_parser = subparsers.add_parser(
        "aggregate", help="Aggregate collected data"
    )
    aggregate_parser.add_argument("input", help="Input JSONL file")
    aggregate_parser.add_argument("-o", "--output", help="Output JSON file")
    aggregate_parser.add_argument(
        "-w",
        "--window-hours",
        type=float,
        default=1.0,
        help="Aggregation window size in hours",
    )

    # Status command
    status_parser = subparsers.add_parser("status", help="Check agent status")
    status_parser.add_argument(
        "-d",
        "--data-dir",
        default="/Users/sac/dev/kgcl/data",
        help="Data directory to check",
    )

    # Config command
    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_parser.add_argument(
        "-g", "--generate", action="store_true", help="Generate default configuration"
    )
    config_parser.add_argument("-v", "--validate", help="Validate configuration file")
    config_parser.add_argument(
        "-o", "--output", help="Output file for generated config"
    )

    # Parse arguments
    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)

    # Execute command
    if args.command == "run":
        cmd_run(args)
    elif args.command == "discover":
        cmd_discover(args)
    elif args.command == "aggregate":
        cmd_aggregate(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "config":
        cmd_config(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

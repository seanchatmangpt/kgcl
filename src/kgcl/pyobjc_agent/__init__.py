"""
PyObjC Agent for macOS capability discovery and monitoring.

This package provides a comprehensive system for discovering and monitoring
macOS capabilities through PyObjC frameworks.

Main components:
- crawler: Framework and API discovery
- plugins: Capability-specific plugins
- collectors: Continuous event collection
- aggregators: Feature aggregation
- agent: Main daemon and orchestration

Usage:
    # Run as daemon
    python -m kgcl.pyobjc_agent run

    # Discover capabilities
    python -m kgcl.pyobjc_agent discover

    # Aggregate collected data
    python -m kgcl.pyobjc_agent aggregate data/frontmost_app.jsonl
"""

__version__ = "1.0.0"

from .agent import PyObjCAgent, create_default_agent
from .crawler import PyObjCFrameworkCrawler, FrameworkName
from .plugins import (
    BaseCapabilityPlugin,
    CapabilityDescriptor,
    CapabilityData,
    load_builtin_plugins,
    get_registry
)
from .collectors import (
    BaseCollector,
    CollectorConfig,
    create_frontmost_app_collector,
    create_browser_history_collector,
    create_calendar_collector
)
from .aggregators import (
    FeatureAggregator,
    FrontmostAppAggregator,
    BrowserHistoryAggregator,
    CalendarAggregator,
    aggregate_jsonl_file
)

__all__ = [
    # Agent
    "PyObjCAgent",
    "create_default_agent",

    # Crawler
    "PyObjCFrameworkCrawler",
    "FrameworkName",

    # Plugins
    "BaseCapabilityPlugin",
    "CapabilityDescriptor",
    "CapabilityData",
    "load_builtin_plugins",
    "get_registry",

    # Collectors
    "BaseCollector",
    "CollectorConfig",
    "create_frontmost_app_collector",
    "create_browser_history_collector",
    "create_calendar_collector",

    # Aggregators
    "FeatureAggregator",
    "FrontmostAppAggregator",
    "BrowserHistoryAggregator",
    "CalendarAggregator",
    "aggregate_jsonl_file",
]

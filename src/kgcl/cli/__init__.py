"""KGCL CLI - Knowledge Graph Capture & Learning Command Line Interface.

This module provides command-line tools for interacting with the KGCL system:

- kgc-daily-brief: Generate daily briefs from recent events
- kgc-weekly-retro: Generate weekly retrospectives
- kgc-feature-list: Browse and explore features
- kgc-query: Execute SPARQL queries against the knowledge graph
- kgc-config: Manage configuration settings

Each command provides comprehensive help via --help option.
"""

from kgcl.cli.config import config
from kgcl.cli.daily_brief import daily_brief
from kgcl.cli.feature_list import feature_list
from kgcl.cli.query import query
from kgcl.cli.weekly_retro import weekly_retro

__version__ = "0.1.0"

__all__ = [
    "config",
    "daily_brief",
    "feature_list",
    "query",
    "weekly_retro",
    "__version__",
]

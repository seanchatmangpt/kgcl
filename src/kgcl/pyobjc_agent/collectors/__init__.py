"""
Event collectors for continuous capability monitoring.

This package provides collectors that:
- Sample capabilities at regular intervals
- Batch events for efficient I/O
- Output JSONL format for streaming ingestion
- Support backpressure and buffering
"""

from .base import BaseCollector, CollectorConfig, CollectorStatus
from .browser_history_collector import BrowserHistoryCollector
from .calendar_collector import CalendarCollector
from .frontmost_app_collector import FrontmostAppCollector

__all__ = [
    "BaseCollector",
    "BrowserHistoryCollector",
    "CalendarCollector",
    "CollectorConfig",
    "CollectorStatus",
    "FrontmostAppCollector",
]

"""
Frontmost application collector.

Samples the currently active application at regular intervals
to build a timeline of application usage.
"""

import logging
from typing import Any

from ..plugins import get_registry
from .base import BaseCollector, CollectorConfig

logger = logging.getLogger(__name__)


class FrontmostAppCollector(BaseCollector):
    """
    Collector for frontmost application tracking.

    Samples the active application at intervals to build usage timeline.
    Useful for:
    - Application usage analytics
    - Context detection
    - Focus time tracking
    - Activity patterns
    """

    def __init__(self, config: CollectorConfig):
        """
        Initialize frontmost app collector.

        Args:
            config: Collector configuration
        """
        super().__init__(config)
        self._plugin = None
        self._last_app_bundle_id = None
        self._last_app_name = None
        self._session_start = None

    def validate_configuration(self) -> bool:
        """Validate collector configuration."""
        # Get AppKit plugin from registry
        registry = get_registry()
        self._plugin = registry.get_plugin("appkit", auto_initialize=True)

        if not self._plugin:
            logger.error("AppKit plugin not available for frontmost app collector")
            return False

        # Verify plugin has frontmost_application capability
        try:
            capability = self._plugin.get_capability_by_name("frontmost_application")
            if not capability:
                logger.error("frontmost_application capability not found")
                return False

            logger.info("Frontmost app collector validated successfully")
            return True

        except Exception as e:
            logger.error(f"Error validating frontmost app collector: {e}")
            return False

    def collect_event(self) -> dict[str, Any] | None:
        """
        Collect current frontmost application.

        Returns
        -------
            Event data with frontmost app info or None
        """
        try:
            # Collect frontmost app data
            capability_data = self._plugin.collect_capability_data("frontmost_application")

            if capability_data.error:
                logger.error(f"Error collecting frontmost app: {capability_data.error}")
                return None

            app_data = capability_data.data

            # Extract app info
            bundle_id = app_data.get("bundle_id")
            app_name = app_data.get("app_name")

            if not bundle_id:
                return None

            # Detect app switch
            is_switch = self._last_app_bundle_id is not None and bundle_id != self._last_app_bundle_id

            # Calculate session duration if switching
            session_duration = None
            if is_switch and self._session_start:
                from datetime import UTC, datetime

                current_time = datetime.now(UTC)
                session_duration = (current_time - self._session_start).total_seconds()

            # Update tracking
            if is_switch:
                from datetime import UTC, datetime

                self._session_start = datetime.now(UTC)

            self._last_app_bundle_id = bundle_id
            self._last_app_name = app_name

            # Build event
            event = {
                "bundle_id": bundle_id,
                "app_name": app_name,
                "process_id": app_data.get("process_id"),
                "is_active": app_data.get("is_active", True),
                "is_switch": is_switch,
                "session_duration_seconds": session_duration,
                "launch_date": app_data.get("launch_date"),
            }

            return event

        except Exception as e:
            logger.error(f"Error in frontmost app collection: {e}")
            raise


def create_frontmost_app_collector(
    interval_seconds: float = 1.0, output_path: str | None = None, **kwargs
) -> FrontmostAppCollector:
    """
    Factory function to create frontmost app collector.

    Args:
        interval_seconds: Sampling interval (default 1 second)
        output_path: Path to JSONL output file
        **kwargs: Additional collector config parameters

    Returns
    -------
        Configured FrontmostAppCollector instance
    """
    config = CollectorConfig(
        name="frontmost_app",
        interval_seconds=interval_seconds,
        output_path=output_path or "/Users/sac/dev/kgcl/data/frontmost_app.jsonl",
        batch_size=kwargs.get("batch_size", 50),
        batch_timeout_seconds=kwargs.get("batch_timeout_seconds", 60.0),
        **{k: v for k, v in kwargs.items() if k not in ["batch_size", "batch_timeout_seconds"]},
    )

    return FrontmostAppCollector(config)

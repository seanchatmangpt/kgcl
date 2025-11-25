"""
Browser history collector.

Periodically reads browser history databases to track
web browsing activity.
"""

import logging
from datetime import datetime
from typing import Any

from ..plugins import get_registry
from .base import BaseCollector, CollectorConfig

logger = logging.getLogger(__name__)


class BrowserHistoryCollector(BaseCollector):
    """
    Collector for browser history tracking.

    Periodically samples browser history to detect:
    - New page visits
    - Browsing patterns
    - Domain access
    - Session reconstruction
    """

    def __init__(self, config: CollectorConfig):
        """
        Initialize browser history collector.

        Args:
            config: Collector configuration
        """
        super().__init__(config)
        self._plugin = None
        self._seen_urls: set[str] = set()
        self._last_collection_time: datetime | None = None

    def validate_configuration(self) -> bool:
        """Validate collector configuration."""
        # Get browser plugin from registry
        registry = get_registry()
        self._plugin = registry.get_plugin("browser", auto_initialize=True)

        if not self._plugin:
            logger.error("Browser plugin not available for history collector")
            return False

        # Check entitlements
        entitlements = self._plugin.check_entitlements()
        has_access = any(entitlements.values())

        if not has_access:
            logger.warning(
                "No browser history access available. May require Full Disk Access permission."
            )
            # Continue anyway - will just collect empty data

        logger.info("Browser history collector validated successfully")
        return True

    def collect_event(self) -> dict[str, Any] | None:
        """
        Collect recent browser history entries.

        Returns
        -------
            Event data with new browser visits or None
        """
        try:
            # Determine time window
            if self._last_collection_time:
                # Only get history since last collection
                hours_back = (
                    datetime.utcnow() - self._last_collection_time
                ).total_seconds() / 3600.0
                hours_back = max(hours_back, 0.1)  # At least 6 minutes
            else:
                # First collection - get last hour
                hours_back = 1.0

            # Collect recent browsing activity
            capability_data = self._plugin.collect_capability_data(
                "recent_browsing_activity", parameters={"hours_back": hours_back}
            )

            if capability_data.error:
                logger.warning(f"Error collecting browser history: {capability_data.error}")
                return None

            activity_data = capability_data.data

            # Update last collection time
            self._last_collection_time = datetime.utcnow()

            # Get individual browser histories for new visits
            new_visits = []

            # Safari
            if activity_data.get("browsers", {}).get("safari", 0) > 0:
                safari_visits = self._get_new_visits("safari_history", hours_back)
                new_visits.extend(safari_visits)

            # Chrome
            if activity_data.get("browsers", {}).get("chrome", 0) > 0:
                chrome_visits = self._get_new_visits("chrome_history", hours_back)
                new_visits.extend(chrome_visits)

            # Build event
            event = {
                "total_visits": activity_data.get("total_visits", 0),
                "new_visits_count": len(new_visits),
                "new_visits": new_visits[:100],  # Limit to 100 per event
                "top_domains": activity_data.get("top_domains", []),
                "unique_domains": activity_data.get("unique_domains", 0),
                "time_window_hours": hours_back,
                "browsers": activity_data.get("browsers", {}),
            }

            return event

        except Exception as e:
            logger.error(f"Error in browser history collection: {e}")
            raise

    def _get_new_visits(self, capability_name: str, hours_back: float) -> list:
        """
        Get new visits from a specific browser.

        Args:
            capability_name: Browser capability name
            hours_back: Hours to look back

        Returns
        -------
            List of new visit dictionaries
        """
        try:
            capability_data = self._plugin.collect_capability_data(
                capability_name, parameters={"hours_back": hours_back, "limit": 200}
            )

            if capability_data.error:
                return []

            visits = capability_data.data.get("visits", [])

            # Filter for new URLs
            new_visits = []
            for visit in visits:
                url = visit.get("url")
                visit_time = visit.get("visit_time")

                # Create unique key (URL + timestamp for multiple visits)
                visit_key = f"{url}:{visit_time}"

                if visit_key not in self._seen_urls:
                    self._seen_urls.add(visit_key)
                    new_visits.append(
                        {
                            "browser": capability_name.replace("_history", ""),
                            "url": url,
                            "title": visit.get("title", ""),
                            "visit_time": visit_time,
                        }
                    )

            # Cleanup seen URLs set if too large
            if len(self._seen_urls) > 10000:
                # Keep only recent 5000
                self._seen_urls = set(list(self._seen_urls)[-5000:])

            return new_visits

        except Exception as e:
            logger.error(f"Error getting new visits for {capability_name}: {e}")
            return []


def create_browser_history_collector(
    interval_seconds: float = 300.0,  # 5 minutes
    output_path: str | None = None,
    **kwargs,
) -> BrowserHistoryCollector:
    """
    Factory function to create browser history collector.

    Args:
        interval_seconds: Sampling interval (default 5 minutes)
        output_path: Path to JSONL output file
        **kwargs: Additional collector config parameters

    Returns
    -------
        Configured BrowserHistoryCollector instance
    """
    config = CollectorConfig(
        name="browser_history",
        interval_seconds=interval_seconds,
        output_path=output_path or "/Users/sac/dev/kgcl/data/browser_history.jsonl",
        batch_size=kwargs.get("batch_size", 10),
        batch_timeout_seconds=kwargs.get("batch_timeout_seconds", 600.0),
        **{k: v for k, v in kwargs.items() if k not in ["batch_size", "batch_timeout_seconds"]},
    )

    return BrowserHistoryCollector(config)

"""
Calendar events collector.

Periodically queries calendar events to track:
- Upcoming appointments
- Meeting schedules
- Availability changes
- Calendar-based context
"""

import logging
from typing import Any

from ..plugins import get_registry
from .base import BaseCollector, CollectorConfig

logger = logging.getLogger(__name__)


class CalendarCollector(BaseCollector):
    """
    Collector for calendar events tracking.

    Monitors calendar for:
    - Upcoming events
    - Current meetings
    - Availability status
    - Schedule changes
    """

    def __init__(self, config: CollectorConfig):
        """
        Initialize calendar collector.

        Args:
            config: Collector configuration
        """
        super().__init__(config)
        self._plugin = None
        self._seen_event_ids: set[str] = set()
        self._last_availability_status = None

    def validate_configuration(self) -> bool:
        """Validate collector configuration."""
        # Get calendar plugin from registry
        registry = get_registry()
        self._plugin = registry.get_plugin("calendar", auto_initialize=True)

        if not self._plugin:
            logger.error("Calendar plugin not available for calendar collector")
            return False

        # Check entitlements
        entitlements = self._plugin.check_entitlements()
        has_access = entitlements.get("calendar_access", False)

        if not has_access:
            logger.warning(
                "Calendar access not granted. "
                "Grant access in System Preferences > Security & Privacy > Calendar"
            )
            # Continue anyway - will just collect empty data

        logger.info("Calendar collector validated successfully")
        return True

    def collect_event(self) -> dict[str, Any] | None:
        """
        Collect calendar event data.

        Returns
        -------
            Event data with calendar information or None
        """
        try:
            # Get upcoming events
            upcoming_data = self._plugin.collect_capability_data("upcoming_events")

            if upcoming_data.error:
                logger.warning(
                    f"Error collecting upcoming events: {upcoming_data.error}"
                )
                return {
                    "error": upcoming_data.error,
                    "upcoming_count": 0,
                    "events_today": 0,
                }

            upcoming = upcoming_data.data

            # Get availability status
            availability_data = self._plugin.collect_capability_data(
                "availability_status"
            )
            availability = availability_data.data if not availability_data.error else {}

            # Detect availability changes
            current_status = availability.get("is_busy", False)
            status_changed = (
                self._last_availability_status is not None
                and current_status != self._last_availability_status
            )
            self._last_availability_status = current_status

            # Get current and next events
            current_event = availability.get("current_event")
            next_event = upcoming.get("next_event")

            # Build unique event IDs to detect new events
            current_event_id = None
            if current_event:
                current_event_id = self._make_event_id(current_event)

            next_event_id = None
            if next_event:
                next_event_id = self._make_event_id(next_event)

            # Check for new events
            new_event_started = (
                current_event_id and current_event_id not in self._seen_event_ids
            )

            if current_event_id:
                self._seen_event_ids.add(current_event_id)

            if next_event_id:
                self._seen_event_ids.add(next_event_id)

            # Cleanup seen events set
            if len(self._seen_event_ids) > 1000:
                self._seen_event_ids = set(list(self._seen_event_ids)[-500:])

            # Build event
            event = {
                "upcoming_count": upcoming.get("count", 0),
                "events_today": upcoming.get("events_today", 0),
                "events_24h": upcoming.get("upcoming_24h", 0),
                "is_busy": current_status,
                "availability_changed": status_changed,
                "new_event_started": new_event_started,
                "current_event": current_event,
                "next_event": next_event,
                "next_free_slot": availability.get("next_free_slot"),
            }

            return event

        except Exception as e:
            logger.error(f"Error in calendar collection: {e}")
            raise

    def _make_event_id(self, event: dict[str, Any]) -> str:
        """
        Create unique ID for an event.

        Args:
            event: Event dictionary

        Returns
        -------
            Unique event identifier
        """
        return f"{event.get('title', '')}:{event.get('start_date', '')}"


def create_calendar_collector(
    interval_seconds: float = 300.0,  # 5 minutes
    output_path: str | None = None,
    **kwargs,
) -> CalendarCollector:
    """
    Factory function to create calendar collector.

    Args:
        interval_seconds: Sampling interval (default 5 minutes)
        output_path: Path to JSONL output file
        **kwargs: Additional collector config parameters

    Returns
    -------
        Configured CalendarCollector instance
    """
    config = CollectorConfig(
        name="calendar_events",
        interval_seconds=interval_seconds,
        output_path=output_path or "/Users/sac/dev/kgcl/data/calendar_events.jsonl",
        batch_size=kwargs.get("batch_size", 10),
        batch_timeout_seconds=kwargs.get("batch_timeout_seconds", 600.0),
        **{
            k: v
            for k, v in kwargs.items()
            if k not in ["batch_size", "batch_timeout_seconds"]
        },
    )

    return CalendarCollector(config)

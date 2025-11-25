"""
Calendar plugin for EventKit integration.

This plugin provides capabilities for:
- Reading calendar events
- Querying event stores
- Calendar availability tracking
- Meeting/appointment detection
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from .base import BaseCapabilityPlugin, CapabilityData, CapabilityDescriptor, EntitlementLevel

logger = logging.getLogger(__name__)


class CalendarPlugin(BaseCapabilityPlugin):
    """
    EventKit-based calendar capability discovery plugin.

    Provides access to:
    - Calendar events
    - Reminders
    - Event availability
    - Calendar metadata
    """

    @property
    def plugin_name(self) -> str:
        return "Calendar EventKit Plugin"

    @property
    def plugin_version(self) -> str:
        return "1.0.0"

    @property
    def required_frameworks(self) -> list[str]:
        return ["EventKit", "Foundation"]

    def discover_capabilities(self) -> list[CapabilityDescriptor]:
        """Discover calendar-related capabilities."""
        capabilities = [
            CapabilityDescriptor(
                name="calendar_events",
                description="Query calendar events within a time range",
                framework="EventKit",
                required_entitlement=EntitlementLevel.CALENDAR,
                refresh_interval=300.0,  # 5 minutes
                tags={"calendar", "events", "scheduling"},
                data_schema={
                    "type": "object",
                    "properties": {
                        "events": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "start_date": {"type": "string", "format": "date-time"},
                                    "end_date": {"type": "string", "format": "date-time"},
                                    "location": {"type": "string"},
                                    "is_all_day": {"type": "boolean"},
                                    "calendar_name": {"type": "string"},
                                },
                            },
                        }
                    },
                },
            ),
            CapabilityDescriptor(
                name="upcoming_events",
                description="Get upcoming calendar events",
                framework="EventKit",
                required_entitlement=EntitlementLevel.CALENDAR,
                refresh_interval=60.0,
                tags={"calendar", "events", "upcoming"},
                data_schema={
                    "type": "object",
                    "properties": {
                        "count": {"type": "integer"},
                        "next_event": {"type": "object"},
                        "events_today": {"type": "integer"},
                    },
                },
            ),
            CapabilityDescriptor(
                name="calendar_list",
                description="List available calendars",
                framework="EventKit",
                required_entitlement=EntitlementLevel.CALENDAR,
                refresh_interval=3600.0,  # 1 hour
                tags={"calendar", "metadata"},
                data_schema={
                    "type": "object",
                    "properties": {
                        "calendars": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "type": {"type": "string"},
                                    "color": {"type": "string"},
                                    "is_subscribed": {"type": "boolean"},
                                },
                            },
                        }
                    },
                },
            ),
            CapabilityDescriptor(
                name="availability_status",
                description="Check calendar availability for time periods",
                framework="EventKit",
                required_entitlement=EntitlementLevel.CALENDAR,
                refresh_interval=300.0,
                tags={"calendar", "availability", "scheduling"},
                data_schema={
                    "type": "object",
                    "properties": {
                        "is_busy": {"type": "boolean"},
                        "current_event": {"type": "object"},
                        "next_free_slot": {"type": "string", "format": "date-time"},
                    },
                },
            ),
        ]

        return capabilities

    def check_entitlements(self) -> dict[str, bool]:
        """Check for calendar access entitlements."""
        entitlements = {"calendar_access": self._check_calendar_access()}

        return entitlements

    def _check_calendar_access(self) -> bool:
        """
        Check if calendar access is granted.

        Returns
        -------
            True if calendar access is available
        """
        try:
            from EventKit import EKEventStore

            store = EKEventStore.alloc().init()

            # Check authorization status
            # Note: This doesn't prompt, just checks current status
            # In a real app, you'd use requestAccessToEntityType:completion:
            auth_status = store.authorizationStatusForEntityType_(0)  # EKEntityTypeEvent

            # 0 = Not Determined, 1 = Restricted, 2 = Denied, 3 = Authorized
            if auth_status != 3:
                logger.warning(
                    f"Calendar access not authorized. Status: {auth_status}. "
                    "Grant calendar access in System Preferences > Security & Privacy > Calendar"
                )
                return False

            return True

        except Exception as e:
            logger.error(f"Error checking calendar access: {e}")
            return False

    def collect_capability_data(
        self, capability_name: str, parameters: dict[str, Any] | None = None
    ) -> CapabilityData:
        """Collect calendar data."""
        timestamp = datetime.utcnow()
        params = parameters or {}

        try:
            if capability_name == "calendar_events":
                data = self._get_calendar_events(params)
            elif capability_name == "upcoming_events":
                data = self._get_upcoming_events(params)
            elif capability_name == "calendar_list":
                data = self._get_calendar_list()
            elif capability_name == "availability_status":
                data = self._get_availability_status(params)
            else:
                raise ValueError(f"Unknown capability: {capability_name}")

            return CapabilityData(
                capability_name=capability_name,
                timestamp=timestamp,
                data=data,
                metadata={"plugin": self.plugin_id},
            )

        except Exception as e:
            logger.error(f"Error collecting {capability_name}: {e}")
            return CapabilityData(
                capability_name=capability_name, timestamp=timestamp, data={}, error=str(e)
            )

    def _get_event_store(self):
        """Get or create EventKit event store."""
        try:
            from EventKit import EKEventStore

            return EKEventStore.alloc().init()
        except Exception as e:
            logger.error(f"Failed to create event store: {e}")
            raise

    def _get_calendar_events(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Query calendar events within a time range.

        Args:
            params: Query parameters (start_date, end_date, days_ahead, etc.)

        Returns
        -------
            Dictionary with calendar events
        """
        try:
            from Foundation import NSDate

            store = self._get_event_store()

            # Parse time range parameters
            days_ahead = params.get("days_ahead", 7)
            start_date = params.get("start_date")
            end_date = params.get("end_date")

            if not start_date:
                start_date = datetime.utcnow()
            elif isinstance(start_date, str):
                start_date = datetime.fromisoformat(start_date)

            if not end_date:
                end_date = start_date + timedelta(days=days_ahead)
            elif isinstance(end_date, str):
                end_date = datetime.fromisoformat(end_date)

            # Convert to NSDate
            ns_start = NSDate.dateWithTimeIntervalSince1970_(start_date.timestamp())
            ns_end = NSDate.dateWithTimeIntervalSince1970_(end_date.timestamp())

            # Get calendars
            calendars = store.calendarsForEntityType_(0)  # EKEntityTypeEvent

            if not calendars:
                return {"error": "No calendars available or access denied", "events": []}

            # Create predicate for date range
            predicate = store.predicateForEventsWithStartDate_endDate_calendars_(
                ns_start, ns_end, calendars
            )

            # Fetch events
            events = store.eventsMatchingPredicate_(predicate)

            event_list = []
            for event in events:
                event_data = {
                    "title": str(event.title()) if event.title() else "",
                    "start_date": datetime.fromtimestamp(
                        event.startDate().timeIntervalSince1970()
                    ).isoformat(),
                    "end_date": datetime.fromtimestamp(
                        event.endDate().timeIntervalSince1970()
                    ).isoformat(),
                    "is_all_day": bool(event.isAllDay()),
                    "location": str(event.location()) if event.location() else "",
                    "calendar_name": str(event.calendar().title()) if event.calendar() else "",
                    "has_attendees": bool(event.attendees() and len(event.attendees()) > 0),
                    "status": event.status(),  # 0=None, 1=Confirmed, 2=Tentative, 3=Cancelled
                }

                event_list.append(event_data)

            return {
                "count": len(event_list),
                "events": event_list,
                "query_params": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
            }

        except Exception as e:
            logger.error(f"Error fetching calendar events: {e}")
            raise

    def _get_upcoming_events(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Get upcoming calendar events.

        Args:
            params: Query parameters

        Returns
        -------
            Dictionary with upcoming events summary
        """
        # Get events for next 24 hours
        events_data = self._get_calendar_events({"days_ahead": 1})

        events = events_data.get("events", [])

        # Find next event
        now = datetime.utcnow()
        future_events = [e for e in events if datetime.fromisoformat(e["start_date"]) > now]

        # Sort by start time
        future_events.sort(key=lambda e: e["start_date"])

        next_event = future_events[0] if future_events else None

        # Count today's events
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        events_today = len(
            [
                e
                for e in events
                if today_start <= datetime.fromisoformat(e["start_date"]) < today_end
            ]
        )

        return {
            "count": len(future_events),
            "next_event": next_event,
            "events_today": events_today,
            "upcoming_24h": len(future_events),
        }

    def _get_calendar_list(self) -> dict[str, Any]:
        """
        Get list of available calendars.

        Returns
        -------
            Dictionary with calendar metadata
        """
        try:
            store = self._get_event_store()
            calendars = store.calendarsForEntityType_(0)  # EKEntityTypeEvent

            calendar_list = []
            for calendar in calendars:
                calendar_data = {
                    "title": str(calendar.title()) if calendar.title() else "",
                    "type": calendar.type(),  # 0=Local, 1=CalDAV, 2=Exchange, etc.
                    "is_subscribed": bool(calendar.isSubscribed()),
                    "allows_modifications": bool(calendar.allowsContentModifications()),
                }

                # Get color if available
                if hasattr(calendar, "color") and calendar.color():
                    color = calendar.color()
                    # Convert CGColor to hex (simplified)
                    calendar_data["color"] = "N/A"  # Would need more complex conversion

                calendar_list.append(calendar_data)

            return {"count": len(calendar_list), "calendars": calendar_list}

        except Exception as e:
            logger.error(f"Error fetching calendar list: {e}")
            raise

    def _get_availability_status(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Check current availability status.

        Args:
            params: Query parameters

        Returns
        -------
            Dictionary with availability information
        """
        now = datetime.utcnow()

        # Get events for current time window
        events_data = self._get_calendar_events({"start_date": now.isoformat(), "days_ahead": 1})

        events = events_data.get("events", [])

        # Find current event
        current_event = None
        for event in events:
            start = datetime.fromisoformat(event["start_date"])
            end = datetime.fromisoformat(event["end_date"])
            if start <= now <= end:
                current_event = event
                break

        # Find next free slot
        next_free_slot = None
        if current_event:
            # Free after current event ends
            next_free_slot = current_event["end_date"]
        else:
            # Currently free
            next_free_slot = now.isoformat()

        return {
            "is_busy": current_event is not None,
            "current_event": current_event,
            "next_free_slot": next_free_slot,
            "checked_at": now.isoformat(),
        }

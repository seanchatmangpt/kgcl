"""
Feature aggregators for time-windowed event processing.

Aggregates collected events into feature values suitable for
knowledge graph ingestion and analysis.
"""

import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TimeWindow:
    """Represents a time window for aggregation."""

    start_time: datetime
    end_time: datetime
    window_type: str = "hour"  # hour, day, week

    @property
    def duration_seconds(self) -> float:
        """Get duration in seconds."""
        return (self.end_time - self.start_time).total_seconds()

    def contains(self, timestamp: datetime) -> bool:
        """Check if timestamp falls within window."""
        return self.start_time <= timestamp < self.end_time


@dataclass
class AggregatedFeature:
    """
    An aggregated feature computed from events.

    Attributes
    ----------
        feature_name: Name of the feature
        time_window: Time window for aggregation
        value: Computed feature value
        unit: Unit of measurement
        metadata: Additional metadata
    """

    feature_name: str
    time_window: TimeWindow
    value: Any
    unit: str = "count"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "feature": self.feature_name,
            "value": self.value,
            "unit": self.unit,
            "time_window": {
                "start": self.time_window.start_time.isoformat(),
                "end": self.time_window.end_time.isoformat(),
                "type": self.time_window.window_type,
            },
            "metadata": self.metadata,
        }


class FeatureAggregator:
    """
    Base class for feature aggregation.

    Processes JSONL event streams and computes aggregated features
    over time windows.
    """

    def __init__(self, window_size_hours: float = 1.0):
        """
        Initialize aggregator.

        Args:
            window_size_hours: Size of aggregation window in hours
        """
        self.window_size_hours = window_size_hours
        self._current_window: TimeWindow | None = None
        self._events_buffer: list[dict[str, Any]] = []

    def add_event(self, event: dict[str, Any]) -> None:
        """
        Add event to aggregation buffer.

        Args:
            event: Event dictionary with timestamp
        """
        self._events_buffer.append(event)

    def _create_window(self, start_time: datetime) -> TimeWindow:
        """
        Create a time window.

        Args:
            start_time: Window start time

        Returns
        -------
            TimeWindow instance
        """
        # Round start time to hour
        rounded_start = start_time.replace(minute=0, second=0, microsecond=0)
        end_time = rounded_start + timedelta(hours=self.window_size_hours)

        return TimeWindow(
            start_time=rounded_start,
            end_time=end_time,
            window_type="hour" if self.window_size_hours <= 1 else "custom",
        )

    def aggregate(self, events: list[dict[str, Any]]) -> list[AggregatedFeature]:
        """
        Aggregate events into features.

        Args:
            events: List of events to aggregate

        Returns
        -------
            List of aggregated features

        Note: Subclasses should override this method
        """
        raise NotImplementedError("Subclasses must implement aggregate()")


class FrontmostAppAggregator(FeatureAggregator):
    """
    Aggregator for frontmost application events.

    Computes features like:
    - Total time per application
    - Application switch count
    - Most used applications
    - Focus time metrics
    """

    def aggregate(self, events: list[dict[str, Any]]) -> list[AggregatedFeature]:
        """Aggregate frontmost app events."""
        if not events:
            return []

        # Group events by time windows
        windows: dict[TimeWindow, list[dict[str, Any]]] = self._group_by_windows(events)

        features = []

        for window, window_events in windows.items():
            # Calculate app usage time
            app_times: dict[str, float] = self._calculate_app_times(window_events)

            # App switch count
            switch_count = sum(
                1 for e in window_events if e.get("data", {}).get("is_switch", False)
            )

            # Most used app
            most_used_app = (
                max(app_times.items(), key=lambda x: x[1])[0] if app_times else None
            )

            # Total active time
            total_time = sum(app_times.values())

            # Create features
            features.append(
                AggregatedFeature(
                    feature_name="app_usage_total_minutes",
                    time_window=window,
                    value=round(total_time / 60.0, 2),
                    unit="minutes",
                )
            )

            features.append(
                AggregatedFeature(
                    feature_name="app_switch_count",
                    time_window=window,
                    value=switch_count,
                    unit="count",
                )
            )

            features.append(
                AggregatedFeature(
                    feature_name="unique_apps_used",
                    time_window=window,
                    value=len(app_times),
                    unit="count",
                )
            )

            if most_used_app:
                features.append(
                    AggregatedFeature(
                        feature_name="most_used_app",
                        time_window=window,
                        value=most_used_app,
                        unit="app_name",
                        metadata={
                            "duration_minutes": round(
                                app_times[most_used_app] / 60.0, 2
                            )
                        },
                    )
                )

        return features

    def _group_by_windows(
        self, events: list[dict[str, Any]]
    ) -> dict[TimeWindow, list[dict[str, Any]]]:
        """Group events by time windows."""
        windows: dict[TimeWindow, list[dict[str, Any]]] = {}

        for event in events:
            timestamp_str = event.get("timestamp")
            if not timestamp_str:
                continue

            timestamp = datetime.fromisoformat(timestamp_str)
            window = self._create_window(timestamp)

            # Find or create window
            window_key = None
            for w in windows:
                if w.start_time == window.start_time:
                    window_key = w
                    break

            if window_key is None:
                window_key = window
                windows[window_key] = []

            windows[window_key].append(event)

        return windows

    def _calculate_app_times(self, events: list[dict[str, Any]]) -> dict[str, float]:
        """
        Calculate time spent in each app.

        Args:
            events: Events within a time window

        Returns
        -------
            Dictionary mapping app names to seconds
        """
        app_times: defaultdict[str, float] = defaultdict(float)

        # Sort events by timestamp
        sorted_events = sorted(events, key=lambda e: e.get("timestamp", ""))

        for i, event in enumerate(sorted_events):
            data = event.get("data", {})
            app_name = data.get("app_name", "Unknown")

            # Calculate duration until next event or use session duration
            if i < len(sorted_events) - 1:
                # Time until next event
                current_timestamp = event.get("timestamp")
                next_timestamp = sorted_events[i + 1].get("timestamp")
                if current_timestamp is not None and next_timestamp is not None:
                    current_time = datetime.fromisoformat(current_timestamp)
                    next_time = datetime.fromisoformat(next_timestamp)
                    duration = (next_time - current_time).total_seconds()
                else:
                    duration = 0
            else:
                # Last event - use session duration if available
                duration = data.get("session_duration_seconds", 0) or 0

            app_times[app_name] += duration

        return dict(app_times)


class BrowserHistoryAggregator(FeatureAggregator):
    """
    Aggregator for browser history events.

    Computes features like:
    - Total page visits
    - Unique domains visited
    - Top domains
    - Browser usage distribution
    """

    def aggregate(self, events: list[dict[str, Any]]) -> list[AggregatedFeature]:
        """Aggregate browser history events."""
        if not events:
            return []

        windows = self._group_by_windows(events)
        features = []

        for window, window_events in windows.items():
            # Total visits
            total_visits = sum(
                e.get("data", {}).get("total_visits", 0) for e in window_events
            )

            # New visits
            new_visits_count = sum(
                e.get("data", {}).get("new_visits_count", 0) for e in window_events
            )

            # Unique domains
            unique_domains = set()
            for event in window_events:
                data = event.get("data", {})
                for domain_data in data.get("top_domains", []):
                    unique_domains.add(domain_data.get("domain"))

            # Browser usage
            browser_visits: defaultdict[str, int] = defaultdict(int)
            for event in window_events:
                browsers = event.get("data", {}).get("browsers", {})
                for browser, count in browsers.items():
                    browser_visits[browser] += count

            # Create features
            features.append(
                AggregatedFeature(
                    feature_name="browser_total_visits",
                    time_window=window,
                    value=total_visits,
                    unit="count",
                )
            )

            features.append(
                AggregatedFeature(
                    feature_name="browser_new_visits",
                    time_window=window,
                    value=new_visits_count,
                    unit="count",
                )
            )

            features.append(
                AggregatedFeature(
                    feature_name="browser_unique_domains",
                    time_window=window,
                    value=len(unique_domains),
                    unit="count",
                )
            )

            features.append(
                AggregatedFeature(
                    feature_name="browser_usage_distribution",
                    time_window=window,
                    value=dict(browser_visits),
                    unit="count_per_browser",
                    metadata={"browsers": list(browser_visits.keys())},
                )
            )

        return features

    def _group_by_windows(
        self, events: list[dict[str, Any]]
    ) -> dict[TimeWindow, list[dict[str, Any]]]:
        """Group events by time windows."""
        windows: dict[TimeWindow, list[dict[str, Any]]] = {}

        for event in events:
            timestamp_str = event.get("timestamp")
            if not timestamp_str:
                continue

            timestamp = datetime.fromisoformat(timestamp_str)
            window = self._create_window(timestamp)

            window_key = None
            for w in windows:
                if w.start_time == window.start_time:
                    window_key = w
                    break

            if window_key is None:
                window_key = window
                windows[window_key] = []

            windows[window_key].append(event)

        return windows


class CalendarAggregator(FeatureAggregator):
    """
    Aggregator for calendar events.

    Computes features like:
    - Meeting count
    - Busy time percentage
    - Event frequency
    - Availability patterns
    """

    def aggregate(self, events: list[dict[str, Any]]) -> list[AggregatedFeature]:
        """Aggregate calendar events."""
        if not events:
            return []

        windows = self._group_by_windows(events)
        features = []

        for window, window_events in windows.items():
            # Count times when busy
            busy_count = sum(
                1 for e in window_events if e.get("data", {}).get("is_busy", False)
            )

            # Average upcoming events
            avg_upcoming = (
                sum(e.get("data", {}).get("upcoming_count", 0) for e in window_events)
                / len(window_events)
                if window_events
                else 0
            )

            # New events started
            new_events = sum(
                1
                for e in window_events
                if e.get("data", {}).get("new_event_started", False)
            )

            # Events today (use latest value)
            events_today = (
                window_events[-1].get("data", {}).get("events_today", 0)
                if window_events
                else 0
            )

            # Create features
            features.append(
                AggregatedFeature(
                    feature_name="calendar_busy_samples",
                    time_window=window,
                    value=busy_count,
                    unit="count",
                    metadata={"total_samples": len(window_events)},
                )
            )

            features.append(
                AggregatedFeature(
                    feature_name="calendar_avg_upcoming_events",
                    time_window=window,
                    value=round(avg_upcoming, 2),
                    unit="count",
                )
            )

            features.append(
                AggregatedFeature(
                    feature_name="calendar_new_events_started",
                    time_window=window,
                    value=new_events,
                    unit="count",
                )
            )

            features.append(
                AggregatedFeature(
                    feature_name="calendar_events_today",
                    time_window=window,
                    value=events_today,
                    unit="count",
                )
            )

        return features

    def _group_by_windows(
        self, events: list[dict[str, Any]]
    ) -> dict[TimeWindow, list[dict[str, Any]]]:
        """Group events by time windows."""
        windows: dict[TimeWindow, list[dict[str, Any]]] = {}

        for event in events:
            timestamp_str = event.get("timestamp")
            if not timestamp_str:
                continue

            timestamp = datetime.fromisoformat(timestamp_str)
            window = self._create_window(timestamp)

            window_key = None
            for w in windows:
                if w.start_time == window.start_time:
                    window_key = w
                    break

            if window_key is None:
                window_key = window
                windows[window_key] = []

            windows[window_key].append(event)

        return windows


def aggregate_jsonl_file(
    input_path: str, aggregator: FeatureAggregator, output_path: str | None = None
) -> list[AggregatedFeature]:
    """
    Aggregate events from a JSONL file.

    Args:
        input_path: Path to input JSONL file
        aggregator: Aggregator instance to use
        output_path: Optional path to write aggregated features

    Returns
    -------
        List of aggregated features
    """
    logger.info(f"Aggregating events from {input_path}")

    # Read events
    events = []
    try:
        with open(input_path) as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))

        logger.info(f"Loaded {len(events)} events")

    except FileNotFoundError:
        logger.warning(f"Input file not found: {input_path}")
        return []
    except Exception as e:
        logger.error(f"Error reading input file: {e}")
        raise

    # Aggregate
    features = aggregator.aggregate(events)
    logger.info(f"Computed {len(features)} aggregated features")

    # Write output if specified
    if output_path:
        try:
            output = {
                "aggregated_at": datetime.now(UTC).isoformat(),
                "input_file": input_path,
                "event_count": len(events),
                "feature_count": len(features),
                "features": [f.to_dict() for f in features],
            }

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(output, f, indent=2)

            logger.info(f"Wrote aggregated features to {output_path}")

        except Exception as e:
            logger.error(f"Error writing output file: {e}")
            raise

    return features

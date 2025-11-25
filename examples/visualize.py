"""Visualization utilities for KGC OS Graph Agent demonstration.

Provides ASCII-based visualizations of:
- Daily activity timelines
- Feature value charts
- Pattern highlights
- Summary statistics
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from kgcl.ingestion.models import AppEvent, BrowserVisit, CalendarBlock, MaterializedFeature


class ActivityVisualizer:
    """Visualize activity data and features."""

    def __init__(self, width: int = 80) -> None:
        """Initialize visualizer.

        Parameters
        ----------
        width : int
            Character width for visualizations (default: 80)
        """
        self.width = width

    def visualize_timeline(
        self, events: list[AppEvent | BrowserVisit | CalendarBlock], date: datetime | None = None
    ) -> str:
        """Generate ASCII timeline of a day's activity.

        Parameters
        ----------
        events : list[AppEvent | BrowserVisit | CalendarBlock]
            Events to visualize
        date : datetime, optional
            Target date (defaults to first event's date)

        Returns
        -------
        str
            ASCII timeline representation
        """
        if not events:
            return "No events to visualize"

        # Determine date range
        if date is None:
            date = events[0].timestamp.replace(hour=0, minute=0, second=0, microsecond=0)

        start_of_day = date.replace(hour=0)
        end_of_day = date.replace(hour=23, minute=59)

        # Filter events for this day
        day_events = [
            e for e in events if start_of_day <= e.timestamp < end_of_day + timedelta(days=1)
        ]

        if not day_events:
            return f"No events on {date.date()}"

        # Build timeline
        lines = []
        lines.append(f"\n{'=' * self.width}")
        lines.append(f"Activity Timeline - {date.date()}".center(self.width))
        lines.append(f"{'=' * self.width}\n")

        # Hour markers
        hours_line = "Hour: "
        for hour in range(24):
            hours_line += f"{hour:2d} "
        lines.append(hours_line[: self.width])
        lines.append("-" * min(len(hours_line), self.width))

        # Group events by hour
        hourly_events: dict[int, list] = defaultdict(list)
        for event in day_events:
            hour = event.timestamp.hour
            hourly_events[hour].append(event)

        # Create activity bars
        activity_line = "      "
        for hour in range(24):
            count = len(hourly_events[hour])
            if count == 0:
                activity_line += " . "
            elif count <= 2:
                activity_line += " ▂ "
            elif count <= 5:
                activity_line += " ▄ "
            else:
                activity_line += " █ "

        lines.append(activity_line[: self.width])
        lines.append("")

        # Event details by type
        lines.append("Event Breakdown:")
        lines.append(f"  Total Events: {len(day_events)}")

        app_events = [e for e in day_events if isinstance(e, AppEvent)]
        browser_events = [e for e in day_events if isinstance(e, BrowserVisit)]
        calendar_events = [e for e in day_events if isinstance(e, CalendarBlock)]

        lines.append(f"  - App Events: {len(app_events)}")
        lines.append(f"  - Browser Visits: {len(browser_events)}")
        lines.append(f"  - Calendar Events: {len(calendar_events)}")

        # Peak activity hour
        if hourly_events:
            peak_hour = max(hourly_events.keys(), key=lambda h: len(hourly_events[h]))
            lines.append(f"  - Peak Hour: {peak_hour}:00 ({len(hourly_events[peak_hour])} events)")

        lines.append("")
        return "\n".join(lines)

    def visualize_features(self, features: list[MaterializedFeature], top_n: int = 10) -> str:
        """Generate ASCII chart of feature values.

        Parameters
        ----------
        features : list[MaterializedFeature]
            Features to visualize
        top_n : int
            Number of top features to show (default: 10)

        Returns
        -------
        str
            ASCII chart representation
        """
        if not features:
            return "No features to visualize"

        lines = []
        lines.append(f"\n{'=' * self.width}")
        lines.append("Top Features".center(self.width))
        lines.append(f"{'=' * self.width}\n")

        # Sort by value (numeric features only)
        numeric_features = [f for f in features if isinstance(f.value, (int, float))]

        if not numeric_features:
            lines.append("No numeric features to display")
            return "\n".join(lines)

        sorted_features = sorted(numeric_features, key=lambda f: float(f.value), reverse=True)[
            :top_n
        ]

        # Find max value for scaling
        max_value = max(float(f.value) for f in sorted_features)
        if max_value == 0:
            max_value = 1

        # Generate bars
        label_width = 30
        bar_width = self.width - label_width - 15  # Leave space for value

        for feature in sorted_features:
            value = float(feature.value)
            bar_length = int((value / max_value) * bar_width)

            # Truncate feature ID if too long
            feature_id = feature.feature_id
            if len(feature_id) > label_width:
                feature_id = feature_id[: label_width - 3] + "..."

            # Format value
            if value >= 1000:
                value_str = f"{value / 1000:.1f}k"
            elif value >= 1:
                value_str = f"{value:.1f}"
            else:
                value_str = f"{value:.3f}"

            bar = "█" * bar_length
            line = f"{feature_id:<{label_width}} {bar} {value_str}"
            lines.append(line)

        lines.append("")
        return "\n".join(lines)

    def visualize_patterns(self, events: list[AppEvent | BrowserVisit | CalendarBlock]) -> str:
        """Highlight interesting patterns in activity.

        Parameters
        ----------
        events : list[AppEvent | BrowserVisit | CalendarBlock]
            Events to analyze

        Returns
        -------
        str
            Pattern summary
        """
        lines = []
        lines.append(f"\n{'=' * self.width}")
        lines.append("Activity Patterns".center(self.width))
        lines.append(f"{'=' * self.width}\n")

        # App usage patterns
        app_events = [e for e in events if isinstance(e, AppEvent)]
        if app_events:
            app_durations: dict[str, float] = defaultdict(float)
            for event in app_events:
                if event.duration_seconds:
                    app_durations[event.app_display_name or event.app_name] += (
                        event.duration_seconds
                    )

            if app_durations:
                top_app = max(app_durations.keys(), key=lambda a: app_durations[a])
                top_duration = app_durations[top_app]
                lines.append(f"Most Used App: {top_app}")
                lines.append(f"  Total Time: {self._format_duration(top_duration)}")
                lines.append("")

        # Browser patterns
        browser_events = [e for e in events if isinstance(e, BrowserVisit)]
        if browser_events:
            domain_visits: dict[str, int] = defaultdict(int)
            for event in browser_events:
                domain_visits[event.domain] += 1

            if domain_visits:
                top_domain = max(domain_visits.keys(), key=lambda d: domain_visits[d])
                lines.append(f"Most Visited Domain: {top_domain}")
                lines.append(f"  Visit Count: {domain_visits[top_domain]}")
                lines.append("")

        # Context switches
        if len(app_events) > 1:
            switches = 0
            prev_app = None
            for event in sorted(app_events, key=lambda e: e.timestamp):
                if prev_app and event.app_name != prev_app:
                    switches += 1
                prev_app = event.app_name

            lines.append(f"Context Switches: {switches}")
            if switches > 0:
                avg_time = (
                    app_events[-1].timestamp - app_events[0].timestamp
                ).total_seconds() / switches
                lines.append(f"  Avg Time Between Switches: {self._format_duration(avg_time)}")
            lines.append("")

        # Meeting load
        calendar_events = [e for e in events if isinstance(e, CalendarBlock)]
        if calendar_events:
            total_meeting_time = sum(
                (e.end_time - e.timestamp).total_seconds() for e in calendar_events
            )
            lines.append("Meeting Load:")
            lines.append(f"  Total Meetings: {len(calendar_events)}")
            lines.append(f"  Total Time: {self._format_duration(total_meeting_time)}")
            lines.append("")

        return "\n".join(lines)

    def generate_summary_table(self, stats: dict[str, Any]) -> str:
        """Generate summary statistics table.

        Parameters
        ----------
        stats : dict[str, Any]
            Statistics dictionary

        Returns
        -------
        str
            Formatted table
        """
        lines = []
        lines.append(f"\n{'=' * self.width}")
        lines.append("Summary Statistics".center(self.width))
        lines.append(f"{'=' * self.width}\n")

        # Format each stat
        for key, value in stats.items():
            # Format key
            display_key = key.replace("_", " ").title()

            # Format value
            if isinstance(value, float):
                if value >= 1000:
                    display_value = f"{value / 1000:.2f}k"
                else:
                    display_value = f"{value:.2f}"
            elif isinstance(value, int):
                display_value = f"{value:,}"
            elif isinstance(value, dict):
                display_value = f"{len(value)} items"
            else:
                display_value = str(value)

            line = f"  {display_key:<30} {display_value:>15}"
            lines.append(line)

        lines.append("")
        return "\n".join(lines)

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable form.

        Parameters
        ----------
        seconds : float
            Duration in seconds

        Returns
        -------
        str
            Formatted duration
        """
        if seconds < 60:
            return f"{seconds:.0f}s"
        if seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        hours = seconds / 3600
        return f"{hours:.1f}h"


def print_all_visualizations(
    events: list[AppEvent | BrowserVisit | CalendarBlock],
    features: list[MaterializedFeature],
    stats: dict[str, Any],
) -> None:
    """Print all visualizations to console.

    Parameters
    ----------
    events : list[AppEvent | BrowserVisit | CalendarBlock]
        Events to visualize
    features : list[MaterializedFeature]
        Features to visualize
    stats : dict[str, Any]
        Statistics to display
    """
    visualizer = ActivityVisualizer()

    print(visualizer.visualize_timeline(events))
    print(visualizer.visualize_features(features))
    print(visualizer.visualize_patterns(events))
    print(visualizer.generate_summary_table(stats))


if __name__ == "__main__":
    # Demo visualization
    from datetime import datetime

    from kgcl.ingestion.models import AppEvent

    # Create sample events
    base_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    sample_events = [
        AppEvent(
            event_id=f"evt_{i}",
            timestamp=base_time + timedelta(hours=i),
            app_name="com.example.app",
            app_display_name="Example App",
            duration_seconds=1800,
        )
        for i in range(8)
    ]

    visualizer = ActivityVisualizer()
    print(visualizer.visualize_timeline(sample_events))
    print(visualizer.visualize_patterns(sample_events))

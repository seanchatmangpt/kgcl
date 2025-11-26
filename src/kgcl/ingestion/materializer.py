"""Feature materialization engine.

Applies feature templates to raw events and computes derived values.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from kgcl.ingestion.config import FeatureConfig
from kgcl.ingestion.models import (
    AppEvent,
    BrowserVisit,
    CalendarBlock,
    MaterializedFeature,
)


class FeatureMaterializer:
    """Feature materialization engine.

    Computes derived features from raw events with time-window aggregation.
    """

    def __init__(self, config: FeatureConfig) -> None:
        """Initialize feature materializer.

        Parameters
        ----------
        config : FeatureConfig
            Feature configuration
        """
        self.config = config
        self._cache: dict[str, Any] = {}
        self._cache_hits = 0
        self._cache_misses = 0

    def materialize(
        self,
        events: list[AppEvent | BrowserVisit | CalendarBlock],
        window_start: datetime,
        window_end: datetime,
    ) -> list[MaterializedFeature]:
        """Materialize features for event batch.

        Parameters
        ----------
        events : list[AppEvent | BrowserVisit | CalendarBlock]
            Events to process
        window_start : datetime
            Window start time
        window_end : datetime
            Window end time

        Returns
        -------
        list[MaterializedFeature]
            Materialized features
        """
        features: list[MaterializedFeature] = []

        # Filter events by time window
        windowed_events = self._filter_by_window(events, window_start, window_end)

        # Compute each enabled feature
        for feature_id in self.config.enabled_features:
            if feature_id == "app_usage_time":
                features.extend(
                    self._compute_app_usage_time(
                        windowed_events, window_start, window_end
                    )
                )
            elif feature_id == "browser_domain_visits":
                features.extend(
                    self._compute_browser_domain_visits(
                        windowed_events, window_start, window_end
                    )
                )
            elif feature_id == "meeting_count":
                features.extend(
                    self._compute_meeting_count(
                        windowed_events, window_start, window_end
                    )
                )
            elif feature_id == "context_switches":
                features.extend(
                    self._compute_context_switches(
                        windowed_events, window_start, window_end
                    )
                )

        return features

    def materialize_incremental(
        self,
        new_events: list[AppEvent | BrowserVisit | CalendarBlock],
        existing_features: list[MaterializedFeature],
    ) -> list[MaterializedFeature]:
        """Incrementally update features with new events.

        Parameters
        ----------
        new_events : list[AppEvent | BrowserVisit | CalendarBlock]
            New events to process
        existing_features : list[MaterializedFeature]
            Previously computed features

        Returns
        -------
        list[MaterializedFeature]
            Updated features
        """
        if not self.config.incremental_updates:
            # Fall back to full recomputation
            all_events = new_events  # In production, would load existing events
            return self.materialize(all_events, datetime.min, datetime.max)

        # Group existing features by (feature_id, window)
        feature_map: dict[tuple[str, datetime, datetime], MaterializedFeature] = {}
        for feat in existing_features:
            key = (feat.feature_id, feat.window_start, feat.window_end)
            feature_map[key] = feat

        # Determine affected windows
        affected_windows = self._get_affected_windows(new_events)

        # Recompute features for affected windows
        updated_features: list[MaterializedFeature] = []
        for window_start, window_end in affected_windows:
            windowed_events = self._filter_by_window(
                new_events, window_start, window_end
            )
            new_features = self.materialize(windowed_events, window_start, window_end)

            # Merge with existing features
            for new_feat in new_features:
                key = (new_feat.feature_id, new_feat.window_start, new_feat.window_end)
                if key in feature_map:
                    # Update existing feature
                    existing = feature_map[key]
                    merged = self._merge_features(existing, new_feat)
                    feature_map[key] = merged
                else:
                    feature_map[key] = new_feat

        return list(feature_map.values())

    def _compute_app_usage_time(
        self,
        events: list[AppEvent | BrowserVisit | CalendarBlock],
        window_start: datetime,
        window_end: datetime,
    ) -> list[MaterializedFeature]:
        """Compute total time per application.

        Parameters
        ----------
        events : list[AppEvent | BrowserVisit | CalendarBlock]
            Events to process
        window_start : datetime
            Window start
        window_end : datetime
            Window end

        Returns
        -------
        list[MaterializedFeature]
            App usage features
        """
        app_times: dict[str, float] = defaultdict(float)
        app_counts: dict[str, int] = defaultdict(int)

        for event in events:
            if isinstance(event, AppEvent) and event.duration_seconds is not None:
                app_times[event.app_name] += event.duration_seconds
                app_counts[event.app_name] += 1

        features = []
        for app_name, total_time in app_times.items():
            features.append(
                MaterializedFeature(
                    feature_id=f"app_usage_time_{app_name}",
                    window_start=window_start,
                    window_end=window_end,
                    aggregation_type="sum",
                    value=total_time,
                    sample_count=app_counts[app_name],
                    metadata={"app_name": app_name},
                )
            )

        return features

    def _compute_browser_domain_visits(
        self,
        events: list[AppEvent | BrowserVisit | CalendarBlock],
        window_start: datetime,
        window_end: datetime,
    ) -> list[MaterializedFeature]:
        """Compute visit counts per domain.

        Parameters
        ----------
        events : list[AppEvent | BrowserVisit | CalendarBlock]
            Events to process
        window_start : datetime
            Window start
        window_end : datetime
            Window end

        Returns
        -------
        list[MaterializedFeature]
            Domain visit features
        """
        domain_counts: dict[str, int] = defaultdict(int)
        unique_urls: dict[str, set[str]] = defaultdict(set)

        for event in events:
            if isinstance(event, BrowserVisit):
                domain_counts[event.domain] += 1
                unique_urls[event.domain].add(event.url)

        features = []
        for domain, count in domain_counts.items():
            features.append(
                MaterializedFeature(
                    feature_id=f"browser_domain_visits_{domain}",
                    window_start=window_start,
                    window_end=window_end,
                    aggregation_type="count",
                    value=count,
                    sample_count=count,
                    metadata={
                        "domain": domain,
                        "unique_urls": len(unique_urls[domain]),
                    },
                )
            )

        return features

    def _compute_meeting_count(
        self,
        events: list[AppEvent | BrowserVisit | CalendarBlock],
        window_start: datetime,
        window_end: datetime,
    ) -> list[MaterializedFeature]:
        """Compute meeting statistics.

        Parameters
        ----------
        events : list[AppEvent | BrowserVisit | CalendarBlock]
            Events to process
        window_start : datetime
            Window start
        window_end : datetime
            Window end

        Returns
        -------
        list[MaterializedFeature]
            Meeting features
        """
        meeting_count = 0
        total_duration = 0.0

        for event in events:
            if isinstance(event, CalendarBlock):
                meeting_count += 1
                duration = (event.end_time - event.timestamp).total_seconds()
                total_duration += duration

        features = [
            MaterializedFeature(
                feature_id="meeting_count",
                window_start=window_start,
                window_end=window_end,
                aggregation_type="count",
                value=meeting_count,
                sample_count=meeting_count,
                metadata={},
            )
        ]

        if meeting_count > 0:
            features.append(
                MaterializedFeature(
                    feature_id="meeting_total_duration",
                    window_start=window_start,
                    window_end=window_end,
                    aggregation_type="sum",
                    value=total_duration,
                    sample_count=meeting_count,
                    metadata={"avg_duration": total_duration / meeting_count},
                )
            )

        return features

    def _compute_context_switches(
        self,
        events: list[AppEvent | BrowserVisit | CalendarBlock],
        window_start: datetime,
        window_end: datetime,
    ) -> list[MaterializedFeature]:
        """Compute application context switch count.

        Parameters
        ----------
        events : list[AppEvent | BrowserVisit | CalendarBlock]
            Events to process
        window_start : datetime
            Window start
        window_end : datetime
            Window end

        Returns
        -------
        list[MaterializedFeature]
            Context switch features
        """
        app_events = sorted(
            [e for e in events if isinstance(e, AppEvent)], key=lambda e: e.timestamp
        )

        switch_count = 0
        prev_app: str | None = None

        for event in app_events:
            if prev_app is not None and event.app_name != prev_app:
                switch_count += 1
            prev_app = event.app_name

        return [
            MaterializedFeature(
                feature_id="context_switches",
                window_start=window_start,
                window_end=window_end,
                aggregation_type="count",
                value=switch_count,
                sample_count=len(app_events),
                metadata={"unique_apps": len(set(e.app_name for e in app_events))},
            )
        ]

    def _filter_by_window(
        self,
        events: list[AppEvent | BrowserVisit | CalendarBlock],
        window_start: datetime,
        window_end: datetime,
    ) -> list[AppEvent | BrowserVisit | CalendarBlock]:
        """Filter events by time window.

        Parameters
        ----------
        events : list[AppEvent | BrowserVisit | CalendarBlock]
            Events to filter
        window_start : datetime
            Window start
        window_end : datetime
            Window end

        Returns
        -------
        list[AppEvent | BrowserVisit | CalendarBlock]
            Filtered events
        """
        return [e for e in events if window_start <= e.timestamp < window_end]

    def _get_affected_windows(
        self, events: list[AppEvent | BrowserVisit | CalendarBlock]
    ) -> list[tuple[datetime, datetime]]:
        """Determine time windows affected by events.

        Parameters
        ----------
        events : list[AppEvent | BrowserVisit | CalendarBlock]
            Events to analyze

        Returns
        -------
        list[tuple[datetime, datetime]]
            Affected (start, end) windows
        """
        windows = []
        for window_spec in self.config.aggregation_windows:
            # Parse window specification (e.g., "1h", "1d", "1w")
            duration = self._parse_window_spec(window_spec)

            # Find windows containing events
            for event in events:
                window_start = self._align_to_window(event.timestamp, duration)
                window_end = window_start + duration
                window = (window_start, window_end)
                if window not in windows:
                    windows.append(window)

        return windows

    def _parse_window_spec(self, spec: str) -> timedelta:
        """Parse window specification string.

        Parameters
        ----------
        spec : str
            Window spec (e.g., "1h", "2d", "1w")

        Returns
        -------
        timedelta
            Window duration
        """
        unit = spec[-1]
        value = int(spec[:-1])

        if unit == "h":
            return timedelta(hours=value)
        if unit == "d":
            return timedelta(days=value)
        if unit == "w":
            return timedelta(weeks=value)
        msg = f"Invalid window specification: {spec}"
        raise ValueError(msg)

    def _align_to_window(self, timestamp: datetime, duration: timedelta) -> datetime:
        """Align timestamp to window boundary.

        Parameters
        ----------
        timestamp : datetime
            Timestamp to align
        duration : timedelta
            Window duration

        Returns
        -------
        datetime
            Aligned window start
        """
        # Align to hour/day boundaries
        if duration == timedelta(hours=1):
            return timestamp.replace(minute=0, second=0, microsecond=0)
        if duration == timedelta(days=1):
            return timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        # Generic alignment
        epoch = datetime(1970, 1, 1)
        seconds_since_epoch = (timestamp - epoch).total_seconds()
        window_seconds = duration.total_seconds()
        aligned_seconds = (seconds_since_epoch // window_seconds) * window_seconds
        return epoch + timedelta(seconds=aligned_seconds)

    def _merge_features(
        self, existing: MaterializedFeature, new: MaterializedFeature
    ) -> MaterializedFeature:
        """Merge existing and new feature values.

        Parameters
        ----------
        existing : MaterializedFeature
            Existing feature
        new : MaterializedFeature
            New feature

        Returns
        -------
        MaterializedFeature
            Merged feature
        """
        # Combine based on aggregation type
        if existing.aggregation_type == "sum":
            merged_value = float(existing.value) + float(new.value)
        elif existing.aggregation_type == "count":
            merged_value = int(existing.value) + int(new.value)
        elif existing.aggregation_type == "avg":
            # Weighted average
            total_samples = existing.sample_count + new.sample_count
            merged_value = (
                float(existing.value) * existing.sample_count
                + float(new.value) * new.sample_count
            ) / total_samples
        else:
            # Default: use new value
            merged_value = new.value

        return MaterializedFeature(
            feature_id=existing.feature_id,
            window_start=existing.window_start,
            window_end=existing.window_end,
            aggregation_type=existing.aggregation_type,
            value=merged_value,
            sample_count=existing.sample_count + new.sample_count,
            metadata={**existing.metadata, **new.metadata},
        )

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns
        -------
        dict[str, Any]
            Cache statistics
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total_requests if total_requests > 0 else 0.0

        return {
            "cache_size": len(self._cache),
            "max_cache_size": self.config.cache_size,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate": hit_rate,
        }

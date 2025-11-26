"""Tests for feature materializer."""

from datetime import UTC, datetime, timedelta

import pytest

from kgcl.ingestion.config import FeatureConfig
from kgcl.ingestion.materializer import FeatureMaterializer
from kgcl.ingestion.models import AppEvent, BrowserVisit, CalendarBlock


class TestFeatureMaterializer:
    """Tests for FeatureMaterializer."""

    def test_initialization(self):
        """Test materializer initialization."""
        config = FeatureConfig()
        materializer = FeatureMaterializer(config)

        assert materializer.config.incremental_updates is True
        assert len(materializer._cache) == 0

    def test_app_usage_time_feature(self):
        """Test computing app usage time feature."""
        config = FeatureConfig(enabled_features=["app_usage_time"])
        materializer = FeatureMaterializer(config)

        now = datetime.now(UTC).replace(tzinfo=None)
        window_start = now.replace(minute=0, second=0, microsecond=0)
        window_end = window_start + timedelta(hours=1)

        events = [
            AppEvent(
                event_id="app_001",
                timestamp=window_start + timedelta(minutes=10),
                app_name="com.apple.Safari",
                duration_seconds=300.0,
            ),
            AppEvent(
                event_id="app_002",
                timestamp=window_start + timedelta(minutes=20),
                app_name="com.apple.Safari",
                duration_seconds=200.0,
            ),
            AppEvent(
                event_id="app_003",
                timestamp=window_start + timedelta(minutes=30),
                app_name="com.apple.Mail",
                duration_seconds=150.0,
            ),
        ]

        features = materializer.materialize(events, window_start, window_end)

        # Should have features for both apps
        safari_features = [f for f in features if "Safari" in f.feature_id]
        assert len(safari_features) > 0
        assert safari_features[0].value == 500.0  # 300 + 200

    def test_browser_domain_visits_feature(self):
        """Test computing browser domain visits feature."""
        config = FeatureConfig(enabled_features=["browser_domain_visits"])
        materializer = FeatureMaterializer(config)

        now = datetime.now(UTC).replace(tzinfo=None)
        window_start = now.replace(minute=0, second=0, microsecond=0)
        window_end = window_start + timedelta(hours=1)

        events = [
            BrowserVisit(
                event_id="browser_001",
                timestamp=window_start + timedelta(minutes=5),
                url="https://github.com/user/repo1",
                domain="github.com",
                browser_name="Safari",
            ),
            BrowserVisit(
                event_id="browser_002",
                timestamp=window_start + timedelta(minutes=10),
                url="https://github.com/user/repo2",
                domain="github.com",
                browser_name="Safari",
            ),
            BrowserVisit(
                event_id="browser_003",
                timestamp=window_start + timedelta(minutes=15),
                url="https://google.com/search",
                domain="google.com",
                browser_name="Safari",
            ),
        ]

        features = materializer.materialize(events, window_start, window_end)

        # Should have features for both domains
        github_features = [f for f in features if "github.com" in f.feature_id]
        assert len(github_features) > 0
        assert github_features[0].value == 2
        assert github_features[0].metadata["unique_urls"] == 2

    def test_meeting_count_feature(self):
        """Test computing meeting count feature."""
        config = FeatureConfig(enabled_features=["meeting_count"])
        materializer = FeatureMaterializer(config)

        now = datetime.now(UTC).replace(tzinfo=None)
        window_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        window_end = window_start + timedelta(days=1)

        events = [
            CalendarBlock(
                event_id="cal_001",
                timestamp=window_start + timedelta(hours=9),
                end_time=window_start + timedelta(hours=10),
                title="Meeting 1",
            ),
            CalendarBlock(
                event_id="cal_002",
                timestamp=window_start + timedelta(hours=14),
                end_time=window_start + timedelta(hours=15),
                title="Meeting 2",
            ),
        ]

        features = materializer.materialize(events, window_start, window_end)

        # Should have meeting count feature
        count_features = [f for f in features if f.feature_id == "meeting_count"]
        assert len(count_features) > 0
        assert count_features[0].value == 2

        # Should also have total duration feature
        duration_features = [f for f in features if "duration" in f.feature_id]
        assert len(duration_features) > 0

    def test_context_switches_feature(self):
        """Test computing context switches feature."""
        config = FeatureConfig(enabled_features=["context_switches"])
        materializer = FeatureMaterializer(config)

        now = datetime.now(UTC).replace(tzinfo=None)
        window_start = now.replace(minute=0, second=0, microsecond=0)
        window_end = window_start + timedelta(hours=1)

        events = [
            AppEvent(
                event_id="app_001",
                timestamp=window_start + timedelta(minutes=0),
                app_name="com.apple.Safari",
            ),
            AppEvent(
                event_id="app_002",
                timestamp=window_start + timedelta(minutes=10),
                app_name="com.apple.Mail",
            ),
            AppEvent(
                event_id="app_003",
                timestamp=window_start + timedelta(minutes=20),
                app_name="com.apple.Safari",
            ),
            AppEvent(
                event_id="app_004",
                timestamp=window_start + timedelta(minutes=30),
                app_name="com.apple.Mail",
            ),
        ]

        features = materializer.materialize(events, window_start, window_end)

        # Should have context switches feature
        switch_features = [f for f in features if f.feature_id == "context_switches"]
        assert len(switch_features) > 0
        assert switch_features[0].value == 3  # 3 switches between 4 events

    def test_window_filtering(self):
        """Test filtering events by time window."""
        config = FeatureConfig(enabled_features=["app_usage_time"])
        materializer = FeatureMaterializer(config)

        now = datetime.now(UTC).replace(tzinfo=None)
        window_start = now.replace(minute=0, second=0, microsecond=0)
        window_end = window_start + timedelta(hours=1)

        events = [
            # Inside window
            AppEvent(
                event_id="app_001",
                timestamp=window_start + timedelta(minutes=10),
                app_name="com.apple.Safari",
                duration_seconds=100.0,
            ),
            # Outside window (before)
            AppEvent(
                event_id="app_002",
                timestamp=window_start - timedelta(minutes=10),
                app_name="com.apple.Safari",
                duration_seconds=50.0,
            ),
            # Outside window (after)
            AppEvent(
                event_id="app_003",
                timestamp=window_end + timedelta(minutes=10),
                app_name="com.apple.Safari",
                duration_seconds=50.0,
            ),
        ]

        features = materializer.materialize(events, window_start, window_end)

        # Should only count event inside window
        safari_features = [f for f in features if "Safari" in f.feature_id]
        assert len(safari_features) > 0
        assert safari_features[0].value == 100.0

    def test_parse_window_spec(self):
        """Test parsing window specification strings."""
        config = FeatureConfig()
        materializer = FeatureMaterializer(config)

        # Test hour window
        duration = materializer._parse_window_spec("1h")
        assert duration == timedelta(hours=1)

        # Test day window
        duration = materializer._parse_window_spec("1d")
        assert duration == timedelta(days=1)

        # Test week window
        duration = materializer._parse_window_spec("1w")
        assert duration == timedelta(weeks=1)

        # Test invalid spec
        with pytest.raises(ValueError):
            materializer._parse_window_spec("1x")

    def test_align_to_window(self):
        """Test aligning timestamps to window boundaries."""
        config = FeatureConfig()
        materializer = FeatureMaterializer(config)

        # Test hourly alignment
        timestamp = datetime(2024, 11, 24, 10, 35, 42)
        aligned = materializer._align_to_window(timestamp, timedelta(hours=1))
        assert aligned == datetime(2024, 11, 24, 10, 0, 0)

        # Test daily alignment
        aligned = materializer._align_to_window(timestamp, timedelta(days=1))
        assert aligned == datetime(2024, 11, 24, 0, 0, 0)

    def test_merge_features(self):
        """Test merging existing and new features."""
        config = FeatureConfig()
        materializer = FeatureMaterializer(config)

        now = datetime.now(UTC).replace(tzinfo=None)
        window_start = now.replace(minute=0, second=0, microsecond=0)
        window_end = window_start + timedelta(hours=1)

        # Existing feature
        existing = materializer._compute_app_usage_time(
            [
                AppEvent(
                    event_id="app_001",
                    timestamp=window_start + timedelta(minutes=10),
                    app_name="com.apple.Safari",
                    duration_seconds=100.0,
                )
            ],
            window_start,
            window_end,
        )[0]

        # New feature
        new = materializer._compute_app_usage_time(
            [
                AppEvent(
                    event_id="app_002",
                    timestamp=window_start + timedelta(minutes=20),
                    app_name="com.apple.Safari",
                    duration_seconds=50.0,
                )
            ],
            window_start,
            window_end,
        )[0]

        # Merge
        merged = materializer._merge_features(existing, new)

        assert merged.value == 150.0  # 100 + 50
        assert merged.sample_count == 2

    def test_incremental_updates(self):
        """Test incremental feature updates."""
        config = FeatureConfig(
            enabled_features=["app_usage_time"], incremental_updates=True
        )
        materializer = FeatureMaterializer(config)

        now = datetime.now(UTC).replace(tzinfo=None)
        window_start = now.replace(minute=0, second=0, microsecond=0)
        window_end = window_start + timedelta(hours=1)

        # Initial events
        initial_events = [
            AppEvent(
                event_id="app_001",
                timestamp=window_start + timedelta(minutes=10),
                app_name="com.apple.Safari",
                duration_seconds=100.0,
            )
        ]

        existing_features = materializer.materialize(
            initial_events, window_start, window_end
        )

        # New events
        new_events = [
            AppEvent(
                event_id="app_002",
                timestamp=window_start + timedelta(minutes=20),
                app_name="com.apple.Safari",
                duration_seconds=50.0,
            )
        ]

        # Update incrementally
        updated_features = materializer.materialize_incremental(
            new_events, existing_features
        )

        assert len(updated_features) > 0

    def test_cache_stats(self):
        """Test cache statistics."""
        config = FeatureConfig()
        materializer = FeatureMaterializer(config)

        stats = materializer.get_cache_stats()

        assert "cache_size" in stats
        assert "max_cache_size" in stats
        assert "hit_rate" in stats
        assert stats["cache_size"] == 0

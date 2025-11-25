"""Feature materialization pipeline integration tests.

Tests applying feature templates to raw events, aggregating across time windows,
and validating computed values.
"""

from datetime import datetime, timedelta

import pytest

from kgcl.ingestion.config import FeatureConfig
from kgcl.ingestion.materializer import FeatureMaterializer
from kgcl.ingestion.models import AppEvent, BrowserVisit, CalendarBlock


def create_event_batch() -> list:
    """Create batch of events for testing.

    Returns
    -------
    list
        Mixed event types
    """
    base = datetime(2024, 11, 24, 10, 0, 0)
    return (
        [
            AppEvent(
                event_id=f"app_{i:03d}",
                timestamp=base + timedelta(minutes=i * 10),
                app_name="com.microsoft.VSCode" if i % 2 == 0 else "com.apple.Safari",
                duration_seconds=600.0,  # 10 min each
            )
            for i in range(12)  # 2 hours of events
        ]
        + [
            BrowserVisit(
                event_id=f"browser_{i:03d}",
                timestamp=base + timedelta(minutes=i * 15),
                url=f"https://github.com/user/repo{i}",
                domain="github.com",
                browser_name="Safari",
            )
            for i in range(8)  # 2 hours of visits
        ]
        + [
            CalendarBlock(
                event_id=f"cal_{i:03d}",
                timestamp=base + timedelta(hours=i),
                end_time=base + timedelta(hours=i + 1),
                title=f"Meeting {i}",
            )
            for i in range(2)
        ]
    )


class TestFeatureMaterialization:
    """Test feature materialization pipeline."""

    def test_materialize_app_usage_time(self):
        """Test computing app usage time features."""
        events = create_event_batch()
        config = FeatureConfig(enabled_features=["app_usage_time"])
        materializer = FeatureMaterializer(config)

        window_start = datetime(2024, 11, 24, 10, 0, 0)
        window_end = window_start + timedelta(hours=2)

        features = materializer.materialize(events, window_start, window_end)

        # Should have features for both apps
        feature_ids = {f.feature_id for f in features}
        assert any("VSCode" in fid for fid in feature_ids)
        assert any("Safari" in fid for fid in feature_ids)

        # Verify total time for VSCode (6 events * 600s = 3600s)
        vscode = next((f for f in features if "VSCode" in f.feature_id), None)
        assert vscode is not None
        assert vscode.value == pytest.approx(3600.0, rel=0.01)
        assert vscode.sample_count == 6

    def test_materialize_browser_domain_visits(self):
        """Test computing browser visit counts."""
        events = create_event_batch()
        config = FeatureConfig(enabled_features=["browser_domain_visits"])
        materializer = FeatureMaterializer(config)

        window_start = datetime(2024, 11, 24, 10, 0, 0)
        window_end = window_start + timedelta(hours=2)

        features = materializer.materialize(events, window_start, window_end)

        # Should have feature for github.com
        github_feature = next((f for f in features if "github.com" in f.feature_id), None)
        assert github_feature is not None
        assert github_feature.value == 8  # 8 visits
        assert github_feature.aggregation_type == "count"

    def test_materialize_meeting_count(self):
        """Test computing meeting statistics."""
        events = create_event_batch()
        config = FeatureConfig(enabled_features=["meeting_count"])
        materializer = FeatureMaterializer(config)

        window_start = datetime(2024, 11, 24, 10, 0, 0)
        window_end = window_start + timedelta(hours=3)

        features = materializer.materialize(events, window_start, window_end)

        # Should have meeting_count feature
        meeting_count = next((f for f in features if f.feature_id == "meeting_count"), None)
        assert meeting_count is not None
        assert meeting_count.value == 2  # 2 meetings

        # Should also have total duration
        duration_feature = next(
            (f for f in features if f.feature_id == "meeting_total_duration"), None
        )
        assert duration_feature is not None
        assert duration_feature.value == pytest.approx(7200.0, rel=0.01)  # 2 hours

    def test_materialize_context_switches(self):
        """Test computing context switch count."""
        events = create_event_batch()
        config = FeatureConfig(enabled_features=["context_switches"])
        materializer = FeatureMaterializer(config)

        window_start = datetime(2024, 11, 24, 10, 0, 0)
        window_end = window_start + timedelta(hours=2)

        features = materializer.materialize(events, window_start, window_end)

        # Should have context_switches feature
        switches = next((f for f in features if f.feature_id == "context_switches"), None)
        assert switches is not None
        # 12 app events alternating between 2 apps = 11 switches
        assert switches.value == 11
        assert switches.metadata["unique_apps"] == 2

    def test_multiple_time_windows(self):
        """Test materialization across multiple time windows."""
        events = create_event_batch()
        config = FeatureConfig(
            enabled_features=["app_usage_time"],
            aggregation_windows=["1h"],  # Hourly windows
        )
        materializer = FeatureMaterializer(config)

        # First hour
        hour1_start = datetime(2024, 11, 24, 10, 0, 0)
        hour1_end = hour1_start + timedelta(hours=1)
        hour1_features = materializer.materialize(events, hour1_start, hour1_end)

        # Second hour
        hour2_start = hour1_end
        hour2_end = hour2_start + timedelta(hours=1)
        hour2_features = materializer.materialize(events, hour2_start, hour2_end)

        # Both should have features
        assert len(hour1_features) > 0
        assert len(hour2_features) > 0

        # Window boundaries should be correct
        for f in hour1_features:
            assert f.window_start == hour1_start
            assert f.window_end == hour1_end

        for f in hour2_features:
            assert f.window_start == hour2_start
            assert f.window_end == hour2_end

    def test_incremental_updates(self):
        """Test incremental feature materialization."""
        config = FeatureConfig(enabled_features=["app_usage_time"], incremental_updates=True)
        materializer = FeatureMaterializer(config)

        # Initial batch
        initial_events = create_event_batch()[:6]  # First 6 events
        window_start = datetime(2024, 11, 24, 10, 0, 0)
        window_end = window_start + timedelta(hours=2)

        initial_features = materializer.materialize(initial_events, window_start, window_end)

        # New events arrive
        new_events = create_event_batch()[6:9]  # Next 3 events
        updated_features = materializer.materialize_incremental(new_events, initial_features)

        # Should have updated features
        assert len(updated_features) >= len(initial_features)

    def test_aggregation_correctness(self):
        """Test that aggregations are mathematically correct."""
        base = datetime(2024, 11, 24, 10, 0, 0)
        events = [
            AppEvent(
                event_id=f"app_{i}",
                timestamp=base + timedelta(minutes=i),
                app_name="com.test.App",
                duration_seconds=float(i * 100),  # Varying durations
            )
            for i in range(10)
        ]

        config = FeatureConfig(enabled_features=["app_usage_time"])
        materializer = FeatureMaterializer(config)

        window_start = base
        window_end = base + timedelta(hours=1)

        features = materializer.materialize(events, window_start, window_end)

        # Find the app feature
        app_feature = next((f for f in features if "App" in f.feature_id), None)
        assert app_feature is not None

        # Verify: sum of (0*100 + 1*100 + ... + 9*100) = 4500
        expected_total = sum(i * 100 for i in range(10))
        assert app_feature.value == pytest.approx(expected_total, rel=0.01)
        assert app_feature.sample_count == 10

    def test_empty_window_handling(self):
        """Test handling of time windows with no events."""
        events = create_event_batch()
        config = FeatureConfig(enabled_features=["app_usage_time"])
        materializer = FeatureMaterializer(config)

        # Window with no events (far future)
        window_start = datetime(2024, 12, 25, 10, 0, 0)
        window_end = window_start + timedelta(hours=1)

        features = materializer.materialize(events, window_start, window_end)

        # Should return empty list
        assert len(features) == 0

    def test_window_boundary_precision(self):
        """Test precise handling of window boundaries."""
        base = datetime(2024, 11, 24, 10, 0, 0)
        events = [
            AppEvent(
                event_id="app_before",
                timestamp=base - timedelta(seconds=1),  # Just before
                app_name="com.test.App",
                duration_seconds=100.0,
            ),
            AppEvent(
                event_id="app_start",
                timestamp=base,  # Exactly at start
                app_name="com.test.App",
                duration_seconds=100.0,
            ),
            AppEvent(
                event_id="app_end",
                timestamp=base + timedelta(hours=1),  # At end (excluded)
                app_name="com.test.App",
                duration_seconds=100.0,
            ),
        ]

        config = FeatureConfig(enabled_features=["app_usage_time"])
        materializer = FeatureMaterializer(config)

        window_start = base
        window_end = base + timedelta(hours=1)

        features = materializer.materialize(events, window_start, window_end)

        # Should include only "app_start" (100s)
        app_feature = next((f for f in features if "App" in f.feature_id), None)
        assert app_feature is not None
        assert app_feature.value == 100.0
        assert app_feature.sample_count == 1

    def test_all_features_together(self):
        """Test computing all features in one pass."""
        events = create_event_batch()
        config = FeatureConfig(
            enabled_features=[
                "app_usage_time",
                "browser_domain_visits",
                "meeting_count",
                "context_switches",
            ]
        )
        materializer = FeatureMaterializer(config)

        window_start = datetime(2024, 11, 24, 10, 0, 0)
        window_end = window_start + timedelta(hours=3)

        features = materializer.materialize(events, window_start, window_end)

        # Should have features from all categories
        feature_ids = {f.feature_id for f in features}

        # App usage (multiple apps)
        assert any("VSCode" in fid or "Safari" in fid for fid in feature_ids)

        # Browser visits
        assert any("github.com" in fid for fid in feature_ids)

        # Meetings
        assert "meeting_count" in feature_ids

        # Context switches
        assert "context_switches" in feature_ids

        # Total features should be reasonable
        assert len(features) >= 4

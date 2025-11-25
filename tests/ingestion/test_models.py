"""Tests for ingestion models."""

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from kgcl.ingestion.models import (
    AppEvent,
    BrowserVisit,
    CalendarBlock,
    EventBatch,
    EventStatus,
    EventType,
    FeatureInstance,
    MaterializedFeature,
)


class TestAppEvent:
    """Tests for AppEvent model."""

    def test_create_valid_app_event(self):
        """Test creating valid app event."""
        event = AppEvent(
            event_id="test_001",
            timestamp=datetime.now(timezone.utc),
            app_name="com.apple.Safari",
            app_display_name="Safari",
            window_title="Test Page",
            duration_seconds=120.5,
            process_id=1234,
        )

        assert event.event_id == "test_001"
        assert event.app_name == "com.apple.Safari"
        assert event.duration_seconds == 120.5
        assert event.schema_version == "1.0.0"

    def test_timestamp_normalization_utc(self):
        """Test timestamp normalization to UTC."""
        tz_timestamp = datetime.now(timezone.utc)
        event = AppEvent(
            event_id="test_001",
            timestamp=tz_timestamp,
            app_name="com.apple.Safari",
        )

        assert event.timestamp.tzinfo is None

    def test_timestamp_from_iso_string(self):
        """Test timestamp parsing from ISO string."""
        event = AppEvent(
            event_id="test_001",
            timestamp="2024-11-24T10:30:00Z",
            app_name="com.apple.Safari",
        )

        assert event.timestamp.year == 2024
        assert event.timestamp.month == 11
        assert event.timestamp.day == 24

    def test_negative_duration_rejected(self):
        """Test that negative duration is rejected."""
        with pytest.raises(ValidationError):
            AppEvent(
                event_id="test_001",
                timestamp=datetime.now(timezone.utc),
                app_name="com.apple.Safari",
                duration_seconds=-10.0,
            )

    def test_optional_fields(self):
        """Test that optional fields can be None."""
        event = AppEvent(
            event_id="test_001",
            timestamp=datetime.now(timezone.utc),
            app_name="com.apple.Safari",
        )

        assert event.app_display_name is None
        assert event.window_title is None
        assert event.duration_seconds is None


class TestBrowserVisit:
    """Tests for BrowserVisit model."""

    def test_create_valid_browser_visit(self):
        """Test creating valid browser visit."""
        event = BrowserVisit(
            event_id="test_001",
            timestamp=datetime.now(timezone.utc),
            url="https://github.com/user/kgcl",
            domain="github.com",
            title="GitHub - user/kgcl",
            browser_name="Safari",
            duration_seconds=45.2,
        )

        assert event.url == "https://github.com/user/kgcl"
        assert event.domain == "github.com"
        assert event.duration_seconds == 45.2

    def test_with_referrer(self):
        """Test browser visit with referrer."""
        event = BrowserVisit(
            event_id="test_001",
            timestamp=datetime.now(timezone.utc),
            url="https://github.com/user/kgcl",
            domain="github.com",
            browser_name="Safari",
            referrer="https://google.com/search",
        )

        assert event.referrer == "https://google.com/search"


class TestCalendarBlock:
    """Tests for CalendarBlock model."""

    def test_create_valid_calendar_block(self):
        """Test creating valid calendar event."""
        start = datetime.now(timezone.utc)
        end = start + timedelta(hours=1)

        event = CalendarBlock(
            event_id="test_001",
            timestamp=start,
            end_time=end,
            title="Team Meeting",
            description="Weekly sync",
            attendees=["user1@example.com", "user2@example.com"],
        )

        assert event.title == "Team Meeting"
        assert len(event.attendees) == 2
        assert event.is_all_day is False

    def test_all_day_event(self):
        """Test all-day calendar event."""
        event = CalendarBlock(
            event_id="test_001",
            timestamp=datetime(2024, 11, 24),
            end_time=datetime(2024, 11, 25),
            title="Holiday",
            is_all_day=True,
        )

        assert event.is_all_day is True


class TestFeatureInstance:
    """Tests for FeatureInstance model."""

    def test_create_numeric_feature(self):
        """Test creating feature with numeric value."""
        feature = FeatureInstance(
            feature_id="app_usage_time",
            timestamp=datetime.now(timezone.utc),
            value=120.5,
            source_events=["evt_001", "evt_002"],
        )

        assert feature.value == 120.5
        assert len(feature.source_events) == 2

    def test_create_string_feature(self):
        """Test creating feature with string value."""
        feature = FeatureInstance(
            feature_id="most_used_app",
            timestamp=datetime.now(timezone.utc),
            value="com.apple.Safari",
        )

        assert isinstance(feature.value, str)

    def test_feature_metadata(self):
        """Test feature with metadata."""
        feature = FeatureInstance(
            feature_id="context_switches",
            timestamp=datetime.now(timezone.utc),
            value=15,
            metadata={"app_count": 5, "period": "1h"},
        )

        assert feature.metadata["app_count"] == 5


class TestMaterializedFeature:
    """Tests for MaterializedFeature model."""

    def test_create_sum_aggregation(self):
        """Test creating sum aggregation feature."""
        start = datetime.now(timezone.utc)
        end = start + timedelta(hours=1)

        feature = MaterializedFeature(
            feature_id="total_app_time",
            window_start=start,
            window_end=end,
            aggregation_type="sum",
            value=3600.0,
            sample_count=10,
        )

        assert feature.aggregation_type == "sum"
        assert feature.value == 3600.0

    def test_create_count_aggregation(self):
        """Test creating count aggregation feature."""
        start = datetime.now(timezone.utc)
        end = start + timedelta(days=1)

        feature = MaterializedFeature(
            feature_id="meeting_count",
            window_start=start,
            window_end=end,
            aggregation_type="count",
            value=5,
            sample_count=5,
        )

        assert feature.aggregation_type == "count"


class TestEventBatch:
    """Tests for EventBatch model."""

    def test_create_empty_batch(self):
        """Test creating empty event batch."""
        batch = EventBatch(
            batch_id="batch_001",
            events=[],
        )

        assert batch.event_count() == 0
        assert batch.events_by_type() == {}

    def test_create_mixed_batch(self):
        """Test creating batch with mixed event types."""
        now = datetime.now(timezone.utc)
        events = [
            AppEvent(
                event_id="app_001",
                timestamp=now,
                app_name="com.apple.Safari",
            ),
            AppEvent(
                event_id="app_002",
                timestamp=now,
                app_name="com.apple.Mail",
            ),
            BrowserVisit(
                event_id="browser_001",
                timestamp=now,
                url="https://example.com",
                domain="example.com",
                browser_name="Safari",
            ),
        ]

        batch = EventBatch(
            batch_id="batch_001",
            events=events,
        )

        assert batch.event_count() == 3
        counts = batch.events_by_type()
        assert counts["AppEvent"] == 2
        assert counts["BrowserVisit"] == 1

    def test_batch_metadata(self):
        """Test batch with custom metadata."""
        batch = EventBatch(
            batch_id="batch_001",
            events=[],
            metadata={"source": "test", "version": "1.0"},
        )

        assert batch.metadata["source"] == "test"


class TestEnums:
    """Tests for enumeration types."""

    def test_event_type_enum(self):
        """Test EventType enum values."""
        assert EventType.APP_EVENT.value == "app_event"
        assert EventType.BROWSER_VISIT.value == "browser_visit"
        assert EventType.CALENDAR_BLOCK.value == "calendar_block"

    def test_event_status_enum(self):
        """Test EventStatus enum values."""
        assert EventStatus.PENDING.value == "pending"
        assert EventStatus.COMPLETED.value == "completed"

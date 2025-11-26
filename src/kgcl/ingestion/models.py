"""Event models for KGCL ingestion system.

Pydantic models for representing various event types:
- AppEvent: Application usage events
- BrowserVisit: Browser navigation events
- CalendarBlock: Calendar/meeting events
- Feature instances and materialized features
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class EventType(str, Enum):
    """Supported event types."""

    APP_EVENT = "app_event"
    BROWSER_VISIT = "browser_visit"
    CALENDAR_BLOCK = "calendar_block"
    FEATURE_INSTANCE = "feature_instance"


class EventStatus(str, Enum):
    """Event processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AppEvent(BaseModel):
    """Application usage event.

    Captures when a user switches to or focuses an application.
    """

    event_id: str = Field(..., description="Unique event identifier")
    timestamp: datetime = Field(..., description="Event occurrence time (UTC)")
    app_name: str = Field(..., description="Application bundle name")
    app_display_name: str | None = Field(None, description="Human-readable app name")
    window_title: str | None = Field(None, description="Active window title")
    duration_seconds: float | None = Field(None, ge=0, description="Time spent in app")
    process_id: int | None = Field(None, ge=0, description="Process ID")
    schema_version: str = Field(default="1.0.0", description="Event schema version")

    @field_validator("timestamp", mode="before")
    @classmethod
    def normalize_timestamp(cls, v: Any) -> datetime:
        """Ensure timestamp is in UTC."""
        if isinstance(v, str):
            dt = datetime.fromisoformat(v)
        elif isinstance(v, datetime):
            dt = v
        else:
            msg = f"Invalid timestamp type: {type(v)}"
            raise TypeError(msg)

        # Convert to UTC if timezone-aware
        if dt.tzinfo is not None:
            return dt.astimezone(UTC).replace(tzinfo=None)
        return dt

    model_config = {
        "json_schema_extra": {
            "example": {
                "event_id": "evt_app_001",
                "timestamp": "2024-11-24T10:30:00",
                "app_name": "com.apple.Safari",
                "app_display_name": "Safari",
                "window_title": "KGCL Documentation",
                "duration_seconds": 120.5,
                "process_id": 1234,
                "schema_version": "1.0.0",
            }
        }
    }


class BrowserVisit(BaseModel):
    """Browser navigation event.

    Captures webpage visits, navigation patterns, and engagement.
    """

    event_id: str = Field(..., description="Unique event identifier")
    timestamp: datetime = Field(..., description="Visit start time (UTC)")
    url: str = Field(..., description="Visited URL")
    domain: str = Field(..., description="Extracted domain name")
    title: str | None = Field(None, description="Page title")
    browser_name: str = Field(..., description="Browser application name")
    duration_seconds: float | None = Field(None, ge=0, description="Time on page")
    referrer: str | None = Field(None, description="Referring URL")
    tab_id: str | None = Field(None, description="Browser tab identifier")
    schema_version: str = Field(default="1.0.0", description="Event schema version")

    @field_validator("timestamp", mode="before")
    @classmethod
    def normalize_timestamp(cls, v: Any) -> datetime:
        """Ensure timestamp is in UTC."""
        if isinstance(v, str):
            dt = datetime.fromisoformat(v)
        elif isinstance(v, datetime):
            dt = v
        else:
            msg = f"Invalid timestamp type: {type(v)}"
            raise TypeError(msg)

        if dt.tzinfo is not None:
            return dt.astimezone(UTC).replace(tzinfo=None)
        return dt

    model_config = {
        "json_schema_extra": {
            "example": {
                "event_id": "evt_browser_001",
                "timestamp": "2024-11-24T10:30:00",
                "url": "https://github.com/user/kgcl",
                "domain": "github.com",
                "title": "GitHub - user/kgcl",
                "browser_name": "Safari",
                "duration_seconds": 45.2,
                "referrer": "https://google.com/search",
                "tab_id": "tab_001",
                "schema_version": "1.0.0",
            }
        }
    }


class CalendarBlock(BaseModel):
    """Calendar event or meeting block.

    Captures scheduled events, meetings, and time blocks.
    """

    event_id: str = Field(..., description="Unique event identifier")
    timestamp: datetime = Field(..., description="Event start time (UTC)")
    end_time: datetime = Field(..., description="Event end time (UTC)")
    title: str = Field(..., description="Event title")
    description: str | None = Field(None, description="Event description")
    location: str | None = Field(None, description="Event location")
    attendees: list[str] = Field(default_factory=list, description="Attendee email addresses")
    organizer: str | None = Field(None, description="Event organizer email")
    calendar_name: str | None = Field(None, description="Calendar source name")
    is_all_day: bool = Field(default=False, description="All-day event flag")
    schema_version: str = Field(default="1.0.0", description="Event schema version")

    @field_validator("timestamp", "end_time", mode="before")
    @classmethod
    def normalize_timestamp(cls, v: Any) -> datetime:
        """Ensure timestamp is in UTC."""
        if isinstance(v, str):
            dt = datetime.fromisoformat(v)
        elif isinstance(v, datetime):
            dt = v
        else:
            msg = f"Invalid timestamp type: {type(v)}"
            raise TypeError(msg)

        if dt.tzinfo is not None:
            return dt.astimezone(UTC).replace(tzinfo=None)
        return dt

    model_config = {
        "json_schema_extra": {
            "example": {
                "event_id": "evt_cal_001",
                "timestamp": "2024-11-24T14:00:00",
                "end_time": "2024-11-24T15:00:00",
                "title": "Team Standup",
                "description": "Daily sync meeting",
                "location": "Zoom",
                "attendees": ["team@example.com"],
                "organizer": "manager@example.com",
                "calendar_name": "Work",
                "is_all_day": False,
                "schema_version": "1.0.0",
            }
        }
    }


class FeatureInstance(BaseModel):
    """Individual feature observation.

    Represents a single computed feature value at a point in time.
    """

    feature_id: str = Field(..., description="Feature template identifier")
    timestamp: datetime = Field(..., description="Observation time (UTC)")
    value: float | int | str | bool = Field(..., description="Feature value")
    source_events: list[str] = Field(default_factory=list, description="Source event IDs used in computation")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional feature metadata")

    @field_validator("timestamp", mode="before")
    @classmethod
    def normalize_timestamp(cls, v: Any) -> datetime:
        """Ensure timestamp is in UTC."""
        if isinstance(v, str):
            dt = datetime.fromisoformat(v)
        elif isinstance(v, datetime):
            dt = v
        else:
            msg = f"Invalid timestamp type: {type(v)}"
            raise TypeError(msg)

        if dt.tzinfo is not None:
            return dt.astimezone(UTC).replace(tzinfo=None)
        return dt


class MaterializedFeature(BaseModel):
    """Aggregated feature over a time window.

    Represents computed features aggregated over hourly/daily windows.
    """

    feature_id: str = Field(..., description="Feature template identifier")
    window_start: datetime = Field(..., description="Aggregation window start (UTC)")
    window_end: datetime = Field(..., description="Aggregation window end (UTC)")
    aggregation_type: Literal["sum", "avg", "count", "min", "max", "distinct"] = Field(
        ..., description="Aggregation method"
    )
    value: float | int | str | bool = Field(..., description="Aggregated value")
    sample_count: int = Field(..., ge=0, description="Number of samples in aggregation")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class EventBatch(BaseModel):
    """Batch of events for ingestion.

    Supports batched ingestion for performance.
    """

    batch_id: str = Field(..., description="Unique batch identifier")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None), description="Batch creation time (UTC)"
    )
    events: list[AppEvent | BrowserVisit | CalendarBlock] = Field(..., description="Events in batch")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Batch metadata")

    def event_count(self) -> int:
        """Get total number of events in batch."""
        return len(self.events)

    def events_by_type(self) -> dict[str, int]:
        """Count events by type."""
        counts: dict[str, int] = {}
        for event in self.events:
            event_type = type(event).__name__
            counts[event_type] = counts.get(event_type, 0) + 1
        return counts

"""Dataclasses for Apple ingest domain objects."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CalendarEvent:
    identifier: str
    title: str
    start: datetime
    end: datetime
    calendar: str
    location: str | None = None
    notes: str | None = None
    attendees: Sequence[Mapping[str, str]] = field(default_factory=tuple)
    all_day: bool = False

    @classmethod
    def from_eventkit(cls, event: Any) -> CalendarEvent:
        """Create from an EventKit EKEvent-like object."""
        return cls(
            identifier=getattr(event, "eventIdentifier", event.event_id),
            title=getattr(event, "title", getattr(event, "title_property", "")),
            start=event.startDate,
            end=event.endDate,
            calendar=getattr(getattr(event, "calendar", None), "title", "Calendar"),
            location=getattr(event, "location", None) or getattr(event, "location_property", None),
            notes=getattr(event, "notes", None) or getattr(event, "notes_property", None),
            attendees=cls._normalize_attendees(event),
            all_day=bool(getattr(event, "isAllDay", False) or getattr(event, "is_all_day", False)),
        )

    @staticmethod
    def _normalize_attendees(event: Any) -> tuple[Mapping[str, str], ...]:
        """Extract attendees from EventKit object, tolerating missing values."""
        primary = getattr(event, "attendees_list", None)
        fallback = getattr(event, "attendees", None)
        values = primary or fallback or ()
        return tuple(values)


@dataclass(frozen=True)
class ReminderTask:
    identifier: str
    title: str
    completed: bool
    due: datetime | None
    list_name: str
    notes: str | None = None
    priority: int = 0

    @classmethod
    def from_eventkit(cls, reminder: Any) -> ReminderTask:
        return cls(
            identifier=getattr(reminder, "calendarItemIdentifier", reminder.reminder_id),
            title=getattr(reminder, "title", getattr(reminder, "title_property", "")),
            completed=bool(getattr(reminder, "isCompleted", getattr(reminder, "completed", False))),
            due=getattr(reminder, "dueDateComponents", getattr(reminder, "due_date", None)),
            list_name=getattr(getattr(reminder, "calendar", None), "title", getattr(reminder, "list_title", "Inbox")),
            notes=getattr(reminder, "notes", getattr(reminder, "notes_property", None)),
            priority=int(getattr(reminder, "priority_property", getattr(reminder, "priority", 0))),
        )


@dataclass(frozen=True)
class MailMessage:
    identifier: str
    subject: str
    sender: str
    recipients: Sequence[str]
    received: datetime
    flagged: bool = False

    @classmethod
    def from_mailkit(cls, message: Any) -> MailMessage:
        return cls(
            identifier=getattr(message, "messageID", message.message_id),
            subject=getattr(message, "subject", getattr(message, "subject_property", "")),
            sender=cls._extract_sender(message),
            recipients=tuple(r.get("email") for r in getattr(message, "recipients", [])),
            received=getattr(message, "dateReceived", message.date_received),
            flagged=bool(getattr(message, "isFlagged", getattr(message, "is_flagged", False))),
        )

    @staticmethod
    def _extract_sender(message: Any) -> str:
        senders = getattr(message, "senders", [])
        if isinstance(senders, list) and senders:
            entry = senders[0]
            if isinstance(entry, Mapping):
                return entry.get("email") or entry.get("name") or ""
        return getattr(message, "sender_email", "")


@dataclass(frozen=True)
class FileArtifact:
    identifier: str
    name: str
    path: str
    created: datetime
    modified: datetime
    mime_type: str
    tags: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True)
class AppleIngestInput:
    events: Sequence[CalendarEvent] = field(default_factory=tuple)
    reminders: Sequence[ReminderTask] = field(default_factory=tuple)
    mail: Sequence[MailMessage] = field(default_factory=tuple)
    files: Sequence[FileArtifact] = field(default_factory=tuple)


@dataclass(frozen=True)
class AppleIngestStats:
    event_count: int
    reminder_count: int
    mail_count: int
    file_count: int


@dataclass(frozen=True)
class AppleIngestResult:
    stats: AppleIngestStats
    graph_path: Path
    graph: Any
    receipts: dict[str, str]
    output_path: Path
    report: Any | None = None

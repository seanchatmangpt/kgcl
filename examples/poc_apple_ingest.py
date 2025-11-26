"""
POC: Apple Data Ingestion Pipeline - Complete working demonstration.

This single file contains:
1. All types/dataclasses for Apple data (Calendar, Reminders, Mail)
2. Complete ingestion implementation with RDF conversion
3. Comprehensive inline tests (Chicago School TDD)
4. Performance benchmarking (target: 1000 items < 100ms)

Run: python examples/poc_apple_ingest.py

Quality Standards:
- Zero implementation lies (no TODO/FIXME/STUB/HACK/WIP)
- 100% type hints (Python 3.12+ syntax)
- NumPy-style docstrings on all public APIs
- Timezone-aware datetime handling
- Email validation for mail ingestion
"""

from __future__ import annotations

import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class CalendarEvent:
    """Calendar event from Apple Calendar.

    Parameters
    ----------
    id : str
        Unique identifier for the event
    title : str
        Event title/summary
    start_time : datetime
        Event start timestamp (timezone-aware)
    end_time : datetime
        Event end timestamp (timezone-aware)
    location : str | None
        Optional event location
    notes : str | None
        Optional event notes/description
    """

    id: str
    title: str
    start_time: datetime
    end_time: datetime
    location: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        """Validate event data after initialization."""
        if not self.id:
            raise ValueError("Event ID cannot be empty")
        if not self.title:
            raise ValueError("Event title cannot be empty")
        if self.start_time >= self.end_time:
            raise ValueError("Start time must be before end time")


@dataclass(frozen=True)
class Reminder:
    """Reminder from Apple Reminders.

    Parameters
    ----------
    id : str
        Unique identifier for the reminder
    title : str
        Reminder title/description
    due_date : datetime | None
        Optional due date (timezone-aware)
    completed : bool
        Completion status (default: False)
    priority : int
        Priority level 0-9 (default: 0, higher is more important)
    """

    id: str
    title: str
    due_date: datetime | None = None
    completed: bool = False
    priority: int = 0

    def __post_init__(self) -> None:
        """Validate reminder data after initialization."""
        if not self.id:
            raise ValueError("Reminder ID cannot be empty")
        if not self.title:
            raise ValueError("Reminder title cannot be empty")
        if not 0 <= self.priority <= 9:
            raise ValueError("Priority must be between 0 and 9")


@dataclass(frozen=True)
class MailMessage:
    """Email from Apple Mail.

    Parameters
    ----------
    id : str
        Unique identifier for the message
    subject : str
        Email subject line
    sender : str
        Sender email address
    recipients : tuple[str, ...]
        Tuple of recipient email addresses
    date : datetime
        Message timestamp (timezone-aware)
    body : str | None
        Optional message body content
    """

    id: str
    subject: str
    sender: str
    recipients: tuple[str, ...]
    date: datetime
    body: str | None = None

    def __post_init__(self) -> None:
        """Validate mail message data after initialization."""
        if not self.id:
            raise ValueError("Message ID cannot be empty")
        if not self.subject:
            raise ValueError("Message subject cannot be empty")
        if not self._is_valid_email(self.sender):
            raise ValueError(f"Invalid sender email: {self.sender}")
        for recipient in self.recipients:
            if not self._is_valid_email(recipient):
                raise ValueError(f"Invalid recipient email: {recipient}")

    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """Validate email address format.

        Parameters
        ----------
        email : str
            Email address to validate

        Returns
        -------
        bool
            True if email format is valid
        """
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))


@dataclass(frozen=True)
class IngestResult:
    """Result of ingestion operation.

    Parameters
    ----------
    success : bool
        Whether ingestion succeeded overall
    items_processed : int
        Number of items successfully processed
    errors : tuple[str, ...]
        Tuple of error messages encountered
    duration_ms : float
        Processing duration in milliseconds
    """

    success: bool
    items_processed: int
    errors: tuple[str, ...]
    duration_ms: float = 0.0


class AppleDataIngester:
    """Ingest data from Apple applications (Calendar, Reminders, Mail).

    This class provides methods to ingest data from Apple applications
    and convert them to typed Python objects and RDF/Turtle format.

    Examples
    --------
    >>> ingester = AppleDataIngester()
    >>> data = [{"id": "1", "title": "Meeting", "start_time": "2025-01-01T10:00:00Z", "end_time": "2025-01-01T11:00:00Z"}]
    >>> result = ingester.ingest_calendar(data)
    >>> assert result.success
    >>> assert result.items_processed == 1
    """

    def ingest_calendar(self, data: list[dict[str, Any]]) -> IngestResult:
        """Ingest calendar events from raw data.

        Parameters
        ----------
        data : list[dict[str, Any]]
            List of raw calendar event dictionaries

        Returns
        -------
        IngestResult
            Ingestion result with success status and error details
        """
        start_time = time.perf_counter()
        events: list[CalendarEvent] = []
        errors: list[str] = []

        for item in data:
            try:
                event = self._parse_calendar_event(item)
                events.append(event)
            except (ValueError, KeyError, TypeError) as e:
                errors.append(f"Failed to parse event: {e}")

        duration_ms = (time.perf_counter() - start_time) * 1000
        self._cached_events = events

        return IngestResult(
            success=len(errors) == 0,
            items_processed=len(events),
            errors=tuple(errors),
            duration_ms=duration_ms,
        )

    def ingest_reminders(self, data: list[dict[str, Any]]) -> IngestResult:
        """Ingest reminders from raw data.

        Parameters
        ----------
        data : list[dict[str, Any]]
            List of raw reminder dictionaries

        Returns
        -------
        IngestResult
            Ingestion result with success status and error details
        """
        start_time = time.perf_counter()
        reminders: list[Reminder] = []
        errors: list[str] = []

        for item in data:
            try:
                reminder = self._parse_reminder(item)
                reminders.append(reminder)
            except (ValueError, KeyError, TypeError) as e:
                errors.append(f"Failed to parse reminder: {e}")

        duration_ms = (time.perf_counter() - start_time) * 1000
        self._cached_reminders = reminders

        return IngestResult(
            success=len(errors) == 0,
            items_processed=len(reminders),
            errors=tuple(errors),
            duration_ms=duration_ms,
        )

    def ingest_mail(self, data: list[dict[str, Any]]) -> IngestResult:
        """Ingest mail messages from raw data.

        Parameters
        ----------
        data : list[dict[str, Any]]
            List of raw mail message dictionaries

        Returns
        -------
        IngestResult
            Ingestion result with success status and error details
        """
        start_time = time.perf_counter()
        messages: list[MailMessage] = []
        errors: list[str] = []

        for item in data:
            try:
                message = self._parse_mail_message(item)
                messages.append(message)
            except (ValueError, KeyError, TypeError) as e:
                errors.append(f"Failed to parse message: {e}")

        duration_ms = (time.perf_counter() - start_time) * 1000
        self._cached_messages = messages

        return IngestResult(
            success=len(errors) == 0,
            items_processed=len(messages),
            errors=tuple(errors),
            duration_ms=duration_ms,
        )

    def to_rdf(self, items: list[CalendarEvent | Reminder | MailMessage]) -> str:
        """Convert items to RDF/Turtle format.

        Parameters
        ----------
        items : list[CalendarEvent | Reminder | MailMessage]
            List of typed items to convert

        Returns
        -------
        str
            RDF/Turtle formatted string

        Raises
        ------
        ValueError
            If items list is empty or contains unknown types
        """
        if not items:
            raise ValueError("Cannot convert empty items list to RDF")

        rdf_lines: list[str] = [
            "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            "@prefix cal: <http://www.w3.org/2002/12/cal/ical#> .",
            "@prefix mail: <http://example.org/mail#> .",
            "@prefix todo: <http://example.org/todo#> .",
            "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
            "",
        ]

        for item in items:
            if isinstance(item, CalendarEvent):
                rdf_lines.extend(self._calendar_event_to_rdf(item))
            elif isinstance(item, Reminder):
                rdf_lines.extend(self._reminder_to_rdf(item))
            elif isinstance(item, MailMessage):
                rdf_lines.extend(self._mail_message_to_rdf(item))
            else:
                raise ValueError(f"Unknown item type: {type(item)}")

        return "\n".join(rdf_lines)

    def _parse_calendar_event(self, data: dict[str, Any]) -> CalendarEvent:
        """Parse raw calendar event data into CalendarEvent object."""
        return CalendarEvent(
            id=str(data["id"]),
            title=str(data["title"]),
            start_time=self._parse_datetime(data["start_time"]),
            end_time=self._parse_datetime(data["end_time"]),
            location=str(data["location"]) if "location" in data else None,
            notes=str(data["notes"]) if "notes" in data else None,
        )

    def _parse_reminder(self, data: dict[str, Any]) -> Reminder:
        """Parse raw reminder data into Reminder object."""
        due_date = None
        if "due_date" in data and data["due_date"] is not None:
            due_date = self._parse_datetime(data["due_date"])

        return Reminder(
            id=str(data["id"]),
            title=str(data["title"]),
            due_date=due_date,
            completed=bool(data.get("completed", False)),
            priority=int(data.get("priority", 0)),
        )

    def _parse_mail_message(self, data: dict[str, Any]) -> MailMessage:
        """Parse raw mail message data into MailMessage object."""
        recipients_raw = data["recipients"]
        recipients: tuple[str, ...]
        if isinstance(recipients_raw, str):
            recipients = (recipients_raw,)
        else:
            recipients = tuple(str(r) for r in recipients_raw)

        return MailMessage(
            id=str(data["id"]),
            subject=str(data["subject"]),
            sender=str(data["sender"]),
            recipients=recipients,
            date=self._parse_datetime(data["date"]),
            body=str(data["body"]) if "body" in data else None,
        )

    def _parse_datetime(self, value: str | datetime) -> datetime:
        """Parse datetime from string or return existing datetime.

        Parameters
        ----------
        value : str | datetime
            Datetime value to parse

        Returns
        -------
        datetime
            Timezone-aware datetime object

        Raises
        ------
        ValueError
            If datetime string format is invalid
        """
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

        # Handle ISO 8601 formats with 'Z' suffix
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"

        try:
            dt = datetime.fromisoformat(value)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError as e:
            raise ValueError(f"Invalid datetime format: {value}") from e

    def _calendar_event_to_rdf(self, event: CalendarEvent) -> list[str]:
        """Convert CalendarEvent to RDF/Turtle format."""
        rdf: list[str] = [
            f"cal:event_{event.id}",
            "    a cal:Vevent ;",
            f'    cal:summary "{self._escape_rdf_literal(event.title)}" ;',
            f'    cal:dtstart "{event.start_time.isoformat()}"^^xsd:dateTime ;',
            f'    cal:dtend "{event.end_time.isoformat()}"^^xsd:dateTime',
        ]

        if event.location:
            rdf.append(f'    cal:location "{self._escape_rdf_literal(event.location)}"')
        if event.notes:
            rdf.append(f'    cal:description "{self._escape_rdf_literal(event.notes)}"')

        rdf[-1] += " ."
        rdf.append("")
        return rdf

    def _reminder_to_rdf(self, reminder: Reminder) -> list[str]:
        """Convert Reminder to RDF/Turtle format."""
        rdf: list[str] = [
            f"todo:reminder_{reminder.id}",
            "    a todo:Reminder ;",
            f'    todo:title "{self._escape_rdf_literal(reminder.title)}" ;',
            f'    todo:completed "{str(reminder.completed).lower()}"^^xsd:boolean ;',
            f'    todo:priority "{reminder.priority}"^^xsd:integer',
        ]

        if reminder.due_date:
            rdf.append(f'    todo:dueDate "{reminder.due_date.isoformat()}"^^xsd:dateTime')

        rdf[-1] += " ."
        rdf.append("")
        return rdf

    def _mail_message_to_rdf(self, message: MailMessage) -> list[str]:
        """Convert MailMessage to RDF/Turtle format."""
        rdf: list[str] = [
            f"mail:message_{message.id}",
            "    a mail:Message ;",
            f'    mail:subject "{self._escape_rdf_literal(message.subject)}" ;',
            f'    mail:sender "{message.sender}" ;',
            f'    mail:date "{message.date.isoformat()}"^^xsd:dateTime',
        ]

        for recipient in message.recipients:
            rdf.append(f'    mail:recipient "{recipient}"')

        if message.body:
            rdf.append(f'    mail:body "{self._escape_rdf_literal(message.body)}"')

        rdf[-1] += " ."
        rdf.append("")
        return rdf

    def _escape_rdf_literal(self, value: str) -> str:
        """Escape special characters in RDF literals."""
        return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

    # Cache for converted items
    _cached_events: list[CalendarEvent] = []
    _cached_reminders: list[Reminder] = []
    _cached_messages: list[MailMessage] = []


# ============================================================================
# INLINE TESTS (Chicago School TDD - Real objects, observable behavior)
# ============================================================================


def test_ingest_calendar_event_simple() -> None:
    """Simple calendar event ingestion with required fields only."""
    ingester = AppleDataIngester()
    data = [
        {
            "id": "evt-001",
            "title": "Team Meeting",
            "start_time": "2025-01-15T10:00:00Z",
            "end_time": "2025-01-15T11:00:00Z",
        }
    ]

    result = ingester.ingest_calendar(data)

    assert result.success is True
    assert result.items_processed == 1
    assert len(result.errors) == 0
    assert result.duration_ms > 0

    # Verify parsed event
    events = ingester._cached_events
    assert len(events) == 1
    event = events[0]
    assert event.id == "evt-001"
    assert event.title == "Team Meeting"
    assert event.start_time.year == 2025
    assert event.start_time.month == 1
    assert event.start_time.day == 15
    assert event.location is None
    assert event.notes is None


def test_ingest_calendar_event_all_day() -> None:
    """All-day calendar event with location and notes."""
    ingester = AppleDataIngester()
    data = [
        {
            "id": "evt-002",
            "title": "Conference",
            "start_time": "2025-02-01T00:00:00Z",
            "end_time": "2025-02-01T23:59:59Z",
            "location": "Convention Center",
            "notes": "Annual tech conference",
        }
    ]

    result = ingester.ingest_calendar(data)

    assert result.success is True
    assert result.items_processed == 1

    event = ingester._cached_events[0]
    assert event.id == "evt-002"
    assert event.title == "Conference"
    assert event.location == "Convention Center"
    assert event.notes == "Annual tech conference"


def test_ingest_reminder_with_due_date() -> None:
    """Reminder with due date and priority."""
    ingester = AppleDataIngester()
    data = [
        {
            "id": "rem-001",
            "title": "Submit report",
            "due_date": "2025-01-20T17:00:00Z",
            "completed": False,
            "priority": 8,
        }
    ]

    result = ingester.ingest_reminders(data)

    assert result.success is True
    assert result.items_processed == 1

    reminder = ingester._cached_reminders[0]
    assert reminder.id == "rem-001"
    assert reminder.title == "Submit report"
    assert reminder.due_date is not None
    assert reminder.due_date.day == 20
    assert reminder.completed is False
    assert reminder.priority == 8


def test_ingest_reminder_completed() -> None:
    """Completed reminder without due date."""
    ingester = AppleDataIngester()
    data = [
        {
            "id": "rem-002",
            "title": "Buy groceries",
            "completed": True,
        }
    ]

    result = ingester.ingest_reminders(data)

    assert result.success is True
    assert result.items_processed == 1

    reminder = ingester._cached_reminders[0]
    assert reminder.id == "rem-002"
    assert reminder.title == "Buy groceries"
    assert reminder.due_date is None
    assert reminder.completed is True
    assert reminder.priority == 0


def test_ingest_mail_with_recipients() -> None:
    """Mail message with multiple recipients and body."""
    ingester = AppleDataIngester()
    data = [
        {
            "id": "msg-001",
            "subject": "Project Update",
            "sender": "alice@example.com",
            "recipients": ["bob@example.com", "charlie@example.com"],
            "date": "2025-01-10T14:30:00Z",
            "body": "Here is the latest project status.",
        }
    ]

    result = ingester.ingest_mail(data)

    assert result.success is True
    assert result.items_processed == 1

    message = ingester._cached_messages[0]
    assert message.id == "msg-001"
    assert message.subject == "Project Update"
    assert message.sender == "alice@example.com"
    assert len(message.recipients) == 2
    assert "bob@example.com" in message.recipients
    assert "charlie@example.com" in message.recipients
    assert message.body == "Here is the latest project status."


def test_ingest_mail_no_body() -> None:
    """Mail message without body content."""
    ingester = AppleDataIngester()
    data = [
        {
            "id": "msg-002",
            "subject": "Quick question",
            "sender": "dave@example.com",
            "recipients": "eve@example.com",
            "date": "2025-01-11T09:15:00Z",
        }
    ]

    result = ingester.ingest_mail(data)

    assert result.success is True
    assert result.items_processed == 1

    message = ingester._cached_messages[0]
    assert message.id == "msg-002"
    assert message.body is None
    assert len(message.recipients) == 1
    assert message.recipients[0] == "eve@example.com"


def test_to_rdf_calendar_event() -> None:
    """Convert calendar event to RDF/Turtle format."""
    event = CalendarEvent(
        id="evt-rdf-001",
        title="Board Meeting",
        start_time=datetime(2025, 3, 1, 14, 0, 0, tzinfo=timezone.utc),
        end_time=datetime(2025, 3, 1, 16, 0, 0, tzinfo=timezone.utc),
        location="Board Room",
    )

    ingester = AppleDataIngester()
    rdf = ingester.to_rdf([event])

    assert "@prefix cal:" in rdf
    assert "cal:event_evt-rdf-001" in rdf
    assert 'cal:summary "Board Meeting"' in rdf
    assert "cal:dtstart" in rdf
    assert "2025-03-01T14:00:00" in rdf
    assert 'cal:location "Board Room"' in rdf


def test_to_rdf_reminder() -> None:
    """Convert reminder to RDF/Turtle format."""
    reminder = Reminder(
        id="rem-rdf-001",
        title="Review code",
        due_date=datetime(2025, 1, 25, 12, 0, 0, tzinfo=timezone.utc),
        completed=False,
        priority=7,
    )

    ingester = AppleDataIngester()
    rdf = ingester.to_rdf([reminder])

    assert "@prefix todo:" in rdf
    assert "todo:reminder_rem-rdf-001" in rdf
    assert 'todo:title "Review code"' in rdf
    assert 'todo:completed "false"' in rdf
    assert 'todo:priority "7"' in rdf
    assert "todo:dueDate" in rdf


def test_ingest_handles_invalid_data() -> None:
    """Invalid data should be captured in errors, not crash."""
    ingester = AppleDataIngester()
    data = [
        {"id": "evt-001", "title": "Valid Event", "start_time": "2025-01-15T10:00:00Z", "end_time": "2025-01-15T11:00:00Z"},
        {"id": "evt-002"},  # Missing required fields
        {"id": "evt-003", "title": "Bad Times", "start_time": "2025-01-15T11:00:00Z", "end_time": "2025-01-15T10:00:00Z"},  # End before start
    ]

    result = ingester.ingest_calendar(data)

    assert result.success is False
    assert result.items_processed == 1
    assert len(result.errors) == 2
    assert "Failed to parse event" in result.errors[0]


def test_batch_ingest_multiple_types() -> None:
    """Ingest multiple types and convert all to RDF."""
    ingester = AppleDataIngester()

    # Ingest calendar events
    calendar_data = [
        {"id": "e1", "title": "Meeting", "start_time": "2025-01-15T10:00:00Z", "end_time": "2025-01-15T11:00:00Z"}
    ]
    cal_result = ingester.ingest_calendar(calendar_data)
    assert cal_result.success is True

    # Ingest reminders
    reminder_data = [{"id": "r1", "title": "Task 1", "priority": 5}]
    rem_result = ingester.ingest_reminders(reminder_data)
    assert rem_result.success is True

    # Ingest mail
    mail_data = [
        {
            "id": "m1",
            "subject": "Test",
            "sender": "test@example.com",
            "recipients": ["user@example.com"],
            "date": "2025-01-15T12:00:00Z",
        }
    ]
    mail_result = ingester.ingest_mail(mail_data)
    assert mail_result.success is True

    # Convert all to RDF
    all_items: list[CalendarEvent | Reminder | MailMessage] = [
        *ingester._cached_events,
        *ingester._cached_reminders,
        *ingester._cached_messages,
    ]
    rdf = ingester.to_rdf(all_items)

    assert "cal:event_e1" in rdf
    assert "todo:reminder_r1" in rdf
    assert "mail:message_m1" in rdf


def test_performance_1000_items() -> None:
    """Performance: ingest 1000 items < 100ms."""
    ingester = AppleDataIngester()

    # Generate 1000 calendar events
    data = [
        {
            "id": f"perf-{i}",
            "title": f"Event {i}",
            "start_time": f"2025-01-{(i % 28) + 1:02d}T10:00:00Z",
            "end_time": f"2025-01-{(i % 28) + 1:02d}T11:00:00Z",
        }
        for i in range(1000)
    ]

    result = ingester.ingest_calendar(data)

    assert result.success is True
    assert result.items_processed == 1000
    assert result.duration_ms < 100.0, f"Performance regression: {result.duration_ms:.2f}ms (target: <100ms)"


def test_email_validation() -> None:
    """Email validation rejects invalid addresses."""
    ingester = AppleDataIngester()
    invalid_data = [
        {
            "id": "m1",
            "subject": "Test",
            "sender": "invalid-email",  # Invalid format
            "recipients": ["user@example.com"],
            "date": "2025-01-15T12:00:00Z",
        }
    ]

    result = ingester.ingest_mail(invalid_data)

    assert result.success is False
    assert result.items_processed == 0
    assert len(result.errors) == 1
    assert "Invalid sender email" in result.errors[0]


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================


def run_all_tests() -> tuple[int, int]:
    """Run all inline tests and return (passed, failed) counts."""
    tests = [
        ("Calendar Event Simple", test_ingest_calendar_event_simple),
        ("Calendar Event All-Day", test_ingest_calendar_event_all_day),
        ("Reminder With Due Date", test_ingest_reminder_with_due_date),
        ("Reminder Completed", test_ingest_reminder_completed),
        ("Mail With Recipients", test_ingest_mail_with_recipients),
        ("Mail No Body", test_ingest_mail_no_body),
        ("RDF Calendar Event", test_to_rdf_calendar_event),
        ("RDF Reminder", test_to_rdf_reminder),
        ("Invalid Data Handling", test_ingest_handles_invalid_data),
        ("Batch Ingest Multiple Types", test_batch_ingest_multiple_types),
        ("Performance 1000 Items", test_performance_1000_items),
        ("Email Validation", test_email_validation),
    ]

    passed = 0
    failed = 0

    print("=" * 70)
    print("POC: Apple Data Ingestion Pipeline - Test Results")
    print("=" * 70)

    for name, test_func in tests:
        try:
            test_func()
            print(f"✓ {name}")
            passed += 1
        except AssertionError as e:
            print(f"✗ {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {name}: Unexpected error: {e}")
            failed += 1

    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)

    return passed, failed


if __name__ == "__main__":
    passed, failed = run_all_tests()

    # Performance benchmark summary
    print("\nPerformance Benchmark:")
    ingester = AppleDataIngester()
    data_1k = [
        {
            "id": f"bench-{i}",
            "title": f"Event {i}",
            "start_time": f"2025-01-{(i % 28) + 1:02d}T10:00:00Z",
            "end_time": f"2025-01-{(i % 28) + 1:02d}T11:00:00Z",
        }
        for i in range(1000)
    ]
    result = ingester.ingest_calendar(data_1k)
    print(f"  - 1000 items ingested in {result.duration_ms:.2f}ms")
    print(f"  - Target: <100ms | Actual: {result.duration_ms:.2f}ms")
    print(f"  - Status: {'✓ PASS' if result.duration_ms < 100 else '✗ FAIL'}")

    # Exit with proper code
    sys.exit(0 if failed == 0 else 1)

"""Test fixtures for Apple data ingest (EventKit, Mail, Spotlight)."""

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

# ============================================================================
# Mock EventKit Classes (PyObjC EventKitStubs)
# ============================================================================


@dataclass
class MockEKEvent:
    """Mock EventKit EKEvent for testing Calendar ingestion."""

    event_id: str
    title: str
    start_date: datetime
    end_date: datetime
    calendar_title: str = "Calendar"
    location: str | None = None
    notes: str | None = None
    attendees: list[dict] | None = None  # [{"name": str, "email": str}]
    is_all_day: bool = False

    @property
    def eventIdentifier(self) -> str:
        """EventKit property: unique identifier."""
        return self.event_id

    @property
    def title_property(self) -> str:
        """EventKit property: event title."""
        return self.title

    @property
    def startDate(self) -> datetime:
        """EventKit property: start date/time."""
        return self.start_date

    @property
    def endDate(self) -> datetime:
        """EventKit property: end date/time."""
        return self.end_date

    @property
    def calendar(self) -> object:
        """EventKit property: parent calendar."""
        return MockEKCalendar(self.calendar_title)

    @property
    def location_property(self) -> str | None:
        """EventKit property: event location."""
        return self.location

    @property
    def notes_property(self) -> str | None:
        """EventKit property: event notes/description."""
        return self.notes

    @property
    def attendees_list(self) -> list[dict] | None:
        """EventKit property: attendees list."""
        return self.attendees or []

    @property
    def isAllDay(self) -> bool:
        """EventKit property: all-day event flag."""
        return self.is_all_day


@dataclass
class MockEKCalendar:
    """Mock EventKit EKCalendar."""

    title: str


@dataclass
class MockEKReminder:
    """Mock EventKit EKReminder for testing Reminders ingestion."""

    reminder_id: str
    title: str
    completed: bool = False
    due_date: datetime | None = None
    list_title: str = "Inbox"
    notes: str | None = None
    priority: int = 0  # 0=none, 1=high, 5=medium, 9=low

    @property
    def calendarItemIdentifier(self) -> str:
        """EventKit property: unique identifier."""
        return self.reminder_id

    @property
    def title_property(self) -> str:
        """EventKit property: reminder title."""
        return self.title

    @property
    def isCompleted(self) -> bool:
        """EventKit property: completion status."""
        return self.completed

    @property
    def dueDateComponents(self) -> datetime | None:
        """EventKit property: due date."""
        return self.due_date

    @property
    def calendar(self) -> object:
        """EventKit property: parent list."""
        return MockEKList(self.list_title)

    @property
    def notes_property(self) -> str | None:
        """EventKit property: notes."""
        return self.notes

    @property
    def priority_property(self) -> int:
        """EventKit property: priority (0-9)."""
        return self.priority


@dataclass
class MockEKList:
    """Mock EventKit reminder list."""

    title: str


# ============================================================================
# Mock Mail Classes
# ============================================================================


@dataclass
class MockMailMessage:
    """Mock Mail.app message for testing Mail ingestion."""

    message_id: str
    subject: str
    sender_email: str
    sender_name: str
    recipient_emails: list[str]
    date_received: datetime
    is_flagged: bool = False
    body_snippet: str | None = None

    @property
    def messageID(self) -> str:
        """RFC 5322 Message-ID."""
        return self.message_id

    @property
    def subject_property(self) -> str:
        """Mail property: message subject."""
        return self.subject

    @property
    def senders(self) -> list[dict]:
        """Mail property: from addresses."""
        return [{"email": self.sender_email, "name": self.sender_name}]

    @property
    def recipients(self) -> list[dict]:
        """Mail property: to addresses."""
        return [{"email": email} for email in self.recipient_emails]

    @property
    def dateReceived(self) -> datetime:
        """Mail property: date received."""
        return self.date_received

    @property
    def isFlagged(self) -> bool:
        """Mail property: flagged status."""
        return self.is_flagged


# ============================================================================
# Mock Spotlight/File Metadata
# ============================================================================


@dataclass
class MockFileMetadata:
    """Mock file metadata from Spotlight/Finder."""

    file_path: str
    file_name: str
    created_date: datetime
    modified_date: datetime
    file_size: int = 0
    file_type: str = "text/markdown"
    finder_tags: list[str] | None = None

    @property
    def path(self) -> str:
        """File system path."""
        return self.file_path

    @property
    def name(self) -> str:
        """File name."""
        return self.file_name

    @property
    def contentCreationDate(self) -> datetime:
        """Spotlight/FSEvent property: creation date."""
        return self.created_date

    @property
    def contentModificationDate(self) -> datetime:
        """Spotlight/FSEvent property: modification date."""
        return self.modified_date

    @property
    def fileSize(self) -> int:
        """File size in bytes."""
        return self.file_size

    @property
    def contentType(self) -> str:
        """MIME type / UTType."""
        return self.file_type

    @property
    def tags(self) -> list[str]:
        """Finder tags from xattr."""
        return self.finder_tags or []


# ============================================================================
# Pytest Fixtures: Test Data
# ============================================================================


@pytest.fixture
def calendar_event_simple():
    """Simple calendar event (untitled event should fail validation)."""
    return MockEKEvent(
        event_id="ek-event-001",
        title="Team Standup",
        start_date=datetime(2025, 11, 24, 9, 0, 0, tzinfo=UTC),
        end_date=datetime(2025, 11, 24, 9, 30, 0, tzinfo=UTC),
        calendar_title="Work",
    )


@pytest.fixture
def calendar_event_with_attendees():
    """Calendar event with attendees."""
    return MockEKEvent(
        event_id="ek-event-002",
        title="Q4 Planning",
        start_date=datetime(2025, 11, 24, 14, 0, 0, tzinfo=UTC),
        end_date=datetime(2025, 11, 24, 15, 30, 0, tzinfo=UTC),
        calendar_title="Work",
        location="Zoom: https://zoom.us/my-meeting",
        notes="Quarterly planning session",
        attendees=[
            {"name": "Alice Smith", "email": "alice@work.com"},
            {"name": "Bob Jones", "email": "bob@work.com"},
        ],
    )


@pytest.fixture
def calendar_event_all_day():
    """All-day calendar event."""
    return MockEKEvent(
        event_id="ek-event-003",
        title="Company Holiday",
        start_date=datetime(2025, 12, 25, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2025, 12, 26, 0, 0, 0, tzinfo=UTC),
        calendar_title="Holidays",
        is_all_day=True,
    )


@pytest.fixture
def calendar_event_invalid_times():
    """Calendar event with start >= end (should fail validation)."""
    return MockEKEvent(
        event_id="ek-event-bad-001",
        title="Invalid Event",
        start_date=datetime(2025, 11, 24, 15, 0, 0, tzinfo=UTC),
        end_date=datetime(2025, 11, 24, 14, 0, 0, tzinfo=UTC),  # End before start!
        calendar_title="Work",
    )


@pytest.fixture
def calendar_event_no_title():
    """Calendar event with empty title (should fail validation)."""
    return MockEKEvent(
        event_id="ek-event-bad-002",
        title="",  # Empty title!
        start_date=datetime(2025, 11, 24, 10, 0, 0, tzinfo=UTC),
        end_date=datetime(2025, 11, 24, 11, 0, 0, tzinfo=UTC),
        calendar_title="Work",
    )


@pytest.fixture
def reminder_task_simple():
    """Simple task (incomplete, no due date)."""
    return MockEKReminder(
        reminder_id="ek-reminder-001", title="Review Q4 metrics", completed=False, list_title="Work"
    )


@pytest.fixture
def reminder_task_with_due_date():
    """Task with due date."""
    return MockEKReminder(
        reminder_id="ek-reminder-002",
        title="Submit budget proposal",
        completed=False,
        due_date=datetime(2025, 11, 28, 17, 0, 0, tzinfo=UTC),
        list_title="Work",
        priority=1,  # High priority
    )


@pytest.fixture
def reminder_task_completed():
    """Completed task."""
    return MockEKReminder(
        reminder_id="ek-reminder-003",
        title="Finalize presentation",
        completed=True,
        due_date=datetime(2025, 11, 24, 12, 0, 0, tzinfo=UTC),
        list_title="Work",
    )


@pytest.fixture
def reminder_task_today():
    """Task marked as due today (should validate due date is today)."""
    today = datetime.now(tz=UTC).replace(hour=17, minute=0, second=0, microsecond=0)
    return MockEKReminder(
        reminder_id="ek-reminder-today",
        title="Daily standup",
        completed=False,
        due_date=today,
        list_title="Work",
    )


@pytest.fixture
def reminder_task_no_status():
    """Task with no status (should fail validation if required)."""
    return MockEKReminder(
        reminder_id="ek-reminder-bad-001",
        title="Update wiki",
        completed=None,  # No status!
        list_title="Work",
    )


@pytest.fixture
def mail_message_simple():
    """Simple email message."""
    return MockMailMessage(
        message_id="<msg-001@mail.example.com>",
        subject="Q4 Review Feedback",
        sender_email="alice@work.com",
        sender_name="Alice Smith",
        recipient_emails=["you@work.com"],
        date_received=datetime(2025, 11, 24, 10, 30, 0, tzinfo=UTC),
    )


@pytest.fixture
def mail_message_flagged():
    """Flagged email message."""
    return MockMailMessage(
        message_id="<msg-002@mail.example.com>",
        subject="ACTION REQUIRED: Budget Approval",
        sender_email="finance@work.com",
        sender_name="Finance Team",
        recipient_emails=["you@work.com", "manager@work.com"],
        date_received=datetime(2025, 11, 24, 14, 15, 0, tzinfo=UTC),
        is_flagged=True,
    )


@pytest.fixture
def mail_message_no_sender():
    """Email with no sender (should fail validation)."""
    return MockMailMessage(
        message_id="<msg-bad-001@mail.example.com>",
        subject="Mystery Email",
        sender_email="",  # No sender!
        sender_name="",
        recipient_emails=["you@work.com"],
        date_received=datetime(2025, 11, 24, 11, 0, 0, tzinfo=UTC),
    )


@pytest.fixture
def file_markdown_note():
    """Markdown note file."""
    return MockFileMetadata(
        file_path="/Users/sac/Documents/Q4_Review.md",
        file_name="Q4_Review.md",
        created_date=datetime(2025, 11, 20, 9, 0, 0, tzinfo=UTC),
        modified_date=datetime(2025, 11, 24, 10, 45, 0, tzinfo=UTC),
        file_size=2048,
        file_type="text/markdown",
        finder_tags=["project", "q4", "review"],
    )


@pytest.fixture
def file_document():
    """Rich text document."""
    return MockFileMetadata(
        file_path="/Users/sac/Documents/Budget_Draft.docx",
        file_name="Budget_Draft.docx",
        created_date=datetime(2025, 11, 18, 14, 30, 0, tzinfo=UTC),
        modified_date=datetime(2025, 11, 24, 16, 0, 0, tzinfo=UTC),
        file_size=51200,
        file_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        finder_tags=["finance"],
    )


@pytest.fixture
def file_invalid_path():
    """File with invalid path (should fail validation)."""
    return MockFileMetadata(
        file_path="invalid/relative/path.md",  # Not absolute!
        file_name="path.md",
        created_date=datetime(2025, 11, 24, 10, 0, 0, tzinfo=UTC),
        modified_date=datetime(2025, 11, 24, 10, 0, 0, tzinfo=UTC),
        file_type="text/markdown",
    )


# ============================================================================
# Batch Fixtures
# ============================================================================


@pytest.fixture
def calendar_event_batch(
    calendar_event_simple, calendar_event_with_attendees, calendar_event_all_day
):
    """Batch of multiple calendar events."""
    return [calendar_event_simple, calendar_event_with_attendees, calendar_event_all_day]


@pytest.fixture
def reminder_task_batch(reminder_task_simple, reminder_task_with_due_date, reminder_task_completed):
    """Batch of multiple reminders."""
    return [reminder_task_simple, reminder_task_with_due_date, reminder_task_completed]


@pytest.fixture
def mail_message_batch(mail_message_simple, mail_message_flagged):
    """Batch of multiple mail messages."""
    return [mail_message_simple, mail_message_flagged]


@pytest.fixture
def file_metadata_batch(file_markdown_note, file_document):
    """Batch of multiple files."""
    return [file_markdown_note, file_document]


# ============================================================================
# Combined Ingest Batches
# ============================================================================


@pytest.fixture
def full_ingest_data(
    calendar_event_batch, reminder_task_batch, mail_message_batch, file_metadata_batch
):
    """Complete ingest data: all 4 data sources."""
    return {
        "calendar_events": calendar_event_batch,
        "reminders": reminder_task_batch,
        "mail_messages": mail_message_batch,
        "files": file_metadata_batch,
    }


@pytest.fixture
def invalid_ingest_data():
    """Ingest data with intentional validation failures (for quality testing)."""
    return {
        "bad_calendar_events": [
            MockEKEvent(
                event_id="ek-event-bad-001",
                title="Invalid Event",
                start_date=datetime(2025, 11, 24, 15, 0, 0, tzinfo=UTC),
                end_date=datetime(2025, 11, 24, 14, 0, 0, tzinfo=UTC),
                calendar_title="Work",
            ),
            MockEKEvent(
                event_id="ek-event-bad-002",
                title="",
                start_date=datetime(2025, 11, 24, 10, 0, 0, tzinfo=UTC),
                end_date=datetime(2025, 11, 24, 11, 0, 0, tzinfo=UTC),
                calendar_title="Work",
            ),
        ],
        "bad_reminders": [
            MockEKReminder(
                reminder_id="reminder-bad-001",
                title="No Status Task",
                completed=False,
                list_title="Work",
            )
        ],
        "bad_mail_messages": [
            MockMailMessage(
                message_id="<msg-bad-001@mail.example.com>",
                subject="No Sender Message",
                sender_email="",
                sender_name="",
                recipient_emails=["user@company.com"],
                date_received=datetime(2025, 11, 24, 10, 0, 0, tzinfo=UTC),
            )
        ],
        "bad_files": [
            MockFileMetadata(
                file_path="relative/path/file.txt",
                file_name="file.txt",
                created_date=datetime(2025, 11, 24, 10, 0, 0, tzinfo=UTC),
                modified_date=datetime(2025, 11, 24, 10, 0, 0, tzinfo=UTC),
                file_type="text/plain",
            )
        ],
    }

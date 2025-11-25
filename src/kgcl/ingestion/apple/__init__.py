"""Apple data ingest engines for macOS/iOS frameworks.

Provides PyObjC-based ingestion for:
- Calendar events (EventKit)
- Reminders/tasks (EventKit)
- Email metadata (Mail.app)
- File metadata (Spotlight/Finder)

All ingest engines produce schema.org RDF triples with Apple-specific tracking.
"""

from kgcl.ingestion.apple.calendar import CalendarIngestEngine
from kgcl.ingestion.apple.files import FilesIngestEngine
from kgcl.ingestion.apple.mail import MailIngestEngine
from kgcl.ingestion.apple.pipeline import AppleIngestPipeline
from kgcl.ingestion.apple.reminders import RemindersIngestEngine

__all__ = [
    "AppleIngestPipeline",
    "CalendarIngestEngine",
    "FilesIngestEngine",
    "MailIngestEngine",
    "RemindersIngestEngine",
]

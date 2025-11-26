"""Configuration loader for apple.ingest.ttl."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rdflib import Graph, Literal, Namespace

APPLE = Namespace("urn:kgc:apple:")
KGC = Namespace("urn:kgc:")

DEFAULT_KGC_DIR = Path(__file__).resolve().parents[3] / ".kgc"
DEFAULT_CONFIG_PATH = DEFAULT_KGC_DIR / "apple.ingest.ttl"


@dataclass(frozen=True)
class AppleIngestConfig:
    """Parsed ingest configuration from `.kgc/apple.ingest.ttl`."""

    include_calendars: bool
    include_reminders: bool
    include_mail: bool
    include_files: bool
    calendar_past_days: int
    calendar_future_days: int
    reminder_completed_age: int
    mail_past_days: int
    file_threshold_days: int
    max_events: int
    max_reminders: int
    max_mail: int
    max_files: int
    output_path: Path
    backup_path: Path
    cache_expiry_seconds: int


def _bool(graph: Graph, subject, predicate) -> bool:
    literal = graph.value(subject=subject, predicate=predicate)
    if isinstance(literal, Literal):
        return literal.toPython()  # type: ignore[no-any-return]
    return False


def _int(graph: Graph, subject, predicate, default: int = 0) -> int:
    literal = graph.value(subject=subject, predicate=predicate)
    if isinstance(literal, Literal) and literal.datatype:
        try:
            return int(literal)
        except (TypeError, ValueError):
            return default
    return default


def load_ingest_config(path: Path | None = None) -> AppleIngestConfig:
    """Load ingest configuration from the provided TTL file."""
    config_path = path or DEFAULT_CONFIG_PATH
    if not config_path.exists():
        raise FileNotFoundError(f"Apple ingest configuration not found at {config_path}")

    graph = Graph()
    graph.parse(config_path, format="turtle")

    subject = APPLE["IngestionConfig"]
    output_literal = graph.value(subject=subject, predicate=APPLE.outputPath)
    backup_literal = graph.value(subject=subject, predicate=APPLE.backupPath)

    return AppleIngestConfig(
        include_calendars=_bool(graph, subject, APPLE.includeCalendars),
        include_reminders=_bool(graph, subject, APPLE.includeReminders),
        include_mail=_bool(graph, subject, APPLE.includeMail),
        include_files=_bool(graph, subject, APPLE.includeFiles),
        calendar_past_days=_int(
            graph, graph.value(subject=subject, predicate=APPLE.includeCalendarDateRange), KGC.pastDays, 90
        ),
        calendar_future_days=_int(
            graph, graph.value(subject=subject, predicate=APPLE.includeCalendarDateRange), KGC.futureDays, 180
        ),
        reminder_completed_age=_int(graph, subject, APPLE.reminderCompletedAgeThreshold, 30),
        mail_past_days=_int(graph, graph.value(subject=subject, predicate=APPLE.mailDateRange), KGC.pastDays, 60),
        file_threshold_days=_int(graph, subject, APPLE.fileModificationThreshold, 90),
        max_events=_int(graph, subject, APPLE.maxEvents, 2000),
        max_reminders=_int(graph, subject, APPLE.maxReminders, 1000),
        max_mail=_int(graph, subject, APPLE.maxMailMessages, 500),
        max_files=_int(graph, subject, APPLE.maxFiles, 5000),
        output_path=Path(str(output_literal or "data/apple-ingest.ttl")),
        backup_path=Path(str(backup_literal or "data/backups/")),
        cache_expiry_seconds=_int(graph, subject, APPLE.cacheExpiry, 3600),
    )

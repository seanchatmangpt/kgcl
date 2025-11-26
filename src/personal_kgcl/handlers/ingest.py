"""Apple ingest CLI handler."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Literal

from kgcl.ingestion.apple_pyobjc import AppleIngestConfig as CoreAppleIngestConfig
from kgcl.ingestion.apple_pyobjc import AppleIngestor
from personal_kgcl.ingest.config import AppleIngestConfig, load_ingest_config
from personal_kgcl.ingest.engine import AppleIngestEngine
from personal_kgcl.ingest.models import (
    AppleIngestInput,
    CalendarEvent,
    FileArtifact,
    MailMessage,
    ReminderTask,
)

SourceName = Literal["calendars", "reminders", "mail", "files"]


def scan_apple(
    source: Iterable[SourceName] | None = None,
    input: Path | None = None,
    output: Path | None = None,
    verbose: bool = False,
    dry_run: bool = False,
) -> str:
    """Run the Apple ingest pipeline."""
    config = load_ingest_config()
    if output:
        config = replace(config, output_path=output)

    selected_sources = set(source or ["calendars", "reminders", "mail", "files"])
    payload = _load_payload(input) if input else None

    if payload is None:
        ingestor = AppleIngestor(
            CoreAppleIngestConfig(
                output_path=config.output_path if output is None else output
            )
        )
        output_path = ingestor.ingest(payload_path=input)
        return f"PyObjC ingest complete → {output_path}"

    ingest_input = _build_ingest_input(payload, selected_sources)
    engine = AppleIngestEngine(config=config)
    result = engine.ingest(ingest_input, dry_run=dry_run)

    message = (
        f"Ingested {result.stats.event_count} events, "
        f"{result.stats.reminder_count} reminders, "
        f"{result.stats.mail_count} mail messages, "
        f"{result.stats.file_count} files."
    )
    if dry_run:
        if verbose:
            message += f"\n[DRY RUN] Would write to {result.output_path}\nReceipts: {len(result.receipts)} items"
        else:
            message += f" [DRY RUN] Would write → {result.output_path}"
    elif verbose:
        message += f"\nGraph written to {result.output_path}\nReceipts: {len(result.receipts)} items"
    else:
        message += f" Output → {result.output_path}"
    return message


def _load_payload(path: Path | None) -> dict | None:
    if path is None:
        return None
    if not path.exists():
        raise FileNotFoundError(f"Ingest payload not found at {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _parse_dt(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)


def _convert_events(records: list[dict]) -> list[CalendarEvent]:
    events: list[CalendarEvent] = []
    for record in records:
        events.append(
            CalendarEvent(
                identifier=record["id"],
                title=record["title"],
                start=_parse_dt(record["start"]) or datetime.min,
                end=_parse_dt(record["end"]) or datetime.min,
                calendar=record.get("calendar", "Unknown"),
                location=record.get("location"),
                notes=record.get("notes"),
                attendees=record.get("attendees", []),
                all_day=bool(record.get("all_day", False)),
            )
        )
    return events


def _convert_reminders(records: list[dict]) -> list[ReminderTask]:
    tasks: list[ReminderTask] = []
    for record in records:
        tasks.append(
            ReminderTask(
                identifier=record["id"],
                title=record["title"],
                completed=bool(record.get("completed", False)),
                due=_parse_dt(record.get("due")),
                list_name=record.get("list", "Inbox"),
                notes=record.get("notes"),
                priority=int(record.get("priority", 0)),
            )
        )
    return tasks


def _convert_mail(records: list[dict]) -> list[MailMessage]:
    messages: list[MailMessage] = []
    for record in records:
        messages.append(
            MailMessage(
                identifier=record["id"],
                subject=record["subject"],
                sender=record.get("sender", ""),
                recipients=record.get("recipients", []),
                received=_parse_dt(record.get("received")) or datetime.min,
                flagged=bool(record.get("flagged", False)),
            )
        )
    return messages


def _convert_files(records: list[dict]) -> list[FileArtifact]:
    files: list[FileArtifact] = []
    for record in records:
        files.append(
            FileArtifact(
                identifier=record["path"],
                name=record.get("name", Path(record["path"]).name),
                path=record["path"],
                created=_parse_dt(record.get("created")) or datetime.min,
                modified=_parse_dt(record.get("modified")) or datetime.min,
                mime_type=record.get("mime_type", "application/octet-stream"),
                tags=record.get("tags", []),
            )
        )
    return files


def _build_ingest_input(payload: dict, sources: set[str]) -> AppleIngestInput:
    events = (
        _convert_events(payload.get("events", [])) if "calendars" in sources else []
    )
    reminders = (
        _convert_reminders(payload.get("reminders", []))
        if "reminders" in sources
        else []
    )
    mail = _convert_mail(payload.get("mail", [])) if "mail" in sources else []
    files = _convert_files(payload.get("files", [])) if "files" in sources else []

    return AppleIngestInput(events=events, reminders=reminders, mail=mail, files=files)

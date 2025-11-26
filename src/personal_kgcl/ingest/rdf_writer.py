"""Utilities to build RDF graphs from ingest domain objects."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import quote

from rdflib import RDF, Graph, Literal, Namespace, URIRef
from rdflib.namespace import XSD

from personal_kgcl.ingest.models import (
    AppleIngestInput,
    CalendarEvent,
    FileArtifact,
    MailMessage,
    ReminderTask,
)

SCHEMA = Namespace("http://schema.org/")
APPLE = Namespace("urn:kgc:apple:")


def _uri(kind: str, identifier: str) -> URIRef:
    normalized = identifier.replace(" ", "-")
    safe_id = quote(normalized, safe="-._@")
    return URIRef(f"urn:kgc:apple:{kind}/{safe_id}")


def _hash_components(*components: str) -> str:
    digest = hashlib.sha256()
    for part in components:
        digest.update(part.encode("utf-8"))
        digest.update(b"|")
    return digest.hexdigest()


class QueryFriendlyGraph(Graph):
    """Graph subclass that tolerates predicate-only value queries."""

    def value(  # type: ignore[override]
        self, subject=None, predicate=RDF.value, object=None, default=None, any=True
    ):
        if subject is None and predicate is not None and object is None:
            try:
                return next(self.objects(None, predicate))
            except StopIteration:
                return default
        return super().value(subject, predicate, object, default, any)


@dataclass
class AppleGraphBuilder:
    """Builds RDF graphs from structured ingest data."""

    graph: Graph = field(default_factory=QueryFriendlyGraph)
    receipts: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.graph.bind("schema", SCHEMA)
        self.graph.bind("apple", APPLE)

    def add_events(self, events: Iterable[CalendarEvent]) -> None:
        for event in events:
            self._add_event(event)

    def add_reminders(self, reminders: Iterable[ReminderTask]) -> None:
        for task in reminders:
            self._add_reminder(task)

    def add_mail(self, messages: Iterable[MailMessage]) -> None:
        for message in messages:
            self._add_message(message)

    def add_files(self, files: Iterable[FileArtifact]) -> None:
        for artifact in files:
            self._add_file(artifact)

    def _add_event(self, event: CalendarEvent) -> None:
        uri = _uri("event", event.identifier)
        if event.end < event.start:
            msg = (
                f"Calendar event '{event.title}' has end time "
                f"{event.end.isoformat()} before start time {event.start.isoformat()}"
            )
            raise ValueError(msg)
        self.graph.add((uri, RDF.type, SCHEMA.Event))
        self.graph.add((uri, RDF.type, APPLE.CalendarEvent))
        self.graph.add((uri, SCHEMA.name, Literal(event.title)))
        self.graph.add((uri, SCHEMA.startDate, Literal(event.start)))
        self.graph.add((uri, SCHEMA.endDate, Literal(event.end)))
        self.graph.add((uri, APPLE.calendar, Literal(event.calendar)))
        self.graph.add((uri, APPLE.hasIdentifier, Literal(event.identifier)))
        if event.location:
            self.graph.add((uri, SCHEMA.location, Literal(event.location)))
        if event.notes:
            self.graph.add((uri, SCHEMA.description, Literal(event.notes)))
        if event.all_day:
            self.graph.add((uri, APPLE.isAllDay, Literal(True)))
        for attendee in event.attendees:
            attendee_uri = _uri(
                "attendee",
                _hash_components(uri, attendee.get("email", attendee.get("name", ""))),
            )
            self.graph.add((attendee_uri, RDF.type, SCHEMA.Person))
            if attendee.get("name"):
                self.graph.add((attendee_uri, SCHEMA.name, Literal(attendee["name"])))
            if attendee.get("email"):
                self.graph.add((attendee_uri, SCHEMA.email, Literal(attendee["email"])))
            self.graph.add((uri, SCHEMA.attendee, attendee_uri))

        self._add_receipt(
            uri,
            event.identifier,
            event.title,
            event.start.isoformat(),
            event.end.isoformat(),
        )

    def _add_reminder(self, task: ReminderTask) -> None:
        uri = _uri("reminder", task.identifier)
        self.graph.add((uri, RDF.type, SCHEMA.Action))
        self.graph.add((uri, SCHEMA.name, Literal(task.title)))
        self.graph.add((uri, APPLE.list, Literal(task.list_name)))
        self.graph.add((uri, APPLE.hasIdentifier, Literal(task.identifier)))
        status_value = (
            "http://schema.org/CompletedActionStatus"
            if task.completed
            else "http://schema.org/PotentialActionStatus"
        )
        self.graph.add((uri, SCHEMA.actionStatus, Literal(status_value)))
        if task.due:
            self.graph.add((uri, SCHEMA.dueDate, Literal(task.due)))
        if task.notes:
            self.graph.add((uri, SCHEMA.description, Literal(task.notes)))
        if task.priority:
            self.graph.add((uri, APPLE.priority, Literal(task.priority)))
        self._add_receipt(uri, task.identifier, task.title, str(task.completed))

    def _add_message(self, message: MailMessage) -> None:
        uri = _uri("mail", message.identifier)
        self.graph.add((uri, RDF.type, SCHEMA.Message))
        self.graph.add((uri, SCHEMA.name, Literal(message.subject)))
        self.graph.add((uri, SCHEMA.dateReceived, Literal(message.received)))
        self.graph.add((uri, APPLE.hasIdentifier, Literal(message.identifier)))
        if message.sender:
            self.graph.add((uri, SCHEMA.author, Literal(message.sender)))
        for recipient in message.recipients:
            self.graph.add((uri, SCHEMA.recipient, Literal(recipient)))
        if message.flagged:
            self.graph.add((uri, APPLE.hasTag, Literal("flagged")))
        self._add_receipt(uri, message.identifier, message.subject, message.sender)

    def _add_file(self, artifact: FileArtifact) -> None:
        uri = _uri("file", artifact.identifier)
        self.graph.add((uri, RDF.type, SCHEMA.CreativeWork))
        self.graph.add((uri, SCHEMA.name, Literal(artifact.name)))
        self.graph.add((uri, SCHEMA.url, Literal(artifact.path, datatype=XSD.anyURI)))
        self.graph.add((uri, SCHEMA.dateCreated, Literal(artifact.created)))
        self.graph.add((uri, SCHEMA.dateModified, Literal(artifact.modified)))
        self.graph.add((uri, APPLE.hasIdentifier, Literal(artifact.identifier)))
        self.graph.add((uri, SCHEMA.fileFormat, Literal(artifact.mime_type)))
        for tag in artifact.tags:
            self.graph.add((uri, SCHEMA.keywords, Literal(tag)))
        self._add_receipt(uri, artifact.identifier, artifact.name, artifact.path)

    def _add_receipt(self, uri: URIRef, *components: str) -> None:
        digest = _hash_components(*components)
        self.graph.add((uri, APPLE.receiptHash, Literal(digest)))
        self.receipts[str(uri)] = digest


def build_graph(input_data: AppleIngestInput) -> AppleGraphBuilder:
    builder = AppleGraphBuilder()
    builder.add_events(input_data.events)
    builder.add_reminders(input_data.reminders)
    builder.add_mail(input_data.mail)
    builder.add_files(input_data.files)
    return builder

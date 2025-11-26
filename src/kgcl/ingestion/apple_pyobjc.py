"""Apple ecosystem ingest via PyObjC (with JSON fallback)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rdflib import RDF, Graph, Literal, Namespace, URIRef

try:
    import EventKit  # type: ignore[import-not-found]

    HAVE_PYOBJC = True
except ImportError:  # pragma: no cover - CI environments rarely have PyObjC
    HAVE_PYOBJC = False

APPLE = Namespace("urn:kgc:apple:")
SCHEMA = Namespace("http://schema.org/")


@dataclass
class AppleIngestConfig:
    """Configuration for Apple ingest pipeline."""

    output_path: Path
    include_calendars: bool = True
    include_reminders: bool = True
    include_mail: bool = False
    include_files: bool = True


class AppleIngestor:
    """Collects macOS/iOS context data and emits RDF."""

    def __init__(self, config: AppleIngestConfig) -> None:
        self._config = config
        self._graph = Graph()
        self._graph.bind("apple", APPLE)
        self._graph.bind("schema", SCHEMA)

    def ingest(self, payload_path: Path | None = None) -> Path:
        """Run ingest and write Turtle to configured path."""
        records = self._collect(payload_path)
        self._emit_records(records)
        self._validate()
        self._config.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._graph.serialize(self._config.output_path, format="turtle")
        return self._config.output_path

    def _collect(self, payload_path: Path | None) -> dict[str, list[dict[str, Any]]]:
        if payload_path:
            return json.loads(payload_path.read_text(encoding="utf-8"))
        if not HAVE_PYOBJC:
            raise RuntimeError(
                "PyObjC not available and no payload provided. "
                "Run on macOS with PyObjC or supply --input JSON."
            )
        # Return empty data when PyObjC is available but no actual data collected yet.
        # Real implementation would use EventKit/Mail APIs via PyObjC.
        return {"events": [], "reminders": [], "mail": [], "files": []}

    def _emit_records(self, records: dict[str, list[dict[str, Any]]]) -> None:
        for event in records.get("events", []):
            subject = URIRef(event["uri"])
            self._graph.add((subject, RDF.type, APPLE.CalendarEvent))
            self._graph.add((subject, SCHEMA.name, Literal(event["title"])))
            self._graph.add((subject, APPLE.hasStartTime, Literal(event["start"])))
            self._graph.add((subject, APPLE.hasEndTime, Literal(event["end"])))
            self._graph.add((subject, APPLE.hasSourceApp, Literal("Calendar")))

        for reminder in records.get("reminders", []):
            subject = URIRef(reminder["uri"])
            self._graph.add((subject, RDF.type, APPLE.Reminder))
            self._graph.add((subject, SCHEMA.name, Literal(reminder["title"])))
            self._graph.add((subject, APPLE.hasDueTime, Literal(reminder.get("due"))))
            self._graph.add(
                (subject, APPLE.hasStatus, Literal(reminder.get("status", "unknown")))
            )

        for message in records.get("mail", []):
            subject = URIRef(message["uri"])
            self._graph.add((subject, RDF.type, APPLE.MailMessage))
            self._graph.add((subject, SCHEMA.name, Literal(message["subject"])))
            self._graph.add((subject, SCHEMA.author, Literal(message["from"])))
            self._graph.add(
                (subject, SCHEMA.dateReceived, Literal(message.get("received")))
            )

        for artifact in records.get("files", []):
            subject = URIRef(artifact["uri"])
            self._graph.add((subject, RDF.type, APPLE.FileArtifact))
            self._graph.add((subject, SCHEMA.name, Literal(artifact["name"])))
            self._graph.add((subject, SCHEMA.url, Literal(artifact["path"])))
            if modified := artifact.get("modified"):
                self._graph.add((subject, SCHEMA.dateModified, Literal(modified)))

    def _validate(self) -> None:
        """Run SHACL validation if shapes are available."""
        shapes_path = Path(".kgc/types.ttl")
        if not shapes_path.exists():
            return
        try:
            from pyshacl import validate  # type: ignore[import-not-found]

            shapes_graph = Graph()
            shapes_graph.parse(shapes_path, format="turtle")
            conforms, _, results_text = validate(
                data_graph=self._graph, shacl_graph=shapes_graph, inference="rdfs"
            )
            if not conforms:
                raise ValueError(
                    f"Apple ingest failed SHACL validation: {results_text}"
                )
        except ImportError:
            # Defer validation until pyshacl is available
            return

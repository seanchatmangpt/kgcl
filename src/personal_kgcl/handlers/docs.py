"""Handlers for documentation projections."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from rdflib import RDF, Graph, Literal, Namespace, URIRef

SCHEMA = Namespace("http://schema.org/")
APPLE = Namespace("urn:kgc:apple:")


def _load_graph(path: Path) -> Graph:
    graph = Graph()
    graph.parse(path, format="turtle")
    return graph


def _format_event_row(subject: URIRef, graph: Graph) -> str:
    # Support both schema.org and Apple namespace predicates
    title = graph.value(subject=subject, predicate=SCHEMA.name)
    start = graph.value(subject=subject, predicate=SCHEMA.startDate) or graph.value(
        subject=subject, predicate=APPLE.hasStartTime
    )
    end = graph.value(subject=subject, predicate=SCHEMA.endDate) or graph.value(
        subject=subject, predicate=APPLE.hasEndTime
    )
    location = graph.value(subject=subject, predicate=SCHEMA.location)

    start_str = _format_dt_literal(start)
    end_str = _format_dt_literal(end)
    location_str = f" — {location}" if location else ""

    return f"| {title} | {start_str} | {end_str} |{location_str} |"


def _format_dt_literal(value: Literal | None) -> str:
    if not isinstance(value, Literal):
        return "-"
    if isinstance(value.value, datetime):
        return value.value.isoformat()
    return str(value)


def generate_agenda(
    day: str,
    input_path: Path | None = None,
    output_path: Path | None = None,
    verbose: bool = False,
    dry_run: bool = False,
) -> str:
    """Render a lean agenda markdown document directly from RDF.

    Parameters
    ----------
    day:
        Day selector (e.g., "today", "this-week").
    input_path:
        Optional override for the ingest RDF file (defaults to `data/apple-ingest.ttl`).
    output_path:
        Optional override for the generated markdown.
    verbose:
        Include extra metadata in the returned summary.
    dry_run:
        Skip writing but still produce the markdown string.
    """
    ingest_path = input_path or Path("data/apple-ingest.ttl")
    if not ingest_path.exists():
        raise FileNotFoundError(
            f"Ingest graph not found at {ingest_path}. Run `kgct scan-apple` before generating projections."
        )

    graph = _load_graph(ingest_path)
    agenda_rows = _collect_events(graph)

    if not agenda_rows:
        raise ValueError("No events found in ingest graph; nothing to render.")

    markdown = _render_markdown(day, agenda_rows)
    destination = output_path or Path("docs/agenda.md")

    if not dry_run:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(markdown, encoding="utf-8")

    if verbose:
        return f"Agenda ({len(agenda_rows)} events) → {destination}\n{markdown}"
    return f"Agenda generated with {len(agenda_rows)} events → {destination}"


def _collect_events(graph: Graph) -> list[str]:
    rows: list[str] = []
    # Support both schema.org Event and Apple CalendarEvent types
    event_types = [SCHEMA.Event, APPLE.CalendarEvent]
    for event_type in event_types:
        for subject in graph.subjects(RDF.type, event_type):
            if isinstance(subject, URIRef):
                rows.append(_format_event_row(subject, graph))
    rows.sort()
    return rows


def _render_markdown(day: str, rows: Iterable[str]) -> str:
    header = [
        "# Agenda",
        "",
        f"Generated for: **{day}**",
        "",
        "| Title | Start | End | Location |",
        "| --- | --- | --- | --- |",
    ]
    body = list(rows)
    return "\n".join(header + body) + "\n"



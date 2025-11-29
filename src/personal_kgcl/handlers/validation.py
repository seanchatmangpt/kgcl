"""Validation utilities for the KGCT CLI."""

from __future__ import annotations

from pathlib import Path

from rdflib import Graph

from personal_kgcl.ingest.validation import AppleIngestValidator, ValidationReport


def validate_ingest(input_path: Path | None = None, verbose: bool = False, dry_run: bool = False) -> str:
    """Validate the ingest RDF graph against SHACL invariants."""
    graph_path = input_path or Path("data/apple-ingest.ttl")
    if not graph_path.exists():
        raise FileNotFoundError(f"No ingest graph found at {graph_path}")

    graph = Graph()
    graph.parse(graph_path, format="turtle")

    validator = AppleIngestValidator()
    report: ValidationReport = validator.validate(graph)

    if not report.conforms:
        raise ValueError(
            "Ingest graph failed validation:\n" + (report.text if verbose else "See detailed report with --verbose.")
        )

    if dry_run:
        return "[DRY-RUN] Validation succeeded."

    message = f"Validation passed for {graph_path}"
    if verbose:
        message += f"\n{report.text}"
    return message



"""Orchestrates the Apple ingest workflow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from personal_kgcl.ingest.config import AppleIngestConfig, load_ingest_config
from personal_kgcl.ingest.models import AppleIngestInput, AppleIngestResult, AppleIngestStats
from personal_kgcl.ingest.rdf_writer import build_graph
from personal_kgcl.ingest.validation import AppleIngestValidator


@dataclass
class AppleIngestEngine:
    config: AppleIngestConfig | None = None
    validator: AppleIngestValidator | None = None

    def ingest(self, data: AppleIngestInput, dry_run: bool = False) -> AppleIngestResult:
        config = self.config or load_ingest_config()

        builder = build_graph(data)
        graph = builder.graph

        if not dry_run:
            output_path = config.output_path
            output_path.parent.mkdir(parents=True, exist_ok=True)
            graph.serialize(output_path, format="turtle")
        else:
            output_path = Path("dry-run.ttl")

        report = None
        validator = self.validator or AppleIngestValidator()
        if validator:
            report = validator.validate(graph)
            if not report.conforms:
                raise ValueError("Ingest graph failed SHACL validation:\n" + report.text)

        stats = AppleIngestStats(
            event_count=len(data.events),
            reminder_count=len(data.reminders),
            mail_count=len(data.mail),
            file_count=len(data.files),
        )

        return AppleIngestResult(
            stats=stats,
            graph_path=output_path,
            graph=graph,
            receipts=builder.receipts,
            output_path=output_path,
            report=report,
        )


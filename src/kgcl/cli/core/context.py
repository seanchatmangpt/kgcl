"""CLI execution context and dependency container."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kgcl.cli.core.clipboard import ClipboardGateway
from kgcl.cli.core.config_store import CliConfigStore
from kgcl.cli.core.renderers import CliRenderer
from kgcl.cli.core.services import ConfigService, DspyService, IngestionService, LinkmlValidator, SparqlService


@dataclass(frozen=True)
class CliContext:
    """Runtime context shared across CLI commands."""

    project_root: Path
    renderer: CliRenderer
    clipboard: ClipboardGateway
    config_store: CliConfigStore
    ingestion_service: IngestionService
    dspy_service: DspyService
    sparql_service: SparqlService
    config_service: ConfigService
    linkml_validator: LinkmlValidator

    def with_renderer(self, renderer: CliRenderer) -> CliContext:
        """Return a copy with a different renderer."""
        return CliContext(
            project_root=self.project_root,
            renderer=renderer,
            clipboard=self.clipboard,
            config_store=self.config_store,
            ingestion_service=self.ingestion_service,
            dspy_service=self.dspy_service,
            sparql_service=self.sparql_service,
            config_service=self.config_service,
            linkml_validator=self.linkml_validator,
        )

"""Service protocol definitions for CLI commands."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class DailyBriefRequest:
    """Request metadata for daily brief generation."""

    start_date: str
    end_date: str
    model: str
    verbose: bool = False


class IngestionService(Protocol):
    """Service responsible for ingest/materialization flows."""

    def load_daily_brief(self, request: DailyBriefRequest) -> dict[str, Any]:
        """Return features/events for the daily brief request."""


class DspyService(Protocol):
    """Service for executing DSPy signatures."""

    def generate_daily_brief(self, features: dict[str, Any], model: str) -> dict[str, Any]:
        """Produce a structured brief using DSPy or fallback logic."""


class SparqlService(Protocol):
    """Service for running SPARQL queries."""

    def query(self, query_text: str, *, limit: int | None = None) -> list[dict[str, str]]:
        """Execute a SPARQL query and return bindings."""


class ConfigService(Protocol):
    """Service for typed configuration access."""

    def snapshot(self) -> dict[str, Any]:
        """Return current config snapshot."""

    def update(self, new_config: dict[str, Any]) -> None:
        """Persist config updates."""


class LinkmlValidator(Protocol):
    """Service for enforcing LinkML/SHACL validation."""

    def validate(self, payload: dict[str, Any]) -> None:
        """Raise if payload violates schema."""

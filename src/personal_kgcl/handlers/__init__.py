"""Handlers invoked by the generated KGCT CLI."""

from .codegen import generate_cli
from .docs import generate_agenda
from .ingest import scan_apple
from .validation import validate_ingest

__all__ = ["generate_agenda", "generate_cli", "scan_apple", "validate_ingest"]



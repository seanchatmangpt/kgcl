"""CLI-specific error types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CliCommandError(Exception):
    """Raised when a CLI command fails in a controlled manner."""

    message: str
    details: dict[str, str] | None = None

    def __str__(self) -> str:
        return self.message

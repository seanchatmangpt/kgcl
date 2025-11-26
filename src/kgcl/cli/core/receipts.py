"""Execution receipt utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class ExecutionReceipt:
    """Structured record for CLI command results."""

    command: str
    success: bool
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC).replace(tzinfo=None))
    finished_at: datetime = field(default_factory=lambda: datetime.now(UTC).replace(tzinfo=None))
    metadata: dict[str, Any] = field(default_factory=dict)

    def duration_seconds(self) -> float:
        """Return execution duration."""
        return (self.finished_at - self.started_at).total_seconds()

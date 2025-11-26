"""CliApp orchestrator for KGCL commands."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TypeVar

from rich.console import Console

from kgcl.cli.core.context import CliContext
from kgcl.cli.core.errors import CliCommandError
from kgcl.cli.core.receipts import ExecutionReceipt

T = TypeVar("T")


@dataclass
class CliApp:
    """Wraps command execution with consistent telemetry and error handling."""

    context: CliContext
    console: Console

    def run(self, command_name: str, func: Callable[[CliContext], T]) -> tuple[T | None, ExecutionReceipt]:
        """Execute a command and capture a receipt."""
        started_at = datetime.now(UTC).replace(tzinfo=None)
        try:
            result = func(self.context)
            receipt = ExecutionReceipt(
                command=command_name,
                success=True,
                started_at=started_at,
                finished_at=datetime.now(UTC).replace(tzinfo=None),
                metadata={"message": "ok"},
            )
            return result, receipt
        except CliCommandError as error:
            self.console.print(f"[red]{error.message}[/red]")
            if error.details:
                for key, value in error.details.items():
                    self.console.print(f"[red]- {key}: {value}[/red]")
            receipt = ExecutionReceipt(
                command=command_name,
                success=False,
                started_at=started_at,
                finished_at=datetime.now(UTC).replace(tzinfo=None),
                metadata={"error": error.message, **(error.details or {})},
            )
            return None, receipt

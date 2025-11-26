"""Rendering utilities for CLI output."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from kgcl.cli.core.clipboard import ClipboardGateway


class OutputFormat(str, Enum):
    """Supported output renderings."""

    JSON = "json"
    TABLE = "table"
    MARKDOWN = "markdown"


@dataclass
class RenderedOutput:
    """Result of rendering a payload."""

    format: OutputFormat
    content: str
    clipboard_copied: bool = False
    file_written: Path | None = None


@dataclass
class CliRenderer:
    """Handles formatting and delivery of CLI payloads."""

    console: Console
    clipboard: ClipboardGateway

    def render(
        self,
        payload: Any,
        *,
        fmt: OutputFormat,
        clipboard: bool = False,
        output_file: Path | None = None,
        table_columns: list[str] | None = None,
    ) -> RenderedOutput:
        """Render payload to console/file/clipboard."""
        if fmt is OutputFormat.JSON:
            text = json.dumps(payload, indent=2, default=str)
            self.console.print(text)
        elif fmt is OutputFormat.MARKDOWN:
            text = str(payload)
            self.console.print(Panel(Markdown(text)))
        elif fmt is OutputFormat.TABLE:
            text = self._render_table(payload, columns=table_columns)
        else:
            raise ValueError(f"Unsupported format {fmt}")

        copied = clipboard and self.clipboard.copy(text)
        written: Path | None = None
        if output_file:
            output_file.write_text(text, encoding="utf-8")
            written = output_file

        return RenderedOutput(format=fmt, content=text, clipboard_copied=copied, file_written=written)

    def _render_table(self, payload: Any, columns: list[str] | None) -> str:
        if not isinstance(payload, Iterable):
            raise ValueError("Table payload must be iterable")
        rows = list(payload)
        if not rows:
            self.console.print("[yellow]No records to display[/yellow]")
            return ""
        if columns is None:
            first = rows[0]
            columns = list(first.keys()) if isinstance(first, dict) else ["value"]

        table = Table(show_header=True, header_style="bold cyan")
        for column in columns:
            table.add_column(column)

        for row in rows:
            if isinstance(row, dict):
                table.add_row(*[str(row.get(column, "")) for column in columns])
            else:
                table.add_row(str(row))

        self.console.print(table)
        return "\n".join(
            ["\t".join(str(row.get(col, "")) for col in columns) if isinstance(row, dict) else str(row) for row in rows]
        )

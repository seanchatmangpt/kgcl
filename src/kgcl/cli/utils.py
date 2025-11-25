"""Shared utilities for KGCL CLI tools.

Provides output formatting, error handling, and clipboard integration.
"""

import json
import subprocess
import sys
from collections.abc import Sequence
from enum import Enum
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table


class OutputFormat(str, Enum):
    """Supported output formats."""

    JSON = "json"
    CSV = "csv"
    TSV = "tsv"
    TABLE = "table"
    MARKDOWN = "markdown"


console = Console()
error_console = Console(stderr=True)


def print_error(message: str, exit_code: int = 1) -> None:
    """Print an error message and optionally exit.

    Parameters
    ----------
    message : str
        Error message to display
    exit_code : int, optional
        Exit code (0 means don't exit), by default 1

    """
    error_console.print(f"[bold red]Error:[/bold red] {message}")
    if exit_code > 0:
        sys.exit(exit_code)


def print_success(message: str) -> None:
    """Print a success message.

    Parameters
    ----------
    message : str
        Success message to display

    """
    console.print(f"[bold green]✓[/bold green] {message}")


def print_warning(message: str) -> None:
    """Print a warning message.

    Parameters
    ----------
    message : str
        Warning message to display

    """
    console.print(f"[bold yellow]Warning:[/bold yellow] {message}")


def print_info(message: str) -> None:
    """Print an info message.

    Parameters
    ----------
    message : str
        Info message to display

    """
    console.print(f"[bold blue]ℹ[/bold blue] {message}")


def print_markdown(content: str, title: str | None = None) -> None:
    """Print markdown-formatted content.

    Parameters
    ----------
    content : str
        Markdown content to render
    title : str, optional
        Optional title for the panel

    """
    md = Markdown(content)
    if title:
        console.print(Panel(md, title=title, border_style="blue"))
    else:
        console.print(md)


def print_json(data: Any, indent: int = 2) -> None:
    """Print data as formatted JSON.

    Parameters
    ----------
    data : Any
        Data to serialize as JSON
    indent : int, optional
        Indentation level, by default 2

    """
    json_str = json.dumps(data, indent=indent, default=str)
    syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)
    console.print(syntax)


def print_table(
    data: Sequence[dict[str, Any]], columns: list[str] | None = None, title: str | None = None
) -> None:
    """Print data as a formatted table.

    Parameters
    ----------
    data : Sequence[dict[str, Any]]
        List of dictionaries to display
    columns : list[str], optional
        Column names to display (defaults to all keys from first row)
    title : str, optional
        Table title

    """
    if not data:
        print_warning("No data to display")
        return

    if columns is None:
        columns = list(data[0].keys())

    table = Table(title=title, show_header=True, header_style="bold cyan")

    for col in columns:
        table.add_column(col)

    for row in data:
        table.add_row(*[str(row.get(col, "")) for col in columns])

    console.print(table)


def export_csv(data: Sequence[dict[str, Any]], output_file: Path) -> None:
    """Export data to CSV file.

    Parameters
    ----------
    data : Sequence[dict[str, Any]]
        Data to export
    output_file : Path
        Output file path

    """
    import csv

    if not data:
        print_warning("No data to export")
        return

    with output_file.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(data[0].keys()))
        writer.writeheader()
        writer.writerows(data)

    print_success(f"Exported to {output_file}")


def export_tsv(data: Sequence[dict[str, Any]], output_file: Path) -> None:
    """Export data to TSV file.

    Parameters
    ----------
    data : Sequence[dict[str, Any]]
        Data to export
    output_file : Path
        Output file path

    """
    import csv

    if not data:
        print_warning("No data to export")
        return

    with output_file.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(data[0].keys()), delimiter="\t")
        writer.writeheader()
        writer.writerows(data)

    print_success(f"Exported to {output_file}")


def export_json(data: Any, output_file: Path, indent: int = 2) -> None:
    """Export data to JSON file.

    Parameters
    ----------
    data : Any
        Data to export
    output_file : Path
        Output file path
    indent : int, optional
        Indentation level, by default 2

    """
    with output_file.open("w") as f:
        json.dump(data, f, indent=indent, default=str)

    print_success(f"Exported to {output_file}")


def copy_to_clipboard(text: str) -> bool:
    """Copy text to system clipboard.

    Parameters
    ----------
    text : str
        Text to copy

    Returns
    -------
    bool
        True if successful, False otherwise

    """
    try:
        # Try pbcopy (macOS)
        subprocess.run(
            ["pbcopy"],
            input=text.encode(),
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    try:
        # Try xclip (Linux)
        subprocess.run(
            ["xclip", "-selection", "clipboard"],
            input=text.encode(),
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    try:
        # Try xsel (Linux alternative)
        subprocess.run(
            ["xsel", "--clipboard", "--input"],
            input=text.encode(),
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    return False


def format_output(
    data: Any, format_type: OutputFormat, output_file: Path | None = None, clipboard: bool = False
) -> None:
    """Format and output data according to specified format.

    Parameters
    ----------
    data : Any
        Data to format and output
    format_type : OutputFormat
        Output format type
    output_file : Path, optional
        File to write output to
    clipboard : bool, optional
        Copy output to clipboard, by default False

    """
    if format_type == OutputFormat.JSON:
        if output_file:
            export_json(data, output_file)
        else:
            print_json(data)
            if clipboard:
                text = json.dumps(data, indent=2, default=str)
                if copy_to_clipboard(text):
                    print_success("Copied to clipboard")
                else:
                    print_warning("Could not copy to clipboard")

    elif format_type == OutputFormat.CSV:
        if output_file:
            export_csv(data, output_file)
        else:
            print_error("CSV format requires --output option")

    elif format_type == OutputFormat.TSV:
        if output_file:
            export_tsv(data, output_file)
        else:
            print_error("TSV format requires --output option")

    elif format_type == OutputFormat.TABLE:
        if isinstance(data, list):
            print_table(data)
        else:
            print_error("Table format requires list of dictionaries")

    elif format_type == OutputFormat.MARKDOWN:
        if isinstance(data, str):
            print_markdown(data)
            if clipboard:
                if copy_to_clipboard(data):
                    print_success("Copied to clipboard")
                else:
                    print_warning("Could not copy to clipboard")
            if output_file:
                output_file.write_text(data)
                print_success(f"Written to {output_file}")
        else:
            print_error("Markdown format requires string data")


def confirm_action(message: str, default: bool = False) -> bool:
    """Prompt user for confirmation.

    Parameters
    ----------
    message : str
        Confirmation message
    default : bool, optional
        Default response, by default False

    Returns
    -------
    bool
        User's confirmation

    """
    return click.confirm(message, default=default)


def get_config_dir() -> Path:
    """Get or create KGCL configuration directory.

    Returns
    -------
    Path
        Configuration directory path

    """
    config_dir = Path.home() / ".config" / "kgcl"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_file(name: str = "config.json") -> Path:
    """Get configuration file path.

    Parameters
    ----------
    name : str, optional
        Configuration file name, by default "config.json"

    Returns
    -------
    Path
        Configuration file path

    """
    return get_config_dir() / name


def load_config() -> dict[str, Any]:
    """Load configuration from file.

    Returns
    -------
    dict[str, Any]
        Configuration dictionary

    """
    config_file = get_config_file()
    if config_file.exists():
        with config_file.open() as f:
            return json.load(f)
    return {}


def save_config(config_data: dict[str, Any]) -> None:
    """Save configuration to file.

    Parameters
    ----------
    config_data : dict[str, Any]
        Configuration data to save

    """
    config_file = get_config_file()
    with config_file.open("w") as f:
        json.dump(config_data, f, indent=2)
    print_success(f"Configuration saved to {config_file}")

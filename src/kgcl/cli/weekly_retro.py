"""Weekly retrospective CLI command."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import click

from kgcl.cli.bootstrap import build_cli_app
from kgcl.cli.core.errors import CliCommandError
from kgcl.cli.core.renderers import OutputFormat
from kgcl.cli.core.services import DailyBriefRequest

cli_app = build_cli_app()


@click.command()
@click.option(
    "--end-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="End date for the retrospective (defaults to today)",
)
@click.option("--days", type=int, default=7, help="Number of days to include (default: 7)")
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Output file path")
@click.option("--clipboard", "-c", is_flag=True, help="Copy result to clipboard")
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice([f.value for f in OutputFormat]),
    default=OutputFormat.MARKDOWN.value,
    help="Output format",
)
@click.option("--model", type=str, default="llama3.2", help="Ollama model to use for generation")
@click.option("--include-metrics", is_flag=True, help="Include detailed metrics in output")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def weekly_retro(
    end_date: datetime | None,
    days: int,
    output: Path | None,
    clipboard: bool,
    output_format: str,
    model: str,
    include_metrics: bool,
    verbose: bool,
) -> None:
    """Generate a weekly retrospective summary from aggregated event features.

    Analyzes event data over a multi-day window (typically 7 days) to produce
    a structured retrospective report showing productivity patterns, focus time,
    top applications used, and browsing activity. The report helps identify
    trends, time allocation patterns, and areas for improvement.

    The retrospective aggregates daily brief features across the specified time
    window and presents summaries in markdown or structured formats. Optional
    detailed metrics provide quantitative insights into daily averages and
    productivity indicators.

    Parameters
    ----------
    end_date : datetime or None, optional
        End date for the retrospective analysis window. If None (default),
        uses the current date/time. The retrospective will analyze events
        ending on this date and spanning backwards for the specified number
        of days.
    days : int, default=7
        Number of days to include in the retrospective window. For example,
        days=7 analyzes the past week; days=14 covers two weeks. Must be
        positive integer. The start date is calculated as end_date - days.
    output : Path or None, optional
        File path where the rendered retrospective will be written. If None
        (default), output is only displayed to console. File is written in
        the format specified by output_format.
    clipboard : bool, default=False
        Whether to copy the rendered retrospective to system clipboard. When
        True, the report is available for pasting into other applications
        (e.g., team standup notes, personal journals). Works alongside
        console/file output.
    output_format : str, default="markdown"
        Output rendering format. Must be one of: "markdown" (formatted text
        with headers/lists/tables), "json" (structured summary dictionary).
        The "table" format is not recommended for retrospectives due to
        hierarchical data structure.
    model : str, default="llama3.2"
        Ollama model identifier for any LLM-powered feature generation or
        analysis. Common options include "llama3.2", "llama3.3", "mistral".
        The model must be available in local Ollama installation. Currently
        used for feature loading but not for retrospective narrative generation.
    include_metrics : bool, default=False
        Include detailed quantitative metrics in the output. When True, adds
        a "Metrics" section showing average events per day and average focus
        hours per day. Useful for tracking productivity trends over time.
    verbose : bool, default=False
        Enable detailed progress output during retrospective generation. Shows
        internal pipeline steps, feature loading, and data aggregation. Useful
        for debugging or understanding data flow.

    Returns
    -------
    None
        This function produces side effects (console output, file writes,
        clipboard updates) but does not return a value. Success is indicated
        by "Weekly retrospective generated successfully" message. The retrospective
        payload is internally stored but not returned to the caller.

    Raises
    ------
    CliCommandError
        If the weekly retrospective pipeline fails to generate a valid result.
        This can occur due to missing event data, feature loading errors, or
        data aggregation failures.
    FileNotFoundError
        If the output file path parent directory does not exist. Create the
        parent directory before calling this function.
    ValueError
        If the output_format is not a valid OutputFormat enum value (json,
        markdown), or if days is not a positive integer.

    Examples
    --------
    Generate default 7-day retrospective ending today:

    >>> from datetime import datetime
    >>> weekly_retro(
    ...     end_date=None,
    ...     days=7,
    ...     output=None,
    ...     clipboard=False,
    ...     output_format="markdown",
    ...     model="llama3.2",
    ...     include_metrics=False,
    ...     verbose=False,
    ... )
    Weekly retrospective generated successfully

    Generate 14-day retrospective with detailed metrics:

    >>> weekly_retro(
    ...     end_date=None,
    ...     days=14,
    ...     output=None,
    ...     clipboard=False,
    ...     output_format="markdown",
    ...     model="llama3.2",
    ...     include_metrics=True,
    ...     verbose=True,
    ... )
    Weekly retrospective generated successfully

    Generate retrospective for specific date range and save to file:

    >>> from pathlib import Path
    >>> target_end = datetime(2025, 11, 24)
    >>> output_path = Path("reports/retro-week-ending-2025-11-24.md")
    >>> weekly_retro(
    ...     end_date=target_end,
    ...     days=7,
    ...     output=output_path,
    ...     clipboard=True,
    ...     output_format="markdown",
    ...     model="llama3.3",
    ...     include_metrics=True,
    ...     verbose=False,
    ... )
    Weekly retrospective generated successfully

    Generate retrospective in JSON format for programmatic analysis:

    >>> weekly_retro(
    ...     end_date=None,
    ...     days=7,
    ...     output=None,
    ...     clipboard=False,
    ...     output_format="json",
    ...     model="llama3.2",
    ...     include_metrics=False,
    ...     verbose=False,
    ... )
    Weekly retrospective generated successfully

    Notes
    -----
    The retrospective structure includes:
    - Window summary (start date → end date)
    - Total event count across the window
    - Total focus hours (deep work time)
    - Top applications by usage hours
    - Top browsing domains by visit count
    - Optional: Average metrics per day (events/day, focus hours/day)

    The function loads daily brief features for the specified window and
    aggregates them into weekly summaries. This requires the underlying
    ingestion service to have access to event data for the requested period.

    When include_metrics=True, the "Metrics" section provides actionable
    insights for productivity tracking and trend analysis. Average events/day
    indicates activity density; average focus hours/day tracks deep work time.

    See Also
    --------
    daily_brief : Generate daily brief from recent events
    feature_list : List available features from the knowledge graph
    """
    target_end = end_date or datetime.now()
    start_date = target_end - timedelta(days=days)

    def _execute(context):
        request = DailyBriefRequest(
            start_date=start_date.isoformat(), end_date=target_end.isoformat(), model=model, verbose=verbose
        )
        features = context.ingestion_service.load_daily_brief(request)
        payload = _build_retro_payload(features, include_metrics, days)
        fmt = OutputFormat(output_format)
        data = payload["markdown"] if fmt is OutputFormat.MARKDOWN else payload["summary"]
        context.renderer.render(data, fmt=fmt, clipboard=clipboard, output_file=output)
        return payload

    result, _ = cli_app.run("weekly-retro", _execute)
    if result is None:
        raise CliCommandError("Weekly retrospective failed")
    click.echo("Weekly retrospective generated successfully")


def _build_retro_payload(features: dict, include_metrics: bool, days: int) -> dict:
    feature_set = features["features"]
    metadata = feature_set.metadata
    summary = {
        "event_count": metadata.get("event_count", 0),
        "focus_hours": feature_set.input_data.focus_time,
        "top_apps": metadata.get("top_apps", []),
        "top_domains": metadata.get("top_domains", []),
        "window": metadata.get("window", {}),
    }
    lines = [
        "# Weekly Retrospective",
        "",
        f"Window: {summary['window'].get('start')} → {summary['window'].get('end')}",
        "",
        f"- Total events: {summary['event_count']}",
        f"- Focus hours: {summary['focus_hours']}",
        "",
        "## Top Apps",
    ]
    lines += [f"- {item['name']}: {item['hours']}h" for item in summary["top_apps"]] or ["- None"]
    lines.append("")
    lines.append("## Top Domains")
    lines += [f"- {item['domain']}: {item['visits']} visits" for item in summary["top_domains"]] or ["- None"]

    if include_metrics:
        lines.append("")
        lines.append("## Metrics")
        lines.append(f"- Average events/day: {summary['event_count'] / max(days, 1):.2f}")
        lines.append(f"- Focus hours/day: {summary['focus_hours'] / max(days, 1):.2f}")

    lines.append("\n---\nGenerated via KGCL Lean CLI.")
    return {"markdown": "\n".join(lines), "summary": summary}


if __name__ == "__main__":
    weekly_retro()

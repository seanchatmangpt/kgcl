"""Daily brief CLI command.

Generate a daily brief from yesterday and today's events.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import click

from kgcl.cli.bootstrap import build_cli_app
from kgcl.cli.core.errors import CliCommandError
from kgcl.cli.core.renderers import OutputFormat
from kgcl.cli.daily_brief_pipeline import (
    DailyBriefEventBatch,
    DailyBriefFeatureBuilder,
    DailyBriefFeatureSet,
    DailyBriefResult,
    EventLogLoader,
    generate_daily_brief,
)

cli_app = build_cli_app()


def _ingest_events(start_date: datetime, end_date: datetime, verbose: bool) -> DailyBriefEventBatch:
    """Load calendar/app/browser events for the requested window."""
    loader = EventLogLoader()
    batch = loader.load(start_date, end_date)
    if verbose:
        click.echo(
            f"Ingested {batch.event_count} events "
            f"from {batch.start_date.date()} → {batch.end_date.date()} "
            f"(synthetic={batch.synthetic})"
        )
    return batch


def _materialize_features(batch: DailyBriefEventBatch, verbose: bool) -> DailyBriefFeatureSet:
    """Materialize features used to drive the DSPy generation."""
    builder = DailyBriefFeatureBuilder()
    feature_set = builder.build(batch)
    if verbose:
        click.echo(
            f"Materialized {feature_set.metadata['materialized_features']} features "
            f"from {feature_set.metadata['event_count']} events"
        )
    return feature_set


def _generate_brief(feature_set: DailyBriefFeatureSet, model: str, verbose: bool) -> DailyBriefResult:
    """Generate the final brief output using DSPy."""
    brief = generate_daily_brief(feature_set, model=model)
    if verbose:
        click.echo(f"Generated daily brief with model={model} (llm_enabled={brief.metadata['llm_enabled']})")
    return brief


def _select_payload_for_format(brief: DailyBriefResult, output_format: OutputFormat) -> Any:
    """Select the rendered payload for the requested output format."""
    fmt_value = output_format.value if hasattr(output_format, "value") else str(output_format)
    if fmt_value == OutputFormat.MARKDOWN.value:
        return brief.to_markdown()
    if fmt_value == OutputFormat.TABLE.value:
        return brief.to_rows()
    return brief.to_dict()


@click.command()
@click.option(
    "--date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="Target date for the brief (defaults to today)",
)
@click.option("--lookback", type=int, default=1, help="Number of days to look back (default: 1)")
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
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def daily_brief(
    date: datetime | None,
    lookback: int,
    output: Path | None,
    *,
    clipboard: bool,
    output_format: str,
    model: str,
    verbose: bool,
) -> None:
    """Generate a daily brief from recent calendar, app, and browser events.

    Orchestrates a three-phase pipeline to create actionable daily summaries:
    1. Event ingestion from Apple ecosystem (Calendar, Apps, Safari)
    2. Feature materialization extracting focus time, context switches, top apps
    3. Brief generation using DSPy and local Ollama LLM

    The generated brief includes structured insights about productivity patterns,
    time allocation, and activity context to support daily planning and
    retrospective review.

    Parameters
    ----------
    date : datetime or None, optional
        Target date for the brief analysis. If None (default), uses current
        date in UTC timezone. The brief will analyze events ending on this date.
    lookback : int, default=1
        Number of days to look back from the target date when loading events.
        For example, lookback=1 analyzes yesterday and today; lookback=7
        covers the past week. Must be positive integer.
    output : Path or None, optional
        File path where the rendered brief will be written. If None (default),
        output is only displayed to console. File is written in the format
        specified by output_format.
    clipboard : bool, default=False
        Whether to copy the rendered brief to system clipboard. When True,
        the brief is available for pasting into other applications. Works
        alongside console/file output.
    output_format : str, default="markdown"
        Output rendering format. Must be one of: "markdown" (formatted text
        with headers/lists), "table" (tabular row data), or "json" (structured
        dictionary). Format is validated against OutputFormat enum values.
    model : str, default="llama3.2"
        Ollama model identifier to use for LLM-powered brief generation.
        Common options include "llama3.2", "llama3.3", "mistral". The model
        must be available in local Ollama installation.
    verbose : bool, default=False
        Enable detailed progress output showing event counts, materialized
        features, and model usage. Useful for debugging pipeline issues or
        understanding data flow.

    Returns
    -------
    None
        This function produces side effects (console output, file writes,
        clipboard updates) but does not return a value. Success is indicated
        by "Daily brief generated successfully" message. The generated brief
        result is internally stored but not returned to the caller.

    Raises
    ------
    CliCommandError
        If the daily brief pipeline fails to generate a valid result. This
        can occur due to missing event data, feature materialization errors,
        or LLM generation failures.
    FileNotFoundError
        If the output file path parent directory does not exist. Create the
        parent directory before calling this function.
    ValueError
        If the output_format is not a valid OutputFormat enum value (json,
        table, markdown).

    Examples
    --------
    Generate today's brief with default settings (1-day lookback, markdown):

    >>> from datetime import datetime
    >>> daily_brief(
    ...     date=None,
    ...     lookback=1,
    ...     output=None,
    ...     clipboard=False,
    ...     output_format="markdown",
    ...     model="llama3.2",
    ...     verbose=False,
    ... )
    Daily brief generated successfully

    Generate brief for specific date with extended lookback:

    >>> from pathlib import Path
    >>> target_date = datetime(2025, 11, 20)
    >>> daily_brief(
    ...     date=target_date,
    ...     lookback=7,
    ...     output=None,
    ...     clipboard=False,
    ...     output_format="markdown",
    ...     model="llama3.2",
    ...     verbose=True,
    ... )
    Ingested 342 events from 2025-11-13 → 2025-11-20 (synthetic=False)
    Materialized 12 features from 342 events
    Generated daily brief with model=llama3.2 (llm_enabled=True)
    Daily brief generated successfully

    Save brief to file and copy to clipboard in JSON format:

    >>> output_path = Path("reports/daily-brief-2025-11-25.json")
    >>> daily_brief(
    ...     date=None,
    ...     lookback=1,
    ...     output=output_path,
    ...     clipboard=True,
    ...     output_format="json",
    ...     model="llama3.3",
    ...     verbose=False,
    ... )
    Daily brief generated successfully

    Notes
    -----
    The function integrates with the KGCL event ingestion system which requires
    Apple ecosystem data sources. On systems without Apple Calendar/App data,
    synthetic test data may be used as a fallback.

    The DSPy framework and Ollama must be properly configured for LLM-powered
    generation. Without Ollama, the brief will include raw features without
    natural language synthesis.

    See Also
    --------
    weekly_retro : Generate weekly retrospective from aggregated features
    feature_list : List available features from the knowledge graph
    """
    start_dt = (date or datetime.now(UTC).replace(tzinfo=None)) - timedelta(days=lookback)
    end_dt = date or datetime.now(UTC).replace(tzinfo=None)

    def _execute(context):
        batch = _ingest_events(start_dt, end_dt, verbose)
        feature_set = _materialize_features(batch, verbose)
        brief_result = _generate_brief(feature_set, model, verbose)
        fmt = OutputFormat(output_format)
        payload = _select_payload_for_format(brief_result, fmt)
        context.renderer.render(payload, fmt=fmt, clipboard=clipboard, output_file=output)
        return brief_result.to_dict()

    result, _receipt = cli_app.run("daily-brief", _execute)
    if result is None:
        raise CliCommandError("Daily brief failed to generate")

    click.echo("Daily brief generated successfully")


if __name__ == "__main__":
    daily_brief()

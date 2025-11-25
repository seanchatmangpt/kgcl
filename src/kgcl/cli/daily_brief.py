"""Daily brief CLI command.

Generate a daily brief from yesterday and today's events.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import click

from kgcl.cli.daily_brief_pipeline import (
    DailyBriefEventBatch,
    DailyBriefFeatureBuilder,
    DailyBriefFeatureSet,
    DailyBriefResult,
    EventLogLoader,
    generate_daily_brief,
)
from kgcl.cli.utils import OutputFormat, format_output, print_error, print_info, print_success
from kgcl.hooks.security import ErrorSanitizer


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
    """Generate a daily brief from recent events.

    Ingests events from the specified date range, materializes features,
    and generates a structured brief using DSPy and Ollama.

    Examples
    --------
        # Generate today's brief
        $ kgc-daily-brief

        # Generate brief for specific date with 2-day lookback
        $ kgc-daily-brief --date 2024-01-15 --lookback 2

        # Save to file and copy to clipboard
        $ kgc-daily-brief -o brief.md -c

        # Use different model
        $ kgc-daily-brief --model llama3.3
    """
    try:
        # Determine date range
        target_date = date or datetime.now(UTC).replace(tzinfo=None)
        start_date = target_date - timedelta(days=lookback)

        if verbose:
            print_info(f"Generating brief for {start_date.date()} to {target_date.date()}")
            print_info(f"Using model: {model}")

        events_data = _ingest_events(start_date, target_date, verbose=verbose)

        if verbose:
            print_info(
                f"Ingested {events_data.event_count} events (synthetic={events_data.synthetic})"
            )

        features = _materialize_features(events_data, verbose=verbose)

        if verbose:
            print_info(
                f"Prepared feature vector with {features.input_data.context_switches} context switches "
                f"and {features.input_data.meeting_count} meetings"
            )

        brief_result = _generate_brief(features, model, verbose=verbose)

        # Format and output
        fmt = OutputFormat(output_format)
        payload = _select_payload_for_format(brief_result, fmt)
        format_output(payload, fmt, output, clipboard)

        print_success("Daily brief generated successfully")

    except (RuntimeError, ValueError) as exc:
        sanitized = ErrorSanitizer().sanitize(exc)
        print_error(f"Failed to generate daily brief: {sanitized.message}")


def _ingest_events(
    start_date: datetime, end_date: datetime, *, verbose: bool
) -> DailyBriefEventBatch:
    """Load events for the requested time window."""
    loader = EventLogLoader()
    batch = loader.load(start_date, end_date)
    if verbose:
        source_summary = ", ".join(path.name for path in batch.source_files) or "no log files"
        print_info(
            f"Loaded {batch.event_count} events spanning {batch.duration_days:.2f} days from {source_summary}"
        )
    return batch


def _materialize_features(batch: DailyBriefEventBatch, *, verbose: bool) -> DailyBriefFeatureSet:
    """Materialize DailyBriefInput features from events."""
    builder = DailyBriefFeatureBuilder()
    feature_set = builder.build(batch)
    if verbose:
        top_app = (
            feature_set.metadata["top_apps"][0]["name"]
            if feature_set.metadata["top_apps"]
            else "N/A"
        )
        print_info(
            f"Materialized features with focus time {feature_set.input_data.focus_time}h; top app={top_app}"
        )
    return feature_set


def _generate_brief(
    feature_set: DailyBriefFeatureSet, model: str, *, verbose: bool
) -> DailyBriefResult:
    """Generate structured brief content via DSPy module."""
    result = generate_daily_brief(feature_set, model)
    if verbose:
        print_info(
            f"Generated brief summary via model '{model}' (llm_enabled={result.metadata['llm_enabled']})"
        )
    return result


def _select_payload_for_format(result: DailyBriefResult, fmt: OutputFormat) -> object:
    """Select output payload type based on requested format."""
    if fmt == OutputFormat.MARKDOWN:
        return result.to_markdown()
    if fmt in {OutputFormat.TABLE, OutputFormat.CSV, OutputFormat.TSV}:
        return result.to_rows()
    return result.to_dict()


if __name__ == "__main__":
    daily_brief()

"""Weekly retrospective CLI command.

Generate a weekly retrospective from the last 7 days of events.
"""

from datetime import datetime, timedelta
from pathlib import Path

import click

from kgcl.cli.utils import OutputFormat, format_output, print_error, print_info, print_success


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
    """Generate a weekly retrospective from aggregated features.

    Analyzes the last N days of activity, produces narrative insights,
    and includes optional metrics.

    Examples
    --------
        # Generate retrospective for last 7 days
        $ kgc-weekly-retro

        # Custom time range with metrics
        $ kgc-weekly-retro --days 14 --include-metrics

        # Save to file
        $ kgc-weekly-retro -o retro.md

        # Use different model
        $ kgc-weekly-retro --model llama3.3
    """
    try:
        # Determine date range
        target_end = end_date or datetime.now()
        start_date = target_end - timedelta(days=days)

        if verbose:
            print_info(f"Generating retrospective for {start_date.date()} to {target_end.date()}")
            print_info(f"Using model: {model}")

        # Aggregate features from the time range
        features = _aggregate_features(start_date, target_end, verbose)

        if verbose:
            print_info(f"Aggregated {len(features)} feature categories")

        # Generate metrics if requested
        metrics = None
        if include_metrics:
            metrics = _compute_metrics(features, verbose)
            if verbose:
                print_info("Computed retrospective metrics")

        # Generate retrospective using DSPy
        retro_content = _generate_retrospective(features, metrics, model, verbose)

        # Format and output
        fmt = OutputFormat(output_format)
        format_output(retro_content, fmt, output, clipboard)

        print_success("Weekly retrospective generated successfully")

    except Exception as e:
        print_error(f"Failed to generate retrospective: {e}")


def _aggregate_features(start_date: datetime, end_date: datetime, verbose: bool) -> dict:
    """Aggregate features from the specified date range.

    Parameters
    ----------
    start_date : datetime
        Start date
    end_date : datetime
        End date
    verbose : bool
        Enable verbose output

    Returns
    -------
    dict
        Aggregated features by category

    """
    # TODO: Implement actual feature aggregation from UNRDF
    if verbose:
        print_info("Aggregating features from knowledge graph...")

    # Placeholder data
    return {
        "code_changes": {
            "total_commits": 42,
            "files_modified": 28,
            "lines_added": 1247,
            "lines_removed": 389,
        },
        "testing": {"test_runs": 156, "total_tests": 892, "pass_rate": 98.7, "new_tests": 12},
        "productivity": {"active_days": 5, "avg_commits_per_day": 8.4, "peak_activity_hour": 14},
        "quality": {"code_review_comments": 23, "bugs_fixed": 7, "bugs_introduced": 2},
    }


def _compute_metrics(features: dict, verbose: bool) -> dict:
    """Compute detailed metrics from aggregated features.

    Parameters
    ----------
    features : dict
        Aggregated features
    verbose : bool
        Enable verbose output

    Returns
    -------
    dict
        Computed metrics

    """
    if verbose:
        print_info("Computing metrics...")

    # TODO: Implement actual metric computation
    return {
        "velocity": {
            "commits_per_day": features["code_changes"]["total_commits"] / 7,
            "lines_per_day": (
                features["code_changes"]["lines_added"] - features["code_changes"]["lines_removed"]
            )
            / 7,
        },
        "quality_score": features["testing"]["pass_rate"] / 100,
        "activity_consistency": features["productivity"]["active_days"] / 7,
    }


def _generate_retrospective(features: dict, metrics: dict | None, model: str, verbose: bool) -> str:
    """Generate retrospective using DSPy and Ollama.

    Parameters
    ----------
    features : dict
        Aggregated features
    metrics : dict, optional
        Computed metrics
    model : str
        Ollama model name
    verbose : bool
        Enable verbose output

    Returns
    -------
    str
        Generated retrospective in markdown format

    """
    # TODO: Implement actual DSPy WeeklyRetroSignature integration
    if verbose:
        print_info(f"Generating retrospective with {model}...")

    # Placeholder: generate markdown retrospective
    retro = f"""# Weekly Retrospective

## Overview
Analysis of activity from the past 7 days

## Code Changes
- **Total commits**: {features["code_changes"]["total_commits"]}
- **Files modified**: {features["code_changes"]["files_modified"]}
- **Net lines changed**: {features["code_changes"]["lines_added"] - features["code_changes"]["lines_removed"]}

## Testing
- **Test runs**: {features["testing"]["test_runs"]}
- **Pass rate**: {features["testing"]["pass_rate"]}%
- **New tests added**: {features["testing"]["new_tests"]}

## Productivity
- **Active days**: {features["productivity"]["active_days"]}/7
- **Avg commits/day**: {features["productivity"]["avg_commits_per_day"]}
- **Peak activity**: {features["productivity"]["peak_activity_hour"]}:00

## Quality
- **Bugs fixed**: {features["quality"]["bugs_fixed"]}
- **Bugs introduced**: {features["quality"]["bugs_introduced"]}
- **Code reviews**: {features["quality"]["code_review_comments"]} comments
"""

    if metrics:
        retro += f"""
## Metrics
- **Velocity**: {metrics["velocity"]["commits_per_day"]:.1f} commits/day
- **Quality score**: {metrics["quality_score"]:.2%}
- **Activity consistency**: {metrics["activity_consistency"]:.2%}
"""

    retro += """
## Insights
- Strong testing discipline with high pass rate
- Consistent activity throughout the week
- Good balance between feature development and bug fixes

## Action Items
- Continue maintaining test coverage
- Monitor quality trends
- Consider pair programming for complex features
"""

    return retro


if __name__ == "__main__":
    weekly_retro()

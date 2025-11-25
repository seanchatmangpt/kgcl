"""Feature catalog CLI command.

List and explore feature templates and instances in the knowledge graph.
"""

from pathlib import Path

import click

from kgcl.cli.utils import (
    OutputFormat,
    format_output,
    print_error,
    print_info,
    print_success,
    print_table,
)


@click.command()
@click.option(
    "--category",
    type=str,
    help="Filter by category",
)
@click.option(
    "--source",
    type=str,
    help="Filter by source",
)
@click.option(
    "--search",
    type=str,
    help="Search term for feature name",
)
@click.option(
    "--templates-only",
    is_flag=True,
    help="Show only feature templates",
)
@click.option(
    "--instances-only",
    is_flag=True,
    help="Show only feature instances",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file path",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice([f.value for f in OutputFormat]),
    default=OutputFormat.TABLE.value,
    help="Output format",
)
@click.option(
    "--sort-by",
    type=click.Choice(["name", "updated", "category", "source"]),
    default="name",
    help="Sort by field",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Verbose output with full details",
)
def feature_list(
    category: str | None,
    source: str | None,
    search: str | None,
    templates_only: bool,
    instances_only: bool,
    output: Path | None,
    output_format: str,
    sort_by: str,
    verbose: bool,
) -> None:
    """List features from the knowledge graph.

    Query UNRDF for feature templates and instances with filtering and sorting.

    Examples:
        # List all features
        $ kgc-feature-list

        # Filter by category
        $ kgc-feature-list --category metrics

        # Search for specific features
        $ kgc-feature-list --search "test"

        # Show only templates in JSON format
        $ kgc-feature-list --templates-only -f json

        # Export to CSV
        $ kgc-feature-list -f csv -o features.csv
    """
    try:
        if verbose:
            print_info("Querying knowledge graph for features...")

        # Build query filters
        filters = _build_filters(
            category=category,
            source=source,
            search=search,
            templates_only=templates_only,
            instances_only=instances_only,
        )

        if verbose and filters:
            print_info(f"Applied filters: {filters}")

        # Query features from UNRDF
        features = _query_features(filters, verbose)

        if not features:
            print_info("No features found matching criteria")
            return

        # Sort results
        features = _sort_features(features, sort_by)

        if verbose:
            print_info(f"Found {len(features)} features")

        # Format and output
        fmt = OutputFormat(output_format)

        if fmt == OutputFormat.TABLE and not output:
            # Use rich table for terminal display
            _display_table(features, verbose)
        else:
            format_output(features, fmt, output, clipboard=False)

        print_success(f"Listed {len(features)} features")

    except Exception as e:
        print_error(f"Failed to list features: {e}")


def _build_filters(
    category: str | None,
    source: str | None,
    search: str | None,
    templates_only: bool,
    instances_only: bool,
) -> dict:
    """Build filter dictionary from CLI options.

    Parameters
    ----------
    category : str, optional
        Category filter
    source : str, optional
        Source filter
    search : str, optional
        Search term
    templates_only : bool
        Show only templates
    instances_only : bool
        Show only instances

    Returns
    -------
    dict
        Filter dictionary

    """
    filters = {}

    if category:
        filters["category"] = category
    if source:
        filters["source"] = source
    if search:
        filters["search"] = search

    if templates_only:
        filters["type"] = "template"
    elif instances_only:
        filters["type"] = "instance"

    return filters


def _query_features(filters: dict, verbose: bool) -> list[dict]:
    """Query features from UNRDF knowledge graph.

    Parameters
    ----------
    filters : dict
        Query filters
    verbose : bool
        Enable verbose output

    Returns
    -------
    list[dict]
        List of features matching filters

    """
    # TODO: Implement actual SPARQL query to UNRDF
    if verbose:
        print_info("Executing SPARQL query...")

    # Placeholder: return mock feature data
    all_features = [
        {
            "name": "test_pass_rate",
            "type": "template",
            "category": "testing",
            "inputs": "test_results",
            "output": "percentage",
            "last_updated": "2024-01-15",
            "source": "test_runner",
            "description": "Calculate test pass rate",
        },
        {
            "name": "commit_frequency",
            "type": "template",
            "category": "productivity",
            "inputs": "git_commits",
            "output": "number",
            "last_updated": "2024-01-14",
            "source": "git_analyzer",
            "description": "Count commits per day",
        },
        {
            "name": "code_complexity",
            "type": "template",
            "category": "quality",
            "inputs": "source_code",
            "output": "score",
            "last_updated": "2024-01-13",
            "source": "static_analyzer",
            "description": "Measure cyclomatic complexity",
        },
        {
            "name": "daily_test_run_instance",
            "type": "instance",
            "category": "testing",
            "inputs": "test_results_2024_01_15",
            "output": "97.5",
            "last_updated": "2024-01-15",
            "source": "test_runner",
            "description": "Instance of test_pass_rate",
        },
    ]

    # Apply filters
    filtered = all_features

    if "category" in filters:
        filtered = [f for f in filtered if f["category"] == filters["category"]]

    if "source" in filters:
        filtered = [f for f in filtered if f["source"] == filters["source"]]

    if "search" in filters:
        search_term = filters["search"].lower()
        filtered = [f for f in filtered if search_term in f["name"].lower()]

    if "type" in filters:
        filtered = [f for f in filtered if f["type"] == filters["type"]]

    return filtered


def _sort_features(features: list[dict], sort_by: str) -> list[dict]:
    """Sort features by specified field.

    Parameters
    ----------
    features : list[dict]
        Features to sort
    sort_by : str
        Field to sort by

    Returns
    -------
    list[dict]
        Sorted features

    """
    return sorted(features, key=lambda f: f.get(sort_by, ""))


def _display_table(features: list[dict], verbose: bool) -> None:
    """Display features in a formatted table.

    Parameters
    ----------
    features : list[dict]
        Features to display
    verbose : bool
        Show verbose details

    """
    if verbose:
        # Show all columns
        columns = [
            "name",
            "type",
            "category",
            "inputs",
            "output",
            "last_updated",
            "source",
            "description",
        ]
    else:
        # Show summary columns
        columns = ["name", "type", "category", "output", "last_updated"]

    print_table(features, columns, title="Feature Catalog")


if __name__ == "__main__":
    feature_list()

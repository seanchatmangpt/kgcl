"""Feature catalog CLI command."""

from __future__ import annotations

from pathlib import Path

import click

from kgcl.cli.bootstrap import build_cli_app
from kgcl.cli.core.errors import CliCommandError
from kgcl.cli.core.renderers import OutputFormat

cli_app = build_cli_app()


@click.command()
@click.option("--category", type=str, help="Filter by category")
@click.option("--source", type=str, help="Filter by source")
@click.option("--search", type=str, help="Search term for feature name")
@click.option("--templates-only", is_flag=True, help="Show only feature templates")
@click.option("--instances-only", is_flag=True, help="Show only feature instances")
@click.option(
    "--output", "-o", type=click.Path(path_type=Path), help="Output file path"
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
@click.option("--verbose", "-v", is_flag=True, help="Verbose output with full details")
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
    """List features from the KGCL knowledge graph with filtering and sorting.

    Queries the RDF knowledge graph to retrieve feature definitions (templates)
    and feature instances (materialized values). Features represent observable
    dimensions of productivity, performance, and behavior tracked by KGCL.

    The command supports rich filtering by category, source system, name search,
    and type (template vs instance). Results are returned in multiple output
    formats and can be sorted by various fields.

    When the local SPARQL dataset is unavailable, the command falls back to
    synthetic feature data for testing and demonstration purposes.

    Parameters
    ----------
    category : str or None, optional
        Filter features by category substring match (case-insensitive). Common
        categories include "productivity", "performance", "testing", "engineering".
        If None (default), all categories are included. Examples: "product",
        "perf", "test".
    source : str or None, optional
        Filter features by source system substring match (case-insensitive).
        Source identifies where the feature data originates (e.g., "github",
        "unrdf", "synthetic", "ollama"). If None (default), all sources are
        included.
    search : str or None, optional
        Search term for feature name substring match (case-insensitive). Filters
        features whose name contains the search term. If None (default), no name
        filtering is applied. Examples: "focus", "switch", "coverage".
    templates_only : bool, default=False
        Show only feature templates (abstract feature definitions) and exclude
        feature instances. Mutually exclusive with instances_only. When both
        are False, all types are shown.
    instances_only : bool, default=False
        Show only feature instances (concrete materialized feature values) and
        exclude feature templates. Mutually exclusive with templates_only. When
        both are False, all types are shown.
    output : Path or None, optional
        File path where the rendered feature list will be written. If None
        (default), output is only displayed to console. File is written in the
        format specified by output_format.
    output_format : str, default="table"
        Output rendering format. Must be one of: "table" (formatted table with
        columns), "json" (structured JSON array), or "markdown" (markdown-formatted
        text). Format is validated against OutputFormat enum values.
    sort_by : str, default="name"
        Field to sort results by. Must be one of: "name" (alphabetical by feature
        name), "updated" (most recent first), "category" (alphabetical by category),
        "source" (alphabetical by source). Sorting is case-insensitive.
    verbose : bool, default=False
        Enable verbose output showing full feature details including descriptions,
        metadata, and provenance. When False, only core fields (name, type,
        category, source, updated) are displayed.

    Returns
    -------
    None
        This function produces side effects (console output, file writes) but
        does not return a value. Success is indicated by "Listed N features"
        message where N is the count of matching features. The feature rows
        are internally stored but not returned to the caller.

    Raises
    ------
    CliCommandError
        If no features match the requested filters, or if the feature listing
        pipeline fails. This ensures the user is notified when filters are too
        restrictive or data sources are unavailable.
    FileNotFoundError
        If the output file path parent directory does not exist. Create the
        parent directory before calling this function.
    ValueError
        If the output_format is not a valid OutputFormat enum value (json,
        table, markdown), or if sort_by is not a valid field name.

    Examples
    --------
    List all features in default table format:

    >>> feature_list(
    ...     category=None,
    ...     source=None,
    ...     search=None,
    ...     templates_only=False,
    ...     instances_only=False,
    ...     output=None,
    ...     output_format="table",
    ...     sort_by="name",
    ...     verbose=False,
    ... )
    Listed 4 features

    Filter features by category and sort by update time:

    >>> feature_list(
    ...     category="productivity",
    ...     source=None,
    ...     search=None,
    ...     templates_only=False,
    ...     instances_only=False,
    ...     output=None,
    ...     output_format="table",
    ...     sort_by="updated",
    ...     verbose=True,
    ... )
    Listed 1 features

    Search for features containing "focus" in their name:

    >>> feature_list(
    ...     category=None,
    ...     source=None,
    ...     search="focus",
    ...     templates_only=False,
    ...     instances_only=False,
    ...     output=None,
    ...     output_format="json",
    ...     sort_by="name",
    ...     verbose=False,
    ... )
    Listed 1 features

    Show only feature templates from GitHub source:

    >>> from pathlib import Path
    >>> output_path = Path("reports/github-feature-templates.json")
    >>> feature_list(
    ...     category=None,
    ...     source="github",
    ...     search=None,
    ...     templates_only=True,
    ...     instances_only=False,
    ...     output=output_path,
    ...     output_format="json",
    ...     sort_by="category",
    ...     verbose=False,
    ... )
    Listed 0 features

    List all feature instances (materialized data):

    >>> feature_list(
    ...     category=None,
    ...     source=None,
    ...     search=None,
    ...     templates_only=False,
    ...     instances_only=True,
    ...     output=None,
    ...     output_format="table",
    ...     sort_by="name",
    ...     verbose=False,
    ... )
    Listed 2 features

    Notes
    -----
    The SPARQL query uses the KGCL ontology namespace (http://kgcl.io/ontology#)
    to identify features and their properties. Features must be instances of
    kgcl:Feature with required properties: name, category, source, kind, lastUpdated.

    When the SPARQL dataset is unavailable (FileNotFoundError), the function
    automatically falls back to synthetic feature data containing 4 sample
    features for testing purposes.

    The verbose flag controls output detail but does not affect the underlying
    SPARQL query or data retrieval.

    See Also
    --------
    daily_brief : Generate daily brief from recent events and features
    weekly_retro : Generate weekly retrospective from aggregated features
    """
    filters = {
        "category": category,
        "source": source,
        "search": search,
        "templates_only": templates_only,
        "instances_only": instances_only,
    }

    def _execute(context):
        sparql = _build_sparql(filters, sort_by)
        try:
            rows = context.sparql_service.query(sparql)
        except FileNotFoundError:
            rows = _fallback_features(filters, sort_by)
        if not rows:
            raise CliCommandError("No features matched the requested filters")
        fmt = OutputFormat(output_format)
        context.renderer.render(rows, fmt=fmt, clipboard=False, output_file=output)
        return rows

    result, _ = cli_app.run("feature-list", _execute)
    if result is None:
        raise CliCommandError("Feature listing failed")
    click.echo(f"Listed {len(result)} features")


def _build_sparql(filters: dict, sort_by: str) -> str:
    conditions = []
    if filters.get("category"):
        conditions.append(
            f'FILTER(CONTAINS(LCASE(?category), "{filters["category"].lower()}"))'
        )
    if filters.get("source"):
        conditions.append(
            f'FILTER(CONTAINS(LCASE(?source), "{filters["source"].lower()}"))'
        )
    if filters.get("search"):
        conditions.append(
            f'FILTER(CONTAINS(LCASE(?name), "{filters["search"].lower()}"))'
        )
    if filters.get("templates_only"):
        conditions.append('FILTER(?type = "template")')
    if filters.get("instances_only"):
        conditions.append('FILTER(?type = "instance")')
    where_clause = "\n    ".join(conditions)
    order_clause = f"ORDER BY LCASE(?{sort_by})" if sort_by else ""
    return f"""
PREFIX kgcl: <http://kgcl.io/ontology#>
SELECT ?name ?type ?category ?source ?updated
WHERE {{
    ?feature a kgcl:Feature ;
             kgcl:name ?name ;
             kgcl:category ?category ;
             kgcl:source ?source ;
             kgcl:kind ?type ;
             kgcl:lastUpdated ?updated .
    {where_clause}
}}
{order_clause}
"""


_SYNTHETIC_FEATURES = [
    {
        "name": "daily_focus_score",
        "type": "template",
        "category": "productivity",
        "source": "synthetic",
        "updated": "2025-11-24T09:00:00Z",
    },
    {
        "name": "context_switch_rate",
        "type": "template",
        "category": "performance",
        "source": "synthetic",
        "updated": "2025-11-23T18:30:00Z",
    },
    {
        "name": "recent_commits",
        "type": "instance",
        "category": "engineering",
        "source": "github",
        "updated": "2025-11-22T15:00:00Z",
    },
    {
        "name": "test_coverage_delta",
        "type": "instance",
        "category": "testing",
        "source": "unrdf",
        "updated": "2025-11-21T12:00:00Z",
    },
]


def _fallback_features(filters: dict, sort_by: str) -> list[dict[str, str]]:
    """Return synthetic feature rows when local SPARQL data is unavailable."""

    def _matches(row: dict[str, str]) -> bool:
        if (
            filters.get("category")
            and filters["category"].lower() not in row["category"].lower()
        ):
            return False
        if (
            filters.get("source")
            and filters["source"].lower() not in row["source"].lower()
        ):
            return False
        if (
            filters.get("search")
            and filters["search"].lower() not in row["name"].lower()
        ):
            return False
        if filters.get("templates_only") and row["type"] != "template":
            return False
        return not (filters.get("instances_only") and row["type"] != "instance")

    filtered = [row for row in _SYNTHETIC_FEATURES if _matches(row)]
    if sort_by:
        filtered.sort(key=lambda row: row.get(sort_by, "").lower())
    return filtered


if __name__ == "__main__":
    feature_list()

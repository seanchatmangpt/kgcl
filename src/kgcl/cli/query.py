"""Graph query CLI command.

Execute SPARQL queries against the UNRDF knowledge graph.
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

import click
from rdflib import Graph
from rdflib.util import guess_format

from kgcl.cli.utils import OutputFormat, console, format_output, print_error, print_info, print_success

# Template queries for common use cases
TEMPLATE_QUERIES = {
    "all_features": """
        PREFIX kgcl: <http://kgcl.io/ontology#>
        SELECT ?feature ?type ?category
        WHERE {
            ?feature a kgcl:Feature ;
                    kgcl:type ?type ;
                    kgcl:category ?category .
        }
        ORDER BY ?category ?feature
    """,
    "recent_events": """
        PREFIX kgcl: <http://kgcl.io/ontology#>
        SELECT ?event ?timestamp ?type
        WHERE {
            ?event a kgcl:Event ;
                  kgcl:timestamp ?timestamp ;
                  kgcl:type ?type .
            FILTER (?timestamp > "2024-01-01T00:00:00"^^xsd:dateTime)
        }
        ORDER BY DESC(?timestamp)
        LIMIT 100
    """,
    "feature_dependencies": """
        PREFIX kgcl: <http://kgcl.io/ontology#>
        SELECT ?feature ?depends_on
        WHERE {
            ?feature a kgcl:Feature ;
                    kgcl:dependsOn ?depends_on .
        }
    """,
    "metrics_summary": """
        PREFIX kgcl: <http://kgcl.io/ontology#>
        SELECT ?metric (COUNT(?instance) as ?count) (AVG(?value) as ?avg_value)
        WHERE {
            ?instance a kgcl:FeatureInstance ;
                     kgcl:template ?metric ;
                     kgcl:value ?value .
        }
        GROUP BY ?metric
        ORDER BY DESC(?count)
    """,
    "code_changes": """
        PREFIX kgcl: <http://kgcl.io/ontology#>
        SELECT ?file ?timestamp ?lines_added ?lines_removed
        WHERE {
            ?change a kgcl:CodeChange ;
                   kgcl:file ?file ;
                   kgcl:timestamp ?timestamp ;
                   kgcl:linesAdded ?lines_added ;
                   kgcl:linesRemoved ?lines_removed .
        }
        ORDER BY DESC(?timestamp)
        LIMIT 50
    """,
}


@click.command()
@click.option("--query", "-q", type=str, help="SPARQL query to execute")
@click.option("--file", type=click.Path(exists=True, path_type=Path), help="File containing SPARQL query")
@click.option(
    "--template", "-t", type=click.Choice(list(TEMPLATE_QUERIES.keys())), help="Use a predefined query template"
)
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Output file path")
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice([f.value for f in OutputFormat]),
    default=OutputFormat.TABLE.value,
    help="Output format",
)
@click.option("--limit", type=int, help="Limit number of results")
@click.option("--endpoint", type=str, default="http://localhost:3030/kgcl/sparql", help="SPARQL endpoint URL")
@click.option("--show-templates", is_flag=True, help="Show available query templates and exit")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def query(
    query: str | None,
    file: Path | None,
    template: str | None,
    output: Path | None,
    output_format: str,
    limit: int | None,
    endpoint: str,
    show_templates: bool,
    verbose: bool,
) -> None:
    """Execute SPARQL queries against the knowledge graph.

    Examples
    --------
        # Show available templates
        $ kgc-query --show-templates

        # Use a template query
        $ kgc-query -t all_features

        # Execute custom query
        $ kgc-query -q "SELECT * WHERE { ?s ?p ?o } LIMIT 10"

        # Query from file and export to JSON
        $ kgc-query --file query.sparql -f json -o results.json

        # Query with result limit
        $ kgc-query -t recent_events --limit 50
    """
    try:
        if show_templates:
            _show_templates()
            return

        # Determine query source
        sparql_query = _get_query(query, file, template)

        if not sparql_query:
            print_error("No query specified. Use --query, --file, or --template", exit_code=1)
            return

        # Apply limit if specified
        if limit and "LIMIT" not in sparql_query.upper():
            sparql_query += f"\nLIMIT {limit}"

        verbosity = Verbosity.VERBOSE if verbose else Verbosity.QUIET

        if verbosity.is_verbose:
            print_info(f"Executing query against {endpoint}")
            print_info(f"Query:\n{sparql_query}")

        # Execute query
        results = _execute_query(sparql_query, endpoint, verbosity)

        if not results:
            print_info("Query returned no results")
            return

        if verbosity.is_verbose:
            print_info(f"Retrieved {len(results)} results")

        # Format and output
        fmt = OutputFormat(output_format)
        format_output(results, fmt, output, clipboard=False)

        print_success(f"Query executed successfully ({len(results)} results)")

    except (HTTPError, URLError, ValueError, RuntimeError) as exc:
        print_error(f"Query failed: {exc}")


def _show_templates() -> None:
    """Display available query templates."""
    console.print("\n[bold]Available Query Templates:[/bold]\n")

    for name, query in TEMPLATE_QUERIES.items():
        console.print(f"[cyan]{name}[/cyan]")
        console.print(f"  {query.strip()[:100]}...\n")


def _get_query(query: str | None, file: Path | None, template: str | None) -> str | None:
    """Get SPARQL query from various sources.

    Parameters
    ----------
    query : str, optional
        Direct query string
    file : Path, optional
        Query file path
    template : str, optional
        Template name

    Returns
    -------
    str, optional
        SPARQL query string

    """
    if query:
        return query

    if file:
        return file.read_text()

    if template:
        return TEMPLATE_QUERIES.get(template)

    return None


_HTTP_TIMEOUT_SECONDS = 5.0


class Verbosity(Enum):
    """Verbosity settings for CLI output."""

    QUIET = "quiet"
    VERBOSE = "verbose"

    @property
    def is_verbose(self) -> bool:
        """Whether verbose output should be emitted."""
        return self is Verbosity.VERBOSE


def _execute_query(sparql_query: str, endpoint: str, verbosity: Verbosity) -> list[dict[str, str]]:
    """Execute SPARQL query against endpoint.

    Parameters
    ----------
    sparql_query : str
        SPARQL query string
    endpoint : str
        SPARQL endpoint URL
    verbose : bool
        Enable verbose output

    Returns
    -------
    list[dict[str, str]]
        Query results

    Raises
    ------
    requests.RequestException
        If the HTTP endpoint rejects the query
    ValueError
        If the endpoint points to a missing dataset file
    """
    dataset_path = _resolve_local_dataset(endpoint)

    if dataset_path:
        if verbosity.is_verbose:
            print_info(f"Executing SPARQL locally via {dataset_path}")
        return _execute_query_local(sparql_query, dataset_path)

    if verbosity.is_verbose:
        print_info(f"Connecting to SPARQL endpoint at {endpoint}")

    return _execute_query_http(sparql_query, endpoint)


def _resolve_local_dataset(endpoint: str) -> Path | None:
    """Resolve endpoint string to a local dataset path when applicable."""
    candidate = Path(endpoint[7:]) if endpoint.startswith("file://") else Path(endpoint)

    if candidate.exists():
        return candidate

    return None


def _execute_query_local(sparql_query: str, dataset_path: Path) -> list[dict[str, str]]:
    """Run query against a local RDF dataset."""
    if not dataset_path.exists():
        msg = f"Dataset not found: {dataset_path}"
        raise ValueError(msg)

    rdf_format = guess_format(dataset_path.suffix[1:]) or guess_format(dataset_path.name) or "turtle"

    graph = Graph()
    graph.parse(dataset_path, format=rdf_format)
    results = graph.query(sparql_query)

    normalized: list[dict[str, str]] = []
    for binding in results.bindings:
        row: dict[str, str] = {}
        for var, value in binding.items():
            key = str(var)
            key = key.removeprefix("?")
            row[key] = str(value)
        if row:
            normalized.append(row)

    return normalized


def _execute_query_http(sparql_query: str, endpoint: str) -> list[dict[str, str]]:
    """Run query against a remote SPARQL endpoint via HTTP."""
    parsed = urlsplit(endpoint)
    if parsed.scheme not in {"http", "https"}:
        msg = f"Unsupported SPARQL endpoint scheme: {parsed.scheme or 'unknown'}"
        raise ValueError(msg)

    encoded_data = urlencode({"query": sparql_query}).encode("utf-8")
    request = Request(  # Safe due to explicit scheme validation above
        endpoint,
        data=encoded_data,
        headers={"Accept": "application/sparql-results+json", "Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    with urlopen(request, timeout=_HTTP_TIMEOUT_SECONDS) as response:
        payload: dict[str, Any] = json.loads(response.read().decode("utf-8"))
    bindings = payload.get("results", {}).get("bindings", [])

    results: list[dict[str, str]] = []
    for binding in bindings:
        row: dict[str, str] = {}
        for var, value in binding.items():
            string_value = value.get("value")
            if string_value is not None:
                row[var] = string_value
        if row:
            results.append(row)

    return results


if __name__ == "__main__":
    query()

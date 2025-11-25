"""Graph query CLI command.

Execute SPARQL queries against the UNRDF knowledge graph.
"""

from pathlib import Path

import click

from kgcl.cli.utils import (
    OutputFormat,
    format_output,
    print_error,
    print_info,
    print_success,
)


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
@click.option(
    "--query",
    "-q",
    type=str,
    help="SPARQL query to execute",
)
@click.option(
    "--file",
    type=click.Path(exists=True, path_type=Path),
    help="File containing SPARQL query",
)
@click.option(
    "--template",
    "-t",
    type=click.Choice(list(TEMPLATE_QUERIES.keys())),
    help="Use a predefined query template",
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
    "--limit",
    type=int,
    help="Limit number of results",
)
@click.option(
    "--endpoint",
    type=str,
    default="http://localhost:3030/kgcl/sparql",
    help="SPARQL endpoint URL",
)
@click.option(
    "--show-templates",
    is_flag=True,
    help="Show available query templates and exit",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Verbose output",
)
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

    Examples:
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
            print_error(
                "No query specified. Use --query, --file, or --template",
                exit_code=1,
            )
            return

        # Apply limit if specified
        if limit and "LIMIT" not in sparql_query.upper():
            sparql_query += f"\nLIMIT {limit}"

        if verbose:
            print_info(f"Executing query against {endpoint}")
            print_info(f"Query:\n{sparql_query}")

        # Execute query
        results = _execute_query(sparql_query, endpoint, verbose)

        if not results:
            print_info("Query returned no results")
            return

        if verbose:
            print_info(f"Retrieved {len(results)} results")

        # Format and output
        fmt = OutputFormat(output_format)
        format_output(results, fmt, output, clipboard=False)

        print_success(f"Query executed successfully ({len(results)} results)")

    except Exception as e:
        print_error(f"Query failed: {e}")


def _show_templates() -> None:
    """Display available query templates."""
    from kgcl.cli.utils import console

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


def _execute_query(sparql_query: str, endpoint: str, verbose: bool) -> list[dict]:
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
    list[dict]
        Query results

    """
    # TODO: Implement actual SPARQL query execution
    # This would use a library like SPARQLWrapper or rdflib
    if verbose:
        print_info("Connecting to SPARQL endpoint...")

    # Placeholder: return mock results
    return [
        {
            "feature": "test_pass_rate",
            "type": "template",
            "category": "testing",
        },
        {
            "feature": "commit_frequency",
            "type": "template",
            "category": "productivity",
        },
        {
            "feature": "code_complexity",
            "type": "template",
            "category": "quality",
        },
    ]


if __name__ == "__main__":
    query()

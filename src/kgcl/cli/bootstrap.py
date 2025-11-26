"""Bootstrap helpers for CLI context creation."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from kgcl.cli.core import (
    CliApp,
    CliConfigStore,
    CliContext,
    ClipboardGateway,
    CliRenderer,
)
from kgcl.cli.services_impl import (
    DailyBriefDspyService,
    DailyBriefIngestionService,
    JsonConfigService,
    LocalDatasetSparqlService,
    NoOpLinkmlValidator,
)


def build_cli_app(
    project_root: Path | None = None, dataset_path: Path | None = None
) -> CliApp:
    """Construct a fully-wired CliApp with all default services and dependencies.

    Factory function that assembles a complete CLI application context including
    rendering, configuration storage, data ingestion, SPARQL querying, DSPy
    integration, and validation services. This provides dependency injection
    for all CLI commands, ensuring consistent service configuration.

    The function creates a production-ready CliApp with:
    - Rich console rendering and clipboard integration
    - JSON-based configuration storage in .config/kgcl
    - Daily brief ingestion service for Apple ecosystem events
    - DSPy service for LLM-powered feature generation
    - Local SPARQL service querying RDF knowledge graphs
    - LinkML validation service for schema enforcement

    This function is the standard entry point for all CLI commands, providing
    a unified service layer and consistent behavior across the application.

    Parameters
    ----------
    project_root : Path or None, optional, default=None
        Root directory of the KGCL project. Used to resolve relative paths
        for configuration, data files, and service initialization. If None
        (default), uses current working directory (Path.cwd()). Typically
        set to the repository root containing src/, tests/, data/ directories.
    dataset_path : Path or None, optional, default=None
        Path to the RDF/TTL dataset file used by the SPARQL service for
        knowledge graph queries. If None (default), uses the standard location
        at {project_root}/data/apple-ingest.ttl. Override this to use custom
        datasets or test fixtures.

    Returns
    -------
    CliApp
        Fully-configured CLI application instance with wired services:
        - context.renderer: CliRenderer for console/file/clipboard output
        - context.clipboard: ClipboardGateway for system clipboard access
        - context.config_store: CliConfigStore for persistent configuration
        - context.ingestion_service: DailyBriefIngestionService for event loading
        - context.dspy_service: DailyBriefDspyService for LLM generation
        - context.sparql_service: LocalDatasetSparqlService for RDF queries
        - context.config_service: JsonConfigService for config management
        - context.linkml_validator: NoOpLinkmlValidator for schema validation

        The returned CliApp is ready for command execution via app.run().

    Raises
    ------
    FileNotFoundError
        If project_root or dataset_path point to non-existent directories/files
        and are required for service initialization. Some services gracefully
        handle missing files with fallback behavior.
    PermissionError
        If the configuration directory (.config/kgcl) cannot be created due
        to filesystem permissions. Ensure the project_root is writable.

    Examples
    --------
    Build CLI app with default settings (current directory, standard dataset):

    >>> from pathlib import Path
    >>> app = build_cli_app()
    >>> isinstance(app.context.renderer, CliRenderer)
    True
    >>> app.context.project_root == Path.cwd()
    True

    Build CLI app with explicit project root:

    >>> from pathlib import Path
    >>> project_root = Path("/Users/dev/kgcl")
    >>> app = build_cli_app(project_root=project_root)
    >>> app.context.project_root == project_root
    True
    >>> app.context.config_store.root == project_root / ".config" / "kgcl"
    True

    Build CLI app with custom dataset for testing:

    >>> from pathlib import Path
    >>> test_dataset = Path("tests/fixtures/test-data.ttl")
    >>> app = build_cli_app(dataset_path=test_dataset)
    >>> app.context.sparql_service.dataset_path == test_dataset
    True

    Use the built app to run a CLI command:

    >>> app = build_cli_app()
    >>> def my_command(context):
    ...     rows = context.sparql_service.query("SELECT ?s WHERE { ?s ?p ?o } LIMIT 10")
    ...     return rows
    >>> result, receipt = app.run("my-command", my_command)
    >>> len(result) <= 10
    True

    Notes
    -----
    The function uses dependency injection to decouple CLI commands from
    concrete service implementations. This enables:
    - Easy testing by injecting mock services
    - Service customization without modifying commands
    - Consistent configuration across all CLI entry points

    The CliContext dataclass bundles all services and is passed to command
    execution functions via the app.run() method. Commands access services
    through context.service_name pattern.

    The NoOpLinkmlValidator is a placeholder that performs no validation.
    Future versions may integrate real LinkML/SHACL validation for RDF data.

    Configuration storage uses a JSON-based config store at .config/kgcl
    relative to project_root. This directory is created automatically if
    it does not exist.

    See Also
    --------
    CliApp.run : Execute a CLI command with the wired context
    CliContext : Dataclass bundling all CLI services
    DailyBriefIngestionService : Service for loading Apple ecosystem events
    LocalDatasetSparqlService : Service for querying local RDF datasets
    """
    root = project_root or Path.cwd()
    console = Console()
    clipboard = ClipboardGateway()
    renderer = CliRenderer(console=console, clipboard=clipboard)
    config_store = CliConfigStore(root / ".config" / "kgcl")
    ingestion_service = DailyBriefIngestionService(project_root=root)
    dspy_service = DailyBriefDspyService()
    sparql_service = LocalDatasetSparqlService(
        dataset_path=dataset_path or root / "data" / "apple-ingest.ttl"
    )
    config_service = JsonConfigService(config_store)
    validator = NoOpLinkmlValidator(shapes_path=root / ".kgc" / "types.ttl")

    context = CliContext(
        project_root=root,
        renderer=renderer,
        clipboard=clipboard,
        config_store=config_store,
        ingestion_service=ingestion_service,
        dspy_service=dspy_service,
        sparql_service=sparql_service,
        config_service=config_service,
        linkml_validator=validator,
    )
    return CliApp(context=context, console=console)

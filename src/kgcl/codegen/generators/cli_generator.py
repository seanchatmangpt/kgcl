"""CLI code generator using unified framework.

Generates Typer CLI applications from RDF ontology definitions.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rdflib import RDF, Graph, Namespace

from kgcl.codegen.base.generator import BaseGenerator, GenerationResult

CLI = Namespace("urn:kgc:cli:")


@dataclass(frozen=True)
class CliParam:
    """CLI parameter metadata.

    Parameters
    ----------
    name : str
        Parameter name
    help : str
        Help text
    required : bool
        Whether parameter is required
    repeatable : bool
        Whether parameter can be repeated
    default : str | None
        Default value if any
    """

    name: str
    help: str
    required: bool
    repeatable: bool = False
    default: str | None = None


@dataclass(frozen=True)
class CliCommand:
    """CLI command metadata.

    Parameters
    ----------
    name : str
        Command name
    help : str
        Command help text
    handler_module : str
        Python module containing handler
    handler_function : str
        Handler function name
    args : Sequence[CliParam]
        Command arguments
    options : Sequence[CliParam]
        Command options
    """

    name: str
    help: str
    handler_module: str
    handler_function: str
    args: Sequence[CliParam]
    options: Sequence[CliParam]


@dataclass(frozen=True)
class CliMetadata:
    """Parsed CLI metadata from RDF.

    Parameters
    ----------
    root_name : str
        Root command name
    root_help : str
        Root command help text
    commands : Sequence[CliCommand]
        List of CLI commands
    """

    root_name: str
    root_help: str
    commands: Sequence[CliCommand]


class RdfCliParser:
    """Parse CLI definitions from RDF/Turtle files."""

    def parse(self, input_path: Path) -> CliMetadata:
        """Parse RDF file and extract CLI metadata.

        Parameters
        ----------
        input_path : Path
            Path to RDF/Turtle file

        Returns
        -------
        CliMetadata
            Parsed CLI metadata

        Raises
        ------
        FileNotFoundError
            If input file doesn't exist
        """
        if not input_path.exists():
            msg = f"CLI definition not found: {input_path}"
            raise FileNotFoundError(msg)

        graph = Graph()
        graph.parse(input_path, format="turtle")

        commands = self._extract_commands(graph)
        root_node = CLI["KgctRoot"]
        root_name = str(graph.value(subject=root_node, predicate=CLI.name, default="kgct"))
        root_help = str(
            graph.value(subject=root_node, predicate=CLI.help, default="KGC Technician Console")
        )

        return CliMetadata(
            root_name=root_name,
            root_help=root_help,
            commands=commands,
        )

    def _extract_commands(self, graph: Graph) -> list[CliCommand]:
        """Extract command definitions from RDF graph."""
        commands: list[CliCommand] = []
        for node in graph.subjects(RDF.type, CLI.Command):
            name = str(graph.value(subject=node, predicate=CLI.name))
            help_text = str(graph.value(subject=node, predicate=CLI.help))
            handler_module = str(graph.value(subject=node, predicate=CLI.handlerModule))
            handler_function = str(graph.value(subject=node, predicate=CLI.handlerFunction))
            args = self._extract_params(graph, node, CLI.hasArgument)
            options = self._extract_params(graph, node, CLI.hasOption)
            commands.append(
                CliCommand(
                    name=name,
                    help=help_text,
                    handler_module=handler_module,
                    handler_function=handler_function,
                    args=args,
                    options=options,
                )
            )
        commands.sort(key=lambda cmd: cmd.name)
        return commands

    def _extract_params(self, graph: Graph, node: Any, predicate: Any) -> list[CliParam]:
        """Extract parameter definitions."""
        params: list[CliParam] = []
        for obj in graph.objects(subject=node, predicate=predicate):
            params.append(
                CliParam(
                    name=str(graph.value(subject=obj, predicate=CLI.name)),
                    help=str(graph.value(subject=obj, predicate=CLI.help, default="")),
                    required=bool(graph.value(subject=obj, predicate=CLI.isRequired, default=False)),
                    repeatable=bool(graph.value(subject=obj, predicate=CLI.repeatable, default=False)),
                    default=self._literal_to_python(graph.value(subject=obj, predicate=CLI.default)),
                )
            )
        return params

    @staticmethod
    def _literal_to_python(value: Any) -> str | None:
        """Convert RDF literal to Python string."""
        if value is None:
            return None
        return str(value)


class CliGenerator(BaseGenerator[CliMetadata]):
    """Generate Typer CLI applications from RDF ontologies.

    This generator reads CLI command definitions from RDF/Turtle files
    and generates production-ready Typer CLI applications.

    Examples
    --------
    >>> from pathlib import Path
    >>> generator = CliGenerator(
    ...     template_dir=Path("templates/cli"),
    ...     output_dir=Path("src/personal_kgcl"),
    ... )
    >>> result = generator.generate(Path(".kgc/cli.ttl"))
    >>> print(result.output_path)
    src/personal_kgcl/cli.py
    """

    def __init__(
        self,
        template_dir: Path,
        output_dir: Path,
        dry_run: bool = False,
        app_version: str = "0.0.0",
    ) -> None:
        """Initialize CLI generator.

        Parameters
        ----------
        template_dir : Path
            Directory containing CLI templates
        output_dir : Path
            Output directory for generated CLI
        dry_run : bool
            If True, don't write files
        app_version : str
            Application version string
        """
        super().__init__(template_dir, output_dir, dry_run)
        self.app_version = app_version
        self._parser = RdfCliParser()

    @property
    def parser(self) -> RdfCliParser:
        """Return RDF CLI parser instance."""
        return self._parser

    def _transform(self, metadata: CliMetadata, **kwargs: Any) -> dict[str, Any]:
        """Transform CLI metadata to template context.

        Parameters
        ----------
        metadata : CliMetadata
            Parsed CLI metadata
        **kwargs : Any
            Additional options (cli_ontology_path)

        Returns
        -------
        dict[str, Any]
            Template rendering context
        """
        cli_ontology_path = kwargs.get("cli_ontology_path", ".kgc/cli.ttl")

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "kgc_ontology_path": str(cli_ontology_path),
            "cli_ontology_path": str(cli_ontology_path),
            "root_command": {
                "name": metadata.root_name,
                "help": metadata.root_help,
            },
            "commands": metadata.commands,
            "app_version": self.app_version,
        }

    def _get_template_name(self, metadata: CliMetadata, **kwargs: Any) -> str:
        """Get CLI template file name.

        Parameters
        ----------
        metadata : CliMetadata
            CLI metadata
        **kwargs : Any
            Additional options

        Returns
        -------
        str
            Template file name
        """
        return "cli.py.j2"

    def _get_output_path(self, metadata: CliMetadata, **kwargs: Any) -> Path:
        """Get output path for generated CLI.

        Parameters
        ----------
        metadata : CliMetadata
            CLI metadata
        **kwargs : Any
            Additional options (may include output_path override)

        Returns
        -------
        Path
            Output file path
        """
        # Allow override from kwargs
        if "output_path" in kwargs:
            return Path(kwargs["output_path"])

        # Default output path
        return self.output_dir / "cli.py"

    def _build_metadata(self, metadata: CliMetadata, **kwargs: Any) -> dict[str, Any]:
        """Build result metadata.

        Parameters
        ----------
        metadata : CliMetadata
            Original CLI metadata
        **kwargs : Any
            Additional options

        Returns
        -------
        dict[str, Any]
            Result metadata
        """
        return {
            "num_commands": len(metadata.commands),
            "commands": [cmd.name for cmd in metadata.commands],
        }


def generate_cli_module(
    cli_ttl: Path | None = None,
    template_path: Path | None = None,
    output_path: Path | None = None,
    dry_run: bool = False,
) -> GenerationResult:
    """Generate CLI module from RDF definition.

    This is a convenience function for backwards compatibility with the
    original CLI generator API.

    Parameters
    ----------
    cli_ttl : Path | None
        Path to CLI RDF file (default: .kgc/cli.ttl)
    template_path : Path | None
        Path to template file (default: .kgc/projections/cli.py.j2)
    output_path : Path | None
        Output file path (default: src/personal_kgcl/cli.py)
    dry_run : bool
        If True, don't write files

    Returns
    -------
    GenerationResult
        Generation result with output path and metadata
    """
    # Set defaults
    kgc_dir = Path(__file__).resolve().parents[4] / ".kgc"
    cli_ttl_path = cli_ttl or kgc_dir / "cli.ttl"
    template_dir = (template_path or kgc_dir / "projections").parent
    output_dir = (output_path or Path("src/personal_kgcl")).parent

    # Create generator
    generator = CliGenerator(
        template_dir=template_dir,
        output_dir=output_dir,
        dry_run=dry_run,
    )

    # Generate CLI
    return generator.generate(
        cli_ttl_path,
        output_path=output_path,
        cli_ontology_path=cli_ttl_path,
    )


def main() -> None:
    """Console entrypoint for CLI generation."""
    result = generate_cli_module()
    print(f"Generated KGCT CLI → {result.output_path}")


if __name__ == "__main__":
    main()


__all__ = [
    "CliCommand",
    "CliParam",
    "CliMetadata",
    "CliGenerator",
    "RdfCliParser",
    "generate_cli_module",
]

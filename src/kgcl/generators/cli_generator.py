"""
CLI Generator: Generate Typer KGCT CLI from RDF ontology.

This module reads the KGC ontology (specifically CLI command definitions),
and renders the Typer CLI using Jinja2 templating.

Typical usage:
    python -m personal_kgcl.generators.cli_generator \
        --ontology .kgc/ontology.ttl \
        --cli-ontology .kgc/cli.ttl \
        --template .kgc/projections/cli.py.j2 \
        --output personal_kgct_cli.py
"""

import hashlib
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import rdflib
    from rdflib import RDF, RDFS, Graph, Namespace
except ImportError:
    print("Error: rdflib not installed. Install with: pip install rdflib", file=sys.stderr)
    sys.exit(1)

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except ImportError:
    print("Error: jinja2 not installed. Install with: pip install jinja2", file=sys.stderr)
    sys.exit(1)


class CLIGenerator:
    """Generate KGCT Typer CLI from RDF definitions."""

    def __init__(self, ontology_path: Path, template_path: Path, output_path: Path | None = None):
        """Initialize generator."""
        self.ontology_path = Path(ontology_path)
        self.template_path = Path(template_path)
        self.output_path = Path(output_path) if output_path else Path("personal_kgct_cli.py")

        # Load RDF graph
        self.graph = Graph()
        self.graph.parse(self.ontology_path, format="ttl")

        # Define namespaces
        self.CLI = Namespace("urn:kgc:cli:")
        self.KGC = Namespace("urn:kgc:")
        self.RDFS = RDFS

        # Setup Jinja
        template_dir = self.template_path.parent
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def query_commands(self) -> list[dict[str, Any]]:
        """Query RDF for all CLI commands."""
        query = """
        PREFIX cli: <urn:kgc:cli:>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?cmd ?name ?help ?handler_module ?handler_function
        WHERE {
            ?cmd a cli:Command ;
                 cli:name ?name ;
                 cli:help ?help ;
                 cli:handlerModule ?handler_module ;
                 cli:handlerFunction ?handler_function .
        }
        ORDER BY ?name
        """
        results = self.graph.query(query)
        commands = []

        for row in results:
            cmd_uri = str(row.cmd)
            name = str(row.name)
            help_text = str(row.help)
            handler_module = str(row.handler_module)
            handler_function = str(row.handler_function)

            # Query arguments for this command
            args = self._query_args(cmd_uri)
            options = self._query_options(cmd_uri)

            commands.append(
                {
                    "uri": cmd_uri,
                    "name": name,
                    "help": help_text,
                    "handler_module": handler_module,
                    "handler_function": handler_function,
                    "args": args,
                    "options": options,
                    "extended_help": self._get_extended_help(cmd_uri),
                }
            )

        return commands

    def _query_args(self, cmd_uri: str) -> list[dict[str, Any]]:
        """Query positional arguments for a command."""
        query = f"""
        PREFIX cli: <urn:kgc:cli:>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?arg_name ?arg_help ?arg_type ?required
        WHERE {{
            <{cmd_uri}> cli:arg ?arg .
            ?arg cli:name ?arg_name ;
                 cli:help ?arg_help .
            OPTIONAL {{ ?arg cli:pythonType ?arg_type . }}
            OPTIONAL {{ ?arg cli:required ?required . }}
        }}
        ORDER BY ?arg_name
        """
        results = self.graph.query(query)
        args = []

        for row in results:
            args.append(
                {
                    "name": str(row.arg_name),
                    "help": str(row.arg_help),
                    "python_type": str(row.arg_type) if row.arg_type else "str",
                    "required": str(row.required).lower() == "true" if row.required else True,
                }
            )

        return args

    def _query_options(self, cmd_uri: str) -> list[dict[str, Any]]:
        """Query optional flags for a command."""
        query = f"""
        PREFIX cli: <urn:kgc:cli:>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?opt_name ?opt_help ?opt_type ?opt_default ?required
        WHERE {{
            <{cmd_uri}> cli:option ?opt .
            ?opt cli:name ?opt_name ;
                 cli:help ?opt_help .
            OPTIONAL {{ ?opt cli:pythonType ?opt_type . }}
            OPTIONAL {{ ?opt cli:default ?opt_default . }}
            OPTIONAL {{ ?opt cli:required ?required . }}
        }}
        ORDER BY ?opt_name
        """
        results = self.graph.query(query)
        options = []

        for row in results:
            options.append(
                {
                    "name": str(row.opt_name),
                    "help": str(row.opt_help),
                    "python_type": str(row.opt_type) if row.opt_type else "str",
                    "default": str(row.opt_default) if row.opt_default else None,
                    "required": str(row.required).lower() == "true" if row.required else False,
                }
            )

        return options

    def _get_extended_help(self, cmd_uri: str) -> str | None:
        """Get extended help text for a command, if available."""
        query = f"""
        PREFIX cli: <urn:kgc:cli:>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?ext_help
        WHERE {{
            <{cmd_uri}> cli:extendedHelp ?ext_help .
        }}
        """
        results = self.graph.query(query)
        for row in results:
            return str(row.ext_help)
        return None

    def get_root_command(self) -> dict[str, str]:
        """Get root command metadata (from ProjectRoot)."""
        query = """
        PREFIX cli: <urn:kgc:cli:>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?name ?help
        WHERE {
            ?root a cli:Command ;
                  cli:name ?name ;
                  cli:help ?help ;
                  cli:isRoot "true"^^xsd:boolean .
        }
        LIMIT 1
        """
        results = self.graph.query(query)

        for row in results:
            return {"name": str(row.name), "help": str(row.help)}

        # Fallback
        return {"name": "kgct", "help": "KGC Technician Console"}

    def generate(self) -> str:
        """Generate CLI code and return as string."""
        # Query RDF
        root_cmd = self.get_root_command()
        commands = self.query_commands()

        # Prepare template context
        context = {
            "root_command": root_cmd,
            "commands": commands,
            "generated_at": datetime.now().isoformat(),
            "kgc_ontology_path": str(self.ontology_path),
            "app_version": "1.0.0",
        }

        # Render template
        template = self.jinja_env.get_template(self.template_path.name)
        output = template.render(context)

        return output

    def write_output(self, content: str):
        """Write generated code to output file."""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text(content)
        self.output_path.chmod(0o755)  # Make executable
        print(f"✓ Generated: {self.output_path}")

    def generate_receipt(self, content: str) -> str:
        """Generate SHA256 receipt hash of output."""
        return hashlib.sha256(content.encode()).hexdigest()


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate KGCT Typer CLI from RDF ontology")
    parser.add_argument(
        "--ontology",
        type=Path,
        default=Path(".kgc/ontology.ttl"),
        help="Path to ontology.ttl (default: .kgc/ontology.ttl)",
    )
    parser.add_argument(
        "--template",
        type=Path,
        default=Path(".kgc/projections/cli.py.j2"),
        help="Path to CLI template (default: .kgc/projections/cli.py.j2)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("personal_kgct_cli.py"),
        help="Output path (default: personal_kgct_cli.py)",
    )
    parser.add_argument(
        "--check-receipt", action="store_true", help="Verify receipt hash instead of generating"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if not args.ontology.exists():
        print(f"Error: ontology file not found: {args.ontology}", file=sys.stderr)
        sys.exit(1)

    if not args.template.exists():
        print(f"Error: template file not found: {args.template}", file=sys.stderr)
        sys.exit(1)

    try:
        gen = CLIGenerator(args.ontology, args.template, args.output)

        if args.verbose:
            print(f"Generating from: {args.ontology}")
            print(f"Template: {args.template}")
            print(f"Output: {args.output}")

        content = gen.generate()
        gen.write_output(content)

        receipt = gen.generate_receipt(content)
        if args.verbose:
            print(f"Receipt: {receipt}")

        sys.exit(0)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

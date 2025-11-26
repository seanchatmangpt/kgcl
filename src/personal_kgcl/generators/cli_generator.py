"""Render the KGCT Typer CLI from `.kgc/cli.ttl`."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timezone
from pathlib import Path
from typing import List

from jinja2 import Environment, FileSystemLoader, Template
from rdflib import RDF, Graph, Namespace

CLI = Namespace("urn:kgc:cli:")

KGC_DIR = Path(__file__).resolve().parents[3] / ".kgc"
CLI_TTL = KGC_DIR / "cli.ttl"
CLI_TEMPLATE = KGC_DIR / "projections" / "cli.py.j2"
DEFAULT_OUTPUT = Path("src/personal_kgcl/cli.py")


@dataclass(frozen=True)
class CliParam:
    name: str
    help: str
    required: bool
    repeatable: bool = False
    default: str | None = None


@dataclass(frozen=True)
class CliCommand:
    name: str
    help: str
    handler_module: str
    handler_function: str
    args: Sequence[CliParam]
    options: Sequence[CliParam]


@dataclass(frozen=True)
class GeneratedCli:
    output_path: Path
    commands: Sequence[CliCommand]
    source: str


def _load_template(path: Path) -> Template:
    env = Environment(loader=FileSystemLoader(str(path.parent)))
    return env.get_template(path.name)


def _extract_commands(graph: Graph) -> list[CliCommand]:
    commands: list[CliCommand] = []
    for node in graph.subjects(RDF.type, CLI.Command):
        name = str(graph.value(subject=node, predicate=CLI.name))
        help_text = str(graph.value(subject=node, predicate=CLI.help))
        handler_module = str(graph.value(subject=node, predicate=CLI.handlerModule))
        handler_function = str(graph.value(subject=node, predicate=CLI.handlerFunction))
        args = _extract_params(graph, node, CLI.hasArgument)
        options = _extract_params(graph, node, CLI.hasOption)
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


def _extract_params(graph: Graph, node, predicate) -> list[CliParam]:
    params: list[CliParam] = []
    for obj in graph.objects(subject=node, predicate=predicate):
        params.append(
            CliParam(
                name=str(graph.value(subject=obj, predicate=CLI.name)),
                help=str(graph.value(subject=obj, predicate=CLI.help, default="")),
                required=bool(
                    graph.value(subject=obj, predicate=CLI.isRequired, default=False)
                ),
                repeatable=bool(
                    graph.value(subject=obj, predicate=CLI.repeatable, default=False)
                ),
                default=_literal_to_python(
                    graph.value(subject=obj, predicate=CLI.default)
                ),
            )
        )
    return params


def _literal_to_python(value) -> str | None:
    if value is None:
        return None
    return str(value)


def generate_cli_module(
    cli_ttl: Path | None = None,
    template_path: Path | None = None,
    output_path: Path | None = None,
    dry_run: bool = False,
) -> GeneratedCli:
    """Render the CLI template with RDF-derived command metadata."""
    ttl_path = cli_ttl or CLI_TTL
    tpl_path = template_path or CLI_TEMPLATE
    out_path = output_path or DEFAULT_OUTPUT

    graph = Graph()
    graph.parse(ttl_path, format="turtle")

    commands = _extract_commands(graph)
    root_node = CLI["KgctRoot"]
    root_name = str(graph.value(subject=root_node, predicate=CLI.name, default="kgct"))
    root_help = str(
        graph.value(
            subject=root_node, predicate=CLI.help, default="KGC Technician Console"
        )
    )

    template = _load_template(tpl_path)
    rendered = template.render(
        generated_at=datetime.now(UTC).isoformat(),
        kgc_ontology_path=str(ttl_path),
        root_command={"name": root_name, "help": root_help},
        commands=commands,
        app_version="0.0.0",
    )

    if not dry_run:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered, encoding="utf-8")

    return GeneratedCli(output_path=out_path, commands=commands, source=rendered)


def main() -> None:
    """Console entrypoint."""
    generated = generate_cli_module()
    print(f"Generated KGCT CLI → {generated.output_path}")


if __name__ == "__main__":
    main()


__all__ = ["CliCommand", "CliParam", "GeneratedCli", "generate_cli_module"]

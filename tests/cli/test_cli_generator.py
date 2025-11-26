"""Comprehensive tests for CLI generator using Chicago School TDD.

Tests verify behavior of CLIGenerator including:
- RDF graph querying and command extraction
- Jinja2 template rendering
- Receipt hash generation
- Error handling for missing files
- Performance targets (p99 < 100ms)
"""

from __future__ import annotations

import hashlib
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from rdflib import RDF, Graph, Literal, Namespace

from kgcl.generators.cli_generator import CLIGenerator


@pytest.fixture
def sample_cli_ontology(tmp_path: Path) -> Path:
    """Create a minimal CLI ontology for testing."""
    cli_ttl = tmp_path / "cli.ttl"
    content = """
@prefix cli: <urn:kgc:cli:> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

cli:RootCmd a cli:RootCommand ;
    cli:name "kgct" ;
    cli:help "Knowledge Graph CLI Tool" .

cli:DailyBriefCmd a cli:Command ;
    cli:name "daily-brief" ;
    cli:help "Generate daily brief from events" ;
    cli:handlerModule "kgcl.cli.daily_brief" ;
    cli:handlerFunction "daily_brief" ;
    cli:hasOption cli:DailyBriefStartDateOpt ;
    cli:hasOption cli:DailyBriefEndDateOpt .

cli:DailyBriefStartDateOpt a cli:Option ;
    cli:name "start-date" ;
    cli:help "Start date (ISO 8601)" ;
    cli:dataType "str" ;
    cli:isRequired "true" .

cli:DailyBriefEndDateOpt a cli:Option ;
    cli:name "end-date" ;
    cli:help "End date (ISO 8601)" ;
    cli:dataType "str" ;
    cli:isRequired "false" ;
    cli:default "today" .

cli:QueryCmd a cli:Command ;
    cli:name "query" ;
    cli:help "Execute SPARQL query" ;
    cli:handlerModule "kgcl.cli.query" ;
    cli:handlerFunction "query" ;
    cli:hasArgument cli:QueryArg .

cli:QueryArg a cli:Argument ;
    cli:name "query_text" ;
    cli:help "SPARQL query string" ;
    cli:dataType "str" ;
    cli:isRequired "true" .
"""
    cli_ttl.write_text(content, encoding="utf-8")
    return cli_ttl


@pytest.fixture
def sample_template(tmp_path: Path) -> Path:
    """Create a minimal Jinja2 template for testing."""
    template = tmp_path / "cli.py.j2"
    content = """#!/usr/bin/env python3
# Generated at: {{ generated_at }}
# CLI: {{ root_command.name }}

import typer

app = typer.Typer(help="{{ root_command.help }}")

{% for cmd in commands %}
@app.command(name="{{ cmd.name }}")
def {{ cmd.name.replace('-', '_') }}(
    {%- for arg in cmd.args %}
    {{ arg.name }}: {{ arg.python_type }},
    {%- endfor %}
    {%- for opt in cmd.options %}
    {{ opt.name.replace('-', '_') }}: {{ opt.python_type }} = {{ opt.default or 'None' }},
    {%- endfor %}
):
    '''{{ cmd.help }}'''
    from {{ cmd.handler_module }} import {{ cmd.handler_function }}
    {{ cmd.handler_function }}(
        {%- for arg in cmd.args %}{{ arg.name }}, {% endfor %}
        {%- for opt in cmd.options %}{{ opt.name.replace('-', '_') }}={{ opt.name.replace('-', '_') }}, {% endfor %}
    )

{% endfor %}

if __name__ == "__main__":
    app()
"""
    template.write_text(content, encoding="utf-8")
    return template


def test_cli_generator_initialization_succeeds(
    sample_cli_ontology: Path, sample_template: Path, tmp_path: Path
):
    """CLIGenerator initializes successfully with valid paths."""
    output = tmp_path / "output.py"
    generator = CLIGenerator(
        ontology_path=sample_cli_ontology,
        template_path=sample_template,
        output_path=output,
    )
    assert generator.ontology_path == sample_cli_ontology
    assert generator.template_path == sample_template
    assert generator.output_path == output
    assert generator.graph is not None


def test_cli_generator_parses_rdf_graph(
    sample_cli_ontology: Path, sample_template: Path, tmp_path: Path
):
    """CLIGenerator parses RDF graph and extracts namespaces."""
    generator = CLIGenerator(
        ontology_path=sample_cli_ontology,
        template_path=sample_template,
        output_path=tmp_path / "output.py",
    )
    # Verify graph loaded triples
    assert len(generator.graph) > 0
    # Verify CLI namespace is available
    assert generator.CLI is not None
    cli_cmd = generator.CLI.Command
    assert str(cli_cmd) == "urn:kgc:cli:Command"


def test_query_commands_returns_all_commands(
    sample_cli_ontology: Path, sample_template: Path, tmp_path: Path
):
    """query_commands extracts all CLI commands from RDF."""
    generator = CLIGenerator(
        ontology_path=sample_cli_ontology,
        template_path=sample_template,
        output_path=tmp_path / "output.py",
    )
    commands = generator.query_commands()

    # Should find 2 commands: daily-brief and query
    assert len(commands) == 2

    # Verify daily-brief command structure
    daily_brief = next((c for c in commands if c["name"] == "daily-brief"), None)
    assert daily_brief is not None
    assert daily_brief["help"] == "Generate daily brief from events"
    assert daily_brief["handler_module"] == "kgcl.cli.daily_brief"
    assert daily_brief["handler_function"] == "daily_brief"
    assert len(daily_brief["options"]) == 2

    # Verify query command with argument
    query_cmd = next((c for c in commands if c["name"] == "query"), None)
    assert query_cmd is not None
    assert len(query_cmd["args"]) == 1
    assert query_cmd["args"][0]["name"] == "query_text"
    assert query_cmd["args"][0]["required"] is True


def test_query_args_extracts_positional_arguments(
    sample_cli_ontology: Path, sample_template: Path, tmp_path: Path
):
    """_query_args extracts positional arguments for a command."""
    generator = CLIGenerator(
        ontology_path=sample_cli_ontology,
        template_path=sample_template,
        output_path=tmp_path / "output.py",
    )
    commands = generator.query_commands()
    query_cmd = next((c for c in commands if c["name"] == "query"), None)

    assert len(query_cmd["args"]) == 1
    arg = query_cmd["args"][0]
    assert arg["name"] == "query_text"
    assert arg["help"] == "SPARQL query string"
    assert arg["python_type"] == "str"
    assert arg["required"] is True


def test_query_options_extracts_optional_flags(
    sample_cli_ontology: Path, sample_template: Path, tmp_path: Path
):
    """_query_options extracts optional flags for a command."""
    generator = CLIGenerator(
        ontology_path=sample_cli_ontology,
        template_path=sample_template,
        output_path=tmp_path / "output.py",
    )
    commands = generator.query_commands()
    daily_brief = next((c for c in commands if c["name"] == "daily-brief"), None)

    assert len(daily_brief["options"]) == 2

    start_opt = next(
        (o for o in daily_brief["options"] if o["name"] == "start-date"), None
    )
    assert start_opt is not None
    assert start_opt["required"] is True
    assert start_opt["python_type"] == "str"

    end_opt = next((o for o in daily_brief["options"] if o["name"] == "end-date"), None)
    assert end_opt is not None
    assert end_opt["required"] is False
    assert end_opt["default"] == "today"


def test_get_root_command_returns_metadata(
    sample_cli_ontology: Path, sample_template: Path, tmp_path: Path
):
    """get_root_command extracts root command metadata."""
    generator = CLIGenerator(
        ontology_path=sample_cli_ontology,
        template_path=sample_template,
        output_path=tmp_path / "output.py",
    )
    root = generator.get_root_command()

    assert root["name"] == "kgct"
    assert root["help"] == "Knowledge Graph CLI Tool"


def test_generate_renders_template_with_commands(
    sample_cli_ontology: Path, sample_template: Path, tmp_path: Path
):
    """Generate renders Jinja2 template with RDF-extracted commands."""
    generator = CLIGenerator(
        ontology_path=sample_cli_ontology,
        template_path=sample_template,
        output_path=tmp_path / "output.py",
    )
    output = generator.generate()

    # Verify template was rendered
    assert "import typer" in output
    assert "def daily_brief(" in output
    assert "def query(" in output
    assert "query_text: str," in output
    assert "Generated at:" in output


def test_write_output_creates_executable_file(
    sample_cli_ontology: Path, sample_template: Path, tmp_path: Path
):
    """write_output creates executable file with correct permissions."""
    output_path = tmp_path / "output.py"
    generator = CLIGenerator(
        ontology_path=sample_cli_ontology,
        template_path=sample_template,
        output_path=output_path,
    )
    content = generator.generate()
    generator.write_output(content)

    # Verify file exists
    assert output_path.exists()

    # Verify file is executable (0o755)
    import stat

    mode = output_path.stat().st_mode
    assert mode & stat.S_IXUSR  # Owner execute
    assert mode & stat.S_IRUSR  # Owner read
    assert mode & stat.S_IWUSR  # Owner write


def test_generate_receipt_produces_sha256_hash(
    sample_cli_ontology: Path, sample_template: Path, tmp_path: Path
):
    """generate_receipt produces SHA256 hash of output content."""
    generator = CLIGenerator(
        ontology_path=sample_cli_ontology,
        template_path=sample_template,
        output_path=tmp_path / "output.py",
    )
    content = generator.generate()
    receipt = generator.generate_receipt(content)

    # Verify receipt is SHA256 hex digest
    assert len(receipt) == 64  # SHA256 produces 64 hex chars
    assert all(c in "0123456789abcdef" for c in receipt)

    # Verify receipt is deterministic
    expected = hashlib.sha256(content.encode()).hexdigest()
    assert receipt == expected


def test_generator_fails_with_missing_ontology(sample_template: Path, tmp_path: Path):
    """CLIGenerator raises error when ontology file doesn't exist."""
    missing_ontology = tmp_path / "missing.ttl"
    with pytest.raises(FileNotFoundError):
        generator = CLIGenerator(
            ontology_path=missing_ontology,
            template_path=sample_template,
            output_path=tmp_path / "output.py",
        )
        generator.generate()


def test_generator_fails_with_missing_template(
    sample_cli_ontology: Path, tmp_path: Path
):
    """CLIGenerator raises error when template file doesn't exist."""
    missing_template = tmp_path / "missing.j2"
    with pytest.raises(Exception):  # Jinja2 raises TemplateNotFound
        generator = CLIGenerator(
            ontology_path=sample_cli_ontology,
            template_path=missing_template,
            output_path=tmp_path / "output.py",
        )
        generator.generate()


def test_generator_handles_empty_ontology(sample_template: Path, tmp_path: Path):
    """CLIGenerator handles empty ontology gracefully."""
    empty_ontology = tmp_path / "empty.ttl"
    empty_ontology.write_text("", encoding="utf-8")

    generator = CLIGenerator(
        ontology_path=empty_ontology,
        template_path=sample_template,
        output_path=tmp_path / "output.py",
    )
    commands = generator.query_commands()

    # Should return empty list for no commands
    assert commands == []


@pytest.mark.performance
def test_generator_meets_performance_target(
    sample_cli_ontology: Path, sample_template: Path, tmp_path: Path
):
    """CLIGenerator generates output within performance target (p99 < 100ms)."""
    import time

    generator = CLIGenerator(
        ontology_path=sample_cli_ontology,
        template_path=sample_template,
        output_path=tmp_path / "output.py",
    )

    start = time.perf_counter()
    output = generator.generate()
    elapsed_ms = (time.perf_counter() - start) * 1000

    # Performance target: p99 < 100ms for generation
    assert elapsed_ms < 100.0, f"Generation took {elapsed_ms:.2f}ms, expected <100ms"
    assert len(output) > 0


@pytest.mark.integration
def test_full_pipeline_generates_valid_python_file(
    sample_cli_ontology: Path, sample_template: Path, tmp_path: Path
):
    """Full pipeline generates syntactically valid Python file."""
    output_path = tmp_path / "cli.py"
    generator = CLIGenerator(
        ontology_path=sample_cli_ontology,
        template_path=sample_template,
        output_path=output_path,
    )

    content = generator.generate()
    generator.write_output(content)
    receipt = generator.generate_receipt(content)

    # Verify file exists and is non-empty
    assert output_path.exists()
    assert output_path.stat().st_size > 0

    # Verify Python syntax is valid
    import ast

    code = output_path.read_text(encoding="utf-8")
    try:
        ast.parse(code)
    except SyntaxError as e:
        pytest.fail(f"Generated code has syntax errors: {e}")

    # Verify receipt is correct
    expected_receipt = hashlib.sha256(content.encode()).hexdigest()
    assert receipt == expected_receipt


def test_cli_generator_default_fallback_for_missing_root(
    sample_template: Path, tmp_path: Path
):
    """CLIGenerator provides default root command when RDF has none."""
    # Create ontology without RootCommand
    ontology = tmp_path / "cli.ttl"
    ontology.write_text(
        """
@prefix cli: <urn:kgc:cli:> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

cli:TestCmd a cli:Command ;
    cli:name "test" ;
    cli:help "Test command" ;
    cli:handlerModule "test" ;
    cli:handlerFunction "test" .
""",
        encoding="utf-8",
    )

    generator = CLIGenerator(
        ontology_path=ontology,
        template_path=sample_template,
        output_path=tmp_path / "output.py",
    )
    root = generator.get_root_command()

    # Should return fallback defaults
    assert root["name"] == "kgct"
    assert root["help"] == "KGC Technician Console"

"""YAWL CLI commands.

kgcl yawl <noun> <verb> - YAWL workflow engine operations.

Nouns:
  spec    - Specification management
  case    - Case/instance management
  work    - Work item management
  resource - Resource/participant management
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
yawl = typer.Typer(help="YAWL workflow engine operations", no_args_is_help=True)

# Sub-command groups
spec_app = typer.Typer(help="Specification management", no_args_is_help=True)
case_app = typer.Typer(help="Case/instance management", no_args_is_help=True)
work_app = typer.Typer(help="Work item management", no_args_is_help=True)
resource_app = typer.Typer(help="Resource/participant management", no_args_is_help=True)

yawl.add_typer(spec_app, name="spec")
yawl.add_typer(case_app, name="case")
yawl.add_typer(work_app, name="work")
yawl.add_typer(resource_app, name="resource")


# ============================================================================
# Specification Commands
# ============================================================================


@spec_app.command("load")
def spec_load(file: Annotated[Path, typer.Argument(exists=True, help="YAWL specification file (.yawl)")]) -> None:
    """Load a YAWL specification from file.

    Examples
    --------
    $ kgcl yawl spec load workflow.yawl
    """
    from kgcl.yawl.engine.y_engine import YEngine
    from kgcl.yawl.persistence.xml_parser import XMLParser

    try:
        parser = XMLParser()
        specification = parser.parse(file)

        console.print(f"[green]✓[/] Loaded specification: {specification.id}")
        console.print(f"  URI: {specification.uri}")
        console.print(f"  Version: {specification.version}")
        console.print(f"  Root Net: {specification.root_net.id if specification.root_net else 'None'}")

        # Show nets
        if specification.decompositions:
            console.print(f"\n[bold]Decompositions:[/] {len(specification.decompositions)}")
            for decomp in list(specification.decompositions.values())[:5]:
                console.print(f"  • {decomp.id}")

    except Exception as e:
        console.print(f"[red]Error loading specification:[/] {e}")
        raise typer.Exit(code=1)


@spec_app.command("list")
def spec_list() -> None:
    """List all loaded specifications.

    Examples
    --------
    $ kgcl yawl spec list
    """
    from kgcl.yawl.engine.y_engine import YEngine

    try:
        engine = YEngine()
        specs = engine.get_specifications()

        if not specs:
            console.print("[yellow]No specifications loaded[/]")
            return

        table = Table(title="YAWL Specifications")
        table.add_column("ID", style="cyan")
        table.add_column("URI", style="blue")
        table.add_column("Version", style="green")
        table.add_column("Status", style="yellow")

        for spec in specs:
            table.add_row(spec.id, spec.uri, spec.version, spec.status.name)

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(code=1)


@spec_app.command("inspect")
def spec_inspect(spec_id: str = typer.Argument(..., help="Specification ID")) -> None:
    """Inspect specification details.

    Examples
    --------
    $ kgcl yawl spec inspect my-workflow
    """
    from kgcl.yawl.engine.y_engine import YEngine

    try:
        engine = YEngine()
        spec = engine.get_specification(spec_id)

        if not spec:
            console.print(f"[yellow]Specification not found: {spec_id}[/]")
            raise typer.Exit(code=1)

        console.print(Panel.fit(f"[bold]Specification: {spec.id}[/]", border_style="blue"))
        console.print(f"URI: {spec.uri}")
        console.print(f"Version: {spec.version}")
        console.print(f"Status: {spec.status.name}")
        console.print(f"Root Net: {spec.root_net.id if spec.root_net else 'None'}")

        if spec.decompositions:
            console.print(f"\n[bold]Decompositions:[/] {len(spec.decompositions)}")
            for decomp_id, decomp in list(spec.decompositions.items())[:10]:
                console.print(f"  • {decomp_id}: {type(decomp).__name__}")

    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(code=1)


# ============================================================================
# Case Commands
# ============================================================================


@case_app.command("launch")
def case_launch(
    spec_id: str = typer.Argument(..., help="Specification ID"),
    case_id: Annotated[str | None, typer.Option("--case-id", "-c", help="Custom case ID")] = None,
) -> None:
    """Launch a new case from a specification.

    Examples
    --------
    $ kgcl yawl case launch my-workflow
    $ kgcl yawl case launch my-workflow --case-id case-001
    """
    from kgcl.yawl.engine.y_engine import YEngine

    try:
        engine = YEngine()
        case = engine.launch_case(spec_id, case_id)

        console.print(f"[green]✓[/] Launched case: {case.case_id}")
        console.print(f"  Specification: {spec_id}")
        console.print(f"  Status: {case.status.name}")

    except Exception as e:
        console.print(f"[red]Error launching case:[/] {e}")
        raise typer.Exit(code=1)


@case_app.command("list")
def case_list() -> None:
    """List all active cases.

    Examples
    --------
    $ kgcl yawl case list
    """
    from kgcl.yawl.engine.y_engine import YEngine

    try:
        engine = YEngine()
        cases = engine.get_cases()

        if not cases:
            console.print("[yellow]No active cases[/]")
            return

        table = Table(title="YAWL Cases")
        table.add_column("Case ID", style="cyan")
        table.add_column("Specification", style="blue")
        table.add_column("Status", style="green")
        table.add_column("Start Time", style="yellow")

        for case in cases:
            table.add_row(
                case.case_id, case.specification_id, case.status.name, str(case.start_time) if case.start_time else "-"
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(code=1)


@case_app.command("inspect")
def case_inspect(case_id: str = typer.Argument(..., help="Case ID")) -> None:
    """Inspect case details.

    Examples
    --------
    $ kgcl yawl case inspect case-001
    """
    from kgcl.yawl.engine.y_engine import YEngine

    try:
        engine = YEngine()
        case = engine.get_case(case_id)

        if not case:
            console.print(f"[yellow]Case not found: {case_id}[/]")
            raise typer.Exit(code=1)

        console.print(Panel.fit(f"[bold]Case: {case.case_id}[/]", border_style="blue"))
        console.print(f"Specification: {case.specification_id}")
        console.print(f"Status: {case.status.name}")
        console.print(f"Start Time: {case.start_time}")
        if case.completion_time:
            console.print(f"Completion Time: {case.completion_time}")

        # Show case data
        if case.data:
            console.print("\n[bold]Case Data:[/]")
            for key, value in list(case.data.items())[:10]:
                console.print(f"  {key}: {value}")

    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(code=1)


@case_app.command("cancel")
def case_cancel(case_id: str = typer.Argument(..., help="Case ID to cancel")) -> None:
    """Cancel a running case.

    Examples
    --------
    $ kgcl yawl case cancel case-001
    """
    from kgcl.yawl.engine.y_engine import YEngine

    try:
        engine = YEngine()
        engine.cancel_case(case_id)

        console.print(f"[green]✓[/] Cancelled case: {case_id}")

    except Exception as e:
        console.print(f"[red]Error cancelling case:[/] {e}")
        raise typer.Exit(code=1)


# ============================================================================
# Work Item Commands
# ============================================================================


@work_app.command("list")
def work_list(
    case_id: Annotated[str | None, typer.Option("--case", "-c", help="Filter by case ID")] = None,
    status: Annotated[
        str | None, typer.Option("--status", "-s", help="Filter by status (enabled/executing/completed)")
    ] = None,
) -> None:
    """List work items.

    Examples
    --------
    $ kgcl yawl work list
    $ kgcl yawl work list --case case-001
    $ kgcl yawl work list --status enabled
    """
    from kgcl.yawl.engine.y_engine import YEngine

    try:
        engine = YEngine()
        work_items = engine.get_work_items(case_id=case_id, status=status)

        if not work_items:
            console.print("[yellow]No work items found[/]")
            return

        table = Table(title="Work Items")
        table.add_column("ID", style="cyan")
        table.add_column("Case", style="blue")
        table.add_column("Task", style="green")
        table.add_column("Status", style="yellow")

        for item in work_items:
            table.add_row(item.item_id, item.case_id, item.task_id, item.status.name)

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(code=1)


@work_app.command("start")
def work_start(item_id: str = typer.Argument(..., help="Work item ID")) -> None:
    """Start a work item.

    Examples
    --------
    $ kgcl yawl work start item-001
    """
    from kgcl.yawl.engine.y_engine import YEngine

    try:
        engine = YEngine()
        engine.start_work_item(item_id)

        console.print(f"[green]✓[/] Started work item: {item_id}")

    except Exception as e:
        console.print(f"[red]Error starting work item:[/] {e}")
        raise typer.Exit(code=1)


@work_app.command("complete")
def work_complete(
    item_id: str = typer.Argument(..., help="Work item ID"),
    data: Annotated[str | None, typer.Option("--data", "-d", help="JSON data for completion")] = None,
) -> None:
    """Complete a work item.

    Examples
    --------
    $ kgcl yawl work complete item-001
    $ kgcl yawl work complete item-001 --data '{"result": "success"}'
    """
    import json

    from kgcl.yawl.engine.y_engine import YEngine

    try:
        engine = YEngine()

        completion_data = {}
        if data:
            completion_data = json.loads(data)

        engine.complete_work_item(item_id, completion_data)

        console.print(f"[green]✓[/] Completed work item: {item_id}")

    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON data:[/] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Error completing work item:[/] {e}")
        raise typer.Exit(code=1)


# ============================================================================
# Resource Commands
# ============================================================================


@resource_app.command("list")
def resource_list() -> None:
    """List all participants.

    Examples
    --------
    $ kgcl yawl resource list
    """
    from kgcl.yawl.engine.y_engine import YEngine

    try:
        engine = YEngine()
        participants = engine.get_participants()

        if not participants:
            console.print("[yellow]No participants found[/]")
            return

        table = Table(title="Participants")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="blue")
        table.add_column("Roles", style="green")

        for p in participants:
            roles = ", ".join(p.roles) if p.roles else "-"
            table.add_row(p.id, p.name, roles)

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(code=1)


@resource_app.command("add")
def resource_add(
    participant_id: Annotated[str, typer.Argument(help="Participant ID")],
    name: Annotated[str, typer.Argument(help="Participant name")],
    roles: Annotated[list[str] | None, typer.Option("--role", "-r", help="Role (can specify multiple)")] = None,
) -> None:
    """Add a new participant.

    Examples
    --------
    $ kgcl yawl resource add user123 "John Doe" --role admin --role developer
    """
    from kgcl.yawl.engine.y_engine import YEngine
    from kgcl.yawl.resources.y_resource import YParticipant

    try:
        engine = YEngine()

        participant = YParticipant(id=participant_id, name=name, roles=set(roles) if roles else set())

        engine.add_participant(participant)

        console.print(f"[green]✓[/] Added participant: {participant_id}")
        console.print(f"  Name: {name}")
        console.print(f"  Roles: {', '.join(roles) if roles else 'None'}")

    except Exception as e:
        console.print(f"[red]Error adding participant:[/] {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    yawl()

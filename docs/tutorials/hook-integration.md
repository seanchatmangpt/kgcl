# Hook System Integration Example

## Overview

This document demonstrates how to integrate the KGC hook orchestration system with generators for automated projection updates.

## Complete Hook Lifecycle

### 1. Load Hooks from RDF

```python
from pathlib import Path
from rdflib import Graph
from kgcl.hooks import HookLoader, HookRegistry, HookOrchestrator, HookScheduler

# Load RDF graph
graph = Graph()
graph.parse(".kgc/ontology.ttl")
graph.parse(".kgc/hooks.ttl")

# Initialize hook system
hooks_file = Path(".kgc/hooks.ttl")
registry = HookRegistry(graph, hooks_file)
orchestrator = HookOrchestrator(graph, hooks_file)
scheduler = HookScheduler(graph, orchestrator, registry)

# Check loaded hooks
print(f"Loaded {len(registry.get_active_hooks())} active hooks")
for hook in registry.get_active_hooks():
    print(f"  - {hook.definition.name}: {hook.definition.trigger_label}")
```

### 2. Register Effect Handlers

```python
from kgcl.hooks import ExecutionContext
from kgcl.generators import (
    AgendaGenerator,
    QualityReportGenerator,
    ConflictReportGenerator,
    StaleItemsGenerator,
)

# Handler for IngestHook → AgendaGenerator
def handle_ingest_agenda(ctx: ExecutionContext) -> dict:
    """Generate agenda when data is ingested."""
    generator = AgendaGenerator(ctx.graph)
    agenda = generator.generate()

    # Write to target file
    target = Path(ctx.effect.target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(agenda)

    return {
        "generator": "AgendaGenerator",
        "output_file": str(target),
        "lines": len(agenda.splitlines()),
        "success": True
    }

# Handler for ValidationFailureHook → QualityReportGenerator
def handle_validation_failure(ctx: ExecutionContext) -> dict:
    """Generate quality report on validation failure."""
    generator = QualityReportGenerator(ctx.graph)
    report = generator.generate()

    target = Path(ctx.effect.target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report)

    return {
        "generator": "QualityReportGenerator",
        "output_file": str(target),
        "violation_count": ctx.event_data.get("violation_count", 0),
        "success": True
    }

# Handler for ConflictDetectionHook → ConflictReportGenerator
def handle_conflict_detection(ctx: ExecutionContext) -> dict:
    """Generate conflict report when calendar is updated."""
    generator = ConflictReportGenerator(ctx.graph)
    report = generator.generate()

    target = Path(ctx.effect.target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report)

    return {
        "generator": "ConflictReportGenerator",
        "output_file": str(target),
        "conflict_count": report.count("CONFLICT:"),
        "success": True
    }

# Register handlers
orchestrator.register_handler("IngestHook", handle_ingest_agenda)
orchestrator.register_handler("ValidationFailureHook", handle_validation_failure)
orchestrator.register_handler("ConflictDetectionHook", handle_conflict_detection)
```

### 3. Trigger Events

```python
# Trigger data ingest event
result = orchestrator.trigger_event(
    "urn:kgc:apple:DataIngested",
    event_data={
        "source": "Calendar.app",
        "items_ingested": 42,
        "timestamp": "2025-11-24T23:30:00Z"
    },
    actor="kgc-ingest-cli"
)

print(f"Executed {len(result.receipts)} effects")
for receipt in result.receipts:
    print(f"  - {receipt.hook_id}: {receipt.duration_ms:.2f}ms")
    if receipt.handler_result:
        print(f"    Output: {receipt.handler_result.get('output_file')}")

# Trigger validation failure
result = orchestrator.trigger_event(
    "urn:kgc:apple:ValidationFailed",
    event_data={
        "violation_count": 5,
        "severity": "warning",
        "shapes": ["EventShape", "ReminderShape"]
    },
    actor="kgc-validate-cli"
)

# Trigger calendar update
result = orchestrator.trigger_event(
    "urn:kgc:apple:CalendarDataUpdated",
    event_data={
        "events_added": 3,
        "events_modified": 1
    },
    actor="kgc-ingest-cli"
)
```

### 4. Schedule Timed Hooks

```python
# Start scheduler for timed hooks (daily/weekly)
scheduler.start()

# Get schedule summary
summary = scheduler.get_schedule_summary()
print(f"Scheduled {summary['total_timed_hooks']} timed hooks")

for schedule in summary["schedules"]:
    print(f"  - {schedule['hook_name']}")
    print(f"    Cron: {schedule['cron_schedule']}")
    print(f"    Next: {schedule['next_execution']}")
    print(f"    Runs: {schedule['execution_count']}")

# Manually trigger a timed hook
result = scheduler.trigger_hook_manually(
    "DailyReviewHook",
    event_data={"manual_trigger": True}
)

# View execution history
history = scheduler.get_execution_history("DailyReviewHook", limit=5)
for execution in history:
    print(f"  - {execution.scheduled_time}: {execution.result.success}")
```

### 5. Hook Chaining Example

```python
# Handler that triggers another hook
def handle_ontology_change(ctx: ExecutionContext) -> dict:
    """When ontology changes, regenerate CLI and trigger other hooks."""
    from kgcl.generators import CLIGenerator

    generator = CLIGenerator(ctx.graph)
    cli_code = generator.generate()

    target = Path(ctx.effect.target)
    target.write_text(cli_code)

    # Return trigger for other hooks
    return {
        "generator": "CLIGenerator",
        "output_file": str(target),
        "success": True,
        "trigger": "urn:kgc:apple:CLIRegenerated"  # Chain to other hooks
    }

orchestrator.register_handler("OntologyChangeHook", handle_ontology_change)

# Triggering OntologyChangeHook will automatically chain to CLIRegenerated hooks
result = orchestrator.trigger_event(
    "urn:kgc:apple:OntologyModified",
    event_data={"file": "ontology.ttl"},
    actor="kgc-ontology-editor"
)

print(f"Chained hooks: {result.triggered_hooks}")
```

## Integration with CLI

### kgct Command Integration

```python
# In kgct CLI command
import click
from kgcl.hooks import HookOrchestrator

@click.command()
@click.option("--source", required=True)
def ingest(source: str):
    """Ingest Apple ecosystem data and trigger hooks."""
    # Load graph and orchestrator
    graph = load_graph()
    orchestrator = setup_orchestrator(graph)

    # Perform ingestion
    items = ingest_apple_data(source)

    # Trigger hooks automatically
    result = orchestrator.trigger_event(
        "urn:kgc:apple:DataIngested",
        event_data={
            "source": source,
            "items_ingested": len(items),
            "timestamp": datetime.now().isoformat()
        },
        actor="kgct-ingest"
    )

    # Report results
    click.echo(f"Ingested {len(items)} items")
    click.echo(f"Triggered {len(result.receipts)} hook effects")

    for receipt in result.receipts:
        if receipt.handler_result:
            output = receipt.handler_result.get("output_file")
            click.echo(f"  - Generated: {output}")
```

## Error Handling and Resilience

```python
# Configure orchestrator for resilience
orchestrator = HookOrchestrator(
    graph,
    hooks_file,
    continue_on_error=True  # Continue even if one effect fails
)

# Handle errors in effect handler
def resilient_handler(ctx: ExecutionContext) -> dict:
    """Effect handler with error recovery."""
    try:
        generator = AgendaGenerator(ctx.graph)
        output = generator.generate()
        return {"success": True, "output": output}

    except Exception as e:
        logger.error(f"Generation failed: {e}")
        # Return partial result
        return {
            "success": False,
            "error": str(e),
            "fallback": "Error generating agenda - see logs"
        }

# Check receipt for errors
for receipt in result.receipts:
    if receipt.error:
        print(f"Effect failed: {receipt.hook_id}")
        print(f"  Error: {receipt.error}")
        print(f"  Stack: {receipt.stack_trace}")
```

## Performance Monitoring

```python
# Track hook execution performance
for receipt in result.receipts:
    print(f"Hook: {receipt.hook_id}")
    print(f"  Duration: {receipt.duration_ms:.2f}ms")
    print(f"  Memory delta: {receipt.memory_delta_bytes} bytes")

    if receipt.duration_ms > 1000:
        logger.warning(f"Slow hook execution: {receipt.hook_id}")

# Registry statistics
stats = registry.get_statistics()
print(f"Active hooks: {stats['active_hooks']}/{stats['total_hooks']}")
print(f"Error hooks: {stats['error_hooks']}")
```

## Complete Example: Daily Briefing Workflow

```python
from datetime import datetime
from pathlib import Path
from rdflib import Graph
from kgcl.hooks import HookLoader, HookRegistry, HookOrchestrator, HookScheduler
from kgcl.generators import AgendaGenerator

def setup_hook_system(graph: Graph) -> tuple:
    """Initialize complete hook system."""
    hooks_file = Path(".kgc/hooks.ttl")

    registry = HookRegistry(graph, hooks_file)
    orchestrator = HookOrchestrator(graph, hooks_file)
    scheduler = HookScheduler(graph, orchestrator, registry)

    # Register handlers for all hooks
    register_all_handlers(orchestrator, graph)

    return registry, orchestrator, scheduler

def register_all_handlers(orchestrator: HookOrchestrator, graph: Graph):
    """Register all effect handlers."""

    def generate_daily_briefing(ctx: ExecutionContext) -> dict:
        generator = AgendaGenerator(graph)
        briefing = generator.generate()

        # Write to dated file
        date = datetime.now().strftime("%Y-%m-%d")
        target = Path(f"docs/briefings/daily-{date}.md")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(briefing)

        return {"output_file": str(target), "success": True}

    orchestrator.register_handler("DailyReviewHook", generate_daily_briefing)
    # ... register other handlers

# Usage
graph = Graph()
graph.parse(".kgc/ontology.ttl")
graph.parse(".kgc/hooks.ttl")

registry, orchestrator, scheduler = setup_hook_system(graph)

# Start scheduler (runs daily at 6am)
scheduler.start()

# Or trigger manually
result = scheduler.trigger_hook_manually("DailyReviewHook")
print(f"Generated briefing: {result.receipts[0].handler_result['output_file']}")
```

## Next Steps

1. **Integration Testing**: Test hook execution in end-to-end workflows
2. **CLI Integration**: Add hook triggers to all kgct commands
3. **Monitoring**: Add observability for hook execution metrics
4. **Documentation**: Generate hook documentation from RDF metadata
5. **Web UI**: Create dashboard for hook status and history

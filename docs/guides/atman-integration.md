# Atman Engine Integration Guide

## Overview

This guide demonstrates how the Atman Engine integrates with other KGCL subsystems to form a complete knowledge graph platform.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  CLI Layer                                                  │
│  - daily-brief, weekly-retro, query                         │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│  Atman Engine (Core Mutation Layer)                         │
│  - QuadDelta → μ → Receipt                                  │
│  - Hook System (PRE/POST)                                   │
│  - Lockchain Provenance                                     │
└──────┬───────────┬────────────┬─────────────┬───────────────┘
       │           │            │             │
┌──────▼──────┐ ┌──▼─────┐ ┌────▼────┐ ┌─────▼─────────┐
│  KGCL Hooks │ │ UNRDF  │ │  OTEL   │ │ DSPy Runtime  │
│  System     │ │ Engine │ │ Tracing │ │ (Ollama)      │
└─────────────┘ └────────┘ └─────────┘ └───────────────┘
```

## 1. Integration with KGCL Hooks System

The Atman engine's hook system can trigger KGCL's broader hook ecosystem.

### Bridge Pattern

```python
from kgcl.engine import Atman, KnowledgeHook, HookMode, QuadDelta
from kgcl.hooks import HookRegistry, HookExecutionPipeline
from kgcl.hooks.value_objects import Hook, HookContext, HookPhase

class AtmanKGCLBridge:
    """Bridge Atman hooks to KGCL hook system."""

    def __init__(self):
        self.atman_engine = Atman()
        self.kgcl_registry = HookRegistry()

    async def atman_pre_hook(self, store, delta, ctx) -> bool:
        """Execute KGCL PRE hooks before Atman mutation."""
        kgcl_context = HookContext(
            phase=HookPhase.PRE_TASK,
            metadata={
                "tx_id": ctx.tx_id,
                "actor": ctx.actor,
                "additions": len(delta.additions),
                "removals": len(delta.removals),
            },
        )

        # Execute KGCL hooks
        pipeline = HookExecutionPipeline(self.kgcl_registry)
        result = await pipeline.execute_phase(HookPhase.PRE_TASK, kgcl_context)

        # Only allow if KGCL hooks succeeded
        return result.success

    async def atman_post_hook(self, store, delta, ctx) -> bool:
        """Execute KGCL POST hooks after Atman mutation."""
        kgcl_context = HookContext(
            phase=HookPhase.POST_TASK,
            metadata={
                "tx_id": ctx.tx_id,
                "actor": ctx.actor,
                "committed": True,
            },
        )

        pipeline = HookExecutionPipeline(self.kgcl_registry)
        await pipeline.execute_phase(HookPhase.POST_TASK, kgcl_context)

        return True

    def register_bridge(self):
        """Register bridge hooks in Atman engine."""
        pre_hook = KnowledgeHook(
            "kgcl-pre-bridge",
            HookMode.PRE,
            self.atman_pre_hook,
            priority=200,
        )
        post_hook = KnowledgeHook(
            "kgcl-post-bridge",
            HookMode.POST,
            self.atman_post_hook,
            priority=100,
        )

        self.atman_engine.register_hook(pre_hook)
        self.atman_engine.register_hook(post_hook)

    async def apply(self, delta: QuadDelta, actor: str = "system"):
        """Apply transaction through both systems."""
        return await self.atman_engine.apply(delta, actor=actor)

# Usage
bridge = AtmanKGCLBridge()
bridge.register_bridge()

delta = QuadDelta(additions=[("urn:a", "urn:b", "urn:c")])
receipt = await bridge.apply(delta, actor="user:alice")
```

### Event-Driven Hook Triggering

```python
from kgcl.engine import Atman, KnowledgeHook, HookMode
from kgcl.hooks import HookRegistry

class EventDrivenAtman:
    """Atman engine with event-driven KGCL hooks."""

    def __init__(self):
        self.engine = Atman()
        self.hook_registry = HookRegistry()
        self._setup_event_hooks()

    def _setup_event_hooks(self):
        """Setup hooks that emit KGCL events."""

        async def emit_mutation_event(store, delta, ctx) -> bool:
            """Emit graph.mutation event."""
            await self.hook_registry.trigger(
                "graph.mutation",
                {
                    "tx_id": ctx.tx_id,
                    "actor": ctx.actor,
                    "additions": delta.additions,
                    "removals": delta.removals,
                    "timestamp": ctx.timestamp,
                },
            )
            return True

        async def emit_commit_event(store, delta, ctx) -> bool:
            """Emit graph.commit event."""
            await self.hook_registry.trigger(
                "graph.commit",
                {
                    "tx_id": ctx.tx_id,
                    "merkle_root": self.engine.tip_hash,
                },
            )
            return True

        self.engine.register_hook(
            KnowledgeHook("emit-mutation", HookMode.PRE, emit_mutation_event)
        )
        self.engine.register_hook(
            KnowledgeHook("emit-commit", HookMode.POST, emit_commit_event)
        )

    async def apply(self, delta, actor="system"):
        """Apply with event emission."""
        return await self.engine.apply(delta, actor=actor)

# Usage
event_engine = EventDrivenAtman()

# Register KGCL event listeners
@event_engine.hook_registry.on("graph.mutation")
async def log_mutations(event):
    print(f"Mutation by {event['actor']}: +{len(event['additions'])} -{len(event['removals'])}")

delta = QuadDelta(additions=[("urn:a", "urn:b", "urn:c")])
await event_engine.apply(delta, actor="user:alice")
```

## 2. Integration with UNRDF Engine

The UNRDF engine provides SPARQL and RDF processing. Atman mutations can trigger UNRDF workflows.

### SPARQL Validation Hook

```python
from kgcl.engine import Atman, KnowledgeHook, HookMode, QuadDelta
from kgcl.unrdf_engine import UnrdfEngine
from rdflib import Dataset

class SparqlValidatedAtman:
    """Atman with SPARQL-based validation."""

    def __init__(self):
        self.atman = Atman()
        self.unrdf = UnrdfEngine()
        self._setup_validation()

    def _setup_validation(self):
        """Setup SPARQL validation hooks."""

        async def validate_with_sparql(store: Dataset, delta, ctx) -> bool:
            """Validate using SPARQL ASK queries."""
            # Example: Ensure all entities have rdf:type
            for subj, pred, obj in delta.additions:
                if pred == "schema:name":
                    # Check if entity has type
                    ask_query = f"""
                    ASK {{
                        <{subj}> a ?type .
                    }}
                    """
                    result = store.query(ask_query)

                    if not result.askAnswer:
                        # No type found, check if adding in same delta
                        has_type_in_delta = any(
                            s == subj and p == "rdf:type"
                            for s, p, o in delta.additions
                        )
                        if not has_type_in_delta:
                            return False  # Block: no type

            return True

        self.atman.register_hook(
            KnowledgeHook(
                "sparql-validator",
                HookMode.PRE,
                validate_with_sparql,
                priority=150,
            )
        )

    async def apply(self, delta, actor="system"):
        """Apply with SPARQL validation."""
        return await self.atman.apply(delta, actor=actor)

# Usage
validated_engine = SparqlValidatedAtman()

# This will be blocked (no rdf:type)
delta_invalid = QuadDelta(
    additions=[("urn:entity:123", "schema:name", "Alice")]
)
receipt = await validated_engine.apply(delta_invalid)
assert receipt.committed is False

# This will succeed
delta_valid = QuadDelta(
    additions=[
        ("urn:entity:123", "rdf:type", "schema:Person"),
        ("urn:entity:123", "schema:name", "Alice"),
    ]
)
receipt = await validated_engine.apply(delta_valid)
assert receipt.committed is True
```

### UNRDF Ingestion Pipeline

```python
from kgcl.engine import Atman, QuadDelta
from kgcl.unrdf_engine import UnrdfEngine
from kgcl.unrdf_engine.ingestion import IngestionPipeline

class UnrdfAtmanPipeline:
    """Ingest data through UNRDF into Atman."""

    def __init__(self):
        self.atman = Atman()
        self.unrdf = UnrdfEngine()
        self.ingestion = IngestionPipeline(self.unrdf)

    async def ingest_and_mutate(self, data_source: str):
        """Ingest data and apply to Atman."""
        # 1. Parse with UNRDF
        triples = await self.ingestion.parse_source(data_source)

        # 2. Convert to QuadDelta batches
        batch_size = 64
        receipts = []

        for i in range(0, len(triples), batch_size):
            batch = triples[i:i+batch_size]
            delta = QuadDelta(additions=batch)
            receipt = await self.atman.apply(delta, actor="unrdf:ingestion")

            if not receipt.committed:
                raise RuntimeError(f"Batch {i//batch_size} failed: {receipt.error}")

            receipts.append(receipt)

        return receipts

# Usage
pipeline = UnrdfAtmanPipeline()
receipts = await pipeline.ingest_and_mutate("data/ontology.ttl")
print(f"Ingested {len(receipts)} batches")
```

## 3. Integration with OpenTelemetry

The Atman engine can emit OpenTelemetry spans and metrics.

### OTEL Instrumentation Hook

```python
from kgcl.engine import Atman, KnowledgeHook, HookMode, QuadDelta
from kgcl.observability.tracing import get_tracer
from kgcl.observability.metrics import get_meter
from opentelemetry import trace, metrics

class OTELInstrumentedAtman:
    """Atman with full OpenTelemetry instrumentation."""

    def __init__(self):
        self.atman = Atman()
        self.tracer = get_tracer(__name__)
        self.meter = get_meter(__name__)

        # Metrics
        self.mutation_counter = self.meter.create_counter(
            "atman.mutations.total",
            description="Total mutations applied",
            unit="1",
        )
        self.mutation_duration = self.meter.create_histogram(
            "atman.mutations.duration",
            description="Mutation duration",
            unit="ms",
        )

        self._setup_instrumentation()

    def _setup_instrumentation(self):
        """Setup OTEL hooks."""

        async def trace_mutation(store, delta, ctx) -> bool:
            """Emit OTEL span for mutation."""
            with self.tracer.start_as_current_span("atman.mutation") as span:
                span.set_attribute("tx_id", ctx.tx_id)
                span.set_attribute("actor", ctx.actor)
                span.set_attribute("additions.count", len(delta.additions))
                span.set_attribute("removals.count", len(delta.removals))

                # Add triples as events
                for i, (s, p, o) in enumerate(delta.additions[:5]):  # First 5
                    span.add_event(
                        "triple.add",
                        attributes={"subject": s, "predicate": p, "object": o},
                    )

            return True

        async def record_metrics(store, delta, ctx) -> bool:
            """Record OTEL metrics."""
            # Count mutations
            self.mutation_counter.add(
                1,
                attributes={
                    "actor": ctx.actor,
                    "type": "addition" if delta.additions else "removal",
                },
            )

            return True

        self.atman.register_hook(
            KnowledgeHook("otel-tracer", HookMode.POST, trace_mutation, priority=200)
        )
        self.atman.register_hook(
            KnowledgeHook("otel-metrics", HookMode.POST, record_metrics, priority=100)
        )

    async def apply(self, delta, actor="system"):
        """Apply with OTEL instrumentation."""
        with self.tracer.start_as_current_span("atman.apply") as span:
            receipt = await self.atman.apply(delta, actor=actor)

            # Record metrics
            self.mutation_duration.record(
                receipt.duration_ns / 1_000_000,  # Convert to ms
                attributes={"committed": str(receipt.committed)},
            )

            # Set span attributes
            span.set_attribute("committed", receipt.committed)
            span.set_attribute("merkle_root", receipt.merkle_root[:16])
            span.set_attribute("duration_ms", receipt.duration_ns / 1_000_000)

            if receipt.error:
                span.set_status(trace.Status(trace.StatusCode.ERROR, receipt.error))

            return receipt

# Usage
otel_engine = OTELInstrumentedAtman()

delta = QuadDelta(additions=[("urn:a", "urn:b", "urn:c")])
receipt = await otel_engine.apply(delta, actor="user:alice")
# OTEL spans and metrics automatically emitted
```

### Distributed Tracing

```python
from kgcl.engine import Atman, QuadDelta
from kgcl.observability.tracing import get_tracer
from opentelemetry import trace
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

class DistributedAtman:
    """Atman with distributed tracing support."""

    def __init__(self):
        self.atman = Atman()
        self.tracer = get_tracer(__name__)
        self.propagator = TraceContextTextMapPropagator()

    async def apply_with_context(
        self, delta: QuadDelta, actor: str, trace_context: dict | None = None
    ):
        """Apply transaction with distributed trace context."""
        # Extract parent context
        if trace_context:
            ctx = self.propagator.extract(trace_context)
        else:
            ctx = trace.set_span_in_context(trace.get_current_span())

        # Create span with parent
        with self.tracer.start_as_current_span(
            "atman.distributed.apply", context=ctx
        ) as span:
            span.set_attribute("service", "atman-engine")
            span.set_attribute("actor", actor)

            # Apply mutation
            receipt = await self.atman.apply(delta, actor=actor)

            # Return receipt + trace context for downstream services
            carrier = {}
            self.propagator.inject(carrier)

            return {
                "receipt": receipt,
                "trace_context": carrier,
            }

# Usage (simulating distributed system)
distributed_engine = DistributedAtman()

# Service A creates transaction
result = await distributed_engine.apply_with_context(
    delta=QuadDelta(additions=[("urn:a", "urn:b", "urn:c")]),
    actor="service-a",
)

# Service B continues trace
result2 = await distributed_engine.apply_with_context(
    delta=QuadDelta(additions=[("urn:d", "urn:e", "urn:f")]),
    actor="service-b",
    trace_context=result["trace_context"],
)
```

## 4. Integration with CLI Commands

The Atman engine powers CLI commands like `daily-brief`, `weekly-retro`, and `query`.

### CLI Wrapper

```python
from kgcl.engine import Atman, QuadDelta
from kgcl.cli.core.app import CliApp
from kgcl.cli.core.receipts import ReceiptRenderer
import click

class AtmanCLI:
    """CLI wrapper for Atman engine."""

    def __init__(self):
        self.engine = Atman()
        self.renderer = ReceiptRenderer()

    @click.command()
    @click.option("--additions", "-a", multiple=True, help="Triple to add (s,p,o)")
    @click.option("--removals", "-r", multiple=True, help="Triple to remove (s,p,o)")
    @click.option("--actor", default="cli", help="Actor initiating transaction")
    def mutate(self, additions, removals, actor):
        """Apply mutations to knowledge graph."""
        import asyncio

        # Parse triples
        add_triples = [tuple(t.split(",")) for t in additions]
        remove_triples = [tuple(t.split(",")) for t in removals]

        delta = QuadDelta(additions=add_triples, removals=remove_triples)

        # Apply
        receipt = asyncio.run(self.engine.apply(delta, actor=actor))

        # Render receipt
        self.renderer.render(receipt)

        # Exit code
        return 0 if receipt.committed else 1

    @click.command()
    @click.argument("sparql_query")
    def query(self, sparql_query):
        """Execute SPARQL query against knowledge graph."""
        results = self.engine.store.query(sparql_query)

        for row in results:
            click.echo(row)

    @click.command()
    def status(self):
        """Show engine status."""
        click.echo(f"Triples: {len(self.engine)}")
        click.echo(f"Hooks: {len(self.engine.hooks)}")
        click.echo(f"Tip Hash: {self.engine.tip_hash[:16]}...")
        click.echo(f"Logic Hash: {self.engine.compute_logic_hash()[:16]}...")

# Register commands
cli = AtmanCLI()
app = CliApp()
app.add_command(cli.mutate)
app.add_command(cli.query)
app.add_command(cli.status)
```

**Usage:**

```bash
# Apply mutations
kgcl mutate -a "urn:a,urn:b,urn:c" -a "urn:d,urn:e,urn:f" --actor user:alice

# Query
kgcl query "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10"

# Status
kgcl status
```

### Daily Brief Integration

```python
from kgcl.engine import Atman, QuadDelta
from kgcl.cli.daily_brief import DailyBriefPipeline
from kgcl.signatures.daily_brief import DailyBriefSignature
import dspy

class AtmanDailyBrief:
    """Generate daily brief from Atman mutations."""

    def __init__(self):
        self.engine = Atman()
        self.pipeline = DailyBriefPipeline()

    async def generate_brief(self, start_date, end_date):
        """Generate brief from mutations in date range."""
        # Query mutations in range
        query = f"""
        SELECT ?tx ?actor ?timestamp
        WHERE {{
            ?tx a :Transaction ;
                :actor ?actor ;
                :timestamp ?timestamp .
            FILTER(?timestamp >= "{start_date}"^^xsd:date &&
                   ?timestamp <= "{end_date}"^^xsd:date)
        }}
        """

        results = self.engine.store.query(query)

        # Aggregate data
        mutations_by_actor = {}
        for row in results:
            actor = str(row.actor)
            mutations_by_actor.setdefault(actor, []).append(row)

        # Generate brief with DSPy
        brief = await self.pipeline.generate({
            "mutations": mutations_by_actor,
            "date_range": f"{start_date} to {end_date}",
        })

        return brief

# Usage
daily_brief = AtmanDailyBrief()
brief = await daily_brief.generate_brief("2024-01-01", "2024-01-07")
print(brief)
```

## 5. Integration with DSPy Runtime

The Atman engine can use DSPy for semantic operations.

### Semantic Validation with DSPy

```python
from kgcl.engine import Atman, KnowledgeHook, HookMode, QuadDelta
from kgcl.dspy_runtime import invoke_signature
from kgcl.signatures import ValidationSignature
import dspy

class SemanticValidatedAtman:
    """Atman with DSPy-powered semantic validation."""

    def __init__(self):
        self.atman = Atman()
        self._setup_semantic_validation()

    def _setup_semantic_validation(self):
        """Setup DSPy validation hook."""

        async def semantic_validate(store, delta, ctx) -> bool:
            """Validate using DSPy semantic reasoning."""
            # Extract entities from additions
            entities = []
            for s, p, o in delta.additions:
                entities.append({"subject": s, "predicate": p, "object": o})

            # Validate with DSPy
            validation_result = await invoke_signature(
                ValidationSignature,
                {
                    "entities": entities,
                    "context": "knowledge graph mutation",
                },
            )

            return validation_result.is_valid

        self.atman.register_hook(
            KnowledgeHook(
                "dspy-validator",
                HookMode.PRE,
                semantic_validate,
                priority=100,
            )
        )

    async def apply(self, delta, actor="system"):
        """Apply with semantic validation."""
        return await self.atman.apply(delta, actor=actor)

# Usage
semantic_engine = SemanticValidatedAtman()

delta = QuadDelta(
    additions=[
        ("urn:entity:123", "rdf:type", "schema:Person"),
        ("urn:entity:123", "schema:name", "Alice"),
    ]
)
receipt = await semantic_engine.apply(delta, actor="user:alice")
```

## Complete Integration Example

Here's a full example combining all integrations:

```python
from kgcl.engine import Atman, KnowledgeHook, HookMode, QuadDelta
from kgcl.hooks import HookRegistry
from kgcl.unrdf_engine import UnrdfEngine
from kgcl.observability.tracing import get_tracer
from kgcl.dspy_runtime import invoke_signature
from kgcl.cli.core.receipts import ReceiptRenderer

class IntegratedAtmanPlatform:
    """Complete KGCL platform with all integrations."""

    def __init__(self):
        # Core components
        self.atman = Atman()
        self.kgcl_hooks = HookRegistry()
        self.unrdf = UnrdfEngine()
        self.tracer = get_tracer(__name__)
        self.renderer = ReceiptRenderer()

        # Setup integrations
        self._setup_kgcl_bridge()
        self._setup_unrdf_validation()
        self._setup_otel_instrumentation()

    def _setup_kgcl_bridge(self):
        """Bridge to KGCL hooks."""
        async def emit_event(store, delta, ctx) -> bool:
            await self.kgcl_hooks.trigger("graph.mutation", {
                "tx_id": ctx.tx_id,
                "actor": ctx.actor,
            })
            return True

        self.atman.register_hook(
            KnowledgeHook("kgcl-events", HookMode.POST, emit_event)
        )

    def _setup_unrdf_validation(self):
        """SPARQL-based validation."""
        async def sparql_validate(store, delta, ctx) -> bool:
            # Validate with SPARQL ASK
            return True  # Simplified

        self.atman.register_hook(
            KnowledgeHook("sparql-validator", HookMode.PRE, sparql_validate)
        )

    def _setup_otel_instrumentation(self):
        """OpenTelemetry tracing."""
        async def trace_mutation(store, delta, ctx) -> bool:
            with self.tracer.start_as_current_span("atman.mutation") as span:
                span.set_attribute("tx_id", ctx.tx_id)
            return True

        self.atman.register_hook(
            KnowledgeHook("otel-tracer", HookMode.POST, trace_mutation)
        )

    async def apply(self, delta: QuadDelta, actor: str = "system"):
        """Apply transaction through integrated platform."""
        with self.tracer.start_as_current_span("platform.apply") as span:
            # Apply with all integrations
            receipt = await self.atman.apply(delta, actor=actor)

            # Render receipt
            self.renderer.render(receipt)

            # Set span status
            span.set_attribute("committed", receipt.committed)

            return receipt

# Usage
platform = IntegratedAtmanPlatform()

# Apply mutation (triggers all integrations)
delta = QuadDelta(
    additions=[
        ("urn:entity:123", "rdf:type", "schema:Person"),
        ("urn:entity:123", "schema:name", "Alice"),
    ]
)
receipt = await platform.apply(delta, actor="user:alice")

# All integrations activated:
# ✓ KGCL event emitted
# ✓ SPARQL validation performed
# ✓ OTEL span created
# ✓ Receipt rendered
```

## Testing Integrations

```python
import pytest
from kgcl.engine import Atman, QuadDelta

@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_platform_integration():
    """Test complete platform integration."""
    platform = IntegratedAtmanPlatform()

    # Apply mutation
    delta = QuadDelta(additions=[("urn:a", "urn:b", "urn:c")])
    receipt = await platform.apply(delta, actor="test:integration")

    # Verify
    assert receipt.committed is True
    assert len(receipt.hook_results) >= 3  # KGCL, UNRDF, OTEL hooks

    # Verify KGCL event was emitted
    # (would need mock or test listener)

    # Verify OTEL span was created
    # (would check OTEL exporter)

    # Verify UNRDF validation ran
    # (check receipt.hook_results)
```

## Best Practices

1. **Hook Priority**: KGCL events (low), UNRDF validation (high), OTEL tracing (medium)
2. **Error Handling**: Each integration should handle errors gracefully
3. **Performance**: Monitor hook latency to ensure <100ms p99
4. **Testing**: Test each integration independently and together
5. **Configuration**: Make integrations optional via config

## Additional Resources

- [Atman Engine API](/docs/api/atman-engine-openapi.yaml)
- [KGCL Hooks Documentation](/docs/hooks)
- [UNRDF Engine Guide](/docs/unrdf)
- [OpenTelemetry Integration](/docs/observability)
- [CLI Development](/docs/cli)

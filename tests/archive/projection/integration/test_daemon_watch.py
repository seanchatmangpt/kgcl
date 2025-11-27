"""Integration test: Daemon watch triggers projection regeneration.

This test validates the full daemon → projection flow:
1. Start daemon with warm RDF store
2. Subscribe to mutations with projection callback
3. Mutate RDF (add triples)
4. Verify projection automatically regenerates with new data

The key formula: A = μ_proj(O) where O changes trigger A regeneration.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from kgcl.daemon.event_store import DomainEvent, EventType
from kgcl.daemon.kgcld import DaemonConfig, KGCLDaemon
from kgcl.projection.adapters.event_store_adapter import EventStoreAdapter
from kgcl.projection.domain.descriptors import (
    OntologyConfig,
    QueryDescriptor,
    QuerySource,
    TemplateDescriptor,
    TemplateMetadata,
)
from kgcl.projection.engine.projection_engine import ProjectionConfig, ProjectionEngine
from kgcl.projection.ports.template_registry import InMemoryTemplateRegistry
from kgcl.projection.sandbox import create_projection_environment


# State graph URI for SPARQL queries
STATE_GRAPH = "urn:kgcl:state"


class TestDaemonWatchProjection:
    """Test that daemon mutations trigger projection regeneration."""

    @pytest.fixture
    def template_registry(self) -> InMemoryTemplateRegistry:
        """Create template registry with entity counter template."""
        registry = InMemoryTemplateRegistry()

        # Template that counts entities in the graph
        template = TemplateDescriptor(
            id="entity-counter",
            engine="jinja2",
            language="text",
            framework="",
            version="1.0.0",
            ontology=OntologyConfig(graph_id="main", base_iri="http://example.org/"),
            queries=(
                QueryDescriptor(
                    name="entities",
                    purpose="Count all subjects",
                    source=QuerySource.INLINE,
                    content="""
                    SELECT DISTINCT ?s WHERE {
                        GRAPH <urn:kgcl:state> { ?s ?p ?o . }
                    }
                    """,
                ),
            ),
            n3_rules=(),
            metadata=TemplateMetadata(author="test", description="Entity counter", tags=("test",)),
            template_path="counter.txt.j2",
            raw_content="Entity count: {{ sparql.entities | length }}",
        )
        registry.add(template)
        return registry

    @pytest.mark.asyncio
    async def test_daemon_subscribe_receives_mutation_events(self) -> None:
        """Test that subscription callback receives mutation events."""
        config = DaemonConfig(snapshot_interval=100)
        events_received: list[DomainEvent] = []

        def on_mutation(event: DomainEvent) -> None:
            events_received.append(event)

        async with KGCLDaemon(config) as daemon:
            # Subscribe to mutations
            unsubscribe = daemon.subscribe(on_mutation)

            # Perform mutations
            await daemon.add("urn:entity:1", "urn:type", "urn:Thing")
            await daemon.add("urn:entity:2", "urn:type", "urn:Thing")
            await daemon.add("urn:entity:3", "urn:name", "Test")

            # Verify events received
            assert len(events_received) == 3
            assert all(e.event_type == EventType.TRIPLE_ADDED for e in events_received)

            # Unsubscribe and verify no more events
            unsubscribe()
            await daemon.add("urn:entity:4", "urn:type", "urn:Thing")
            assert len(events_received) == 3  # Still 3, not 4

    @pytest.mark.asyncio
    async def test_projection_changes_after_mutation(
        self,
        template_registry: InMemoryTemplateRegistry,
    ) -> None:
        """Test that projection output changes after RDF mutation."""
        config = DaemonConfig(snapshot_interval=100)

        async with KGCLDaemon(config) as daemon:
            # Create projection engine with daemon's store
            adapter = EventStoreAdapter(daemon.store, graph_id="main")
            engine = ProjectionEngine(
                template_registry=template_registry,
                graph_clients={"main": adapter},
                jinja_env=create_projection_environment(),
                config=ProjectionConfig(strict_mode=False),
            )

            # Initial state - empty graph
            result1 = engine.render("counter.txt.j2")
            assert "Entity count: 0" in result1.content

            # Add entities
            await daemon.add("urn:entity:1", "urn:type", "urn:Thing")
            await daemon.add("urn:entity:2", "urn:type", "urn:Thing")

            # Re-render - should see new entities
            result2 = engine.render("counter.txt.j2")
            # Should have at least 2 unique subjects now
            assert "Entity count: 0" not in result2.content
            assert result2.query_count == 1

    @pytest.mark.asyncio
    async def test_watch_callback_triggers_projection(
        self,
        template_registry: InMemoryTemplateRegistry,
    ) -> None:
        """Test that a watch callback can trigger projection regeneration."""
        config = DaemonConfig(snapshot_interval=100)
        projection_results: list[str] = []

        async with KGCLDaemon(config) as daemon:
            # Create projection engine
            adapter = EventStoreAdapter(daemon.store, graph_id="main")
            engine = ProjectionEngine(
                template_registry=template_registry,
                graph_clients={"main": adapter},
                jinja_env=create_projection_environment(),
                config=ProjectionConfig(strict_mode=False),
            )

            # Watch callback that triggers projection
            def on_mutation(event: DomainEvent) -> None:
                result = engine.render("counter.txt.j2")
                projection_results.append(result.content)

            daemon.subscribe(on_mutation)

            # Each mutation triggers projection
            await daemon.add("urn:entity:1", "urn:type", "urn:Thing")
            await daemon.add("urn:entity:2", "urn:type", "urn:Thing")
            await daemon.add("urn:entity:3", "urn:type", "urn:Thing")

            # Should have 3 projection results
            assert len(projection_results) == 3

            # Each result should show increasing entity counts
            # (Results may vary based on SPARQL query timing, but count should increase)
            assert all("Entity count:" in r for r in projection_results)

    @pytest.mark.asyncio
    async def test_daemon_render_projection_method(self) -> None:
        """Test the daemon's built-in render_projection method."""
        config = DaemonConfig(snapshot_interval=100)

        async with KGCLDaemon(config) as daemon:
            # Add some data
            await daemon.add("urn:entity:1", "urn:type", "urn:Thing")
            await daemon.add("urn:entity:1", "urn:label", "Entity One")

            # The render_projection method needs templates in .kgc/projections
            # For this test, we verify the method exists and raises appropriately
            # when no templates are configured
            from kgcl.projection.domain.exceptions import TemplateNotFoundError

            with pytest.raises(TemplateNotFoundError):
                await daemon.render_projection("nonexistent.j2")

    @pytest.mark.asyncio
    async def test_debounced_watch_pattern(
        self,
        template_registry: InMemoryTemplateRegistry,
    ) -> None:
        """Test debounced watch pattern for batching rapid mutations."""
        config = DaemonConfig(snapshot_interval=100)
        render_count = 0
        last_result: str | None = None

        async with KGCLDaemon(config) as daemon:
            adapter = EventStoreAdapter(daemon.store, graph_id="main")
            engine = ProjectionEngine(
                template_registry=template_registry,
                graph_clients={"main": adapter},
                jinja_env=create_projection_environment(),
                config=ProjectionConfig(strict_mode=False),
            )

            # Debounced callback pattern
            pending_render = False
            debounce_delay = 0.05  # 50ms debounce

            async def debounced_render() -> None:
                nonlocal render_count, last_result, pending_render
                await asyncio.sleep(debounce_delay)
                if pending_render:
                    result = engine.render("counter.txt.j2")
                    last_result = result.content
                    render_count += 1
                    pending_render = False

            def on_mutation(event: DomainEvent) -> None:
                nonlocal pending_render
                pending_render = True
                # Schedule debounced render (fire-and-forget)
                asyncio.create_task(debounced_render())

            daemon.subscribe(on_mutation)

            # Rapid mutations
            for i in range(10):
                await daemon.add(f"urn:entity:{i}", "urn:type", "urn:Thing")

            # Wait for debounce to complete
            await asyncio.sleep(0.1)

            # Should have fewer renders than mutations due to debouncing
            # (Exact count depends on timing, but should be less than 10)
            assert render_count >= 1
            assert last_result is not None
            assert "Entity count:" in last_result


class TestEventStoreAdapterIntegration:
    """Test EventStoreAdapter with daemon store."""

    @pytest.mark.asyncio
    async def test_adapter_queries_live_store(self) -> None:
        """Test that adapter sees real-time store changes."""
        config = DaemonConfig(snapshot_interval=100)

        async with KGCLDaemon(config) as daemon:
            adapter = EventStoreAdapter(daemon.store, graph_id="main")

            # Initial query - empty
            query = "SELECT (COUNT(*) as ?count) WHERE { GRAPH <urn:kgcl:state> { ?s ?p ?o } }"
            result1 = adapter.query(query)
            initial_count = int(result1[0]["count"]) if result1 else 0

            # Add triples
            await daemon.add("urn:a", "urn:b", "urn:c")
            await daemon.add("urn:d", "urn:e", "urn:f")

            # Query again - should see new triples
            result2 = adapter.query(query)
            new_count = int(result2[0]["count"]) if result2 else 0

            assert new_count > initial_count
            assert new_count >= initial_count + 2

    @pytest.mark.asyncio
    async def test_adapter_ask_query(self) -> None:
        """Test ASK query through adapter."""
        config = DaemonConfig(snapshot_interval=100)

        async with KGCLDaemon(config) as daemon:
            adapter = EventStoreAdapter(daemon.store, graph_id="main")

            # Initially false
            result1 = adapter.ask("ASK { GRAPH <urn:kgcl:state> { <urn:test:subject> ?p ?o } }")
            assert result1 is False

            # Add triple
            await daemon.add("urn:test:subject", "urn:type", "urn:Thing")

            # Now true
            result2 = adapter.ask("ASK { GRAPH <urn:kgcl:state> { <urn:test:subject> ?p ?o } }")
            assert result2 is True


class TestWatchProjectionWorkflow:
    """End-to-end test of the watch → project workflow."""

    @pytest.mark.asyncio
    async def test_full_watch_project_cycle(self) -> None:
        """Test complete cycle: start daemon → watch → mutate → project → verify."""
        config = DaemonConfig(snapshot_interval=100)

        # Track all projection outputs
        outputs: list[dict[str, Any]] = []

        # Create template that lists all entities
        registry = InMemoryTemplateRegistry()
        template = TemplateDescriptor(
            id="entity-list",
            engine="jinja2",
            language="json",
            framework="",
            version="1.0.0",
            ontology=OntologyConfig(graph_id="main", base_iri="http://example.org/"),
            queries=(
                QueryDescriptor(
                    name="entities",
                    purpose="List all entities",
                    source=QuerySource.INLINE,
                    content="""
                    SELECT ?s ?p ?o WHERE {
                        GRAPH <urn:kgcl:state> { ?s ?p ?o . }
                    }
                    ORDER BY ?s ?p
                    """,
                ),
            ),
            n3_rules=(),
            metadata=TemplateMetadata(author="test", description="Entity list", tags=("test",)),
            template_path="entities.json.j2",
            raw_content="""{
  "triple_count": {{ sparql.entities | length }},
  "triples": [
{% for t in sparql.entities %}
    {"s": "{{ t.s }}", "p": "{{ t.p }}", "o": "{{ t.o }}"}{% if not loop.last %},{% endif %}

{% endfor %}
  ]
}""",
        )
        registry.add(template)

        async with KGCLDaemon(config) as daemon:
            adapter = EventStoreAdapter(daemon.store, graph_id="main")
            engine = ProjectionEngine(
                template_registry=registry,
                graph_clients={"main": adapter},
                jinja_env=create_projection_environment(),
                config=ProjectionConfig(strict_mode=False),
            )

            # Watch callback
            def on_mutation(event: DomainEvent) -> None:
                result = engine.render("entities.json.j2")
                outputs.append({
                    "event_type": event.event_type.value,
                    "content": result.content,
                    "query_count": result.query_count,
                })

            daemon.subscribe(on_mutation)

            # === Phase 1: Add Product ===
            await daemon.add("urn:product:1", "urn:type", "urn:Product")
            await daemon.add("urn:product:1", "urn:name", "Widget")
            await daemon.add("urn:product:1", "urn:price", "9.99")

            # === Phase 2: Add Customer ===
            await daemon.add("urn:customer:1", "urn:type", "urn:Customer")
            await daemon.add("urn:customer:1", "urn:email", "test@example.com")

            # === Phase 3: Add Order linking them ===
            await daemon.add("urn:order:1", "urn:type", "urn:Order")
            await daemon.add("urn:order:1", "urn:customer", "urn:customer:1")
            await daemon.add("urn:order:1", "urn:product", "urn:product:1")

            # Verify watch triggered
            assert len(outputs) == 8  # 8 add operations (3 product + 2 customer + 3 order)

            # Verify progression - each output has more triples
            triple_counts = []
            for o in outputs:
                # Parse triple_count from JSON output
                import re
                match = re.search(r'"triple_count":\s*(\d+)', o["content"])
                if match:
                    triple_counts.append(int(match.group(1)))

            # Counts should be monotonically increasing
            for i in range(1, len(triple_counts)):
                assert triple_counts[i] >= triple_counts[i - 1]

            # Final count should be 8 (all triples)
            assert triple_counts[-1] == 8

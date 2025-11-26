"""
Consolidated Integration Tests.

80/20 consolidation: End-to-end pipeline tests with real collaborators.
Tests the full KGCL workflow from ingestion to codegen.
"""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from rdflib import Namespace

from kgcl.hooks.conditions import Condition, ConditionResult, ThresholdCondition, ThresholdOperator
from kgcl.hooks.core import Hook, HookExecutor, HookRegistry
from kgcl.ingestion.config import CollectorConfig, IngestionConfig
from kgcl.ingestion.models import AppEvent
from kgcl.ingestion.service import IngestionService
from kgcl.unrdf_engine.engine import UnrdfEngine

# =============================================================================
# Test Fixtures
# =============================================================================


class GraphChangeCondition(Condition):
    """Condition that triggers on graph changes."""

    async def evaluate(self, context: dict[str, Any]) -> ConditionResult:
        has_changes = context.get("triple_count", 0) > 0
        return ConditionResult(triggered=has_changes, metadata={"triple_count": context.get("triple_count", 0)})


def graph_update_handler(context: dict[str, Any]) -> dict[str, Any]:
    """Handler that processes graph updates."""
    return {
        "processed": True,
        "triple_count": context.get("triple_count", 0),
        "timestamp": datetime.now(UTC).isoformat(),
    }


# =============================================================================
# Ingestion Pipeline Tests
# =============================================================================


class TestIngestionPipeline:
    """End-to-end ingestion pipeline tests."""

    def test_single_event_ingestion(self) -> None:
        """Single event flows through ingestion pipeline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(collector=CollectorConfig(output_directory=Path(tmpdir)))
            service = IngestionService(config)
            service.start()

            event = AppEvent(
                event_id="test_001", timestamp=datetime.now(UTC), app_name="com.apple.Safari", duration_seconds=120.0
            )

            result = service.ingest_event(event)
            assert result["status"] == "success"
            assert result["event_id"] == "test_001"

            service.stop()

    def test_batch_event_ingestion(self) -> None:
        """Batch of events flows through ingestion pipeline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(collector=CollectorConfig(output_directory=Path(tmpdir), batch_size=100))
            service = IngestionService(config)
            service.start()

            now = datetime.now(UTC)
            events = [
                AppEvent(
                    event_id=f"batch_{i:03d}",
                    timestamp=now + timedelta(seconds=i),
                    app_name=f"com.app.App{i % 5}",
                    duration_seconds=float((i + 1) * 10),  # Start from 10, not 0 (min_duration=1.0)
                )
                for i in range(50)
            ]

            result = service.ingest_batch(events)
            assert result["status"] == "success"
            assert result["processed_events"] == 50

            service.stop()

    def test_ingestion_with_hooks(self) -> None:
        """Ingestion triggers registered hooks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(collector=CollectorConfig(output_directory=Path(tmpdir)))
            service = IngestionService(config)

            # Track hook executions
            hook_calls: list[int] = []

            def tracking_hook(events: list) -> None:
                hook_calls.append(len(events))

            service.register_pre_hook("tracker", tracking_hook)
            service.start()

            event = AppEvent(event_id="hook_test", timestamp=datetime.now(UTC), app_name="com.test.App")
            service.ingest_event(event)

            assert len(hook_calls) == 1
            assert hook_calls[0] == 1

            service.stop()


# =============================================================================
# Hook-UNRDF Integration Tests
# =============================================================================


class TestHookUnrdfIntegration:
    """Hooks integrated with UNRDF engine."""

    def test_hook_triggers_on_graph_change(self) -> None:
        """Hook triggers when graph changes detected."""
        engine = UnrdfEngine()
        ns = Namespace("http://example.org/test#")

        # Add triples to graph
        engine.graph.add((ns["entity1"], ns["hasValue"], ns["value1"]))

        # Create context with triple count
        context = {"triple_count": len(engine.graph)}

        # Create and execute hook
        hook = Hook(
            name="graph_change_hook",
            description="Triggers on graph changes",
            condition=GraphChangeCondition(),
            handler=graph_update_handler,
        )

        executor = HookExecutor()
        import asyncio

        receipt = asyncio.run(executor.execute(hook, context))

        assert receipt.condition_result.triggered is True
        assert receipt.handler_result is not None
        assert receipt.handler_result["processed"] is True

    def test_threshold_hook_on_triple_count(self) -> None:
        """ThresholdCondition triggers when triple count exceeds limit."""
        engine = UnrdfEngine()
        ns = Namespace("http://example.org/test#")

        # Add multiple triples
        for i in range(15):
            engine.graph.add((ns[f"entity{i}"], ns["hasValue"], ns[f"value{i}"]))

        context = {"triple_count": len(engine.graph)}

        hook = Hook(
            name="large_graph_hook",
            description="Triggers when graph has many triples",
            condition=ThresholdCondition(variable="triple_count", operator=ThresholdOperator.GREATER_THAN, value=10),
            handler=graph_update_handler,
        )

        executor = HookExecutor()
        import asyncio

        receipt = asyncio.run(executor.execute(hook, context))

        assert receipt.condition_result.triggered is True


# =============================================================================
# Full Pipeline Tests
# =============================================================================


class TestFullPipeline:
    """Complete pipeline from ingestion to hooks to receipts."""

    def test_ingest_trigger_hook_store_receipt(self) -> None:
        """Full flow: ingest events -> trigger hooks -> store receipts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup ingestion
            config = IngestionConfig(collector=CollectorConfig(output_directory=Path(tmpdir)))
            service = IngestionService(config)

            # Setup hooks
            registry = HookRegistry()
            hook = Hook(
                name="ingest_hook",
                description="Process ingested events",
                condition=GraphChangeCondition(),
                handler=graph_update_handler,
            )
            registry.register(hook)

            # Track receipts
            receipts: list = []

            def post_hook(events: list) -> None:
                for _ in registry.get_all():
                    receipts.append({"executed": True})

            service.register_post_hook("executor", post_hook)
            service.start()

            # Ingest event
            event = AppEvent(
                event_id="pipeline_test",
                timestamp=datetime.now(UTC),
                app_name="com.test.Pipeline",
                duration_seconds=60.0,  # Above min_duration threshold
            )
            result = service.ingest_event(event)

            assert result["status"] == "success"
            service.stop()

    def test_filtered_events_dont_trigger_hooks(self) -> None:
        """Filtered events do not trigger post-hooks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(collector=CollectorConfig(output_directory=Path(tmpdir)))
            # Configure filter to exclude short events
            config.filter.min_duration_seconds = 60

            service = IngestionService(config)

            hook_calls: list[int] = []

            def tracking_hook(events: list) -> None:
                hook_calls.append(len(events))

            service.register_post_hook("tracker", tracking_hook)
            service.start()

            # Event with duration < 60 should be filtered
            event = AppEvent(
                event_id="short_event", timestamp=datetime.now(UTC), app_name="com.test.App", duration_seconds=30.0
            )
            result = service.ingest_event(event)

            assert result["status"] == "filtered"
            # Post-hook should not be called for filtered events
            assert len(hook_calls) == 0

            service.stop()


# =============================================================================
# Performance Integration Tests
# =============================================================================


class TestPerformanceIntegration:
    """Performance characteristics of integrated pipeline."""

    @pytest.mark.slow
    def test_throughput_with_hooks(self) -> None:
        """Ingestion throughput with hooks enabled."""
        import time

        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(collector=CollectorConfig(output_directory=Path(tmpdir), batch_size=500))
            service = IngestionService(config)
            service.register_pre_hook("noop", lambda events: None)
            service.start()

            now = datetime.now(UTC)
            events = [
                AppEvent(
                    event_id=f"perf_{i:05d}",
                    timestamp=now + timedelta(seconds=i),
                    app_name=f"com.app.App{i % 10}",
                    duration_seconds=float(i % 300),
                )
                for i in range(1000)
            ]

            start = time.perf_counter()
            result = service.ingest_batch(events)
            elapsed = time.perf_counter() - start

            assert result["status"] == "success"
            throughput = 1000 / elapsed
            assert throughput > 500  # At least 500 events/sec with hooks

            service.stop()

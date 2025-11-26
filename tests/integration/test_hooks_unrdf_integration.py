"""Focused integration tests for knowledge hooks and UNRDF."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Tuple

import pytest
from rdflib import Namespace, URIRef
from rdflib.namespace import RDF

from kgcl.unrdf_engine.engine import UnrdfEngine
from kgcl.unrdf_engine.hook_registry import PersistentHookRegistry
from kgcl.unrdf_engine.hooks import HookContext, HookPhase, KnowledgeHook
from kgcl.unrdf_engine.ingestion import IngestionPipeline

UNRDF = Namespace("http://unrdf.org/ontology/")
GRAPH_GROWTH_COUNT = 2


class RecordingHook(KnowledgeHook):
    """Hook that captures transaction IDs for priority assertions."""

    def __init__(self, name: str, phase: HookPhase) -> None:
        super().__init__(name=name, phases=[phase])
        self.calls: list[str] = []

    def execute(self, context: HookContext) -> None:
        """Record every transaction ID the hook observes."""
        self.calls.append(context.transaction_id)


def _create_engine(tmpdir: str) -> tuple[UnrdfEngine, PersistentHookRegistry]:
    """Create an in-memory engine and registry pair for tests."""
    registry = PersistentHookRegistry()
    engine = UnrdfEngine(file_path=Path(tmpdir) / "graph.ttl", hook_registry=registry)
    return engine, registry


class TestHookIntegration:
    """Regression tests covering hook lifecycle behaviour."""

    def test_delta_capture_on_ingestion(self) -> None:
        """POST_COMMIT hook should receive all delta triples."""

        class DeltaHook(KnowledgeHook):
            def __init__(self) -> None:
                super().__init__(name="delta", phases=[HookPhase.POST_COMMIT])
                self.delta: list[tuple[str, str, str]] = []

            def execute(self, context: HookContext) -> None:
                """Capture every triple in the delta graph."""
                for subject, predicate, obj in context.delta:
                    self.delta.append((str(subject), str(predicate), str(obj)))

        with tempfile.TemporaryDirectory() as tmpdir:
            engine, registry = _create_engine(tmpdir)
            hook = DeltaHook()
            registry.register(hook)

            pipeline = IngestionPipeline(engine)
            result = pipeline.ingest_json(
                data={"id": "person-1", "type": "Person", "name": "Test User"},
                agent="tester",
            )

        assert result.success is True
        assert len(hook.delta) >= GRAPH_GROWTH_COUNT

    def test_priority_order_enforced(self) -> None:
        """Higher priority hooks execute before lower priority ones."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine, registry = _create_engine(tmpdir)
            low = RecordingHook("low", HookPhase.POST_COMMIT)
            high = RecordingHook("high", HookPhase.POST_COMMIT)
            low.priority = 10
            high.priority = 100
            registry.register(low)
            registry.register(high)

            pipeline = IngestionPipeline(engine)
            result = pipeline.ingest_json(
                data={"id": "event", "type": "Event"}, agent="tester"
            )

        assert result.success is True
        assert high.calls[0] == low.calls[0]

    def test_post_transaction_error_does_not_abort_commit(self) -> None:
        """POST_TRANSACTION hook failure must not roll back committed work."""

        class FailingHook(KnowledgeHook):
            def __init__(self) -> None:
                super().__init__(name="fail_post", phases=[HookPhase.POST_TRANSACTION])

            def execute(self, context: HookContext) -> None:
                """Record metadata and raise deterministic error."""
                context.metadata["forced_error"] = True
                error_message = "synthetic failure"
                raise RuntimeError(error_message)

        with tempfile.TemporaryDirectory() as tmpdir:
            engine, registry = _create_engine(tmpdir)
            registry.register(FailingHook())

            txn = engine.transaction("tester", "post failure")
            engine.add_triple(
                URIRef("http://example.org/p1"), RDF.type, UNRDF.Person, txn
            )
            engine.commit(txn)

        assert txn.committed is True
        assert len(engine.graph) == 1

    def test_pre_transaction_error_aborts_commit(self) -> None:
        """PRE_TRANSACTION hook should veto commit when signalling rollback."""

        class RejectHook(KnowledgeHook):
            def __init__(self) -> None:
                super().__init__(name="reject", phases=[HookPhase.PRE_TRANSACTION])

            def execute(self, context: HookContext) -> None:
                """Annotate metadata to force rollback."""
                context.metadata["should_rollback"] = True
                context.metadata["rollback_reason"] = "Rejected by hook"

        with tempfile.TemporaryDirectory() as tmpdir:
            engine, registry = _create_engine(tmpdir)
            registry.register(RejectHook())
            txn = engine.transaction("tester", "pre failure")
            engine.add_triple(
                URIRef("http://example.org/p2"), RDF.type, UNRDF.Person, txn
            )

            with pytest.raises(ValueError, match="Rejected by hook"):
                engine.commit(txn)

        assert txn.rolled_back is True
        assert len(engine.graph) == 0

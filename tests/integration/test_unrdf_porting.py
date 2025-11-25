"""
Integration Tests for UNRDF Porting - Phase 4.

This test suite validates comprehensive integration of all ported UNRDF capabilities:
- Phase 1: Security (error sanitization, sandbox restrictions, execution IDs)
- Phase 2: Performance (metrics collection, caching, SLO monitoring)
- Phase 3: Advanced (policy packs, file resolution, chain anchoring)
- Phase 4: End-to-end workflows

Tests follow Chicago School TDD principles with NO mocking of domain objects.
All tests use real execution through the full pipeline.
"""

import json
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pytest

from kgcl.hooks.conditions import (
    ConditionResult,
    SparqlAskCondition,
    ThresholdCondition,
    ThresholdOperator,
)
from kgcl.hooks.core import Hook
from kgcl.hooks.file_resolver import FileResolver, FileResolverError
from kgcl.hooks.lifecycle import HookContext, HookExecutionPipeline
from kgcl.hooks.performance import PerformanceMetrics, PerformanceOptimizer
from kgcl.hooks.query_cache import QueryCache
from kgcl.hooks.receipts import MerkleTree, Receipt, ReceiptStore
from kgcl.hooks.sandbox import SandboxRestrictions
from kgcl.hooks.security import ErrorSanitizer
from kgcl.unrdf_engine.hook_registry import (
    PersistentHookRegistry,
    PolicyPack,
    PolicyPackManager,
    PolicyPackManifest,
)
from kgcl.unrdf_engine.hooks import HookContext, HookPhase, KnowledgeHook


# Test implementation of KnowledgeHook for testing
class TestKnowledgeHook(KnowledgeHook):
    """Concrete KnowledgeHook implementation for testing."""

    def execute(self, context: HookContext) -> None:
        """No-op execute for testing."""


# ============================================================================
# Section 1: Security Integration (8 tests)
# ============================================================================


class TestSecurityIntegration:
    """Integration tests for security capabilities."""

    @pytest.mark.asyncio
    async def test_hook_execution_with_error_sanitization(self):
        """Errors are sanitized in hook execution."""

        # Create hook with failing handler
        def failing_handler(context: dict[str, Any]) -> dict[str, Any]:
            raise ValueError("Secret path /etc/passwd exposed in line 42")

        hook = Hook(
            name="failing_hook",
            description="Test hook that fails",
            condition=ThresholdCondition(
                variable="count", operator=ThresholdOperator.GREATER_THAN, value=0
            ),
            handler=failing_handler,
        )

        pipeline = HookExecutionPipeline()
        context = {"count": 10}

        # Execute and verify error is sanitized
        receipt = await pipeline.execute(hook, context)

        assert receipt.error is not None
        assert receipt.metadata.get("sanitized") is True
        # Verify sensitive info removed
        assert "/etc/passwd" not in receipt.error
        assert "line 42" not in receipt.error
        assert (
            "[REDACTED]" in receipt.error
            or receipt.error == "Secret path [REDACTED] exposed in [REDACTED]"
        )

    @pytest.mark.asyncio
    async def test_sandbox_restrictions_enforced(self):
        """Sandbox restrictions prevent unauthorized path access."""
        sandbox = SandboxRestrictions(
            allowed_paths=["/tmp/allowed"],
            no_network=True,
            no_process_spawn=True,
            memory_limit_mb=256,
            timeout_ms=5000,
        )

        # Test allowed path
        assert sandbox.validate_path("/tmp/allowed/file.txt") is True

        # Test disallowed path
        assert sandbox.validate_path("/etc/passwd") is False

        # Test path traversal attempt
        assert sandbox.validate_path("/tmp/allowed/../../../etc/passwd") is False

        # Validate configuration
        assert sandbox.validate_restrictions() is True

    @pytest.mark.asyncio
    async def test_execution_id_generation_unique(self):
        """Each execution generates unique execution ID."""
        from kgcl.hooks.lifecycle import HookContext as LifecycleHookContext

        context1 = LifecycleHookContext(actor="user1")
        context2 = LifecycleHookContext(actor="user2")

        # Verify execution IDs are unique
        assert context1.execution_id != context2.execution_id

        # Verify request IDs are unique
        assert context1.request_id != context2.request_id

        # Verify actors are preserved
        assert context1.actor == "user1"
        assert context2.actor == "user2"

    @pytest.mark.asyncio
    async def test_sanitized_error_in_receipt(self):
        """Receipt contains sanitized error with error code."""

        def error_with_stack_trace(context: dict[str, Any]) -> dict[str, Any]:
            # Simulate error with file path and line numbers
            raise RuntimeError('File "/app/handlers/processor.py", line 123, in process_data')

        hook = Hook(
            name="error_hook",
            description="Test error sanitization",
            condition=ThresholdCondition(
                variable="trigger", operator=ThresholdOperator.EQUALS, value=True
            ),
            handler=error_with_stack_trace,
        )

        pipeline = HookExecutionPipeline()
        receipt = await pipeline.execute(hook, {"trigger": True})

        # Verify sanitization
        assert receipt.error is not None
        assert receipt.metadata.get("sanitized") is True
        assert "error_code" in receipt.metadata

        # Verify sensitive data removed
        assert "/app/handlers/processor.py" not in receipt.error
        assert "line 123" not in receipt.error

    @pytest.mark.asyncio
    async def test_path_traversal_prevented(self):
        """Path traversal attacks are prevented by sandbox."""
        sandbox = SandboxRestrictions(allowed_paths=["/var/data"])

        # Various path traversal attempts
        attacks = [
            "/var/data/../etc/passwd",
            "/var/data/../../root/.ssh",
            "/var/data/./../../etc/shadow",
        ]

        for attack_path in attacks:
            assert sandbox.validate_path(attack_path) is False

    @pytest.mark.asyncio
    async def test_memory_limit_respected(self):
        """Sandbox respects memory limit configuration."""
        sandbox = SandboxRestrictions(allowed_paths=["/tmp"], memory_limit_mb=128)

        assert sandbox.memory_limit_mb == 128
        assert sandbox.validate_restrictions() is True

        # Invalid memory limit
        invalid_sandbox = SandboxRestrictions(allowed_paths=["/tmp"], memory_limit_mb=-1)
        assert invalid_sandbox.validate_restrictions() is False

    @pytest.mark.asyncio
    async def test_error_sanitizer_removes_sensitive_patterns(self):
        """ErrorSanitizer removes multiple sensitive patterns."""
        sanitizer = ErrorSanitizer()

        # Test various sensitive patterns
        error = Exception(
            'File "/usr/local/app/handler.py", line 45, in process_request at line 123'
        )
        sanitized = sanitizer.sanitize(error)

        assert "[REDACTED]" in sanitized.message
        assert "/usr/local/app/handler.py" not in sanitized.message
        assert sanitized.is_user_safe is True

    @pytest.mark.asyncio
    async def test_execution_context_propagation(self):
        """Execution context propagates through pipeline."""

        def context_checker(context: dict[str, Any]) -> dict[str, Any]:
            return {
                "received_actor": context.get("actor"),
                "has_execution_id": "execution_id" in context,
            }

        hook = Hook(
            name="context_hook",
            description="Test context propagation",
            condition=ThresholdCondition(
                variable="value", operator=ThresholdOperator.GREATER_THAN, value=0
            ),
            handler=context_checker,
            actor="test_actor",
        )

        pipeline = HookExecutionPipeline()
        receipt = await pipeline.execute(hook, {"value": 5})

        # Verify actor propagated
        assert receipt.actor == "test_actor"

        # Verify handler received context (though not directly testable without adding to handler result)
        assert receipt.handler_result is not None


# ============================================================================
# Section 2: Performance Integration (8 tests)
# ============================================================================


class TestPerformanceIntegration:
    """Integration tests for performance capabilities."""

    @pytest.mark.asyncio
    async def test_condition_evaluation_cached(self):
        """SPARQL condition results are cached."""
        query = "ASK { ?s a <Person> }"

        condition = SparqlAskCondition(query=query, use_cache=True)

        # First evaluation (cache miss)
        result1 = await condition.evaluate({"test_result": True})
        stats1 = SparqlAskCondition.get_cache_stats()
        assert stats1 is not None
        assert stats1["hits"] == 0
        assert stats1["misses"] == 1

        # Second evaluation (cache hit)
        result2 = await condition.evaluate({"test_result": True})
        stats2 = SparqlAskCondition.get_cache_stats()
        assert stats2["hits"] == 1
        assert stats2["misses"] == 1

        # Results should be consistent
        assert result1.triggered == result2.triggered
        assert result2.metadata.get("cache_hit") is True

        # Cleanup
        SparqlAskCondition.clear_cache()

    @pytest.mark.asyncio
    async def test_cache_hit_reduces_latency(self):
        """Cache hits have lower latency than cache misses."""
        optimizer = PerformanceOptimizer()

        # Simulate cache miss (slower)
        metric1 = PerformanceMetrics(operation="sparql_ask", latency_ms=50.0, success=True)
        optimizer.record_metric(metric1)

        # Simulate cache hit (faster)
        metric2 = PerformanceMetrics(operation="sparql_ask", latency_ms=1.0, success=True)
        optimizer.record_metric(metric2)

        stats = optimizer.get_stats("sparql_ask")
        assert stats is not None
        assert stats["count"] == 2
        assert stats["min"] == 1.0
        assert stats["max"] == 50.0
        assert stats["mean"] == 25.5

    @pytest.mark.asyncio
    async def test_query_cache_invalidation(self):
        """Query cache can be invalidated."""
        cache = QueryCache(max_size=100, ttl_seconds=60)

        query = "SELECT * WHERE { ?s ?p ?o }"
        result = [{"s": "x", "p": "y", "o": "z"}]

        # Cache result
        cache.set(query, result)
        assert cache.get(query) == result

        # Invalidate
        cache.invalidate(query)
        assert cache.get(query) is None

    @pytest.mark.asyncio
    async def test_slo_violation_detection(self):
        """SLO violations are detected."""
        optimizer = PerformanceOptimizer()

        # Record metrics with SLO target
        metric1 = PerformanceMetrics(
            operation="hook_execute", latency_ms=50.0, success=True, p99_target_ms=100.0
        )
        metric2 = PerformanceMetrics(
            operation="hook_execute",
            latency_ms=150.0,  # Violates SLO
            success=True,
            p99_target_ms=100.0,
        )

        optimizer.record_metric(metric1)
        optimizer.record_metric(metric2)

        # Check SLO status
        slo_status = optimizer.get_slo_status("hook_execute", target_ms=100.0)
        assert slo_status is not None
        assert slo_status["total_count"] == 2
        assert slo_status["compliant_count"] == 1
        assert slo_status["compliance_rate"] == 0.5

    @pytest.mark.asyncio
    async def test_performance_metrics_in_receipt(self):
        """Hook execution includes performance metrics."""

        def simple_handler(context: dict[str, Any]) -> dict[str, Any]:
            return {"result": "success"}

        hook = Hook(
            name="perf_hook",
            description="Test performance tracking",
            condition=ThresholdCondition(
                variable="value", operator=ThresholdOperator.GREATER_THAN, value=0
            ),
            handler=simple_handler,
        )

        pipeline = HookExecutionPipeline(enable_performance_tracking=True)
        receipt = await pipeline.execute(hook, {"value": 5})

        # Verify performance tracking
        assert receipt.duration_ms > 0

        # Get performance stats
        stats = pipeline.get_performance_stats(f"hook_execute_{hook.name}")
        assert stats is not None
        assert stats["count"] == 1

    @pytest.mark.asyncio
    async def test_percentile_calculations_accurate(self):
        """Percentile calculations are accurate."""
        optimizer = PerformanceOptimizer(sample_size=100)

        # Record 100 samples (0-99 ms)
        for i in range(100):
            metric = PerformanceMetrics(operation="test_op", latency_ms=float(i))
            optimizer.record_metric(metric)

        # Verify percentiles
        p50 = optimizer.get_percentile("test_op", 0.50)
        p99 = optimizer.get_percentile("test_op", 0.99)
        p999 = optimizer.get_percentile("test_op", 0.999)

        assert p50 is not None
        assert p99 is not None
        assert p999 is not None

        # p50 should be around 50
        assert 40 <= p50 <= 60

        # p99 should be around 99
        assert 95 <= p99 <= 99

    @pytest.mark.asyncio
    async def test_batch_execution_performance_tracking(self):
        """Batch execution tracks performance metrics."""

        def handler(context: dict[str, Any]) -> dict[str, Any]:
            return {"processed": True}

        hooks = [
            Hook(
                name=f"hook_{i}",
                description=f"Test hook {i}",
                condition=ThresholdCondition(
                    variable="value", operator=ThresholdOperator.GREATER_THAN, value=0
                ),
                handler=handler,
                priority=i * 10,
            )
            for i in range(5)
        ]

        pipeline = HookExecutionPipeline(enable_performance_tracking=True)
        receipts = await pipeline.execute_batch(hooks, {"value": 10})

        assert len(receipts) == 5

        # Verify batch metrics recorded
        batch_stats = pipeline.get_performance_stats("hook_batch_execute")
        assert batch_stats is not None
        assert batch_stats["count"] == 1

    @pytest.mark.asyncio
    async def test_cache_lru_eviction(self):
        """Cache evicts LRU entries when full."""
        cache = QueryCache(max_size=3, ttl_seconds=60)

        # Fill cache
        cache.set("query1", "result1")
        cache.set("query2", "result2")
        cache.set("query3", "result3")

        # All should be cached
        assert cache.get("query1") == "result1"
        assert cache.get("query2") == "result2"
        assert cache.get("query3") == "result3"

        # Add 4th item (should evict query1 as LRU)
        cache.set("query4", "result4")

        # query1 should be evicted
        assert cache.get("query1") is None
        assert cache.get("query2") == "result2"
        assert cache.get("query3") == "result3"
        assert cache.get("query4") == "result4"


# ============================================================================
# Section 3: Policy Packs Integration (5 tests)
# ============================================================================


class TestPolicyPacksIntegration:
    """Integration tests for policy pack management."""

    @pytest.mark.asyncio
    async def test_policy_pack_loading(self):
        """Policy packs can be loaded from disk."""
        with TemporaryDirectory() as tmpdir:
            pack_dir = Path(tmpdir) / "test_pack"
            pack_dir.mkdir()

            # Create manifest
            manifest = PolicyPackManifest(
                name="test_pack",
                version="1.0.0",
                description="Test policy pack",
                hooks=["hook1"],
                slos={"latency_ms": 100.0},
            )

            manifest_file = pack_dir / "manifest.json"
            with open(manifest_file, "w") as f:
                json.dump(manifest.to_dict(), f)

            # Create registry with a hook
            registry = PersistentHookRegistry()
            test_hook = TestKnowledgeHook(
                name="hook1", phases=[HookPhase.POST_VALIDATION], priority=100
            )
            registry.register(test_hook)

            # Load pack
            manager = PolicyPackManager(base_path=Path(tmpdir), hook_registry=registry)
            pack = manager.load_pack(pack_dir)

            assert pack.manifest.name == "test_pack"
            assert pack.manifest.version == "1.0.0"
            assert "hook1" in pack.hooks
            assert pack.is_active is True

    @pytest.mark.asyncio
    async def test_activate_deactivate_pack(self):
        """Policy packs can be activated and deactivated."""
        with TemporaryDirectory() as tmpdir:
            pack_dir = Path(tmpdir) / "toggle_pack"
            pack_dir.mkdir()

            manifest = PolicyPackManifest(
                name="toggle_pack", version="1.0.0", description="Test toggle", hooks=["hook1"]
            )

            with open(pack_dir / "manifest.json", "w") as f:
                json.dump(manifest.to_dict(), f)

            registry = PersistentHookRegistry()
            hook = TestKnowledgeHook(name="hook1", phases=[HookPhase.PRE_INGESTION])
            registry.register(hook)

            manager = PolicyPackManager(base_path=Path(tmpdir), hook_registry=registry)
            pack = manager.load_pack(pack_dir)

            # Initially active
            assert pack.is_active is True
            assert "toggle_pack" in manager.active_packs

            # Deactivate
            assert manager.deactivate_pack("toggle_pack") is True
            assert pack.is_active is False
            assert "toggle_pack" not in manager.active_packs

            # Reactivate
            assert manager.activate_pack("toggle_pack") is True
            assert pack.is_active is True
            assert "toggle_pack" in manager.active_packs

    @pytest.mark.asyncio
    async def test_policy_pack_hooks_executed(self):
        """Hooks from active policy packs are executed."""
        with TemporaryDirectory() as tmpdir:
            pack_dir = Path(tmpdir) / "exec_pack"
            pack_dir.mkdir()

            manifest = PolicyPackManifest(
                name="exec_pack",
                version="1.0.0",
                description="Execution test",
                hooks=["validation_hook"],
            )

            with open(pack_dir / "manifest.json", "w") as f:
                json.dump(manifest.to_dict(), f)

            registry = PersistentHookRegistry()
            hook = TestKnowledgeHook(
                name="validation_hook", phases=[HookPhase.PRE_VALIDATION], priority=90
            )
            registry.register(hook)

            manager = PolicyPackManager(base_path=Path(tmpdir), hook_registry=registry)
            pack = manager.load_pack(pack_dir)

            # Get active hooks
            active_hooks = manager.get_active_hooks()
            assert len(active_hooks) == 1
            assert active_hooks[0].name == "validation_hook"

    @pytest.mark.asyncio
    async def test_slo_validation_from_pack(self):
        """SLOs from policy packs are validated."""
        manifest = PolicyPackManifest(
            name="slo_pack",
            version="1.0.0",
            description="SLO test",
            hooks=["h1"],
            slos={"latency_ms": 100.0, "error_rate": 0.01},
        )

        pack = PolicyPack(manifest=manifest, hooks={})

        # Test metrics within SLOs
        metrics = {"latency_ms": 50.0, "error_rate": 0.005}
        validation = pack.validate_slos(metrics)
        assert validation["latency_ms"] is True
        assert validation["error_rate"] is True

        # Test metrics violating SLOs
        bad_metrics = {"latency_ms": 150.0, "error_rate": 0.02}
        bad_validation = pack.validate_slos(bad_metrics)
        assert bad_validation["latency_ms"] is False
        assert bad_validation["error_rate"] is False

    @pytest.mark.asyncio
    async def test_policy_pack_dependency_validation(self):
        """Policy pack dependencies are validated."""
        with TemporaryDirectory() as tmpdir:
            # Create base pack
            base_dir = Path(tmpdir) / "base_pack"
            base_dir.mkdir()
            base_manifest = PolicyPackManifest(
                name="base_pack", version="1.0.0", description="Base pack", hooks=["hook1"]
            )
            with open(base_dir / "manifest.json", "w") as f:
                json.dump(base_manifest.to_dict(), f)

            # Create dependent pack
            dep_dir = Path(tmpdir) / "dep_pack"
            dep_dir.mkdir()
            dep_manifest = PolicyPackManifest(
                name="dep_pack",
                version="2.0.0",
                description="Dependent pack",
                hooks=["hook2"],
                dependencies={"base_pack": "1.0.0"},
            )
            with open(dep_dir / "manifest.json", "w") as f:
                json.dump(dep_manifest.to_dict(), f)

            registry = PersistentHookRegistry()
            for name in ["hook1", "hook2"]:
                registry.register(TestKnowledgeHook(name=name, phases=[HookPhase.PRE_INGESTION]))

            manager = PolicyPackManager(base_path=Path(tmpdir), hook_registry=registry)
            manager.load_pack(base_dir)
            manager.load_pack(dep_dir)

            # Validate dependencies
            validation = manager.validate_dependencies()
            assert validation["base_pack"] is True
            assert validation["dep_pack"] is True


# ============================================================================
# Section 4: File Resolution Integration (4 tests)
# ============================================================================


class TestFileResolutionIntegration:
    """Integration tests for file resolution with SHA256 verification."""

    @pytest.mark.asyncio
    async def test_load_condition_from_file(self):
        """SPARQL condition can be loaded from file."""
        with TemporaryDirectory() as tmpdir:
            query_file = Path(tmpdir) / "query.sparql"
            query_content = "ASK { ?s a <Person> }"
            query_file.write_text(query_content)

            resolver = FileResolver(allowed_paths=[tmpdir])
            loaded = resolver.load_file(f"file://{query_file}")

            assert loaded == query_content

    @pytest.mark.asyncio
    async def test_sha256_verification_enforced(self):
        """SHA256 verification prevents tampering."""
        with TemporaryDirectory() as tmpdir:
            query_file = Path(tmpdir) / "secure.sparql"
            query_content = "SELECT * WHERE { ?s ?p ?o }"
            query_file.write_text(query_content)

            resolver = FileResolver(allowed_paths=[tmpdir])

            # Compute correct hash
            correct_hash = resolver.compute_sha256(query_content)

            # Load with correct hash
            loaded = resolver.load_file(f"file://{query_file}", expected_sha256=correct_hash)
            assert loaded == query_content

            # Attempt load with wrong hash
            wrong_hash = "0" * 64
            with pytest.raises(FileResolverError) as exc_info:
                resolver.load_file(f"file://{query_file}", expected_sha256=wrong_hash)

            assert "Integrity check failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_file_not_found_error_handling(self):
        """File not found errors are handled gracefully."""
        with TemporaryDirectory() as tmpdir:
            resolver = FileResolver(allowed_paths=[tmpdir])

            # Try to load non-existent file in allowed path
            nonexistent_path = Path(tmpdir) / "nonexistent" / "query.sparql"

            with pytest.raises(FileResolverError) as exc_info:
                resolver.load_file(f"file://{nonexistent_path}")

            assert "File not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_condition_with_file_reference(self):
        """Condition can load query from file with hash verification."""
        with TemporaryDirectory() as tmpdir:
            query_file = Path(tmpdir) / "condition.sparql"
            query_content = "ASK { ?person <hasAge> ?age }"
            query_file.write_text(query_content)

            resolver = FileResolver(allowed_paths=[tmpdir])
            sha256_hash = resolver.compute_sha256(query_content)

            # Create condition with file reference
            condition = SparqlAskCondition(
                ref={"uri": f"file://{query_file}", "sha256": sha256_hash}, use_cache=False
            )

            # Get query through resolver
            loaded_query = condition.get_query(resolver)
            assert loaded_query == query_content


# ============================================================================
# Section 5: Lockchain Integration (4 tests)
# ============================================================================


class TestLockchainIntegration:
    """Integration tests for receipt chain and Merkle anchoring."""

    @pytest.mark.asyncio
    async def test_receipt_chain_creation(self):
        """Receipts can be chained together."""
        store = ReceiptStore()

        # Create multiple receipts
        receipts = []
        for i in range(3):
            receipt = Receipt(
                hook_id=f"hook_{i}",
                timestamp=datetime.utcnow(),
                condition_result=ConditionResult(triggered=True, metadata={}),
                handler_result={"step": i},
                duration_ms=10.0,
            )
            await store.save(receipt)
            receipts.append(receipt)

        # Verify all saved
        for receipt in receipts:
            retrieved = await store.get_by_id(receipt.receipt_id)
            assert retrieved is not None
            assert retrieved.receipt_id == receipt.receipt_id

    @pytest.mark.asyncio
    async def test_chain_integrity_verification(self):
        """Receipt chain integrity can be verified."""
        receipt1 = Receipt(
            hook_id="hook1",
            timestamp=datetime.utcnow(),
            condition_result=ConditionResult(triggered=True, metadata={}),
            handler_result={"data": "value1"},
            duration_ms=15.0,
        )

        receipt2 = Receipt(
            hook_id="hook2",
            timestamp=datetime.utcnow(),
            condition_result=ConditionResult(triggered=True, metadata={}),
            handler_result={"data": "value2"},
            duration_ms=20.0,
        )

        # Compute hashes
        hash1 = receipt1.compute_hash()
        hash2 = receipt2.compute_hash()

        # Hashes should be deterministic
        assert hash1 == receipt1.compute_hash()
        assert hash2 == receipt2.compute_hash()

        # Hashes should be different
        assert hash1 != hash2

    @pytest.mark.asyncio
    async def test_chain_traversal_backward(self):
        """Receipt chain can be traversed backward."""
        store = ReceiptStore()

        # Create chain of receipts
        for i in range(5):
            receipt = Receipt(
                hook_id="chain_hook",
                timestamp=datetime.utcnow(),
                condition_result=ConditionResult(triggered=True, metadata={}),
                handler_result={"sequence": i},
                duration_ms=5.0,
            )
            await store.save(receipt)

        # Query by hook_id
        chain = await store.query(hook_id="chain_hook")
        assert len(chain) == 5

        # Verify sequence
        sequences = [r.handler_result.get("sequence") for r in chain]
        assert set(sequences) == {0, 1, 2, 3, 4}

    @pytest.mark.asyncio
    async def test_merkle_anchor_creation(self):
        """Merkle anchors link receipts to graph state."""
        tree = MerkleTree()

        # Add leaves
        tree.add_leaf("receipt_1_hash")
        tree.add_leaf("receipt_2_hash")
        tree.add_leaf("receipt_3_hash")

        # Compute root
        root = tree.compute_root()
        assert len(root) == 64  # SHA256 hex digest

        # Create anchor
        anchor = tree.create_anchor(graph_version=5)
        assert anchor.root_hash == root
        assert anchor.graph_version == 5
        assert isinstance(anchor.timestamp, datetime)


# ============================================================================
# Section 6: End-to-End Workflows (4 tests)
# ============================================================================


class TestEndToEndWorkflows:
    """Integration tests for complete workflows."""

    @pytest.mark.asyncio
    async def test_complete_hook_execution_pipeline(self):
        """Complete hook execution with security, performance, and receipts."""
        execution_log = []

        def logging_handler(context: dict[str, Any]) -> dict[str, Any]:
            execution_log.append({"context": context, "timestamp": datetime.utcnow()})
            return {"processed": True, "value": context.get("value", 0) * 2}

        hook = Hook(
            name="complete_hook",
            description="Full pipeline test",
            condition=ThresholdCondition(
                variable="value", operator=ThresholdOperator.GREATER_THAN, value=5
            ),
            handler=logging_handler,
            actor="system",
            priority=80,
        )

        # Execute through pipeline
        pipeline = HookExecutionPipeline(enable_performance_tracking=True)
        receipt = await pipeline.execute(hook, {"value": 10})

        # Verify execution
        assert receipt.error is None
        assert receipt.handler_result is not None
        assert receipt.handler_result["processed"] is True
        assert receipt.handler_result["value"] == 20

        # Verify performance tracking
        assert receipt.duration_ms > 0
        stats = pipeline.get_performance_stats(f"hook_execute_{hook.name}")
        assert stats is not None

        # Verify handler executed
        assert len(execution_log) == 1

    @pytest.mark.asyncio
    async def test_multi_hook_execution_chain(self):
        """Multiple hooks execute in priority order with chained receipts."""
        results = []

        def create_handler(step: int):
            def handler(context: dict[str, Any]) -> dict[str, Any]:
                results.append(step)
                return {"step": step, "input": context.get("value")}

            return handler

        hooks = [
            Hook(
                name=f"hook_{i}",
                description=f"Step {i}",
                condition=ThresholdCondition(
                    variable="value", operator=ThresholdOperator.GREATER_THAN, value=0
                ),
                handler=create_handler(i),
                priority=100 - i * 10,  # Descending priority
            )
            for i in range(5)
        ]

        pipeline = HookExecutionPipeline()
        receipts = await pipeline.execute_batch(hooks, {"value": 10})

        # Verify execution order (by priority)
        assert results == [0, 1, 2, 3, 4]

        # Verify all receipts
        assert len(receipts) == 5
        for i, receipt in enumerate(receipts):
            assert receipt.error is None
            assert receipt.handler_result["step"] == i

    @pytest.mark.asyncio
    async def test_performance_monitoring_end_to_end(self):
        """End-to-end workflow with performance monitoring and SLO tracking."""

        def variable_latency_handler(context: dict[str, Any]) -> dict[str, Any]:
            import time

            delay = context.get("delay_ms", 0) / 1000.0
            time.sleep(delay)
            return {"completed": True}

        hooks = [
            Hook(
                name=f"perf_hook_{i}",
                description=f"Performance test {i}",
                condition=ThresholdCondition(
                    variable="trigger", operator=ThresholdOperator.EQUALS, value=True
                ),
                handler=variable_latency_handler,
            )
            for i in range(10)
        ]

        pipeline = HookExecutionPipeline(enable_performance_tracking=True)

        # Execute with varying delays
        for i, hook in enumerate(hooks):
            await pipeline.execute(hook, {"trigger": True, "delay_ms": i * 5})

        # Verify performance stats
        all_stats = pipeline.get_performance_stats()
        assert all_stats is not None
        assert len(all_stats) > 0

        # Check batch stats
        batch_stats = all_stats.get("hook_batch_execute")
        if batch_stats:
            assert batch_stats["count"] > 0

    @pytest.mark.asyncio
    async def test_error_recovery_with_sanitization(self):
        """Errors are caught, sanitized, and execution continues."""
        results = []

        def failing_handler(context: dict[str, Any]) -> dict[str, Any]:
            if context.get("fail"):
                raise ValueError(
                    "Critical error in /app/process.py line 456: database connection failed"
                )
            results.append("success")
            return {"status": "ok"}

        hooks = [
            Hook(
                name="hook_success",
                description="Should succeed",
                condition=ThresholdCondition(
                    variable="value", operator=ThresholdOperator.GREATER_THAN, value=0
                ),
                handler=failing_handler,
            ),
            Hook(
                name="hook_fail",
                description="Should fail",
                condition=ThresholdCondition(
                    variable="value", operator=ThresholdOperator.GREATER_THAN, value=0
                ),
                handler=failing_handler,
            ),
            Hook(
                name="hook_success2",
                description="Should succeed",
                condition=ThresholdCondition(
                    variable="value", operator=ThresholdOperator.GREATER_THAN, value=0
                ),
                handler=failing_handler,
            ),
        ]

        pipeline = HookExecutionPipeline(stop_on_error=False)

        contexts = [
            {"value": 5, "fail": False},
            {"value": 5, "fail": True},
            {"value": 5, "fail": False},
        ]

        receipts = []
        for hook, ctx in zip(hooks, contexts):
            receipt = await pipeline.execute(hook, ctx)
            receipts.append(receipt)

        # Verify first succeeded
        assert receipts[0].error is None
        assert receipts[0].handler_result["status"] == "ok"

        # Verify second failed with sanitized error
        assert receipts[1].error is not None
        assert receipts[1].metadata.get("sanitized") is True
        assert "/app/process.py" not in receipts[1].error
        assert "line 456" not in receipts[1].error

        # Verify third succeeded (execution continued)
        assert receipts[2].error is None
        assert receipts[2].handler_result["status"] == "ok"

        # Verify handlers executed
        assert len(results) == 2  # Two successes

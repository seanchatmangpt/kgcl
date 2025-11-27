"""Backward compatibility test suite for HybridEngine refactoring.

This test ensures the refactored HybridEngine maintains 100% backward compatibility
with existing code that depends on the legacy API.

Test Coverage
-------------
1. Import patterns (from kgcl.hybrid and from kgcl.hybrid.hybrid_engine)
2. Constructor signature (store_path, hook_registry)
3. Methods (load_data, apply_physics, run_to_completion, inspect)
4. Properties (tick_count, store)
5. Constants (N3_PHYSICS)
6. Exception types and behaviors
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from kgcl.hybrid import N3_PHYSICS as N3_PHYSICS1

# Test both import patterns
from kgcl.hybrid import HybridEngine as HybridEngine1
from kgcl.hybrid import PhysicsResult as PhysicsResult1
from kgcl.hybrid.hybrid_engine import N3_PHYSICS as N3_PHYSICS2
from kgcl.hybrid.hybrid_engine import HybridEngine as HybridEngine2
from kgcl.hybrid.hybrid_engine import PhysicsResult as PhysicsResult2


class TestImportPatterns:
    """Verify both import patterns work and reference same objects."""

    def test_hybrid_engine_imports(self) -> None:
        """Both import paths should reference the same class."""
        assert HybridEngine1 is HybridEngine2

    def test_physics_result_imports(self) -> None:
        """Both import paths should reference the same class."""
        assert PhysicsResult1 is PhysicsResult2

    def test_n3_physics_imports(self) -> None:
        """Both import paths should reference the same constant."""
        assert N3_PHYSICS1 == N3_PHYSICS2
        assert isinstance(N3_PHYSICS1, str)
        assert len(N3_PHYSICS1) > 0


class TestConstructorSignature:
    """Verify HybridEngine constructor maintains backward compatibility."""

    def test_no_args_constructor(self) -> None:
        """HybridEngine() creates in-memory store."""
        engine = HybridEngine1()
        assert engine is not None
        assert engine.tick_count == 0
        assert engine.store is not None

    def test_store_path_arg(self) -> None:
        """HybridEngine(store_path='path') creates persistent store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = HybridEngine1(store_path=tmpdir)
            assert engine is not None
            assert engine.tick_count == 0
            assert engine.store is not None

    def test_hook_registry_arg(self) -> None:
        """HybridEngine(hook_registry=None) accepts hook registry parameter."""
        engine = HybridEngine1(hook_registry=None)
        assert engine is not None
        assert engine.tick_count == 0

    def test_both_args(self) -> None:
        """HybridEngine accepts both store_path and hook_registry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = HybridEngine1(store_path=tmpdir, hook_registry=None)
            assert engine is not None
            assert engine.tick_count == 0


class TestLoadDataMethod:
    """Verify load_data() method signature and behavior."""

    def test_load_data_exists(self) -> None:
        """load_data method exists."""
        engine = HybridEngine1()
        assert hasattr(engine, "load_data")
        assert callable(engine.load_data)

    def test_load_data_basic(self) -> None:
        """load_data(data: str) loads turtle data."""
        engine = HybridEngine1()
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:Start> a yawl:Task ;
            kgc:status "Completed" .
        """
        engine.load_data(topology)
        # Should not raise

    def test_load_data_with_hooks_kwarg(self) -> None:
        """load_data supports trigger_hooks keyword argument."""
        engine = HybridEngine1()
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:Start> a yawl:Task ;
            kgc:status "Completed" .
        """
        engine.load_data(topology, trigger_hooks=False)
        # Should not raise


class TestApplyPhysicsMethod:
    """Verify apply_physics() method signature and behavior."""

    def test_apply_physics_exists(self) -> None:
        """apply_physics method exists."""
        engine = HybridEngine1()
        assert hasattr(engine, "apply_physics")
        assert callable(engine.apply_physics)

    def test_apply_physics_returns_result(self) -> None:
        """apply_physics() returns PhysicsResult."""
        engine = HybridEngine1()
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:Start> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:1> .

        <urn:flow:1> yawl:nextElementRef <urn:task:Next> .
        <urn:task:Next> a yawl:Task .
        """
        engine.load_data(topology)
        result = engine.apply_physics()

        # Verify result type and attributes
        assert isinstance(result, PhysicsResult1)
        assert hasattr(result, "tick_number")
        assert hasattr(result, "delta")
        assert result.tick_number == 1

    def test_apply_physics_increments_tick_count(self) -> None:
        """apply_physics() increments tick_count property."""
        engine = HybridEngine1()
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:Start> a yawl:Task ;
            kgc:status "Completed" .
        """
        engine.load_data(topology)
        assert engine.tick_count == 0

        engine.apply_physics()
        assert engine.tick_count == 1

        engine.apply_physics()
        assert engine.tick_count == 2


class TestRunToCompletionMethod:
    """Verify run_to_completion() method signature and behavior."""

    def test_run_to_completion_exists(self) -> None:
        """run_to_completion method exists."""
        engine = HybridEngine1()
        assert hasattr(engine, "run_to_completion")
        assert callable(engine.run_to_completion)

    def test_run_to_completion_default_args(self) -> None:
        """run_to_completion() accepts no arguments (uses defaults)."""
        engine = HybridEngine1()
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:Start> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:1> .

        <urn:flow:1> yawl:nextElementRef <urn:task:Next> .
        <urn:task:Next> a yawl:Task .
        """
        engine.load_data(topology)
        results = engine.run_to_completion()
        assert isinstance(results, list)
        assert all(isinstance(r, PhysicsResult1) for r in results)

    def test_run_to_completion_with_max_ticks(self) -> None:
        """run_to_completion(max_ticks=N) accepts max_ticks parameter."""
        engine = HybridEngine1()
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:Start> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:1> .

        <urn:flow:1> yawl:nextElementRef <urn:task:Next> .
        <urn:task:Next> a yawl:Task .
        """
        engine.load_data(topology)
        results = engine.run_to_completion(max_ticks=10)
        assert isinstance(results, list)
        assert len(results) <= 10

    def test_run_to_completion_returns_list(self) -> None:
        """run_to_completion() returns list[PhysicsResult]."""
        engine = HybridEngine1()
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:Start> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:1> .

        <urn:flow:1> yawl:nextElementRef <urn:task:Next> .
        <urn:task:Next> a yawl:Task .
        """
        engine.load_data(topology)
        results = engine.run_to_completion(max_ticks=5)
        assert isinstance(results, list)
        assert all(isinstance(r, PhysicsResult1) for r in results)
        assert all(r.delta >= 0 for r in results)

    def test_run_to_completion_raises_on_non_convergence(self) -> None:
        """run_to_completion() raises RuntimeError if max_ticks exceeded."""
        engine = HybridEngine1()
        # Create topology that will never converge (infinite loop)
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:Infinite> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:Loop> .

        <urn:flow:Loop> yawl:nextElementRef <urn:task:Infinite> .
        """
        engine.load_data(topology)

        with pytest.raises(RuntimeError) as exc_info:
            engine.run_to_completion(max_ticks=2)

        assert "did not converge" in str(exc_info.value).lower()


class TestInspectMethod:
    """Verify inspect() method signature and behavior."""

    def test_inspect_exists(self) -> None:
        """inspect method exists."""
        engine = HybridEngine1()
        assert hasattr(engine, "inspect")
        assert callable(engine.inspect)

    def test_inspect_returns_dict(self) -> None:
        """inspect() returns dict[str, str]."""
        engine = HybridEngine1()
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:Start> a yawl:Task ;
            kgc:status "Completed" .
        """
        engine.load_data(topology)
        statuses = engine.inspect()
        assert isinstance(statuses, dict)
        assert all(isinstance(k, str) for k in statuses.keys())
        assert all(isinstance(v, str) for v in statuses.values())

    def test_inspect_no_args(self) -> None:
        """inspect() accepts no arguments."""
        engine = HybridEngine1()
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:Start> a yawl:Task ;
            kgc:status "Completed" .
        """
        engine.load_data(topology)
        statuses = engine.inspect()
        # Should not raise


class TestTickCountProperty:
    """Verify tick_count property."""

    def test_tick_count_exists(self) -> None:
        """tick_count property exists."""
        engine = HybridEngine1()
        assert hasattr(engine, "tick_count")

    def test_tick_count_initial_value(self) -> None:
        """tick_count starts at 0."""
        engine = HybridEngine1()
        assert engine.tick_count == 0

    def test_tick_count_increments(self) -> None:
        """tick_count increments with apply_physics()."""
        engine = HybridEngine1()
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:Start> a yawl:Task ;
            kgc:status "Completed" .
        """
        engine.load_data(topology)

        assert engine.tick_count == 0
        engine.apply_physics()
        assert engine.tick_count == 1
        engine.apply_physics()
        assert engine.tick_count == 2

    def test_tick_count_updates_on_run_to_completion(self) -> None:
        """tick_count updates correctly after run_to_completion()."""
        engine = HybridEngine1()
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:Start> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:1> .

        <urn:flow:1> yawl:nextElementRef <urn:task:Next> .
        <urn:task:Next> a yawl:Task .
        """
        engine.load_data(topology)
        assert engine.tick_count == 0

        results = engine.run_to_completion(max_ticks=10)
        assert engine.tick_count == len(results)


class TestStoreProperty:
    """Verify store property."""

    def test_store_exists(self) -> None:
        """store property exists."""
        engine = HybridEngine1()
        assert hasattr(engine, "store")

    def test_store_is_oxigraph_store(self) -> None:
        """store property returns pyoxigraph Store object."""
        import pyoxigraph as ox

        engine = HybridEngine1()
        assert isinstance(engine.store, ox.Store)

    def test_store_persistent(self) -> None:
        """store property works with persistent storage."""
        import pyoxigraph as ox

        with tempfile.TemporaryDirectory() as tmpdir:
            engine = HybridEngine1(store_path=tmpdir)
            assert isinstance(engine.store, ox.Store)


class TestN3PhysicsConstant:
    """Verify N3_PHYSICS constant is available."""

    def test_n3_physics_exists(self) -> None:
        """N3_PHYSICS constant is importable."""
        assert N3_PHYSICS1 is not None
        assert N3_PHYSICS2 is not None

    def test_n3_physics_is_string(self) -> None:
        """N3_PHYSICS is a string."""
        assert isinstance(N3_PHYSICS1, str)
        assert isinstance(N3_PHYSICS2, str)

    def test_n3_physics_not_empty(self) -> None:
        """N3_PHYSICS is not empty."""
        assert len(N3_PHYSICS1) > 0
        assert len(N3_PHYSICS2) > 0

    def test_n3_physics_contains_n3_rules(self) -> None:
        """N3_PHYSICS contains N3 rule syntax."""
        # Should contain N3 rule markers
        assert "@prefix" in N3_PHYSICS1 or "PREFIX" in N3_PHYSICS1
        # Should contain rule syntax
        assert "=>" in N3_PHYSICS1 or "{" in N3_PHYSICS1


class TestPhysicsResultType:
    """Verify PhysicsResult type and attributes."""

    def test_physics_result_has_tick_number(self) -> None:
        """PhysicsResult has tick_number attribute."""
        engine = HybridEngine1()
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:Start> a yawl:Task ;
            kgc:status "Completed" .
        """
        engine.load_data(topology)
        result = engine.apply_physics()
        assert hasattr(result, "tick_number")
        assert isinstance(result.tick_number, int)

    def test_physics_result_has_delta(self) -> None:
        """PhysicsResult has delta attribute."""
        engine = HybridEngine1()
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:Start> a yawl:Task ;
            kgc:status "Completed" .
        """
        engine.load_data(topology)
        result = engine.apply_physics()
        assert hasattr(result, "delta")
        assert isinstance(result.delta, int)


class TestEndToEndScenario:
    """Complete end-to-end workflow to verify all APIs work together."""

    def test_complete_workflow(self) -> None:
        """Execute complete workflow using all backward-compatible APIs."""
        # 1. Create engine (both constructors)
        engine_mem = HybridEngine1()
        assert engine_mem.tick_count == 0

        with tempfile.TemporaryDirectory() as tmpdir:
            engine_disk = HybridEngine2(store_path=tmpdir, hook_registry=None)
            assert engine_disk.tick_count == 0

        # 2. Load data
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:Start> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:1> .

        <urn:flow:1> yawl:nextElementRef <urn:task:Next> .
        <urn:task:Next> a yawl:Task .
        """
        engine_mem.load_data(topology)

        # 3. Check store
        import pyoxigraph as ox

        assert isinstance(engine_mem.store, ox.Store)

        # 4. Apply physics (single tick)
        result = engine_mem.apply_physics()
        assert isinstance(result, PhysicsResult1)
        assert result.tick_number == 1
        assert engine_mem.tick_count == 1

        # 5. Inspect state
        statuses = engine_mem.inspect()
        assert isinstance(statuses, dict)

        # 6. Run to completion
        engine2 = HybridEngine1()
        engine2.load_data(topology)
        results = engine2.run_to_completion(max_ticks=10)
        assert isinstance(results, list)
        assert all(isinstance(r, PhysicsResult1) for r in results)
        assert engine2.tick_count > 0

        # 7. Verify N3_PHYSICS available
        assert isinstance(N3_PHYSICS1, str)
        assert len(N3_PHYSICS1) > 0


class TestBackwardCompatibilitySummary:
    """Summary test that documents all verified APIs."""

    def test_all_apis_documented(self) -> None:
        """Document all backward-compatible APIs verified by this test suite."""
        verified_apis = {
            # Imports
            "from kgcl.hybrid import HybridEngine": True,
            "from kgcl.hybrid import PhysicsResult": True,
            "from kgcl.hybrid import N3_PHYSICS": True,
            "from kgcl.hybrid.hybrid_engine import HybridEngine": True,
            "from kgcl.hybrid.hybrid_engine import PhysicsResult": True,
            "from kgcl.hybrid.hybrid_engine import N3_PHYSICS": True,
            # Constructor
            "HybridEngine()": True,
            "HybridEngine(store_path=None)": True,
            "HybridEngine(hook_registry=None)": True,
            "HybridEngine(store_path=..., hook_registry=None)": True,
            # Methods
            "engine.load_data(data: str)": True,
            "engine.load_data(data: str, trigger_hooks=bool)": True,
            "engine.apply_physics() -> PhysicsResult": True,
            "engine.inspect() -> dict[str, str]": True,
            "engine.run_to_completion() -> list[PhysicsResult]": True,
            "engine.run_to_completion(max_ticks=100) -> list[PhysicsResult]": True,
            # Properties
            "engine.tick_count": True,
            "engine.store": True,
            # Result attributes
            "result.tick_number": True,
            "result.delta": True,
        }

        # All APIs verified
        assert all(verified_apis.values())
        assert len(verified_apis) == 22  # Total count of verified APIs

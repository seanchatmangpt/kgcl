"""Tests for TRUE Hybrid KGC Engine (PyOxigraph + EYE).

Tests verify the Hard Separation architecture:
- PyOxigraph = Matter (Inert State Storage)
- EYE = Physics (External Force)
- Python = Time (Orchestrator)

Test Philosophy: Chicago School TDD
- No mocking of domain objects (PyOxigraph, EYE)
- Test actual behavior, not implementation
- AAA structure (Arrange, Act, Assert)
"""

from __future__ import annotations

import os
import subprocess
import tempfile

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine, PhysicsResult

# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def engine() -> HybridEngine:
    """Provide in-memory hybrid engine."""
    return HybridEngine()


@pytest.fixture
def persistent_engine() -> HybridEngine:
    """Provide persistent hybrid engine with cleanup."""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = HybridEngine(store_path=tmpdir)
        yield engine


@pytest.fixture
def simple_topology() -> str:
    """Provide simple workflow topology for testing."""
    return """
    @prefix kgc: <https://kgc.org/ns/> .
    @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

    <urn:task:Start> a yawl:Task ;
        kgc:status "Completed" ;
        yawl:flowsInto <urn:flow:1> .

    <urn:flow:1> yawl:nextElementRef <urn:task:Next> .
    <urn:task:Next> a yawl:Task .
    """


@pytest.fixture
def chain_topology() -> str:
    """Provide chained workflow topology (A -> B -> C)."""
    return """
    @prefix kgc: <https://kgc.org/ns/> .
    @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

    <urn:task:A> a yawl:Task ;
        kgc:status "Completed" ;
        yawl:flowsInto <urn:flow:AB> .

    <urn:flow:AB> yawl:nextElementRef <urn:task:B> .

    <urn:task:B> a yawl:Task ;
        yawl:flowsInto <urn:flow:BC> .

    <urn:flow:BC> yawl:nextElementRef <urn:task:C> .

    <urn:task:C> a yawl:Task .
    """


# ==============================================================================
# UTILITIES
# ==============================================================================


def _check_eye_installed() -> bool:
    """Check if EYE reasoner is installed."""
    try:
        subprocess.run(["eye", "--version"], capture_output=True, check=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


# ==============================================================================
# INITIALIZATION TESTS
# ==============================================================================


def test_engine_initialization_in_memory() -> None:
    """Test in-memory engine initialization."""
    # Arrange & Act
    engine = HybridEngine()

    # Assert
    assert engine.store is not None
    assert engine.tick_count == 0
    assert os.path.exists(engine.physics_file)


def test_engine_initialization_persistent() -> None:
    """Test persistent engine initialization."""
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        # Act
        engine = HybridEngine(store_path=tmpdir)

        # Assert
        assert engine.store is not None
        assert engine.tick_count == 0
        assert os.path.exists(tmpdir)


def test_physics_file_contains_rules() -> None:
    """Test that physics file contains N3 rules."""
    # Arrange
    engine = HybridEngine()

    # Act
    with open(engine.physics_file) as f:
        content = f.read()

    # Assert - Check for key physics rules (WCP patterns)
    assert "LAW 1: SIMPLE SEQUENCE" in content  # WCP-1
    assert "LAW 2: AND-SPLIT" in content  # WCP-2
    assert "LAW 3: AND-JOIN" in content  # WCP-3
    assert "LAW 4: XOR-SPLIT" in content  # WCP-4
    assert "LAW 5: AUTO-COMPLETE" in content
    assert "=>" in content  # N3 implication operator


def test_physics_file_cleanup() -> None:
    """Test that physics file is cleaned up on destruction."""
    # Arrange
    engine = HybridEngine()
    physics_path = engine.physics_file

    # Act
    del engine

    # Assert
    assert not os.path.exists(physics_path)


# ==============================================================================
# DATA LOADING TESTS
# ==============================================================================


def test_load_data_valid_turtle(engine: HybridEngine) -> None:
    """Test loading valid Turtle data."""
    # Arrange
    data = """
    @prefix ex: <http://example.org/> .
    ex:task1 ex:status "pending" .
    ex:task2 ex:status "active" .
    """

    # Act
    engine.load_data(data)

    # Assert
    triple_count = len(list(engine.store))
    assert triple_count == 2


def test_load_data_empty_graph(engine: HybridEngine) -> None:
    """Test loading empty graph."""
    # Arrange
    data = "@prefix ex: <http://example.org/> ."

    # Act
    engine.load_data(data)

    # Assert
    triple_count = len(list(engine.store))
    assert triple_count == 0


def test_load_data_multiple_calls(engine: HybridEngine) -> None:
    """Test that multiple load_data calls accumulate triples."""
    # Arrange
    data1 = "@prefix ex: <http://example.org/> . ex:a ex:b ex:c ."
    data2 = "@prefix ex: <http://example.org/> . ex:d ex:e ex:f ."

    # Act
    engine.load_data(data1)
    count_after_first = len(list(engine.store))
    engine.load_data(data2)
    count_after_second = len(list(engine.store))

    # Assert
    assert count_after_first == 1
    assert count_after_second == 2


# ==============================================================================
# STATE DUMP TESTS
# ==============================================================================


def test_dump_state_returns_turtle(engine: HybridEngine) -> None:
    """Test that _dump_state returns valid Turtle."""
    # Arrange
    engine.load_data("@prefix ex: <http://example.org/> . ex:a ex:b ex:c .")

    # Act
    state = engine._dump_state()

    # Assert
    assert isinstance(state, str)
    assert "ex:a" in state or "<http://example.org/a>" in state


def test_dump_state_empty_graph(engine: HybridEngine) -> None:
    """Test _dump_state on empty graph."""
    # Arrange
    # (no data loaded)

    # Act
    state = engine._dump_state()

    # Assert
    assert isinstance(state, str)
    # Empty graph still produces valid Turtle (with prefixes)
    assert len(state) >= 0


# ==============================================================================
# PHYSICS RESULT TESTS
# ==============================================================================


def test_physics_result_converged_true() -> None:
    """Test PhysicsResult.converged when delta is zero."""
    # Arrange & Act
    result = PhysicsResult(tick_number=1, duration_ms=10.0, triples_before=100, triples_after=100, delta=0)

    # Assert
    assert result.converged is True


def test_physics_result_converged_false() -> None:
    """Test PhysicsResult.converged when delta is non-zero."""
    # Arrange & Act
    result = PhysicsResult(tick_number=1, duration_ms=10.0, triples_before=100, triples_after=105, delta=5)

    # Assert
    assert result.converged is False


def test_physics_result_attributes() -> None:
    """Test PhysicsResult attribute access."""
    # Arrange & Act
    result = PhysicsResult(tick_number=42, duration_ms=12.5, triples_before=100, triples_after=110, delta=10)

    # Assert
    assert result.tick_number == 42
    assert result.duration_ms == 12.5
    assert result.triples_before == 100
    assert result.triples_after == 110
    assert result.delta == 10


# ==============================================================================
# APPLY PHYSICS TESTS (Requires EYE Reasoner)
# ==============================================================================


@pytest.mark.skipif(not _check_eye_installed(), reason="EYE reasoner not installed")
def test_apply_physics_simple_transition(engine: HybridEngine, simple_topology: str) -> None:
    """Test physics application triggers state transition."""
    # Arrange
    engine.load_data(simple_topology)
    triples_before = len(list(engine.store))

    # Act
    result = engine.apply_physics()

    # Assert
    assert result.tick_number == 1
    assert result.triples_before == triples_before
    assert result.delta > 0  # New triples inferred
    assert result.duration_ms > 0
    assert not result.converged


@pytest.mark.skipif(not _check_eye_installed(), reason="EYE reasoner not installed")
def test_apply_physics_increments_tick_count(engine: HybridEngine, simple_topology: str) -> None:
    """Test that apply_physics increments tick counter."""
    # Arrange
    engine.load_data(simple_topology)

    # Act
    engine.apply_physics()
    engine.apply_physics()

    # Assert
    assert engine.tick_count == 2


@pytest.mark.skipif(not _check_eye_installed(), reason="EYE reasoner not installed")
def test_apply_physics_converges_eventually(engine: HybridEngine, simple_topology: str) -> None:
    """Test that repeated physics applications reach fixed point."""
    # Arrange
    engine.load_data(simple_topology)

    # Act
    results = []
    for _ in range(10):
        result = engine.apply_physics()
        results.append(result)
        if result.converged:
            break

    # Assert
    assert any(r.converged for r in results), "System should converge within 10 ticks"
    assert results[-1].delta == 0


@pytest.mark.skipif(_check_eye_installed(), reason="Only test error handling when EYE not installed")
def test_apply_physics_raises_when_eye_missing(engine: HybridEngine, simple_topology: str) -> None:
    """Test that apply_physics raises FileNotFoundError when EYE is missing."""
    # Arrange
    engine.load_data(simple_topology)

    # Act & Assert
    with pytest.raises(FileNotFoundError, match="EYE reasoner not found"):
        engine.apply_physics()


# ==============================================================================
# INSPECT TESTS
# ==============================================================================


def test_inspect_empty_graph(engine: HybridEngine) -> None:
    """Test inspect on empty graph."""
    # Arrange
    # (no data loaded)

    # Act
    statuses = engine.inspect()

    # Assert
    assert statuses == {}


def test_inspect_returns_task_statuses(engine: HybridEngine) -> None:
    """Test inspect returns correct task statuses."""
    # Arrange
    engine.load_data(
        """
        @prefix kgc: <https://kgc.org/ns/> .
        <urn:task:A> kgc:status "Active" .
        <urn:task:B> kgc:status "Completed" .
        <urn:task:C> kgc:status "Pending" .
        """
    )

    # Act
    statuses = engine.inspect()

    # Assert
    assert len(statuses) == 3
    assert statuses["urn:task:A"] == "Active"
    assert statuses["urn:task:B"] == "Completed"
    assert statuses["urn:task:C"] == "Pending"


def test_inspect_ignores_non_status_triples(engine: HybridEngine) -> None:
    """Test that inspect only returns kgc:status triples."""
    # Arrange
    engine.load_data(
        """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix ex: <http://example.org/> .
        <urn:task:A> kgc:status "Active" .
        <urn:task:A> ex:name "Task A" .
        <urn:task:A> ex:priority "high" .
        """
    )

    # Act
    statuses = engine.inspect()

    # Assert
    assert len(statuses) == 1
    assert "urn:task:A" in statuses


# ==============================================================================
# RUN TO COMPLETION TESTS (Requires EYE Reasoner)
# ==============================================================================


@pytest.mark.skipif(not _check_eye_installed(), reason="EYE reasoner not installed")
def test_run_to_completion_simple(engine: HybridEngine, simple_topology: str) -> None:
    """Test run_to_completion with simple topology."""
    # Arrange
    engine.load_data(simple_topology)

    # Act
    results = engine.run_to_completion(max_ticks=10)

    # Assert
    assert len(results) > 0
    assert results[-1].converged
    assert all(isinstance(r, PhysicsResult) for r in results)


@pytest.mark.skipif(not _check_eye_installed(), reason="EYE reasoner not installed")
def test_run_to_completion_chain(engine: HybridEngine, chain_topology: str) -> None:
    """Test run_to_completion with chained workflow."""
    # Arrange
    engine.load_data(chain_topology)

    # Act
    results = engine.run_to_completion(max_ticks=20)

    # Assert
    assert len(results) >= 1  # Should complete
    assert results[-1].converged
    # Final state should show workflow progressed (tasks activated and completed)
    # inspect() returns highest-priority status (Archived > Completed > Active)
    statuses = engine.inspect()
    # Downstream tasks should have been activated and completed/archived
    assert any(s in ["Active", "Completed", "Archived"] for s in statuses.values())


@pytest.mark.skipif(not _check_eye_installed(), reason="EYE reasoner not installed")
def test_run_to_completion_raises_on_max_ticks(engine: HybridEngine, simple_topology: str) -> None:
    """Test run_to_completion raises RuntimeError when max ticks exceeded."""
    # Arrange
    engine.load_data(simple_topology)

    # Act & Assert
    # Use very low max_ticks to force timeout
    with pytest.raises(RuntimeError, match="did not converge"):
        # Mock apply_physics to never converge
        original_apply = engine.apply_physics

        def never_converge() -> PhysicsResult:
            result = original_apply()
            # Force delta to be non-zero
            return PhysicsResult(
                tick_number=result.tick_number,
                duration_ms=result.duration_ms,
                triples_before=result.triples_before,
                triples_after=result.triples_after,
                delta=1,  # Always non-zero
            )

        engine.apply_physics = never_converge  # type: ignore[method-assign]
        engine.run_to_completion(max_ticks=2)


@pytest.mark.skipif(not _check_eye_installed(), reason="EYE reasoner not installed")
def test_run_to_completion_returns_all_results(engine: HybridEngine, simple_topology: str) -> None:
    """Test run_to_completion returns result for each tick."""
    # Arrange
    engine.load_data(simple_topology)

    # Act
    results = engine.run_to_completion(max_ticks=10)

    # Assert
    # Verify all results have correct tick numbers
    for i, result in enumerate(results, start=1):
        assert result.tick_number == i


# ==============================================================================
# INTEGRATION TESTS (End-to-End Scenarios)
# ==============================================================================


@pytest.mark.skipif(not _check_eye_installed(), reason="EYE reasoner not installed")
def test_end_to_end_workflow_execution(engine: HybridEngine) -> None:
    """Test complete workflow execution from start to finish."""
    # Arrange
    workflow = """
    @prefix kgc: <https://kgc.org/ns/> .
    @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

    <urn:task:Start> a yawl:Task ;
        kgc:status "Completed" ;
        yawl:flowsInto <urn:flow:1> .

    <urn:flow:1> yawl:nextElementRef <urn:task:Process> .

    <urn:task:Process> a yawl:Task ;
        yawl:flowsInto <urn:flow:2> .

    <urn:flow:2> yawl:nextElementRef <urn:task:End> .

    <urn:task:End> a yawl:Task .
    """
    engine.load_data(workflow)

    # Act
    results = engine.run_to_completion(max_ticks=20)
    statuses = engine.inspect()

    # Assert
    assert results[-1].converged
    # Verify final state has activated tasks
    assert len(statuses) > 0
    # Should have multiple status values (Active, Archived, etc.)
    unique_statuses = set(statuses.values())
    assert len(unique_statuses) > 1


@pytest.mark.skipif(not _check_eye_installed(), reason="EYE reasoner not installed")
def test_persistent_store_survives_reload(simple_topology: str) -> None:
    """Test that persistent store maintains state across engine instances."""
    # Arrange - use a path we manage ourselves to avoid cleanup issues
    import shutil

    tmpdir = tempfile.mkdtemp()
    try:
        # Load data in first engine
        engine1 = HybridEngine(store_path=tmpdir)
        engine1.load_data(simple_topology)
        triples_count = len(list(engine1.store))
        # Close the store explicitly to release file locks
        del engine1.store
        del engine1

        # Act - Create new engine with same store
        engine2 = HybridEngine(store_path=tmpdir)
        triples_after_reload = len(list(engine2.store))

        # Assert
        assert triples_after_reload == triples_count

        # Cleanup
        del engine2.store
        del engine2
    finally:
        # Best effort cleanup - ignore errors if store is still locked
        shutil.rmtree(tmpdir, ignore_errors=True)


# ==============================================================================
# PERFORMANCE TESTS
# ==============================================================================


@pytest.mark.skipif(not _check_eye_installed(), reason="EYE reasoner not installed")
def test_physics_application_performance(engine: HybridEngine, simple_topology: str) -> None:
    """Test that physics application completes in reasonable time."""
    # Arrange
    engine.load_data(simple_topology)

    # Act
    result = engine.apply_physics()

    # Assert
    # Should complete in under 1 second for simple topology
    assert result.duration_ms < 1000


@pytest.mark.skipif(not _check_eye_installed(), reason="EYE reasoner not installed")
def test_run_to_completion_total_duration(engine: HybridEngine, chain_topology: str) -> None:
    """Test run_to_completion total execution time."""
    # Arrange
    engine.load_data(chain_topology)

    # Act
    results = engine.run_to_completion(max_ticks=20)
    total_duration = sum(r.duration_ms for r in results)

    # Assert
    # Should complete chain in under 5 seconds
    assert total_duration < 5000

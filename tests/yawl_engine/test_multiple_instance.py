"""Tests for YAWL Multiple Instance patterns (12-15).

Tests verify:
- Pattern 12: Fire-and-forget spawning without synchronization
- Pattern 13: Fixed instance count with synchronization barrier
- Pattern 14: Runtime-determined count with synchronization
- Pattern 15: Dynamic spawning based on events/conditions

All tests use Chicago School TDD with real RDF graphs and no mocking.
"""

# Magic values OK in tests

from __future__ import annotations

from typing import cast

import pytest
from rdflib import Graph, Literal, Namespace, URIRef

from kgcl.yawl_engine.patterns.multiple_instance import (
    ExecutionResult,
    MIDesignTime,
    MIDynamic,
    MIRunTimeKnown,
    MIState,
    MIWithoutSync,
    check_completion,
    mark_instance_complete,
)

# RDF namespaces
YAWL = Namespace("http://www.yawlsystem.com/yawl/elements/")
EX = Namespace("http://example.org/")


@pytest.fixture
def empty_graph() -> Graph:
    """Create empty RDF graph for testing."""
    return Graph()


@pytest.fixture
def sample_task() -> URIRef:
    """Sample workflow task for testing."""
    return EX.processOrder


class TestMIWithoutSync:
    """Tests for Pattern 12: MI without Synchronization."""

    def test_spawn_instances_basic(self, empty_graph: Graph, sample_task: URIRef) -> None:
        """Fire-and-forget spawning creates all instances."""
        pattern = MIWithoutSync()
        instance_ids = pattern.spawn_instances(empty_graph, sample_task, count=5)

        assert len(instance_ids) == 5
        assert all(isinstance(iid, str) for iid in instance_ids)
        assert all(str(sample_task) in iid for iid in instance_ids)

        # Verify all instances in graph
        instances = list(empty_graph.subjects(YAWL.instanceOf, sample_task))
        assert len(instances) == 5

    def test_spawn_instances_state_is_running(self, empty_graph: Graph, sample_task: URIRef) -> None:
        """Spawned instances start in RUNNING state."""
        pattern = MIWithoutSync()
        instance_ids = pattern.spawn_instances(empty_graph, sample_task, count=3)

        for iid in instance_ids:
            state_values = list(empty_graph.objects(URIRef(iid), YAWL.state))
            assert len(state_values) == 1
            assert str(state_values[0]) == MIState.RUNNING.value

    def test_spawn_instances_numbered(self, empty_graph: Graph, sample_task: URIRef) -> None:
        """Each instance has sequential number."""
        pattern = MIWithoutSync()
        pattern.spawn_instances(empty_graph, sample_task, count=4)

        numbers = []
        for instance_uri in empty_graph.subjects(YAWL.instanceOf, sample_task):
            num_obj = list(empty_graph.objects(instance_uri, YAWL.instanceNumber))
            assert len(num_obj) == 1
            numbers.append(int(cast(Literal, num_obj[0]).value))

        assert sorted(numbers) == [0, 1, 2, 3]

    def test_spawn_zero_count_raises(self, empty_graph: Graph, sample_task: URIRef) -> None:
        """Zero count raises ValueError."""
        pattern = MIWithoutSync()
        with pytest.raises(ValueError, match="must be positive"):
            pattern.spawn_instances(empty_graph, sample_task, count=0)

    def test_spawn_negative_count_raises(self, empty_graph: Graph, sample_task: URIRef) -> None:
        """Negative count raises ValueError."""
        pattern = MIWithoutSync()
        with pytest.raises(ValueError, match="must be positive"):
            pattern.spawn_instances(empty_graph, sample_task, count=-5)

    def test_execute_with_context(self, empty_graph: Graph, sample_task: URIRef) -> None:
        """Execute spawns instances from context count."""
        pattern = MIWithoutSync()
        result = pattern.execute(empty_graph, sample_task, context={"count": 7})

        assert result.success
        assert len(result.instance_ids) == 7
        assert result.state == MIState.RUNNING
        assert result.metadata["pattern"] == 12
        assert result.metadata["sync"] is False

    def test_execute_default_count(self, empty_graph: Graph, sample_task: URIRef) -> None:
        """Execute with no count defaults to 1 instance."""
        pattern = MIWithoutSync()
        result = pattern.execute(empty_graph, sample_task, context={})

        assert result.success
        assert len(result.instance_ids) == 1


class TestMIDesignTime:
    """Tests for Pattern 13: MI with Design-Time Knowledge."""

    def test_fixed_instance_count(self, empty_graph: Graph, sample_task: URIRef) -> None:
        """Pattern spawns exactly the design-time count."""
        pattern = MIDesignTime(instance_count=3)
        result = pattern.execute(empty_graph, sample_task, context={})

        assert result.success
        assert len(result.instance_ids) == 3
        assert result.metadata["instance_count"] == 3

    def test_synchronization_barrier_created(self, empty_graph: Graph, sample_task: URIRef) -> None:
        """Synchronization barrier tracks required instances."""
        pattern = MIDesignTime(instance_count=5)
        result = pattern.execute(empty_graph, sample_task, context={})

        parent_id = result.metadata["parent_id"]
        parent_uri = URIRef(parent_id)

        required = list(empty_graph.objects(parent_uri, YAWL.requiredInstances))
        completed = list(empty_graph.objects(parent_uri, YAWL.completedInstances))

        assert len(required) == 1
        assert int(cast(Literal, required[0]).value) == 5
        assert len(completed) == 1
        assert int(cast(Literal, completed[0]).value) == 0

    def test_all_instances_have_parent(self, empty_graph: Graph, sample_task: URIRef) -> None:
        """All instances reference same parent MI."""
        pattern = MIDesignTime(instance_count=4)
        result = pattern.execute(empty_graph, sample_task, context={})

        parent_id = result.metadata["parent_id"]
        parents = set()

        for iid in result.instance_ids:
            parent_refs = list(empty_graph.objects(URIRef(iid), YAWL.parentMI))
            assert len(parent_refs) == 1
            parents.add(str(parent_refs[0]))

        assert len(parents) == 1
        assert next(iter(parents)) == parent_id

    def test_requires_sync_metadata(self, empty_graph: Graph, sample_task: URIRef) -> None:
        """Result metadata indicates synchronization required."""
        pattern = MIDesignTime(instance_count=2)
        result = pattern.execute(empty_graph, sample_task, context={})

        assert result.metadata["requires_sync"] is True
        assert result.metadata["pattern"] == 13

    def test_zero_count_raises(self) -> None:
        """Zero instance count raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            MIDesignTime(instance_count=0)

    def test_negative_count_raises(self) -> None:
        """Negative instance count raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            MIDesignTime(instance_count=-3)


class TestMIRunTimeKnown:
    """Tests for Pattern 14: MI with Runtime Knowledge."""

    def test_runtime_count_from_variable(self, empty_graph: Graph, sample_task: URIRef) -> None:
        """Instance count determined from runtime variable."""
        pattern = MIRunTimeKnown(instance_count_variable="order_count")
        result = pattern.execute(empty_graph, sample_task, context={"order_count": 7})

        assert result.success
        assert len(result.instance_ids) == 7
        assert result.metadata["instance_count"] == 7
        assert result.metadata["count_variable"] == "order_count"

    def test_missing_variable_fails(self, empty_graph: Graph, sample_task: URIRef) -> None:
        """Missing count variable causes failure."""
        pattern = MIRunTimeKnown(instance_count_variable="missing_var")
        result = pattern.execute(empty_graph, sample_task, context={})

        assert not result.success
        assert result.state == MIState.FAILED
        assert result.error is not None
        assert "not found in context" in result.error

    def test_invalid_count_type_fails(self, empty_graph: Graph, sample_task: URIRef) -> None:
        """Non-integer count value causes failure."""
        pattern = MIRunTimeKnown(instance_count_variable="count")
        result = pattern.execute(empty_graph, sample_task, context={"count": "five"})

        assert not result.success
        assert result.state == MIState.FAILED
        assert result.error is not None
        assert "positive integer" in result.error

    def test_zero_count_fails(self, empty_graph: Graph, sample_task: URIRef) -> None:
        """Zero runtime count causes failure."""
        pattern = MIRunTimeKnown(instance_count_variable="count")
        result = pattern.execute(empty_graph, sample_task, context={"count": 0})

        assert not result.success
        assert result.state == MIState.FAILED

    def test_negative_count_fails(self, empty_graph: Graph, sample_task: URIRef) -> None:
        """Negative runtime count causes failure."""
        pattern = MIRunTimeKnown(instance_count_variable="count")
        result = pattern.execute(empty_graph, sample_task, context={"count": -5})

        assert not result.success

    def test_synchronization_barrier_created(self, empty_graph: Graph, sample_task: URIRef) -> None:
        """Synchronization barrier uses runtime count."""
        pattern = MIRunTimeKnown(instance_count_variable="items")
        result = pattern.execute(empty_graph, sample_task, context={"items": 10})

        parent_uri = URIRef(result.metadata["parent_id"])
        required_objs = list(empty_graph.objects(parent_uri, YAWL.requiredInstances))
        required = int(cast(Literal, required_objs[0]).value)

        assert required == 10

    def test_custom_variable_name(self, empty_graph: Graph, sample_task: URIRef) -> None:
        """Custom variable name works correctly."""
        pattern = MIRunTimeKnown(instance_count_variable="batch_size")
        result = pattern.execute(empty_graph, sample_task, context={"batch_size": 15})

        assert result.success
        assert len(result.instance_ids) == 15


class TestMIDynamic:
    """Tests for Pattern 15: MI without Runtime Knowledge."""

    def test_dynamic_spawning_from_events(self, empty_graph: Graph, sample_task: URIRef) -> None:
        """One instance spawned per event."""
        pattern = MIDynamic(spawn_condition="new_order")
        result = pattern.execute(empty_graph, sample_task, context={"events": ["order1", "order2", "order3"]})

        assert result.success
        assert len(result.instance_ids) == 3
        assert result.metadata["initial_instance_count"] == 3

    def test_no_events_spawns_zero(self, empty_graph: Graph, sample_task: URIRef) -> None:
        """No events results in zero instances."""
        pattern = MIDynamic(spawn_condition="new_item")
        result = pattern.execute(empty_graph, sample_task, context={})

        assert result.success
        assert len(result.instance_ids) == 0

    def test_event_data_stored(self, empty_graph: Graph, sample_task: URIRef) -> None:
        """Event data attached to each instance."""
        pattern = MIDynamic(spawn_condition="event")
        events = ["event_a", "event_b"]
        result = pattern.execute(empty_graph, sample_task, context={"events": events})

        for iid in result.instance_ids:
            trigger_values = list(empty_graph.objects(URIRef(iid), YAWL.triggerEvent))
            assert len(trigger_values) == 1
            assert str(trigger_values[0]) in events

    def test_termination_condition_stored(self, empty_graph: Graph, sample_task: URIRef) -> None:
        """Termination condition stored in parent."""
        pattern = MIDynamic(spawn_condition="new_order", termination_condition="all_processed")
        result = pattern.execute(empty_graph, sample_task, context={"events": ["e1"]})

        parent_uri = URIRef(result.metadata["parent_id"])
        term_cond = list(empty_graph.objects(parent_uri, YAWL.terminationCondition))

        assert len(term_cond) == 1
        assert str(term_cond[0]) == "all_processed"

    def test_no_sync_for_dynamic(self, empty_graph: Graph, sample_task: URIRef) -> None:
        """Dynamic pattern doesn't require pre-sync."""
        pattern = MIDynamic(spawn_condition="event")
        result = pattern.execute(empty_graph, sample_task, context={"events": ["e1", "e2"]})

        assert result.metadata["requires_sync"] is False

    def test_spawned_count_tracked(self, empty_graph: Graph, sample_task: URIRef) -> None:
        """Parent tracks total spawned instances."""
        pattern = MIDynamic(spawn_condition="event")
        result = pattern.execute(empty_graph, sample_task, context={"events": ["a", "b", "c", "d"]})

        parent_uri = URIRef(result.metadata["parent_id"])
        spawned_objs = list(empty_graph.objects(parent_uri, YAWL.spawnedInstances))
        spawned = int(cast(Literal, spawned_objs[0]).value)

        assert spawned == 4

    def test_dynamic_flag_set(self, empty_graph: Graph, sample_task: URIRef) -> None:
        """Parent marked as dynamic spawning."""
        pattern = MIDynamic(spawn_condition="event")
        result = pattern.execute(empty_graph, sample_task, context={"events": ["e"]})

        parent_uri = URIRef(result.metadata["parent_id"])
        is_dynamic = list(empty_graph.objects(parent_uri, YAWL.dynamicSpawning))

        assert len(is_dynamic) == 1
        assert bool(cast(Literal, is_dynamic[0]).value)


class TestCompletionTracking:
    """Tests for MI completion tracking utilities."""

    def test_check_completion_all_done(self, empty_graph: Graph) -> None:
        """All instances completed returns True."""
        parent_id = "http://example.org/parent-123"
        parent_uri = URIRef(parent_id)

        empty_graph.add((parent_uri, YAWL.requiredInstances, Literal(3)))
        empty_graph.add((parent_uri, YAWL.completedInstances, Literal(3)))

        assert check_completion(empty_graph, parent_id) is True

    def test_check_completion_partial(self, empty_graph: Graph) -> None:
        """Partial completion returns False."""
        parent_id = "http://example.org/parent-456"
        parent_uri = URIRef(parent_id)

        empty_graph.add((parent_uri, YAWL.requiredInstances, Literal(5)))
        empty_graph.add((parent_uri, YAWL.completedInstances, Literal(2)))

        assert check_completion(empty_graph, parent_id) is False

    def test_check_completion_missing_data(self, empty_graph: Graph) -> None:
        """Missing completion data returns False."""
        parent_id = "http://example.org/parent-789"
        assert check_completion(empty_graph, parent_id) is False

    def test_mark_instance_complete_updates_state(self, empty_graph: Graph) -> None:
        """Marking complete updates instance state."""
        instance_id = "http://example.org/instance-1"
        instance_uri = URIRef(instance_id)
        parent_uri = URIRef("http://example.org/parent")

        empty_graph.add((instance_uri, YAWL.state, Literal(MIState.RUNNING.value)))
        empty_graph.add((instance_uri, YAWL.parentMI, parent_uri))
        empty_graph.add((parent_uri, YAWL.completedInstances, Literal(0)))

        mark_instance_complete(empty_graph, instance_id)

        state_values = list(empty_graph.objects(instance_uri, YAWL.state))
        assert len(state_values) == 1
        assert str(state_values[0]) == MIState.COMPLETED.value

    def test_mark_instance_complete_increments_counter(self, empty_graph: Graph) -> None:
        """Marking complete increments parent counter."""
        instance_id = "http://example.org/instance-2"
        instance_uri = URIRef(instance_id)
        parent_uri = URIRef("http://example.org/parent")

        empty_graph.add((instance_uri, YAWL.parentMI, parent_uri))
        empty_graph.add((parent_uri, YAWL.completedInstances, Literal(3)))

        mark_instance_complete(empty_graph, instance_id)

        completed_objs = list(empty_graph.objects(parent_uri, YAWL.completedInstances))
        completed = int(cast(Literal, completed_objs[0]).value)
        assert completed == 4

    def test_mark_instance_no_parent_safe(self, empty_graph: Graph) -> None:
        """Marking instance without parent doesn't crash."""
        instance_id = "http://example.org/orphan"
        instance_uri = URIRef(instance_id)

        empty_graph.add((instance_uri, YAWL.state, Literal(MIState.RUNNING.value)))

        # Should not raise
        mark_instance_complete(empty_graph, instance_id)


class TestExecutionResultValidation:
    """Tests for ExecutionResult dataclass validation."""

    def test_failed_without_error_raises(self) -> None:
        """Failed result without error message raises ValueError."""
        with pytest.raises(ValueError, match="Failed execution must provide error"):
            ExecutionResult(
                success=False,
                instance_ids=[],
                state=MIState.FAILED,
                error=None,  # Missing!
            )

    def test_success_with_error_raises(self) -> None:
        """Successful result with error message raises ValueError."""
        with pytest.raises(ValueError, match="Successful execution cannot have error"):
            ExecutionResult(success=True, instance_ids=["i1"], state=MIState.COMPLETED, error="Should not be here")

    def test_valid_failure(self) -> None:
        """Valid failure result with error message."""
        result = ExecutionResult(success=False, instance_ids=[], state=MIState.FAILED, error="Something went wrong")

        assert not result.success
        assert result.error == "Something went wrong"

    def test_valid_success(self) -> None:
        """Valid success result without error."""
        result = ExecutionResult(success=True, instance_ids=["i1", "i2"], state=MIState.COMPLETED)

        assert result.success
        assert result.error is None


class TestIntegrationScenarios:
    """Integration tests for complete MI workflows."""

    def test_design_time_full_cycle(self, empty_graph: Graph, sample_task: URIRef) -> None:
        """Complete design-time MI lifecycle."""
        # Spawn 3 instances
        pattern = MIDesignTime(instance_count=3)
        result = pattern.execute(empty_graph, sample_task, context={})

        assert result.success
        parent_id = result.metadata["parent_id"]

        # Complete each instance
        for iid in result.instance_ids:
            mark_instance_complete(empty_graph, iid)

        # Check overall completion
        assert check_completion(empty_graph, parent_id)

    def test_runtime_variable_workflow(self, empty_graph: Graph, sample_task: URIRef) -> None:
        """Runtime variable determines instance count."""
        # Simulate batch of 5 orders
        context = {"order_count": 5, "batch_id": "B-123"}

        pattern = MIRunTimeKnown(instance_count_variable="order_count")
        result = pattern.execute(empty_graph, sample_task, context)

        assert result.success
        assert len(result.instance_ids) == 5

        # Complete first 3
        for iid in result.instance_ids[:3]:
            mark_instance_complete(empty_graph, iid)

        parent_id = result.metadata["parent_id"]
        assert not check_completion(empty_graph, parent_id)

        # Complete remaining 2
        for iid in result.instance_ids[3:]:
            mark_instance_complete(empty_graph, iid)

        assert check_completion(empty_graph, parent_id)

    def test_dynamic_event_driven(self, empty_graph: Graph, sample_task: URIRef) -> None:
        """Dynamic spawning from event stream."""
        events = [
            {"order_id": "O-1", "customer": "Alice"},
            {"order_id": "O-2", "customer": "Bob"},
            {"order_id": "O-3", "customer": "Carol"},
        ]

        pattern = MIDynamic(spawn_condition="order_received", termination_condition="queue_empty")

        result = pattern.execute(empty_graph, sample_task, context={"events": events})

        assert result.success
        assert len(result.instance_ids) == 3
        assert result.metadata["spawn_condition"] == "order_received"
        assert result.metadata["termination_condition"] == "queue_empty"

        # Verify each instance has trigger event
        for iid in result.instance_ids:
            triggers = list(empty_graph.objects(URIRef(iid), YAWL.triggerEvent))
            assert len(triggers) == 1

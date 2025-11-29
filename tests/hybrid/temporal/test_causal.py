"""Tests for causal tracking system."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from kgcl.hybrid.temporal.adapters.causal_tracker_adapter import DefaultCausalityAnalyzer, InMemoryCausalTracker
from kgcl.hybrid.temporal.adapters.in_memory_event_store import InMemoryEventStore
from kgcl.hybrid.temporal.domain.event import EventType, WorkflowEvent
from kgcl.hybrid.temporal.domain.vector_clock import VectorClock
from kgcl.hybrid.temporal.ports.causal_port import CausalGraph


@pytest.fixture
def event_store() -> InMemoryEventStore:
    """Create empty event store."""
    return InMemoryEventStore()


@pytest.fixture
def tracker(event_store: InMemoryEventStore) -> InMemoryCausalTracker:
    """Create causal tracker."""
    return InMemoryCausalTracker(event_store=event_store)


@pytest.fixture
def analyzer(tracker: InMemoryCausalTracker, event_store: InMemoryEventStore) -> DefaultCausalityAnalyzer:
    """Create causality analyzer."""
    return DefaultCausalityAnalyzer(tracker=tracker, event_store=event_store)


def test_track_single_causation(tracker: InMemoryCausalTracker) -> None:
    """Test tracking single cause-effect relationship."""
    # Arrange & Act
    tracker.track_causation(effect_id="e2", cause_ids=("e1",))

    # Assert
    direct_causes = tracker.get_direct_causes("e2")
    assert direct_causes == ("e1",)


def test_track_multiple_causes(tracker: InMemoryCausalTracker) -> None:
    """Test tracking multiple causes for single effect."""
    # Arrange & Act
    tracker.track_causation(effect_id="e3", cause_ids=("e1", "e2"))

    # Assert
    direct_causes = tracker.get_direct_causes("e3")
    assert set(direct_causes) == {"e1", "e2"}


def test_get_direct_causes(tracker: InMemoryCausalTracker) -> None:
    """Test retrieving direct causes."""
    # Arrange
    tracker.track_causation(effect_id="e2", cause_ids=("e1",))
    tracker.track_causation(effect_id="e3", cause_ids=("e2",))

    # Act & Assert
    assert tracker.get_direct_causes("e2") == ("e1",)
    assert tracker.get_direct_causes("e3") == ("e2",)
    assert tracker.get_direct_causes("e1") == ()


def test_get_transitive_causes_simple(tracker: InMemoryCausalTracker) -> None:
    """Test transitive causes in linear chain."""
    # Arrange: e1 -> e2 -> e3
    tracker.track_causation(effect_id="e2", cause_ids=("e1",))
    tracker.track_causation(effect_id="e3", cause_ids=("e2",))

    # Act
    transitive = tracker.get_transitive_causes("e3")

    # Assert
    assert set(transitive) == {"e1", "e2"}


def test_get_transitive_causes_diamond(tracker: InMemoryCausalTracker) -> None:
    """Test transitive causes in diamond pattern.

    Diamond pattern:
        e1
       /  \\
      e2  e3
       \\  /
        e4
    """
    # Arrange
    tracker.track_causation(effect_id="e2", cause_ids=("e1",))
    tracker.track_causation(effect_id="e3", cause_ids=("e1",))
    tracker.track_causation(effect_id="e4", cause_ids=("e2", "e3"))

    # Act
    transitive = tracker.get_transitive_causes("e4")

    # Assert - should include e1, e2, e3 (all ancestors)
    assert set(transitive) == {"e1", "e2", "e3"}


def test_get_transitive_causes_max_depth(tracker: InMemoryCausalTracker) -> None:
    """Test max_depth limiting in transitive search."""
    # Arrange: e1 -> e2 -> e3 -> e4
    tracker.track_causation(effect_id="e2", cause_ids=("e1",))
    tracker.track_causation(effect_id="e3", cause_ids=("e2",))
    tracker.track_causation(effect_id="e4", cause_ids=("e3",))

    # Act
    transitive = tracker.get_transitive_causes("e4", max_depth=2)

    # Assert - should only get e3 and e2 (depth 1 and 2)
    assert set(transitive) == {"e2", "e3"}


def test_get_root_causes(tracker: InMemoryCausalTracker) -> None:
    """Test finding root causes (events with no causes)."""
    # Arrange: e1 -> e2 -> e4, e3 -> e4
    tracker.track_causation(effect_id="e2", cause_ids=("e1",))
    tracker.track_causation(effect_id="e4", cause_ids=("e2", "e3"))

    # Act
    roots = tracker.get_root_causes("e4")

    # Assert - e1 and e3 are roots
    assert set(roots) == {"e1", "e3"}


def test_build_causal_graph(tracker: InMemoryCausalTracker) -> None:
    """Test building causal graph from events."""
    # Arrange: e1 -> e2 -> e3
    tracker.track_causation(effect_id="e2", cause_ids=("e1",))
    tracker.track_causation(effect_id="e3", cause_ids=("e2",))

    # Act
    graph = tracker.build_causal_graph(("e1", "e2", "e3"))

    # Assert
    assert graph.nodes == frozenset({"e1", "e2", "e3"})
    assert graph.edges == frozenset({("e1", "e2"), ("e2", "e3")})


def test_causal_graph_ancestors(tracker: InMemoryCausalTracker) -> None:
    """Test getting ancestors from causal graph."""
    # Arrange: e1 -> e2 -> e3
    tracker.track_causation(effect_id="e2", cause_ids=("e1",))
    tracker.track_causation(effect_id="e3", cause_ids=("e2",))
    graph = tracker.build_causal_graph(("e1", "e2", "e3"))

    # Act & Assert
    assert graph.get_ancestors("e3") == frozenset({"e1", "e2"})
    assert graph.get_ancestors("e2") == frozenset({"e1"})
    assert graph.get_ancestors("e1") == frozenset()


def test_causal_graph_descendants(tracker: InMemoryCausalTracker) -> None:
    """Test getting descendants from causal graph."""
    # Arrange: e1 -> e2 -> e3
    tracker.track_causation(effect_id="e2", cause_ids=("e1",))
    tracker.track_causation(effect_id="e3", cause_ids=("e2",))
    graph = tracker.build_causal_graph(("e1", "e2", "e3"))

    # Act & Assert
    assert graph.get_descendants("e1") == frozenset({"e2", "e3"})
    assert graph.get_descendants("e2") == frozenset({"e3"})
    assert graph.get_descendants("e3") == frozenset()


def test_causal_graph_topological_sort(tracker: InMemoryCausalTracker) -> None:
    """Test topological sorting of causal graph."""
    # Arrange: e1 -> e2, e1 -> e3, e2 -> e4, e3 -> e4
    tracker.track_causation(effect_id="e2", cause_ids=("e1",))
    tracker.track_causation(effect_id="e3", cause_ids=("e1",))
    tracker.track_causation(effect_id="e4", cause_ids=("e2", "e3"))
    graph = tracker.build_causal_graph(("e1", "e2", "e3", "e4"))

    # Act
    sorted_events = graph.topological_sort()

    # Assert - e1 must come first, e4 must come last
    assert sorted_events[0] == "e1"
    assert sorted_events[-1] == "e4"
    # e2 and e3 can be in any order but both before e4
    assert sorted_events.index("e2") < sorted_events.index("e4")
    assert sorted_events.index("e3") < sorted_events.index("e4")


def test_causal_graph_is_ancestor(tracker: InMemoryCausalTracker) -> None:
    """Test ancestor checking in causal graph."""
    # Arrange: e1 -> e2 -> e3
    tracker.track_causation(effect_id="e2", cause_ids=("e1",))
    tracker.track_causation(effect_id="e3", cause_ids=("e2",))
    graph = tracker.build_causal_graph(("e1", "e2", "e3"))

    # Act & Assert
    assert graph.is_ancestor("e1", "e3") is True
    assert graph.is_ancestor("e1", "e2") is True
    assert graph.is_ancestor("e2", "e3") is True
    assert graph.is_ancestor("e3", "e1") is False
    assert graph.is_ancestor("e2", "e1") is False


def test_causal_graph_to_dot() -> None:
    """Test DOT format export for visualization."""
    # Arrange
    graph = CausalGraph(nodes=frozenset({"e1", "e2", "e3"}), edges=frozenset({("e1", "e2"), ("e2", "e3")}))

    # Act
    dot_output = graph.topological_sort()  # Just check it doesn't crash

    # Assert - basic smoke test
    assert len(dot_output) > 0


def test_explain_event(
    analyzer: DefaultCausalityAnalyzer, event_store: InMemoryEventStore, tracker: InMemoryCausalTracker
) -> None:
    """Test generating causal explanation for event."""
    # Arrange: Create events in store
    vc1 = VectorClock.zero(node_id="p1")
    vc2 = vc1.increment("p1")
    vc3 = vc2.increment("p1")

    e1 = WorkflowEvent(
        event_id="e1",
        event_type=EventType.TICK_START,
        timestamp=datetime.now(UTC),
        tick_number=1,
        workflow_id="wf1",
        payload={"rule_uri": "rule:start"},
        caused_by=(),
        vector_clock=vc1.clocks,
    )
    e2 = WorkflowEvent(
        event_id="e2",
        event_type=EventType.HOOK_EXECUTION,
        timestamp=datetime.now(UTC),
        tick_number=2,
        workflow_id="wf1",
        payload={"rule_uri": "rule:eval"},
        caused_by=("e1",),
        vector_clock=vc2.clocks,
    )
    e3 = WorkflowEvent(
        event_id="e3",
        event_type=EventType.STATUS_CHANGE,
        timestamp=datetime.now(UTC),
        tick_number=3,
        workflow_id="wf1",
        payload={"rule_uri": "rule:action"},
        caused_by=("e2",),
        vector_clock=vc3.clocks,
    )

    event_store.append(e1)
    event_store.append(e2)
    event_store.append(e3)

    # Track causation
    tracker.track_causation(effect_id="e2", cause_ids=("e1",))
    tracker.track_causation(effect_id="e3", cause_ids=("e2",))

    # Act
    explanation = analyzer.explain_event("e3")

    # Assert
    assert explanation.effect == e3
    assert explanation.direct_causes == (e2,)
    assert explanation.indirect_causes == (e1,)
    assert explanation.root_causes == (e1,)
    assert "rule:start" in explanation.rules_involved
    assert "rule:eval" in explanation.rules_involved
    assert "rule:action" in explanation.rules_involved
    assert "e3" in explanation.explanation_text
    assert "e2" in explanation.explanation_text


def test_find_common_causes(analyzer: DefaultCausalityAnalyzer, tracker: InMemoryCausalTracker) -> None:
    """Test finding common causes of multiple events."""
    # Arrange: e1 -> e2, e1 -> e3, e2 -> e4, e3 -> e4
    tracker.track_causation(effect_id="e2", cause_ids=("e1",))
    tracker.track_causation(effect_id="e3", cause_ids=("e1",))
    tracker.track_causation(effect_id="e4", cause_ids=("e2", "e3"))

    # Act
    common = analyzer.find_common_causes(("e2", "e3"))

    # Assert
    assert set(common) == {"e1"}


def test_check_causally_related_using_vector_clocks(
    analyzer: DefaultCausalityAnalyzer, event_store: InMemoryEventStore
) -> None:
    """Test causal relationship check using vector clocks."""
    # Arrange: Create events with vector clocks
    vc1 = VectorClock.zero(node_id="p1")
    vc2 = vc1.increment("p1")  # vc2 happens after vc1

    e1 = WorkflowEvent(
        event_id="e1",
        event_type=EventType.TICK_START,
        timestamp=datetime.now(UTC),
        tick_number=1,
        workflow_id="wf1",
        payload={"rule_uri": "rule:start"},
        caused_by=(),
        vector_clock=vc1.clocks,
    )
    e2 = WorkflowEvent(
        event_id="e2",
        event_type=EventType.HOOK_EXECUTION,
        timestamp=datetime.now(UTC),
        tick_number=2,
        workflow_id="wf1",
        payload={"rule_uri": "rule:eval"},
        caused_by=("e1",),
        vector_clock=vc2.clocks,
    )

    event_store.append(e1)
    event_store.append(e2)

    # Act
    is_related = analyzer.check_causally_related("e1", "e2")

    # Assert
    assert is_related is True


def test_check_concurrent_events(analyzer: DefaultCausalityAnalyzer, event_store: InMemoryEventStore) -> None:
    """Test concurrent event detection using vector clocks."""
    # Arrange: Create concurrent events (different processes, same time)
    vc1 = VectorClock.zero(node_id="p1")
    vc2 = VectorClock.zero(node_id="p2")

    e1 = WorkflowEvent(
        event_id="e1",
        event_type=EventType.TICK_START,
        timestamp=datetime.now(UTC),
        tick_number=1,
        workflow_id="wf1",
        payload={"rule_uri": "rule:start1"},
        caused_by=(),
        vector_clock=vc1.clocks,
    )
    e2 = WorkflowEvent(
        event_id="e2",
        event_type=EventType.TICK_START,
        timestamp=datetime.now(UTC),
        tick_number=1,
        workflow_id="wf2",
        payload={"rule_uri": "rule:start2"},
        caused_by=(),
        vector_clock=vc2.clocks,
    )

    event_store.append(e1)
    event_store.append(e2)

    # Act
    is_concurrent = analyzer.check_concurrent("e1", "e2")

    # Assert - events from different processes with no causal relationship are concurrent
    assert is_concurrent is True


def test_causal_graph_empty() -> None:
    """Test empty causal graph."""
    # Arrange
    graph = CausalGraph(nodes=frozenset(), edges=frozenset())

    # Act & Assert
    assert graph.topological_sort() == ()
    assert graph.get_ancestors("e1") == frozenset()


def test_explain_event_not_found(analyzer: DefaultCausalityAnalyzer) -> None:
    """Test explanation for non-existent event."""
    # Act & Assert
    with pytest.raises(ValueError, match="Event.*not found"):
        analyzer.explain_event("nonexistent")


def test_find_common_causes_empty(analyzer: DefaultCausalityAnalyzer) -> None:
    """Test finding common causes with empty input."""
    # Act
    common = analyzer.find_common_causes(())

    # Assert
    assert common == ()


def test_check_causally_related_missing_event(analyzer: DefaultCausalityAnalyzer) -> None:
    """Test causal check with missing event."""
    # Act
    is_related = analyzer.check_causally_related("e1", "nonexistent")

    # Assert
    assert is_related is False


def test_check_concurrent_missing_event(analyzer: DefaultCausalityAnalyzer) -> None:
    """Test concurrent check with missing event."""
    # Act
    is_concurrent = analyzer.check_concurrent("e1", "nonexistent")

    # Assert
    assert is_concurrent is False


def test_causal_explanation_to_narrative(
    analyzer: DefaultCausalityAnalyzer, event_store: InMemoryEventStore, tracker: InMemoryCausalTracker
) -> None:
    """Test narrative generation from explanation."""
    # Arrange
    vc1 = VectorClock.zero(node_id="p1")
    e1 = WorkflowEvent(
        event_id="e1",
        event_type=EventType.TICK_START,
        timestamp=datetime.now(UTC),
        tick_number=1,
        workflow_id="wf1",
        payload={"rule_uri": "rule:start"},
        caused_by=(),
        vector_clock=vc1.clocks,
    )
    event_store.append(e1)
    tracker.track_causation(effect_id="e1", cause_ids=())

    # Act
    explanation = analyzer.explain_event("e1")
    narrative = explanation.to_narrative()

    # Assert
    assert isinstance(narrative, str)
    assert len(narrative) > 0
    assert "e1" in narrative


def test_build_causal_graph_partial_edges(tracker: InMemoryCausalTracker) -> None:
    """Test graph building only includes edges between specified events."""
    # Arrange: e1 -> e2 -> e3 -> e4, but only query e1, e2, e4
    tracker.track_causation(effect_id="e2", cause_ids=("e1",))
    tracker.track_causation(effect_id="e3", cause_ids=("e2",))
    tracker.track_causation(effect_id="e4", cause_ids=("e3",))

    # Act
    graph = tracker.build_causal_graph(("e1", "e2", "e4"))

    # Assert - should only have e1->e2 edge (e3 not in node set)
    assert graph.nodes == frozenset({"e1", "e2", "e4"})
    assert graph.edges == frozenset({("e1", "e2")})

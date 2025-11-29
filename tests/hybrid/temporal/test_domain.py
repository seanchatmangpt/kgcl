"""Comprehensive tests for temporal event sourcing domain models."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from kgcl.hybrid.temporal.domain import (
    EventChain,
    EventType,
    LTLFormula,
    LTLOperator,
    LTLResult,
    TemporalSlice,
    VectorClock,
    WorkflowEvent,
)


class TestEventType:
    """Test EventType enum."""

    def test_event_type_has_11_values(self) -> None:
        """Verify EventType enum has exactly 11 event types."""
        assert len(EventType) == 11

    def test_event_type_coverage(self) -> None:
        """Verify all expected event types exist."""
        expected = {
            "STATUS_CHANGE",
            "TOKEN_MOVE",
            "SPLIT",
            "JOIN",
            "CANCELLATION",
            "MI_SPAWN",
            "MI_COMPLETE",
            "HOOK_EXECUTION",
            "VALIDATION",
            "TICK_START",
            "TICK_END",
        }
        actual = {e.name for e in EventType}
        assert actual == expected


class TestWorkflowEvent:
    """Test WorkflowEvent domain model."""

    def test_create_event_generates_id_and_hash(self) -> None:
        """Verify create() generates event_id and computes hash."""
        event = WorkflowEvent.create(
            event_type=EventType.TICK_START, workflow_id="wf-123", tick_number=1, payload={"action": "start"}
        )

        assert event.event_id != ""
        assert event.event_hash != ""
        assert len(event.event_hash) == 64  # SHA-256 hex

    def test_compute_hash_is_deterministic(self) -> None:
        """Verify hash computation is deterministic for same event."""
        ts = datetime.now(UTC)
        event1 = WorkflowEvent(
            event_id="evt-1",
            event_type=EventType.STATUS_CHANGE,
            timestamp=ts,
            tick_number=5,
            workflow_id="wf-1",
            payload={"status": "running"},
        )

        event2 = WorkflowEvent(
            event_id="evt-1",
            event_type=EventType.STATUS_CHANGE,
            timestamp=ts,
            tick_number=5,
            workflow_id="wf-1",
            payload={"status": "running"},
        )

        assert event1.compute_hash() == event2.compute_hash()

    def test_compute_hash_changes_with_payload(self) -> None:
        """Verify hash changes when payload differs."""
        ts = datetime.now(UTC)
        event1 = WorkflowEvent(
            event_id="evt-1",
            event_type=EventType.STATUS_CHANGE,
            timestamp=ts,
            tick_number=5,
            workflow_id="wf-1",
            payload={"status": "running"},
        )

        event2 = WorkflowEvent(
            event_id="evt-1",
            event_type=EventType.STATUS_CHANGE,
            timestamp=ts,
            tick_number=5,
            workflow_id="wf-1",
            payload={"status": "completed"},
        )

        assert event1.event_hash != event2.event_hash

    def test_event_is_immutable(self) -> None:
        """Verify WorkflowEvent is frozen and immutable."""
        event = WorkflowEvent.create(event_type=EventType.TOKEN_MOVE, workflow_id="wf-1", tick_number=1, payload={})

        with pytest.raises(AttributeError):
            event.tick_number = 2  # type: ignore[misc]

    def test_caused_by_captures_dependencies(self) -> None:
        """Verify caused_by tracks causal dependencies."""
        event = WorkflowEvent.create(
            event_type=EventType.JOIN, workflow_id="wf-1", tick_number=3, payload={}, caused_by=("evt-1", "evt-2")
        )

        assert event.caused_by == ("evt-1", "evt-2")


class TestEventChain:
    """Test EventChain domain model."""

    def test_append_creates_new_chain(self) -> None:
        """Verify append() creates new immutable chain."""
        chain1 = EventChain(workflow_id="wf-1", events=())

        event = WorkflowEvent.create(
            event_type=EventType.TICK_START,
            workflow_id="wf-1",
            tick_number=1,
            payload={},
            previous_hash=chain1.genesis_hash,
        )

        chain2 = chain1.append(event)

        # Original chain unchanged
        assert len(chain1.events) == 0
        # New chain has event
        assert len(chain2.events) == 1
        assert chain2.events[0] == event

    def test_verify_detects_tampering(self) -> None:
        """Verify verify() detects hash chain tampering."""
        chain = EventChain(workflow_id="wf-1", events=())

        # Create valid chain
        event1 = WorkflowEvent.create(
            event_type=EventType.TICK_START,
            workflow_id="wf-1",
            tick_number=1,
            payload={},
            previous_hash=chain.genesis_hash,
        )
        chain = chain.append(event1)

        event2 = WorkflowEvent.create(
            event_type=EventType.STATUS_CHANGE,
            workflow_id="wf-1",
            tick_number=2,
            payload={},
            previous_hash=event1.event_hash,
        )
        chain = chain.append(event2)

        # Valid chain should verify
        is_valid, error = chain.verify()
        assert is_valid
        assert error == ""

        # Tamper with event by creating modified version
        tampered_event = WorkflowEvent(
            event_id=event1.event_id,
            event_type=event1.event_type,
            timestamp=event1.timestamp,
            tick_number=event1.tick_number,
            workflow_id=event1.workflow_id,
            payload={"tampered": True},  # Changed payload
            caused_by=event1.caused_by,
            vector_clock=event1.vector_clock,
            previous_hash=event1.previous_hash,
        )

        # Create tampered chain
        tampered_chain = EventChain(workflow_id="wf-1", events=(tampered_event, event2))

        is_valid, error = tampered_chain.verify()
        assert not is_valid
        # Error message can be either hash mismatch or chain link mismatch
        assert "mismatch" in error.lower() or "doesn't match" in error.lower()

    def test_verify_detects_broken_chain(self) -> None:
        """Verify verify() detects broken hash links."""
        chain = EventChain(workflow_id="wf-1", events=())

        event1 = WorkflowEvent.create(
            event_type=EventType.TICK_START,
            workflow_id="wf-1",
            tick_number=1,
            payload={},
            previous_hash=chain.genesis_hash,
        )

        # Create event2 with wrong previous_hash
        event2 = WorkflowEvent.create(
            event_type=EventType.STATUS_CHANGE,
            workflow_id="wf-1",
            tick_number=2,
            payload={},
            previous_hash="wrong_hash",
        )

        # Manually create broken chain
        broken_chain = EventChain(workflow_id="wf-1", events=(event1, event2))

        is_valid, error = broken_chain.verify()
        assert not is_valid
        assert "doesn't match" in error.lower()

    def test_append_validates_workflow_id(self) -> None:
        """Verify append() rejects events with wrong workflow_id."""
        chain = EventChain(workflow_id="wf-1", events=())

        event = WorkflowEvent.create(
            event_type=EventType.TICK_START,
            workflow_id="wf-2",  # Wrong workflow
            tick_number=1,
            payload={},
            previous_hash=chain.genesis_hash,
        )

        with pytest.raises(ValueError, match="workflow_id"):
            chain.append(event)

    def test_append_validates_previous_hash(self) -> None:
        """Verify append() rejects events with wrong previous_hash."""
        chain = EventChain(workflow_id="wf-1", events=())

        event = WorkflowEvent.create(
            event_type=EventType.TICK_START, workflow_id="wf-1", tick_number=1, payload={}, previous_hash="wrong_hash"
        )

        with pytest.raises(ValueError, match="previous_hash"):
            chain.append(event)


class TestVectorClock:
    """Test VectorClock domain model."""

    def test_zero_creates_single_node_clock(self) -> None:
        """Verify zero() creates clock with single node at 0."""
        vc = VectorClock.zero("node-1")

        assert vc.clocks == (("node-1", 0),)

    def test_increment_is_monotonic(self) -> None:
        """Verify increment() is monotonically increasing."""
        vc = VectorClock.zero("node-1")

        vc2 = vc.increment("node-1")
        vc3 = vc2.increment("node-1")

        clock_dict = dict(vc3.clocks)
        assert clock_dict["node-1"] == 2

    def test_increment_creates_new_clock(self) -> None:
        """Verify increment() creates new immutable clock."""
        vc1 = VectorClock.zero("node-1")
        vc2 = vc1.increment("node-1")

        # Original unchanged
        assert dict(vc1.clocks)["node-1"] == 0
        # New clock incremented
        assert dict(vc2.clocks)["node-1"] == 1

    def test_happens_before_transitivity(self) -> None:
        """Verify happens_before() is transitive."""
        vc1 = VectorClock.zero("node-1")
        vc2 = vc1.increment("node-1")
        vc3 = vc2.increment("node-1")

        # Transitivity: if A < B and B < C, then A < C
        assert vc1.happens_before(vc2)
        assert vc2.happens_before(vc3)
        assert vc1.happens_before(vc3)

    def test_happens_before_partial_order(self) -> None:
        """Verify happens_before() defines partial order."""
        # Create clocks for different nodes
        vc1 = VectorClock(clocks=(("node-1", 1), ("node-2", 0)))
        vc2 = VectorClock(clocks=(("node-1", 0), ("node-2", 1)))

        # Neither happened before the other (concurrent)
        assert not vc1.happens_before(vc2)
        assert not vc2.happens_before(vc1)

    def test_merge_is_commutative(self) -> None:
        """Verify merge() is commutative (A ∪ B = B ∪ A)."""
        vc1 = VectorClock(clocks=(("node-1", 3), ("node-2", 1)))
        vc2 = VectorClock(clocks=(("node-1", 1), ("node-2", 4)))

        merged1 = vc1.merge(vc2)
        merged2 = vc2.merge(vc1)

        assert merged1.clocks == merged2.clocks

    def test_merge_takes_element_wise_max(self) -> None:
        """Verify merge() takes element-wise maximum."""
        vc1 = VectorClock(clocks=(("node-1", 3), ("node-2", 1)))
        vc2 = VectorClock(clocks=(("node-1", 1), ("node-2", 4)))

        merged = vc1.merge(vc2)
        clock_dict = dict(merged.clocks)

        assert clock_dict["node-1"] == 3  # max(3, 1)
        assert clock_dict["node-2"] == 4  # max(1, 4)

    def test_concurrent_with_detects_concurrent_events(self) -> None:
        """Verify concurrent_with() detects concurrent clocks."""
        vc1 = VectorClock(clocks=(("node-1", 1), ("node-2", 0)))
        vc2 = VectorClock(clocks=(("node-1", 0), ("node-2", 1)))

        assert vc1.concurrent_with(vc2)
        assert vc2.concurrent_with(vc1)

    def test_concurrent_with_rejects_ordered_events(self) -> None:
        """Verify concurrent_with() returns False for ordered events."""
        vc1 = VectorClock.zero("node-1")
        vc2 = vc1.increment("node-1")

        assert not vc1.concurrent_with(vc2)
        assert not vc2.concurrent_with(vc1)


class TestLTLFormula:
    """Test LTLFormula domain model."""

    def test_always_formula_creation(self) -> None:
        """Verify ALWAYS formula can be created."""
        formula = LTLFormula(operator=LTLOperator.ALWAYS, inner="ASK { ?task :status :completed }")

        assert formula.operator == LTLOperator.ALWAYS
        assert isinstance(formula.inner, str)

    def test_until_requires_right_operand(self) -> None:
        """Verify UNTIL operator requires right-hand formula."""
        with pytest.raises(ValueError, match="UNTIL"):
            LTLFormula(operator=LTLOperator.UNTIL, inner="ASK { ?task :status :running }")

    def test_nested_formula(self) -> None:
        """Verify formulas can be nested."""
        inner_formula = LTLFormula(operator=LTLOperator.EVENTUALLY, inner="ASK { ?task :status :completed }")

        outer_formula = LTLFormula(operator=LTLOperator.ALWAYS, inner=inner_formula)

        assert isinstance(outer_formula.inner, LTLFormula)

    def test_until_formula_with_both_operands(self) -> None:
        """Verify UNTIL formula with both operands."""
        formula = LTLFormula(
            operator=LTLOperator.UNTIL, inner="ASK { ?task :status :running }", right="ASK { ?task :status :completed }"
        )

        assert formula.right is not None


class TestLTLResult:
    """Test LTLResult domain model."""

    def test_result_holds_true(self) -> None:
        """Verify LTLResult for formula that holds."""
        result = LTLResult(holds=True, explanation="Formula satisfied")

        assert result.holds
        assert result.violated_at is None
        assert result.violating_event_id is None

    def test_result_holds_false_with_violation(self) -> None:
        """Verify LTLResult for violated formula."""
        violation_time = datetime.now(UTC)
        result = LTLResult(
            holds=False,
            violated_at=violation_time,
            violating_event_id="evt-123",
            explanation="Status change violated invariant",
        )

        assert not result.holds
        assert result.violated_at == violation_time
        assert result.violating_event_id == "evt-123"


class TestTemporalSlice:
    """Test TemporalSlice domain model."""

    def test_is_current_when_valid_until_none(self) -> None:
        """Verify is_current() returns True when valid_until is None."""
        ts = TemporalSlice(
            entity_uri="entity:1", valid_from=datetime.now(UTC), valid_until=None, properties={"status": "active"}
        )

        assert ts.is_current()

    def test_is_current_false_when_valid_until_set(self) -> None:
        """Verify is_current() returns False when valid_until is set."""
        now = datetime.now(UTC)
        ts = TemporalSlice(
            entity_uri="entity:1", valid_from=now, valid_until=now + timedelta(hours=1), properties={"status": "active"}
        )

        assert not ts.is_current()

    def test_overlaps_detects_overlap(self) -> None:
        """Verify overlaps() detects overlapping intervals."""
        now = datetime.now(UTC)

        ts1 = TemporalSlice(entity_uri="entity:1", valid_from=now, valid_until=now + timedelta(hours=2), properties={})

        ts2 = TemporalSlice(
            entity_uri="entity:1",
            valid_from=now + timedelta(hours=1),
            valid_until=now + timedelta(hours=3),
            properties={},
        )

        assert ts1.overlaps(ts2)
        assert ts2.overlaps(ts1)

    def test_overlaps_rejects_non_overlapping(self) -> None:
        """Verify overlaps() returns False for non-overlapping intervals."""
        now = datetime.now(UTC)

        ts1 = TemporalSlice(entity_uri="entity:1", valid_from=now, valid_until=now + timedelta(hours=1), properties={})

        ts2 = TemporalSlice(
            entity_uri="entity:1",
            valid_from=now + timedelta(hours=2),
            valid_until=now + timedelta(hours=3),
            properties={},
        )

        assert not ts1.overlaps(ts2)
        assert not ts2.overlaps(ts1)

    def test_overlaps_rejects_different_entities(self) -> None:
        """Verify overlaps() returns False for different entities."""
        now = datetime.now(UTC)

        ts1 = TemporalSlice(entity_uri="entity:1", valid_from=now, valid_until=now + timedelta(hours=2), properties={})

        ts2 = TemporalSlice(entity_uri="entity:2", valid_from=now, valid_until=now + timedelta(hours=2), properties={})

        assert not ts1.overlaps(ts2)


# Property-based tests using Hypothesis
class TestVectorClockProperties:
    """Property-based tests for VectorClock."""

    @given(st.lists(st.tuples(st.text(min_size=1, max_size=10), st.integers(min_value=0)), min_size=1, max_size=5))
    def test_merge_is_idempotent(self, clocks: list[tuple[str, int]]) -> None:
        """Verify merge(A, A) = A."""
        vc = VectorClock(clocks=tuple(clocks))
        merged = vc.merge(vc)

        assert merged.clocks == vc.clocks

    @given(
        st.lists(st.tuples(st.text(min_size=1, max_size=10), st.integers(min_value=0)), min_size=1, max_size=5),
        st.lists(st.tuples(st.text(min_size=1, max_size=10), st.integers(min_value=0)), min_size=1, max_size=5),
    )
    def test_merge_is_associative(self, clocks1: list[tuple[str, int]], clocks2: list[tuple[str, int]]) -> None:
        """Verify merge is associative: (A ∪ B) ∪ C = A ∪ (B ∪ C)."""
        vc1 = VectorClock(clocks=tuple(clocks1))
        vc2 = VectorClock(clocks=tuple(clocks2))
        vc3 = VectorClock.zero("node-test")

        left = vc1.merge(vc2).merge(vc3)
        right = vc1.merge(vc2.merge(vc3))

        assert set(left.clocks) == set(right.clocks)

    @given(st.text(min_size=1, max_size=10), st.integers(min_value=1, max_value=10))
    def test_increment_monotonicity(self, node_id: str, increments: int) -> None:
        """Verify repeated increments are monotonic."""
        vc = VectorClock.zero(node_id)

        for _i in range(increments):
            vc_next = vc.increment(node_id)
            assert vc.happens_before(vc_next) or vc == vc_next
            vc = vc_next

    @given(st.lists(st.tuples(st.text(min_size=1, max_size=10), st.integers(min_value=0)), min_size=1, max_size=5))
    def test_happens_before_irreflexive(self, clocks: list[tuple[str, int]]) -> None:
        """Verify happens_before is irreflexive: not A < A."""
        vc = VectorClock(clocks=tuple(clocks))

        assert not vc.happens_before(vc)

    @given(
        st.lists(st.tuples(st.text(min_size=1, max_size=10), st.integers(min_value=0)), min_size=1, max_size=5),
        st.lists(st.tuples(st.text(min_size=1, max_size=10), st.integers(min_value=0)), min_size=1, max_size=5),
    )
    def test_happens_before_antisymmetric(self, clocks1: list[tuple[str, int]], clocks2: list[tuple[str, int]]) -> None:
        """Verify happens_before is antisymmetric: if A < B then not B < A."""
        vc1 = VectorClock(clocks=tuple(clocks1))
        vc2 = VectorClock(clocks=tuple(clocks2))

        if vc1.happens_before(vc2):
            assert not vc2.happens_before(vc1)


class TestEventChainProperties:
    """Property-based tests for EventChain."""

    @given(st.integers(min_value=1, max_value=10), st.text(min_size=1, max_size=20))
    def test_valid_chain_always_verifies(self, num_events: int, workflow_id: str) -> None:
        """Verify properly constructed chains always verify."""
        chain = EventChain(workflow_id=workflow_id, events=())

        previous_hash = chain.genesis_hash
        for i in range(num_events):
            event = WorkflowEvent.create(
                event_type=EventType.STATUS_CHANGE,
                workflow_id=workflow_id,
                tick_number=i,
                payload={"index": i},
                previous_hash=previous_hash,
            )
            chain = chain.append(event)
            previous_hash = event.event_hash

        is_valid, error = chain.verify()
        assert is_valid
        assert error == ""

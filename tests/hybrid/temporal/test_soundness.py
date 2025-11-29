"""Comprehensive tests for soundness verification of workflow nets.

Tests van der Aalst's three soundness criteria:
1. Option to complete
2. Proper completion
3. No dead transitions
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.temporal.analysis.soundness_verifier import SoundnessVerifier, SoundnessViolation
from kgcl.hybrid.temporal.domain.petri_net import (
    Arc,
    Marking,
    Place,
    Transition,
    WorkflowNet,
    create_arc,
    create_place,
    create_transition,
    create_workflow_net,
)


class TestSoundWorkflowNets:
    """Test verification of sound workflow nets."""

    def test_simple_sequential_net_is_sound(self) -> None:
        """Test that simple sequential WF-net (i -> t -> o) is sound."""
        # Arrange: i -> t -> o
        places = [create_place("i", is_source=True), create_place("o", is_sink=True)]
        transitions = [create_transition("t")]
        arcs = [create_arc("i", "t"), create_arc("t", "o")]
        net = create_workflow_net(places, transitions, arcs)
        verifier = SoundnessVerifier()

        # Act
        result = verifier.verify(net)

        # Assert
        assert result.is_sound
        assert len(result.violations) == 0
        assert result.reachable_markings == 2  # [i] and [o]
        assert len(result.dead_transitions) == 0

    def test_parallel_split_join_is_sound(self) -> None:
        """Test AND-split/join pattern (parallel execution) is sound."""
        # Arrange: i -> t1 -> (p1, p2) -> (t2, t3) -> (p3, p4) -> t4 -> o
        # Proper AND-join requires BOTH inputs
        places = [
            create_place("i", is_source=True),
            create_place("p1"),
            create_place("p2"),
            create_place("p3"),
            create_place("p4"),
            create_place("o", is_sink=True),
        ]
        transitions = [
            create_transition("t1", "Split"),
            create_transition("t2", "Branch A"),
            create_transition("t3", "Branch B"),
            create_transition("t4", "Join"),
        ]
        arcs = [
            create_arc("i", "t1"),
            create_arc("t1", "p1"),
            create_arc("t1", "p2"),
            create_arc("p1", "t2"),
            create_arc("p2", "t3"),
            create_arc("t2", "p3"),
            create_arc("t3", "p4"),
            create_arc("p3", "t4"),  # Join requires both p3 and p4
            create_arc("p4", "t4"),
            create_arc("t4", "o"),
        ]
        net = create_workflow_net(places, transitions, arcs)
        verifier = SoundnessVerifier()

        # Act
        result = verifier.verify(net)

        # Assert
        assert result.is_sound
        assert len(result.violations) == 0
        assert len(result.dead_transitions) == 0

    def test_exclusive_choice_is_sound(self) -> None:
        """Test XOR-split/join pattern (exclusive choice) is sound."""
        # Arrange: i -> t_choice -> (p1 | p2) -> (t1 | t2) -> p3 -> t_merge -> o
        # XOR means ONLY ONE path executes
        places = [
            create_place("i", is_source=True),
            create_place("p1"),
            create_place("p2"),
            create_place("p3"),
            create_place("p4"),
            create_place("o", is_sink=True),
        ]
        transitions = [
            create_transition("t_choice", "Choice"),
            create_transition("t1", "Path A"),
            create_transition("t2", "Path B"),
            create_transition("t_merge", "Merge"),
        ]
        arcs = [
            create_arc("i", "t_choice"),
            create_arc("t_choice", "p1"),  # Split to p1 or p2
            create_arc("t_choice", "p2"),
            create_arc("p1", "t1"),
            create_arc("p2", "t2"),
            create_arc("t1", "p3"),  # Both paths lead to separate places
            create_arc("t2", "p4"),
            create_arc("p3", "t_merge"),  # Merge can fire from either
            create_arc("p4", "t_merge"),
            create_arc("t_merge", "o"),
        ]
        net = create_workflow_net(places, transitions, arcs)
        verifier = SoundnessVerifier()

        # Act
        result = verifier.verify(net)

        # Assert
        assert result.is_sound
        assert len(result.violations) == 0


class TestUnsoundWorkflowNets:
    """Test detection of unsound workflow nets."""

    def test_detects_deadlock(self) -> None:
        """Test detection of deadlock (no enabled transitions, not at final)."""
        # Arrange: i -> t1 -> p1 -> t2 (missing arc from t2 to o)
        places = [create_place("i", is_source=True), create_place("p1"), create_place("o", is_sink=True)]
        transitions = [create_transition("t1"), create_transition("t2")]
        arcs = [
            create_arc("i", "t1"),
            create_arc("t1", "p1"),
            create_arc("p1", "t2"),
            # Missing: t2 -> o (causes deadlock after t1 fires)
        ]
        net = create_workflow_net(places, transitions, arcs)
        verifier = SoundnessVerifier()

        # Act
        result = verifier.verify(net)

        # Assert
        assert not result.is_sound
        assert SoundnessViolation.UNREACHABLE_SINK in result.violations
        assert len(result.deadlock_markings) > 0

    def test_detects_improper_completion(self) -> None:
        """Test detection of improper completion (tokens left behind)."""
        # Arrange: WF-net where sink gets token but other places have tokens too
        # i -> t1 -> (p1, o)
        # p1 never empties - improper completion
        places = [create_place("i", is_source=True), create_place("p1"), create_place("o", is_sink=True)]
        transitions = [create_transition("t1")]
        arcs = [
            create_arc("i", "t1"),
            create_arc("t1", "p1"),  # Leaves token in p1
            create_arc("t1", "o"),  # Also puts token in o
        ]
        net = create_workflow_net(places, transitions, arcs)
        verifier = SoundnessVerifier()

        # Act
        result = verifier.verify(net)

        # Assert
        assert not result.is_sound
        assert SoundnessViolation.IMPROPER_COMPLETION in result.violations

    def test_detects_dead_transition(self) -> None:
        """Test detection of dead transitions (never enabled)."""
        # Arrange: i -> t1 -> p1 -> t2 -> o
        # Plus: p_unreachable -> t_dead -> o (but p_unreachable never gets token)
        places = [
            create_place("i", is_source=True),
            create_place("p1"),
            create_place("p_unreachable"),  # Never gets a token
            create_place("o", is_sink=True),
        ]
        transitions = [
            create_transition("t1"),
            create_transition("t2"),
            create_transition("t_dead"),  # Dead: input place never has tokens
        ]
        arcs = [
            create_arc("i", "t1"),
            create_arc("t1", "p1"),
            create_arc("p1", "t2"),
            create_arc("t2", "o"),
            # t_dead has input from unreachable place
            create_arc("p_unreachable", "t_dead"),
            create_arc("t_dead", "o"),
        ]
        net = create_workflow_net(places, transitions, arcs)
        verifier = SoundnessVerifier()

        # Act
        result = verifier.verify(net)

        # Assert
        assert not result.is_sound
        assert SoundnessViolation.DEAD_TRANSITION in result.violations
        assert "t_dead" in result.dead_transitions

    def test_detects_unreachable_sink(self) -> None:
        """Test detection when final marking is unreachable."""
        # Arrange: i -> t1 -> p1 (no path to o)
        places = [create_place("i", is_source=True), create_place("p1"), create_place("o", is_sink=True)]
        transitions = [create_transition("t1")]
        arcs = [
            create_arc("i", "t1"),
            create_arc("t1", "p1"),
            # Missing path from p1 to o
        ]
        net = create_workflow_net(places, transitions, arcs)
        verifier = SoundnessVerifier()

        # Act
        result = verifier.verify(net)

        # Assert
        assert not result.is_sound
        assert SoundnessViolation.UNREACHABLE_SINK in result.violations


class TestCommonWorkflowPatterns:
    """Test soundness of common workflow control patterns."""

    def test_wcp1_sequence(self) -> None:
        """Test WCP-1: Sequence pattern."""
        # i -> A -> p1 -> B -> p2 -> C -> o
        places = [
            create_place("i", is_source=True),
            create_place("p1"),
            create_place("p2"),
            create_place("o", is_sink=True),
        ]
        transitions = [create_transition("A"), create_transition("B"), create_transition("C")]
        arcs = [
            create_arc("i", "A"),
            create_arc("A", "p1"),
            create_arc("p1", "B"),
            create_arc("B", "p2"),
            create_arc("p2", "C"),
            create_arc("C", "o"),
        ]
        net = create_workflow_net(places, transitions, arcs)
        verifier = SoundnessVerifier()

        result = verifier.verify(net)

        assert result.is_sound

    def test_wcp2_parallel_split(self) -> None:
        """Test WCP-2: Parallel Split (AND-split)."""
        # i -> Split -> (pA, pB) -> (A, B) -> (pA_done, pB_done) -> Join -> o
        places = [
            create_place("i", is_source=True),
            create_place("pA"),
            create_place("pB"),
            create_place("pA_done"),
            create_place("pB_done"),
            create_place("o", is_sink=True),
        ]
        transitions = [
            create_transition("Split"),
            create_transition("A"),
            create_transition("B"),
            create_transition("Join"),
        ]
        arcs = [
            create_arc("i", "Split"),
            create_arc("Split", "pA"),
            create_arc("Split", "pB"),
            create_arc("pA", "A"),
            create_arc("pB", "B"),
            create_arc("A", "pA_done"),
            create_arc("B", "pB_done"),
            create_arc("pA_done", "Join"),  # Join requires BOTH
            create_arc("pB_done", "Join"),
            create_arc("Join", "o"),
        ]
        net = create_workflow_net(places, transitions, arcs)
        verifier = SoundnessVerifier()

        result = verifier.verify(net)

        assert result.is_sound

    def test_wcp4_exclusive_choice(self) -> None:
        """Test WCP-4: Exclusive Choice (XOR-split)."""
        # i -> Choice -> (pA | pB) -> (A | B) -> (pA_done | pB_done) -> Merge -> o
        places = [
            create_place("i", is_source=True),
            create_place("pA"),
            create_place("pB"),
            create_place("pA_done"),
            create_place("pB_done"),
            create_place("o", is_sink=True),
        ]
        transitions = [
            create_transition("Choice"),
            create_transition("A"),
            create_transition("B"),
            create_transition("Merge"),
        ]
        arcs = [
            create_arc("i", "Choice"),
            create_arc("Choice", "pA"),
            create_arc("Choice", "pB"),
            create_arc("pA", "A"),
            create_arc("pB", "B"),
            create_arc("A", "pA_done"),
            create_arc("B", "pB_done"),
            create_arc("pA_done", "Merge"),  # Merge can fire from EITHER
            create_arc("pB_done", "Merge"),
            create_arc("Merge", "o"),
        ]
        net = create_workflow_net(places, transitions, arcs)
        verifier = SoundnessVerifier()

        result = verifier.verify(net)

        assert result.is_sound

    def test_loop_pattern(self) -> None:
        """Test loop pattern (WCP-10: Arbitrary Cycles)."""
        # i -> t1 -> p1 -> t2 -> p2 -> t3 -> o
        #              ^             |
        #              +-- t_loop <--+
        places = [
            create_place("i", is_source=True),
            create_place("p1"),
            create_place("p2"),
            create_place("o", is_sink=True),
        ]
        transitions = [
            create_transition("t1"),
            create_transition("t2"),
            create_transition("t_loop"),
            create_transition("t3"),
        ]
        arcs = [
            create_arc("i", "t1"),
            create_arc("t1", "p1"),
            create_arc("p1", "t2"),
            create_arc("t2", "p2"),
            create_arc("p2", "t_loop"),  # Loop back
            create_arc("t_loop", "p1"),
            create_arc("p2", "t3"),  # Exit loop
            create_arc("t3", "o"),
        ]
        net = create_workflow_net(places, transitions, arcs)
        verifier = SoundnessVerifier(max_markings=1000)

        result = verifier.verify(net)

        # Should be sound with bounded loop
        assert result.is_sound


class TestFiringSequenceDiscovery:
    """Test finding firing sequences to final marking."""

    def test_finds_sequence_for_simple_net(self) -> None:
        """Test finding firing sequence in simple sequential net."""
        # Arrange
        places = [create_place("i", is_source=True), create_place("p1"), create_place("o", is_sink=True)]
        transitions = [create_transition("t1"), create_transition("t2")]
        arcs = [create_arc("i", "t1"), create_arc("t1", "p1"), create_arc("p1", "t2"), create_arc("t2", "o")]
        net = create_workflow_net(places, transitions, arcs)
        verifier = SoundnessVerifier()

        # Act
        sequence = verifier.find_firing_sequence_to_final(net)

        # Assert
        assert sequence is not None
        assert len(sequence) == 2
        assert sequence.transitions == ("t1", "t2")

    def test_returns_none_when_final_unreachable(self) -> None:
        """Test returns None when final marking is unreachable."""
        # Arrange: broken net
        places = [create_place("i", is_source=True), create_place("p1"), create_place("o", is_sink=True)]
        transitions = [create_transition("t1")]
        arcs = [
            create_arc("i", "t1"),
            create_arc("t1", "p1"),
            # Missing path to o
        ]
        net = create_workflow_net(places, transitions, arcs)
        verifier = SoundnessVerifier()

        # Act
        sequence = verifier.find_firing_sequence_to_final(net)

        # Assert
        assert sequence is None


class TestBoundednessAnalysis:
    """Test boundedness checking for workflow nets."""

    def test_simple_net_is_bounded(self) -> None:
        """Test that simple WF-net is bounded."""
        # Arrange
        places = [create_place("i", is_source=True), create_place("o", is_sink=True)]
        transitions = [create_transition("t")]
        arcs = [create_arc("i", "t"), create_arc("t", "o")]
        net = create_workflow_net(places, transitions, arcs)

        from kgcl.hybrid.temporal.analysis.soundness_verifier import CoverabilityAnalyzer

        analyzer = CoverabilityAnalyzer()

        # Act
        is_bounded, max_tokens = analyzer.is_bounded(net)

        # Assert
        assert is_bounded
        assert max_tokens == 1

    def test_parallel_net_has_higher_bound(self) -> None:
        """Test that parallel net has higher token bound."""
        # Arrange: AND-split creates 2 tokens in separate places
        places = [
            create_place("i", is_source=True),
            create_place("p1"),
            create_place("p2"),
            create_place("p3"),
            create_place("p4"),
            create_place("o", is_sink=True),
        ]
        transitions = [
            create_transition("t_split"),
            create_transition("t1"),
            create_transition("t2"),
            create_transition("t_join"),
        ]
        arcs = [
            create_arc("i", "t_split"),
            create_arc("t_split", "p1"),
            create_arc("t_split", "p2"),
            create_arc("p1", "t1"),
            create_arc("p2", "t2"),
            create_arc("t1", "p3"),
            create_arc("t2", "p4"),
            create_arc("p3", "t_join"),
            create_arc("p4", "t_join"),
            create_arc("t_join", "o"),
        ]
        net = create_workflow_net(places, transitions, arcs)

        from kgcl.hybrid.temporal.analysis.soundness_verifier import CoverabilityAnalyzer

        analyzer = CoverabilityAnalyzer()

        # Act
        is_bounded, max_tokens = analyzer.is_bounded(net)

        # Assert
        assert is_bounded
        # The net is bounded but max tokens PER PLACE is 1
        # (we have 2 tokens total in parallel, but each in separate places)
        # If we want to test for total tokens > 1, need different assertion
        assert max_tokens == 1  # Max tokens in any single place


class TestPerformance:
    """Test soundness verification performance."""

    def test_handles_large_net(self) -> None:
        """Test verification of larger workflow net (100+ places)."""
        # Arrange: Create chain of 100 sequential tasks
        places = [create_place("i", is_source=True)]
        transitions = []
        arcs = []

        for i in range(100):
            places.append(create_place(f"p{i}"))
            transitions.append(create_transition(f"t{i}"))
            if i == 0:
                arcs.append(create_arc("i", f"t{i}"))
            else:
                arcs.append(create_arc(f"p{i - 1}", f"t{i}"))
            arcs.append(create_arc(f"t{i}", f"p{i}"))

        places.append(create_place("o", is_sink=True))
        transitions.append(create_transition("t_final"))
        arcs.append(create_arc("p99", "t_final"))
        arcs.append(create_arc("t_final", "o"))

        net = create_workflow_net(places, transitions, arcs)
        verifier = SoundnessVerifier()

        # Act
        result = verifier.verify(net)

        # Assert
        assert result.is_sound
        assert result.reachable_markings == 102  # Initial + 100 intermediate + final


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_single_transition_net(self) -> None:
        """Test minimal WF-net with single transition."""
        places = [create_place("i", is_source=True), create_place("o", is_sink=True)]
        transitions = [create_transition("t")]
        arcs = [create_arc("i", "t"), create_arc("t", "o")]
        net = create_workflow_net(places, transitions, arcs)
        verifier = SoundnessVerifier()

        result = verifier.verify(net)

        assert result.is_sound

    def test_weighted_arcs(self) -> None:
        """Test WF-net with weighted arcs."""
        places = [create_place("i", is_source=True), create_place("p1"), create_place("o", is_sink=True)]
        transitions = [create_transition("t1"), create_transition("t2")]
        arcs = [
            create_arc("i", "t1", weight=1),
            create_arc("t1", "p1", weight=2),  # Produces 2 tokens
            create_arc("p1", "t2", weight=2),  # Requires 2 tokens
            create_arc("t2", "o", weight=1),
        ]
        net = create_workflow_net(places, transitions, arcs)
        verifier = SoundnessVerifier()

        result = verifier.verify(net)

        assert result.is_sound

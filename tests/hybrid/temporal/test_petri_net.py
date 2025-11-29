"""Tests for Petri net domain models.

Tests formal Petri net semantics, marking operations, transition firing,
and common workflow patterns (sequence, AND-split, XOR-split).
"""

import pytest

from kgcl.hybrid.temporal.domain.petri_net import (
    Arc,
    FiringSequence,
    Marking,
    PetriNet,
    Place,
    Transition,
    WorkflowNet,
    create_arc,
    create_place,
    create_transition,
    create_workflow_net,
)


class TestPlace:
    """Test Place creation and properties."""

    def test_create_simple_place(self) -> None:
        """Test creating a simple place."""
        p = Place(id="p1", name="Place 1")
        assert p.id == "p1"
        assert p.name == "Place 1"
        assert not p.is_source
        assert not p.is_sink

    def test_create_source_place(self) -> None:
        """Test creating a source place."""
        p = Place(id="start", is_source=True)
        assert p.id == "start"
        assert p.is_source
        assert not p.is_sink

    def test_create_sink_place(self) -> None:
        """Test creating a sink place."""
        p = Place(id="end", is_sink=True)
        assert p.id == "end"
        assert not p.is_source
        assert p.is_sink

    def test_place_hashable(self) -> None:
        """Test places can be used in sets."""
        p1 = Place(id="p1")
        p2 = Place(id="p2")
        p1_dup = Place(id="p1", name="Different Name")

        places = {p1, p2, p1_dup}
        assert len(places) == 2  # p1 and p1_dup have same hash

    def test_place_frozen(self) -> None:
        """Test places are immutable."""
        p = Place(id="p1")
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            p.name = "New Name"  # type: ignore[misc]


class TestTransition:
    """Test Transition creation and properties."""

    def test_create_simple_transition(self) -> None:
        """Test creating a simple transition."""
        t = Transition(id="t1", name="Activity A")
        assert t.id == "t1"
        assert t.name == "Activity A"
        assert not t.is_silent
        assert t.guard is None

    def test_create_silent_transition(self) -> None:
        """Test creating a silent (tau) transition."""
        t = Transition(id="tau", is_silent=True)
        assert t.is_silent

    def test_create_guarded_transition(self) -> None:
        """Test creating a transition with guard."""
        t = Transition(id="t1", guard="amount > 1000")
        assert t.guard == "amount > 1000"

    def test_transition_hashable(self) -> None:
        """Test transitions can be used in sets."""
        t1 = Transition(id="t1")
        t2 = Transition(id="t2")
        t1_dup = Transition(id="t1", name="Different")

        transitions = {t1, t2, t1_dup}
        assert len(transitions) == 2


class TestArc:
    """Test Arc creation and properties."""

    def test_create_simple_arc(self) -> None:
        """Test creating a simple arc."""
        a = Arc(source="p1", target="t1")
        assert a.source == "p1"
        assert a.target == "t1"
        assert a.weight == 1

    def test_create_weighted_arc(self) -> None:
        """Test creating a weighted arc."""
        a = Arc(source="p1", target="t1", weight=3)
        assert a.weight == 3

    def test_arc_hashable(self) -> None:
        """Test arcs can be used in sets."""
        a1 = Arc(source="p1", target="t1")
        a2 = Arc(source="p2", target="t1")
        a1_dup = Arc(source="p1", target="t1", weight=2)

        arcs = {a1, a2, a1_dup}
        assert len(arcs) == 2


class TestMarking:
    """Test Marking operations."""

    def test_create_empty_marking(self) -> None:
        """Test creating empty marking."""
        m = Marking()
        assert len(m) == 0
        assert m.to_dict() == {}

    def test_create_marking_from_dict(self) -> None:
        """Test creating marking from dictionary."""
        m = Marking.from_dict({"p1": 2, "p2": 1})
        assert m.get("p1") == 2
        assert m.get("p2") == 1
        assert len(m) == 3

    def test_marking_get_nonexistent(self) -> None:
        """Test getting tokens from place not in marking."""
        m = Marking.from_dict({"p1": 1})
        assert m.get("p2") == 0

    def test_marking_add_tokens(self) -> None:
        """Test adding tokens to marking."""
        m = Marking.from_dict({"p1": 1})
        m2 = m.add("p1", 2)
        assert m2.get("p1") == 3
        assert m.get("p1") == 1  # Original unchanged

    def test_marking_add_to_new_place(self) -> None:
        """Test adding tokens to new place."""
        m = Marking.from_dict({"p1": 1})
        m2 = m.add("p2", 1)
        assert m2.get("p1") == 1
        assert m2.get("p2") == 1

    def test_marking_remove_tokens(self) -> None:
        """Test removing tokens from marking."""
        m = Marking.from_dict({"p1": 3})
        m2 = m.remove("p1", 2)
        assert m2.get("p1") == 1

    def test_marking_remove_all_tokens(self) -> None:
        """Test removing all tokens removes place from marking."""
        m = Marking.from_dict({"p1": 2})
        m2 = m.remove("p1", 2)
        assert "p1" not in m2.to_dict()
        assert len(m2) == 0

    def test_marking_remove_insufficient_tokens(self) -> None:
        """Test removing more tokens than available raises error."""
        m = Marking.from_dict({"p1": 1})
        with pytest.raises(ValueError, match="Cannot remove 2 tokens"):
            m.remove("p1", 2)

    def test_marking_places_with_tokens(self) -> None:
        """Test getting places with tokens."""
        m = Marking.from_dict({"p1": 2, "p2": 1, "p3": 0})
        places = m.places_with_tokens()
        assert places == {"p1", "p2"}

    def test_marking_immutability(self) -> None:
        """Test marking operations return new instances."""
        m1 = Marking.from_dict({"p1": 1})
        m2 = m1.add("p2", 1)
        assert m1 != m2
        assert m1.get("p2") == 0
        assert m2.get("p2") == 1


class TestPetriNet:
    """Test PetriNet structure and operations."""

    @pytest.fixture
    def simple_net(self) -> PetriNet:
        """Create a simple Petri net: p1 -> t1 -> p2."""
        places = (Place(id="p1", name="Place 1"), Place(id="p2", name="Place 2"))
        transitions = (Transition(id="t1", name="Transition 1"),)
        arcs = (Arc(source="p1", target="t1"), Arc(source="t1", target="p2"))
        return PetriNet(places=places, transitions=transitions, arcs=arcs, name="Simple Net")

    def test_get_place(self, simple_net: PetriNet) -> None:
        """Test getting place by ID."""
        p = simple_net.get_place("p1")
        assert p is not None
        assert p.id == "p1"
        assert simple_net.get_place("nonexistent") is None

    def test_get_transition(self, simple_net: PetriNet) -> None:
        """Test getting transition by ID."""
        t = simple_net.get_transition("t1")
        assert t is not None
        assert t.id == "t1"
        assert simple_net.get_transition("nonexistent") is None

    def test_preset(self, simple_net: PetriNet) -> None:
        """Test getting preset (input nodes)."""
        preset_t1 = simple_net.preset("t1")
        assert preset_t1 == {"p1"}

        preset_p2 = simple_net.preset("p2")
        assert preset_p2 == {"t1"}

    def test_postset(self, simple_net: PetriNet) -> None:
        """Test getting postset (output nodes)."""
        postset_p1 = simple_net.postset("p1")
        assert postset_p1 == {"t1"}

        postset_t1 = simple_net.postset("t1")
        assert postset_t1 == {"p2"}

    def test_input_arcs(self, simple_net: PetriNet) -> None:
        """Test getting input arcs."""
        input_arcs = simple_net.input_arcs("t1")
        assert len(input_arcs) == 1
        assert input_arcs[0].source == "p1"

    def test_output_arcs(self, simple_net: PetriNet) -> None:
        """Test getting output arcs."""
        output_arcs = simple_net.output_arcs("t1")
        assert len(output_arcs) == 1
        assert output_arcs[0].target == "p2"

    def test_is_enabled_true(self, simple_net: PetriNet) -> None:
        """Test transition is enabled with sufficient tokens."""
        m = Marking.from_dict({"p1": 1})
        assert simple_net.is_enabled("t1", m)

    def test_is_enabled_false(self, simple_net: PetriNet) -> None:
        """Test transition is not enabled without tokens."""
        m = Marking.from_dict({"p2": 1})
        assert not simple_net.is_enabled("t1", m)

    def test_enabled_transitions(self, simple_net: PetriNet) -> None:
        """Test getting all enabled transitions."""
        m = Marking.from_dict({"p1": 1})
        enabled = simple_net.enabled_transitions(m)
        assert enabled == {"t1"}

    def test_fire_transition(self, simple_net: PetriNet) -> None:
        """Test firing transition updates marking."""
        m1 = Marking.from_dict({"p1": 1})
        m2 = simple_net.fire("t1", m1)

        assert m2.get("p1") == 0
        assert m2.get("p2") == 1

    def test_fire_disabled_transition(self, simple_net: PetriNet) -> None:
        """Test firing disabled transition raises error."""
        m = Marking.from_dict({"p2": 1})
        with pytest.raises(ValueError, match="not enabled"):
            simple_net.fire("t1", m)

    def test_weighted_arc_enablement(self) -> None:
        """Test transition with weighted arcs."""
        places = (Place(id="p1"), Place(id="p2"))
        transitions = (Transition(id="t1"),)
        arcs = (Arc(source="p1", target="t1", weight=3), Arc(source="t1", target="p2"))
        net = PetriNet(places=places, transitions=transitions, arcs=arcs)

        m1 = Marking.from_dict({"p1": 2})
        assert not net.is_enabled("t1", m1)

        m2 = Marking.from_dict({"p1": 3})
        assert net.is_enabled("t1", m2)

        m3 = net.fire("t1", m2)
        assert m3.get("p1") == 0
        assert m3.get("p2") == 1


class TestWorkflowNet:
    """Test WorkflowNet specific operations."""

    @pytest.fixture
    def simple_wf_net(self) -> WorkflowNet:
        """Create a simple workflow net: i -> t1 -> o."""
        places = [create_place("i", is_source=True), create_place("o", is_sink=True)]
        transitions = [create_transition("t1", "Activity")]
        arcs = [create_arc("i", "t1"), create_arc("t1", "o")]
        return create_workflow_net(places, transitions, arcs, "Simple WF-net")

    def test_source_place(self, simple_wf_net: WorkflowNet) -> None:
        """Test getting source place."""
        source = simple_wf_net.source_place()
        assert source is not None
        assert source.id == "i"
        assert source.is_source

    def test_sink_place(self, simple_wf_net: WorkflowNet) -> None:
        """Test getting sink place."""
        sink = simple_wf_net.sink_place()
        assert sink is not None
        assert sink.id == "o"
        assert sink.is_sink

    def test_initial_marking(self, simple_wf_net: WorkflowNet) -> None:
        """Test initial marking has one token in source."""
        m = simple_wf_net.initial_marking()
        assert m.get("i") == 1
        assert len(m) == 1

    def test_final_marking(self, simple_wf_net: WorkflowNet) -> None:
        """Test final marking has one token in sink."""
        m = simple_wf_net.final_marking()
        assert m.get("o") == 1
        assert len(m) == 1

    def test_is_proper_wf_net(self, simple_wf_net: WorkflowNet) -> None:
        """Test WF-net validation."""
        is_valid, reason = simple_wf_net.is_proper_wf_net()
        assert is_valid
        assert "Valid" in reason

    def test_multiple_sources_invalid(self) -> None:
        """Test WF-net with multiple sources is invalid."""
        places = [Place(id="i1", is_source=True), Place(id="i2", is_source=True), Place(id="o", is_sink=True)]
        transitions = [Transition(id="t1")]
        arcs = [Arc(source="i1", target="t1"), Arc(source="i2", target="t1"), Arc(source="t1", target="o")]
        net = WorkflowNet(places=tuple(places), transitions=tuple(transitions), arcs=tuple(arcs))

        is_valid, reason = net.is_proper_wf_net()
        assert not is_valid
        assert "source" in reason.lower()

    def test_no_sink_invalid(self) -> None:
        """Test WF-net without marked sink is invalid."""
        # p1 has no outgoing arcs but is not marked as sink
        places = [Place(id="i", is_source=True), Place(id="p1")]
        transitions = [Transition(id="t1")]
        arcs = [Arc(source="i", target="t1"), Arc(source="t1", target="p1")]
        net = WorkflowNet(places=tuple(places), transitions=tuple(transitions), arcs=tuple(arcs))

        is_valid, reason = net.is_proper_wf_net()
        assert not is_valid
        assert "sink" in reason.lower()


class TestFiringSequence:
    """Test FiringSequence operations."""

    def test_empty_sequence(self) -> None:
        """Test creating empty firing sequence."""
        seq = FiringSequence()
        assert len(seq) == 0
        assert seq.transitions == ()

    def test_append_transition(self) -> None:
        """Test appending transition to sequence."""
        seq1 = FiringSequence()
        seq2 = seq1.append("t1")
        seq3 = seq2.append("t2")

        assert len(seq3) == 2
        assert seq3.transitions == ("t1", "t2")

    def test_immutability(self) -> None:
        """Test firing sequence immutability."""
        seq1 = FiringSequence()
        seq2 = seq1.append("t1")
        assert len(seq1) == 0
        assert len(seq2) == 1


class TestFactoryFunctions:
    """Test factory functions."""

    def test_create_place(self) -> None:
        """Test create_place factory."""
        p = create_place("p1", name="Place 1", is_source=True)
        assert p.id == "p1"
        assert p.name == "Place 1"
        assert p.is_source

    def test_create_place_default_name(self) -> None:
        """Test create_place uses ID as default name."""
        p = create_place("p1")
        assert p.name == "p1"

    def test_create_transition(self) -> None:
        """Test create_transition factory."""
        t = create_transition("t1", name="Activity", is_silent=True, guard="x > 0")
        assert t.id == "t1"
        assert t.name == "Activity"
        assert t.is_silent
        assert t.guard == "x > 0"

    def test_create_transition_default_name(self) -> None:
        """Test create_transition uses ID as default name."""
        t = create_transition("t1")
        assert t.name == "t1"

    def test_create_arc(self) -> None:
        """Test create_arc factory."""
        a = create_arc("p1", "t1", weight=2)
        assert a.source == "p1"
        assert a.target == "t1"
        assert a.weight == 2

    def test_create_workflow_net(self) -> None:
        """Test create_workflow_net factory."""
        places = [create_place("i", is_source=True)]
        transitions = [create_transition("t1")]
        arcs = [create_arc("i", "t1")]
        net = create_workflow_net(places, transitions, arcs, "Test Net")

        assert net.name == "Test Net"
        assert len(net.places) == 1
        assert len(net.transitions) == 1
        assert len(net.arcs) == 1


class TestWorkflowPatterns:
    """Test common workflow control-flow patterns."""

    def test_sequence_pattern(self) -> None:
        """Test sequence pattern: i -> t1 -> p1 -> t2 -> o."""
        places = [create_place("i", is_source=True), create_place("p1"), create_place("o", is_sink=True)]
        transitions = [create_transition("t1", "A"), create_transition("t2", "B")]
        arcs = [create_arc("i", "t1"), create_arc("t1", "p1"), create_arc("p1", "t2"), create_arc("t2", "o")]
        net = create_workflow_net(places, transitions, arcs, "Sequence")

        # Execute sequence
        m = net.initial_marking()
        assert net.enabled_transitions(m) == {"t1"}

        m = net.fire("t1", m)
        assert net.enabled_transitions(m) == {"t2"}

        m = net.fire("t2", m)
        assert m == net.final_marking()

    def test_and_split_pattern(self) -> None:
        """Test AND-split (parallel split): i -> t1 -> (p1, p2)."""
        places = [
            create_place("i", is_source=True),
            create_place("p1"),
            create_place("p2"),
            create_place("o", is_sink=True),
        ]
        transitions = [create_transition("t_split", "Split"), create_transition("t_join", "Join")]
        arcs = [
            create_arc("i", "t_split"),
            create_arc("t_split", "p1"),
            create_arc("t_split", "p2"),
            create_arc("p1", "t_join"),
            create_arc("p2", "t_join"),
            create_arc("t_join", "o"),
        ]
        net = create_workflow_net(places, transitions, arcs, "AND-split")

        # Fire split
        m = net.initial_marking()
        m = net.fire("t_split", m)

        # Both branches active
        assert m.get("p1") == 1
        assert m.get("p2") == 1

        # Join requires both tokens
        assert net.is_enabled("t_join", m)
        m = net.fire("t_join", m)
        assert m == net.final_marking()

    def test_xor_split_pattern(self) -> None:
        """Test XOR-split (exclusive choice): i -> (t1 | t2) -> o."""
        places = [
            create_place("i", is_source=True),
            create_place("p1"),
            create_place("p2"),
            create_place("o", is_sink=True),
        ]
        transitions = [
            create_transition("t1", "Choice A"),
            create_transition("t2", "Choice B"),
            create_transition("t_merge1", "Merge A"),
            create_transition("t_merge2", "Merge B"),
        ]
        arcs = [
            create_arc("i", "t1"),
            create_arc("i", "t2"),
            create_arc("t1", "p1"),
            create_arc("t2", "p2"),
            create_arc("p1", "t_merge1"),
            create_arc("p2", "t_merge2"),
            create_arc("t_merge1", "o"),
            create_arc("t_merge2", "o"),
        ]
        net = create_workflow_net(places, transitions, arcs, "XOR-split")

        # Choose path 1
        m = net.initial_marking()
        assert net.enabled_transitions(m) == {"t1", "t2"}

        m = net.fire("t1", m)
        assert m.get("p1") == 1
        assert m.get("p2") == 0

        m = net.fire("t_merge1", m)
        assert m == net.final_marking()

    def test_and_join_synchronization(self) -> None:
        """Test AND-join requires all input tokens."""
        places = [create_place("p1"), create_place("p2"), create_place("p3")]
        transitions = [create_transition("t_sync", "Synchronize")]
        arcs = [create_arc("p1", "t_sync"), create_arc("p2", "t_sync"), create_arc("t_sync", "p3")]
        net = PetriNet(places=tuple(places), transitions=tuple(transitions), arcs=tuple(arcs))

        # Only one token - not enabled
        m1 = Marking.from_dict({"p1": 1})
        assert not net.is_enabled("t_sync", m1)

        # Both tokens - enabled
        m2 = Marking.from_dict({"p1": 1, "p2": 1})
        assert net.is_enabled("t_sync", m2)

        m3 = net.fire("t_sync", m2)
        assert m3.get("p3") == 1

    def test_loop_pattern(self) -> None:
        """Test loop pattern with backward arc."""
        places = [create_place("i", is_source=True), create_place("p_loop"), create_place("o", is_sink=True)]
        transitions = [
            create_transition("t_enter", "Enter Loop"),
            create_transition("t_repeat", "Repeat"),
            create_transition("t_exit", "Exit Loop"),
        ]
        arcs = [
            create_arc("i", "t_enter"),
            create_arc("t_enter", "p_loop"),
            create_arc("p_loop", "t_repeat"),
            create_arc("t_repeat", "p_loop"),  # Loop back
            create_arc("p_loop", "t_exit"),
            create_arc("t_exit", "o"),
        ]
        net = create_workflow_net(places, transitions, arcs, "Loop")

        # Enter loop
        m = net.initial_marking()
        m = net.fire("t_enter", m)

        # Can repeat multiple times
        assert net.enabled_transitions(m) == {"t_repeat", "t_exit"}
        m = net.fire("t_repeat", m)
        assert m.get("p_loop") == 1

        # Or exit
        m = net.fire("t_exit", m)
        assert m == net.final_marking()

    def test_deferred_choice_pattern(self) -> None:
        """Test deferred choice (environment chooses)."""
        places = [
            create_place("i", is_source=True),
            create_place("p1"),
            create_place("p2"),
            create_place("o", is_sink=True),
        ]
        transitions = [
            create_transition("t1", "Path A"),
            create_transition("t2", "Path B"),
            create_transition("t_merge1", "Merge A"),
            create_transition("t_merge2", "Merge B"),
        ]
        arcs = [
            create_arc("i", "t1"),
            create_arc("i", "t2"),
            create_arc("t1", "p1"),
            create_arc("t2", "p2"),
            create_arc("p1", "t_merge1"),
            create_arc("p2", "t_merge2"),
            create_arc("t_merge1", "o"),
            create_arc("t_merge2", "o"),
        ]
        net = create_workflow_net(places, transitions, arcs, "Deferred Choice")

        # Both transitions enabled initially
        m = net.initial_marking()
        enabled = net.enabled_transitions(m)
        assert "t1" in enabled
        assert "t2" in enabled

        # Firing one disables the other
        m = net.fire("t1", m)
        assert m.get("i") == 0
        assert net.enabled_transitions(m) == {"t_merge1"}

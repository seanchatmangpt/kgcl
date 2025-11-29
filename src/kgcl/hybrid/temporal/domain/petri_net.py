"""Petri net domain models for formal workflow verification.

Implements workflow nets (WF-nets) per van der Aalst's definitions
for soundness verification and process mining.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class NodeType(Enum):
    """Petri net node types."""

    PLACE = auto()
    TRANSITION = auto()


@dataclass(frozen=True)
class Place:
    """Petri net place (passive element, holds tokens).

    Parameters
    ----------
    id : str
        Unique place identifier
    name : str
        Human-readable name
    is_source : bool
        True if this is the unique source place (workflow start)
    is_sink : bool
        True if this is the unique sink place (workflow end)
    """

    id: str
    name: str = ""
    is_source: bool = False
    is_sink: bool = False

    def __hash__(self) -> int:
        """Hash based on ID for use in sets/dicts."""
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        """Equality based on ID only."""
        if not isinstance(other, Place):
            return NotImplemented
        return self.id == other.id


@dataclass(frozen=True)
class Transition:
    """Petri net transition (active element, fires when enabled).

    Parameters
    ----------
    id : str
        Unique transition identifier
    name : str
        Human-readable name (activity name)
    is_silent : bool
        True if invisible transition (tau)
    guard : str | None
        Guard condition expression
    """

    id: str
    name: str = ""
    is_silent: bool = False
    guard: str | None = None

    def __hash__(self) -> int:
        """Hash based on ID for use in sets/dicts."""
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        """Equality based on ID only."""
        if not isinstance(other, Transition):
            return NotImplemented
        return self.id == other.id


@dataclass(frozen=True)
class Arc:
    """Petri net arc connecting place to transition or vice versa.

    Parameters
    ----------
    source : str
        Source node ID
    target : str
        Target node ID
    weight : int
        Arc weight (default 1)
    """

    source: str
    target: str
    weight: int = 1

    def __hash__(self) -> int:
        """Hash based on source and target."""
        return hash((self.source, self.target))

    def __eq__(self, other: object) -> bool:
        """Equality based on source and target only (ignoring weight)."""
        if not isinstance(other, Arc):
            return NotImplemented
        return self.source == other.source and self.target == other.target


@dataclass(frozen=True)
class Marking:
    """Petri net marking (token distribution).

    A marking is a multiset of places, represented as place_id -> token_count.

    Parameters
    ----------
    tokens : tuple[tuple[str, int], ...]
        Tuple of (place_id, token_count) pairs
    """

    tokens: tuple[tuple[str, int], ...] = ()

    @classmethod
    def from_dict(cls, token_dict: dict[str, int]) -> Marking:
        """Create marking from dictionary.

        Parameters
        ----------
        token_dict : dict[str, int]
            Mapping from place_id to token count

        Returns
        -------
        Marking
            New marking with sorted tokens
        """
        return cls(tokens=tuple(sorted(token_dict.items())))

    def to_dict(self) -> dict[str, int]:
        """Convert to dictionary.

        Returns
        -------
        dict[str, int]
            Mapping from place_id to token count
        """
        return dict(self.tokens)

    def get(self, place_id: str) -> int:
        """Get token count for place.

        Parameters
        ----------
        place_id : str
            Place identifier

        Returns
        -------
        int
            Number of tokens in place (0 if place not in marking)
        """
        for pid, count in self.tokens:
            if pid == place_id:
                return count
        return 0

    def add(self, place_id: str, count: int = 1) -> Marking:
        """Return new marking with tokens added to place.

        Parameters
        ----------
        place_id : str
            Place identifier
        count : int
            Number of tokens to add

        Returns
        -------
        Marking
            New marking with tokens added
        """
        token_dict = self.to_dict()
        token_dict[place_id] = token_dict.get(place_id, 0) + count
        # Remove zero entries
        token_dict = {k: v for k, v in token_dict.items() if v > 0}
        return Marking.from_dict(token_dict)

    def remove(self, place_id: str, count: int = 1) -> Marking:
        """Return new marking with tokens removed from place.

        Parameters
        ----------
        place_id : str
            Place identifier
        count : int
            Number of tokens to remove

        Returns
        -------
        Marking
            New marking with tokens removed

        Raises
        ------
        ValueError
            If insufficient tokens in place
        """
        token_dict = self.to_dict()
        current = token_dict.get(place_id, 0)
        if current < count:
            msg = f"Cannot remove {count} tokens from {place_id}, only {current} available"
            raise ValueError(msg)
        token_dict[place_id] = current - count
        if token_dict[place_id] == 0:
            del token_dict[place_id]
        return Marking.from_dict(token_dict)

    def __len__(self) -> int:
        """Total token count.

        Returns
        -------
        int
            Sum of all tokens in marking
        """
        return sum(count for _, count in self.tokens)

    def places_with_tokens(self) -> frozenset[str]:
        """Set of places that have tokens.

        Returns
        -------
        frozenset[str]
            Place IDs with non-zero token count
        """
        return frozenset(pid for pid, count in self.tokens if count > 0)


@dataclass(frozen=True)
class PetriNet:
    """Petri net structure.

    Parameters
    ----------
    places : tuple[Place, ...]
        All places in the net
    transitions : tuple[Transition, ...]
        All transitions in the net
    arcs : tuple[Arc, ...]
        All arcs (flow relation)
    name : str
        Net name
    """

    places: tuple[Place, ...] = ()
    transitions: tuple[Transition, ...] = ()
    arcs: tuple[Arc, ...] = ()
    name: str = ""

    def get_place(self, place_id: str) -> Place | None:
        """Get place by ID.

        Parameters
        ----------
        place_id : str
            Place identifier

        Returns
        -------
        Place | None
            Place if found, None otherwise
        """
        for p in self.places:
            if p.id == place_id:
                return p
        return None

    def get_transition(self, transition_id: str) -> Transition | None:
        """Get transition by ID.

        Parameters
        ----------
        transition_id : str
            Transition identifier

        Returns
        -------
        Transition | None
            Transition if found, None otherwise
        """
        for t in self.transitions:
            if t.id == transition_id:
                return t
        return None

    def preset(self, node_id: str) -> frozenset[str]:
        """Get preset (input nodes) of a node.

        Parameters
        ----------
        node_id : str
            Node identifier

        Returns
        -------
        frozenset[str]
            IDs of nodes with arcs to this node
        """
        return frozenset(arc.source for arc in self.arcs if arc.target == node_id)

    def postset(self, node_id: str) -> frozenset[str]:
        """Get postset (output nodes) of a node.

        Parameters
        ----------
        node_id : str
            Node identifier

        Returns
        -------
        frozenset[str]
            IDs of nodes with arcs from this node
        """
        return frozenset(arc.target for arc in self.arcs if arc.source == node_id)

    def input_arcs(self, node_id: str) -> tuple[Arc, ...]:
        """Get input arcs of a node.

        Parameters
        ----------
        node_id : str
            Node identifier

        Returns
        -------
        tuple[Arc, ...]
            Arcs targeting this node
        """
        return tuple(arc for arc in self.arcs if arc.target == node_id)

    def output_arcs(self, node_id: str) -> tuple[Arc, ...]:
        """Get output arcs of a node.

        Parameters
        ----------
        node_id : str
            Node identifier

        Returns
        -------
        tuple[Arc, ...]
            Arcs originating from this node
        """
        return tuple(arc for arc in self.arcs if arc.source == node_id)

    def source_place(self) -> Place | None:
        """Get unique source place (i).

        Returns
        -------
        Place | None
            Source place if exactly one exists, None otherwise
        """
        sources = [p for p in self.places if p.is_source]
        return sources[0] if len(sources) == 1 else None

    def sink_place(self) -> Place | None:
        """Get unique sink place (o).

        Returns
        -------
        Place | None
            Sink place if exactly one exists, None otherwise
        """
        sinks = [p for p in self.places if p.is_sink]
        return sinks[0] if len(sinks) == 1 else None

    def is_enabled(self, transition_id: str, marking: Marking) -> bool:
        """Check if transition is enabled at marking.

        A transition is enabled if all input places have sufficient tokens.

        Parameters
        ----------
        transition_id : str
            Transition identifier
        marking : Marking
            Current marking

        Returns
        -------
        bool
            True if transition is enabled
        """
        for arc in self.input_arcs(transition_id):
            if marking.get(arc.source) < arc.weight:
                return False
        return True

    def enabled_transitions(self, marking: Marking) -> frozenset[str]:
        """Get all transitions enabled at marking.

        Parameters
        ----------
        marking : Marking
            Current marking

        Returns
        -------
        frozenset[str]
            IDs of enabled transitions
        """
        return frozenset(t.id for t in self.transitions if self.is_enabled(t.id, marking))

    def fire(self, transition_id: str, marking: Marking) -> Marking:
        """Fire transition and return new marking.

        Parameters
        ----------
        transition_id : str
            Transition to fire
        marking : Marking
            Current marking

        Returns
        -------
        Marking
            New marking after firing

        Raises
        ------
        ValueError
            If transition is not enabled
        """
        if not self.is_enabled(transition_id, marking):
            msg = f"Transition {transition_id} not enabled at {marking}"
            raise ValueError(msg)

        new_marking = marking

        # Remove tokens from input places
        for arc in self.input_arcs(transition_id):
            new_marking = new_marking.remove(arc.source, arc.weight)

        # Add tokens to output places
        for arc in self.output_arcs(transition_id):
            new_marking = new_marking.add(arc.target, arc.weight)

        return new_marking


@dataclass(frozen=True)
class WorkflowNet(PetriNet):
    """Workflow net (WF-net) - special Petri net for workflows.

    A WF-net has:
    - Exactly one source place i (no incoming arcs)
    - Exactly one sink place o (no outgoing arcs)
    - Every node on a path from i to o

    Initial marking: [i]
    Final marking: [o]
    """

    def initial_marking(self) -> Marking:
        """Get initial marking [i].

        Returns
        -------
        Marking
            Marking with one token in source place

        Raises
        ------
        ValueError
            If WF-net has no source place
        """
        source = self.source_place()
        if source is None:
            msg = "WF-net has no source place"
            raise ValueError(msg)
        return Marking.from_dict({source.id: 1})

    def final_marking(self) -> Marking:
        """Get final marking [o].

        Returns
        -------
        Marking
            Marking with one token in sink place

        Raises
        ------
        ValueError
            If WF-net has no sink place
        """
        sink = self.sink_place()
        if sink is None:
            msg = "WF-net has no sink place"
            raise ValueError(msg)
        return Marking.from_dict({sink.id: 1})

    def is_proper_wf_net(self) -> tuple[bool, str]:
        """Check if this is a proper WF-net.

        Returns
        -------
        tuple[bool, str]
            (is_valid, reason)
        """
        # Check unique source (no incoming arcs)
        sources = [p for p in self.places if not self.preset(p.id)]
        if len(sources) != 1:
            return False, f"Expected 1 source place, found {len(sources)}"

        # Check unique sink (no outgoing arcs)
        sinks = [p for p in self.places if not self.postset(p.id)]
        if len(sinks) != 1:
            return False, f"Expected 1 sink place, found {len(sinks)}"

        # Verify source and sink are marked
        source = sources[0]
        sink = sinks[0]
        if not source.is_source:
            return False, f"Source place {source.id} not marked as source"
        if not sink.is_sink:
            return False, f"Sink place {sink.id} not marked as sink"

        # Check all nodes on path from source to sink
        # (simplified - full check requires reachability)
        return True, "Valid WF-net structure"


@dataclass(frozen=True)
class FiringSequence:
    """Sequence of transition firings.

    Parameters
    ----------
    transitions : tuple[str, ...]
        Ordered sequence of transition IDs
    """

    transitions: tuple[str, ...] = ()

    def append(self, transition_id: str) -> FiringSequence:
        """Return new sequence with transition appended.

        Parameters
        ----------
        transition_id : str
            Transition to append

        Returns
        -------
        FiringSequence
            New sequence with transition added
        """
        return FiringSequence(transitions=(*self.transitions, transition_id))

    def __len__(self) -> int:
        """Sequence length.

        Returns
        -------
        int
            Number of transitions in sequence
        """
        return len(self.transitions)


# Factory functions
def create_place(id: str, name: str = "", is_source: bool = False, is_sink: bool = False) -> Place:
    """Create a place.

    Parameters
    ----------
    id : str
        Unique place identifier
    name : str
        Human-readable name (defaults to id)
    is_source : bool
        True if source place
    is_sink : bool
        True if sink place

    Returns
    -------
    Place
        New place instance
    """
    return Place(id=id, name=name or id, is_source=is_source, is_sink=is_sink)


def create_transition(id: str, name: str = "", is_silent: bool = False, guard: str | None = None) -> Transition:
    """Create a transition.

    Parameters
    ----------
    id : str
        Unique transition identifier
    name : str
        Human-readable name (defaults to id)
    is_silent : bool
        True if invisible transition (tau)
    guard : str | None
        Guard condition expression

    Returns
    -------
    Transition
        New transition instance
    """
    return Transition(id=id, name=name or id, is_silent=is_silent, guard=guard)


def create_arc(source: str, target: str, weight: int = 1) -> Arc:
    """Create an arc.

    Parameters
    ----------
    source : str
        Source node ID
    target : str
        Target node ID
    weight : int
        Arc weight (default 1)

    Returns
    -------
    Arc
        New arc instance
    """
    return Arc(source=source, target=target, weight=weight)


def create_workflow_net(
    places: list[Place], transitions: list[Transition], arcs: list[Arc], name: str = ""
) -> WorkflowNet:
    """Create a workflow net.

    Parameters
    ----------
    places : list[Place]
        All places in the net
    transitions : list[Transition]
        All transitions in the net
    arcs : list[Arc]
        All arcs in the net
    name : str
        Net name

    Returns
    -------
    WorkflowNet
        New workflow net instance
    """
    return WorkflowNet(places=tuple(places), transitions=tuple(transitions), arcs=tuple(arcs), name=name)

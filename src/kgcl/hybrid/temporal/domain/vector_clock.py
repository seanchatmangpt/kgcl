"""Lamport vector clock for distributed causality tracking."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VectorClock:
    """Lamport vector clock for distributed causality.

    Vector clocks track happened-before relationships in distributed systems.
    Each node maintains a logical clock that increments on local events and
    merges on message receipt.

    Parameters
    ----------
    clocks : tuple[tuple[str, int], ...]
        Mapping of node_id to logical clock value
    """

    clocks: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        """Normalize clocks to remove duplicate node IDs, keeping max value."""
        clock_dict: dict[str, int] = {}
        for node_id, time in self.clocks:
            clock_dict[node_id] = max(clock_dict.get(node_id, 0), time)

        normalized = tuple(sorted(clock_dict.items()))
        if normalized != self.clocks:
            object.__setattr__(self, "clocks", normalized)

    @staticmethod
    def zero(node_id: str) -> VectorClock:
        """Create a zero vector clock for a single node.

        Parameters
        ----------
        node_id : str
            Node identifier

        Returns
        -------
        VectorClock
            Vector clock with single node at time 0
        """
        return VectorClock(clocks=((node_id, 0),))

    def increment(self, node_id: str) -> VectorClock:
        """Increment clock for specified node.

        Parameters
        ----------
        node_id : str
            Node whose clock to increment

        Returns
        -------
        VectorClock
            New vector clock with incremented value
        """
        clock_dict = dict(self.clocks)
        clock_dict[node_id] = clock_dict.get(node_id, 0) + 1
        return VectorClock(clocks=tuple(sorted(clock_dict.items())))

    def merge(self, other: VectorClock) -> VectorClock:
        """Merge this clock with another, taking element-wise maximum.

        Parameters
        ----------
        other : VectorClock
            Vector clock to merge with

        Returns
        -------
        VectorClock
            Merged vector clock
        """
        clock_dict = dict(self.clocks)

        for node_id, time in other.clocks:
            clock_dict[node_id] = max(clock_dict.get(node_id, 0), time)

        return VectorClock(clocks=tuple(sorted(clock_dict.items())))

    def happens_before(self, other: VectorClock) -> bool:
        """Check if this clock happened before another.

        Clock A happens before B iff:
        - For all nodes, A[node] <= B[node]
        - For at least one node, A[node] < B[node]

        Parameters
        ----------
        other : VectorClock
            Vector clock to compare with

        Returns
        -------
        bool
            True if this clock happened before other
        """
        this_dict = dict(self.clocks)
        other_dict = dict(other.clocks)

        # Get all nodes from both clocks
        all_nodes = set(this_dict.keys()) | set(other_dict.keys())

        # Check if all components are <=
        all_leq = all(this_dict.get(node, 0) <= other_dict.get(node, 0) for node in all_nodes)

        # Check if at least one component is <
        any_less = any(this_dict.get(node, 0) < other_dict.get(node, 0) for node in all_nodes)

        return all_leq and any_less

    def concurrent_with(self, other: VectorClock) -> bool:
        """Check if this clock is concurrent with another.

        Clocks are concurrent if neither happened before the other.

        Parameters
        ----------
        other : VectorClock
            Vector clock to compare with

        Returns
        -------
        bool
            True if clocks are concurrent
        """
        return not self.happens_before(other) and not other.happens_before(self)

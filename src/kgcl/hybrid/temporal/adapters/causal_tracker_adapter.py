"""Causal tracking implementation using event store."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from kgcl.hybrid.temporal.domain.vector_clock import VectorClock
from kgcl.hybrid.temporal.ports.causal_port import CausalExplanation, CausalGraph, CausalityAnalyzer, CausalTracker
from kgcl.hybrid.temporal.ports.event_store_port import EventStore


@dataclass
class InMemoryCausalTracker:
    """In-memory causal tracker with DAG operations.

    Maintains bidirectional mappings for efficient causal queries.

    Attributes
    ----------
    event_store : EventStore
        Event store for retrieving event details
    """

    event_store: EventStore

    # Internal state
    _causes: dict[str, tuple[str, ...]] = field(default_factory=dict)
    _effects: dict[str, list[str]] = field(default_factory=dict)

    def track_causation(self, effect_id: str, cause_ids: tuple[str, ...]) -> None:
        """Record causal relationship.

        Parameters
        ----------
        effect_id : str
            Event that was caused
        cause_ids : tuple[str, ...]
            Events that caused the effect
        """
        self._causes[effect_id] = cause_ids

        # Update reverse mapping
        for cause_id in cause_ids:
            if cause_id not in self._effects:
                self._effects[cause_id] = []
            if effect_id not in self._effects[cause_id]:
                self._effects[cause_id].append(effect_id)

    def get_direct_causes(self, event_id: str) -> tuple[str, ...]:
        """Get immediate causes of an event.

        Parameters
        ----------
        event_id : str
            Event to query

        Returns
        -------
        tuple[str, ...]
            Direct cause event IDs
        """
        return self._causes.get(event_id, ())

    def get_transitive_causes(self, event_id: str, max_depth: int = 100) -> tuple[str, ...]:
        """Get all causal ancestors up to max_depth.

        Uses BFS to traverse causal graph backwards.

        Parameters
        ----------
        event_id : str
            Event to query
        max_depth : int, default=100
            Maximum traversal depth

        Returns
        -------
        tuple[str, ...]
            All ancestor event IDs in BFS order
        """
        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(event_id, 0)])
        result: list[str] = []

        while queue:
            current_id, depth = queue.popleft()

            if depth >= max_depth:
                continue

            # Get direct causes
            direct_causes = self._causes.get(current_id, ())
            for cause_id in direct_causes:
                if cause_id not in visited:
                    visited.add(cause_id)
                    result.append(cause_id)
                    queue.append((cause_id, depth + 1))

        return tuple(result)

    def get_root_causes(self, event_id: str) -> tuple[str, ...]:
        """Get events with no causes (roots of causal chain).

        Parameters
        ----------
        event_id : str
            Event to query

        Returns
        -------
        tuple[str, ...]
            Root cause event IDs
        """
        all_causes = self.get_transitive_causes(event_id)
        roots: list[str] = []

        for cause_id in all_causes:
            if cause_id not in self._causes or not self._causes[cause_id]:
                roots.append(cause_id)

        return tuple(roots)

    def build_causal_graph(self, event_ids: tuple[str, ...]) -> CausalGraph:
        """Build DAG for a set of events.

        Includes all causal edges between the specified events.

        Parameters
        ----------
        event_ids : tuple[str, ...]
            Events to include in graph

        Returns
        -------
        CausalGraph
            Directed acyclic graph of causality
        """
        event_set = frozenset(event_ids)
        edges: set[tuple[str, str]] = set()

        for effect_id in event_ids:
            if effect_id in self._causes:
                for cause_id in self._causes[effect_id]:
                    if cause_id in event_set:
                        edges.add((cause_id, effect_id))

        return CausalGraph(nodes=event_set, edges=frozenset(edges))


@dataclass
class DefaultCausalityAnalyzer:
    """High-level causal analysis using tracker and event store.

    Attributes
    ----------
    tracker : CausalTracker
        Causal tracking implementation
    event_store : EventStore
        Event store for retrieving event details
    """

    tracker: CausalTracker
    event_store: EventStore

    def explain_event(self, event_id: str) -> CausalExplanation:
        """Generate detailed explanation with narrative.

        Parameters
        ----------
        event_id : str
            Event to explain

        Returns
        -------
        CausalExplanation
            Complete causal explanation
        """
        # 1. Get event from store
        effect = self.event_store.get_by_id(event_id)
        if not effect:
            msg = f"Event {event_id} not found"
            raise ValueError(msg)

        # 2. Get direct causes
        direct_cause_ids = self.tracker.get_direct_causes(event_id)
        direct_causes = tuple(evt for cid in direct_cause_ids if (evt := self.event_store.get_by_id(cid)) is not None)

        # 3. Get transitive causes (indirect = all - direct)
        all_cause_ids = self.tracker.get_transitive_causes(event_id)
        indirect_cause_ids = tuple(cid for cid in all_cause_ids if cid not in direct_cause_ids)
        indirect_causes = tuple(
            evt for cid in indirect_cause_ids if (evt := self.event_store.get_by_id(cid)) is not None
        )

        # 4. Get root causes
        root_cause_ids = self.tracker.get_root_causes(event_id)
        root_causes = tuple(evt for cid in root_cause_ids if (evt := self.event_store.get_by_id(cid)) is not None)

        # 5. Extract rule_uri from event payloads
        rules_involved = tuple(
            sorted(
                {
                    evt.payload.get("rule_uri", "")
                    for evt in [effect, *direct_causes, *indirect_causes]
                    if evt.payload.get("rule_uri")
                }
            )
        )

        # 6. Build narrative text
        explanation_text = self._build_narrative(
            effect=effect, direct_causes=direct_causes, root_causes=root_causes, rules_involved=rules_involved
        )

        return CausalExplanation(
            effect=effect,
            direct_causes=direct_causes,
            indirect_causes=indirect_causes,
            root_causes=root_causes,
            rules_involved=rules_involved,
            explanation_text=explanation_text,
        )

    def _build_narrative(
        self,
        effect: WorkflowEvent,
        direct_causes: tuple[WorkflowEvent, ...],
        root_causes: tuple[WorkflowEvent, ...],
        rules_involved: tuple[str, ...],
    ) -> str:
        """Build human-readable narrative explanation.

        Parameters
        ----------
        effect : WorkflowEvent
            Event being explained
        direct_causes : tuple[WorkflowEvent, ...]
            Direct causes
        root_causes : tuple[WorkflowEvent, ...]
            Root causes
        rules_involved : tuple[str, ...]
            Rules that created causal links

        Returns
        -------
        str
            Multi-line narrative
        """
        lines = [f"Event {effect.event_id} ({effect.event_type}) occurred because:", ""]

        if direct_causes:
            lines.append("Direct causes:")
            for cause in direct_causes:
                lines.append(f"  - {cause.event_id} ({cause.event_type})")
            lines.append("")

        if root_causes:
            lines.append("Root causes:")
            for root in root_causes:
                lines.append(f"  - {root.event_id} ({root.event_type})")
            lines.append("")

        if rules_involved:
            lines.append("Rules involved:")
            for rule in rules_involved:
                lines.append(f"  - {rule}")
            lines.append("")

        return "\n".join(lines)

    def find_common_causes(self, event_ids: tuple[str, ...]) -> tuple[str, ...]:
        """Intersection of all causal ancestors.

        Parameters
        ----------
        event_ids : tuple[str, ...]
            Events to analyze

        Returns
        -------
        tuple[str, ...]
            Common ancestor event IDs
        """
        if not event_ids:
            return ()

        # Get causes for first event
        common_set = set(self.tracker.get_transitive_causes(event_ids[0]))

        # Intersect with causes of remaining events
        for event_id in event_ids[1:]:
            causes = set(self.tracker.get_transitive_causes(event_id))
            common_set &= causes

        return tuple(sorted(common_set))

    def check_causally_related(self, event_a_id: str, event_b_id: str) -> bool:
        """Use vector clocks for happens-before check.

        Parameters
        ----------
        event_a_id : str
            First event
        event_b_id : str
            Second event

        Returns
        -------
        bool
            True if one event caused the other
        """
        # Get events from store
        event_a = self.event_store.get_by_id(event_a_id)
        event_b = self.event_store.get_by_id(event_b_id)

        if not event_a or not event_b:
            return False

        # Reconstruct VectorClock objects from tuples
        vc_a = VectorClock(clocks=event_a.vector_clock)
        vc_b = VectorClock(clocks=event_b.vector_clock)

        # Check vector clock happens-before in both directions
        return vc_a.happens_before(vc_b) or vc_b.happens_before(vc_a)

    def check_concurrent(self, event_a_id: str, event_b_id: str) -> bool:
        """Use vector clocks - concurrent if neither happens-before.

        Parameters
        ----------
        event_a_id : str
            First event
        event_b_id : str
            Second event

        Returns
        -------
        bool
            True if events are concurrent
        """
        # Get events from store
        event_a = self.event_store.get_by_id(event_a_id)
        event_b = self.event_store.get_by_id(event_b_id)

        if not event_a or not event_b:
            return False

        # Reconstruct VectorClock objects from tuples
        vc_a = VectorClock(clocks=event_a.vector_clock)
        vc_b = VectorClock(clocks=event_b.vector_clock)

        # Concurrent if neither happens before the other
        a_before_b = vc_a.happens_before(vc_b)
        b_before_a = vc_b.happens_before(vc_a)

        return not a_before_b and not b_before_a

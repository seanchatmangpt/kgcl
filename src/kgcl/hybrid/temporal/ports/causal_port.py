"""Causal tracking port for "Why did this fire?" queries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from kgcl.hybrid.temporal.domain.event import WorkflowEvent


@dataclass(frozen=True)
class CausalExplanation:
    """Explains why an event occurred.

    Attributes
    ----------
    effect : WorkflowEvent
        The event being explained
    direct_causes : tuple[WorkflowEvent, ...]
        Events that directly triggered this event
    indirect_causes : tuple[WorkflowEvent, ...]
        Events that transitively contributed (not direct)
    root_causes : tuple[WorkflowEvent, ...]
        Events with no causes (roots of causal chain)
    rules_involved : tuple[str, ...]
        URIs of rules that created the causal links
    explanation_text : str
        Human-readable narrative explanation
    """

    effect: WorkflowEvent
    direct_causes: tuple[WorkflowEvent, ...]
    indirect_causes: tuple[WorkflowEvent, ...]
    root_causes: tuple[WorkflowEvent, ...]
    rules_involved: tuple[str, ...]
    explanation_text: str

    def to_narrative(self) -> str:
        """Human-readable explanation of causality.

        Returns
        -------
        str
            Multi-line narrative explanation
        """
        return self.explanation_text


@dataclass(frozen=True)
class CausalGraph:
    """Directed acyclic graph of causal relationships.

    Attributes
    ----------
    nodes : frozenset[str]
        Event IDs in the graph
    edges : frozenset[tuple[str, str]]
        Directed edges (cause_id, effect_id)
    """

    nodes: frozenset[str]
    edges: frozenset[tuple[str, str]]

    def get_ancestors(self, event_id: str) -> frozenset[str]:
        """Get all transitive causes of an event.

        Parameters
        ----------
        event_id : str
            Event to query

        Returns
        -------
        frozenset[str]
            All ancestor event IDs
        """
        visited: set[str] = set()
        stack = [event_id]

        while stack:
            current = stack.pop()
            for cause, effect in self.edges:
                if effect == current and cause not in visited:
                    visited.add(cause)
                    stack.append(cause)

        return frozenset(visited)

    def get_descendants(self, event_id: str) -> frozenset[str]:
        """Get all transitive effects of an event.

        Parameters
        ----------
        event_id : str
            Event to query

        Returns
        -------
        frozenset[str]
            All descendant event IDs
        """
        visited: set[str] = set()
        stack = [event_id]

        while stack:
            current = stack.pop()
            for cause, effect in self.edges:
                if cause == current and effect not in visited:
                    visited.add(effect)
                    stack.append(effect)

        return frozenset(visited)

    def is_ancestor(self, ancestor_id: str, descendant_id: str) -> bool:
        """Check if ancestor is in causal past of descendant.

        Parameters
        ----------
        ancestor_id : str
            Potential ancestor event
        descendant_id : str
            Potential descendant event

        Returns
        -------
        bool
            True if ancestor causally precedes descendant
        """
        return ancestor_id in self.get_ancestors(descendant_id)

    def topological_sort(self) -> tuple[str, ...]:
        """Return events in causal order (Kahn's algorithm).

        Returns
        -------
        tuple[str, ...]
            Events sorted in topological order
        """
        # Calculate in-degrees
        in_degree: dict[str, int] = {node: 0 for node in self.nodes}
        for _, effect in self.edges:
            in_degree[effect] = in_degree.get(effect, 0) + 1

        # Start with nodes having no incoming edges
        queue = [node for node in self.nodes if in_degree[node] == 0]
        result: list[str] = []

        while queue:
            current = queue.pop(0)
            result.append(current)

            # Reduce in-degree of successors
            for cause, effect in self.edges:
                if cause == current:
                    in_degree[effect] -= 1
                    if in_degree[effect] == 0:
                        queue.append(effect)

        return tuple(result)


@runtime_checkable
class CausalTracker(Protocol):
    """Protocol for causal dependency tracking.

    Tracks cause-effect relationships between workflow events
    to enable "why did this fire?" queries.
    """

    def track_causation(self, effect_id: str, cause_ids: tuple[str, ...]) -> None:
        """Record causal relationship.

        Parameters
        ----------
        effect_id : str
            Event that was caused
        cause_ids : tuple[str, ...]
            Events that caused the effect
        """
        ...

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
        ...

    def get_transitive_causes(self, event_id: str, max_depth: int = 100) -> tuple[str, ...]:
        """Get all causal ancestors up to max_depth.

        Parameters
        ----------
        event_id : str
            Event to query
        max_depth : int, default=100
            Maximum traversal depth

        Returns
        -------
        tuple[str, ...]
            All ancestor event IDs
        """
        ...

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
        ...

    def build_causal_graph(self, event_ids: tuple[str, ...]) -> CausalGraph:
        """Build DAG for a set of events.

        Parameters
        ----------
        event_ids : tuple[str, ...]
            Events to include in graph

        Returns
        -------
        CausalGraph
            Directed acyclic graph of causality
        """
        ...


@runtime_checkable
class CausalityAnalyzer(Protocol):
    """Protocol for high-level causal analysis.

    Provides semantic analysis of causal relationships,
    generating explanations and detecting patterns.
    """

    def explain_event(self, event_id: str) -> CausalExplanation:
        """Generate full explanation for why event occurred.

        Parameters
        ----------
        event_id : str
            Event to explain

        Returns
        -------
        CausalExplanation
            Complete causal explanation
        """
        ...

    def find_common_causes(self, event_ids: tuple[str, ...]) -> tuple[str, ...]:
        """Find common causal ancestors of multiple events.

        Parameters
        ----------
        event_ids : tuple[str, ...]
            Events to analyze

        Returns
        -------
        tuple[str, ...]
            Common ancestor event IDs
        """
        ...

    def check_causally_related(self, event_a_id: str, event_b_id: str) -> bool:
        """Check if two events are causally related (either direction).

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
        ...

    def check_concurrent(self, event_a_id: str, event_b_id: str) -> bool:
        """Check if two events are concurrent (neither caused the other).

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
        ...

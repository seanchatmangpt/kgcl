"""Semantic projector port for deriving state from events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class ProjectionResult:
    """Result of state projection."""

    state: dict[str, Any]  # Current state as dict
    as_of: datetime
    sequence_number: int
    events_applied: int
    cache_hit: bool
    duration_ms: float


@dataclass(frozen=True)
class StateDiff:
    """Difference between two projections.

    Note: Values are serialized to JSON strings for hashability.
    """

    additions: frozenset[tuple[str, str]]  # (key, value_json) added
    removals: frozenset[str]  # keys removed
    modifications: frozenset[tuple[str, str, str]]  # (key, old_json, new_json)


@runtime_checkable
class SemanticProjector(Protocol):
    """Protocol for deriving current state from event stream."""

    def project_current(self) -> ProjectionResult:
        """Get current materialized state (O(1) from cache).

        Returns
        -------
        ProjectionResult
            Current state with metadata

        """
        ...

    def project_at_time(self, timestamp: datetime) -> ProjectionResult:
        """Reconstruct state at specific time point.

        Parameters
        ----------
        timestamp : datetime
            Target time point

        Returns
        -------
        ProjectionResult
            State as of timestamp

        """
        ...

    def project_at_sequence(self, sequence: int) -> ProjectionResult:
        """Reconstruct state at specific sequence number.

        Parameters
        ----------
        sequence : int
            Target sequence number

        Returns
        -------
        ProjectionResult
            State at sequence number

        """
        ...

    def invalidate(self) -> None:
        """Invalidate cached projection (called on new events)."""
        ...

    def get_diff(self, from_seq: int, to_seq: int) -> StateDiff:
        """Get changes between two sequence numbers.

        Parameters
        ----------
        from_seq : int
            Starting sequence number
        to_seq : int
            Ending sequence number

        Returns
        -------
        StateDiff
            Changes between sequences

        """
        ...

    def get_entity_history(self, entity_id: str, limit: int = 100) -> list[tuple[datetime, dict[str, Any]]]:
        """Get historical states of a specific entity.

        Parameters
        ----------
        entity_id : str
            Entity identifier
        limit : int, optional
            Maximum history entries, by default 100

        Returns
        -------
        list[tuple[datetime, dict[str, Any]]]
            List of (timestamp, state) tuples

        """
        ...

"""4D ontology temporal slices for entity versioning."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class TemporalSlice:
    """4D ontology temporal part of an entity.

    In 4D ontology (perdurantism), entities are extended through time and
    composed of temporal parts (time slices). Each slice represents the entity's
    state during a validity interval.

    Parameters
    ----------
    entity_uri : str
        RDF URI of the persisting entity
    valid_from : datetime
        Start of validity interval (inclusive)
    valid_until : datetime | None
        End of validity interval (exclusive), None = current
    properties : dict[str, Any]
        Entity properties valid during this interval
    """

    entity_uri: str
    valid_from: datetime
    valid_until: datetime | None  # None = current
    properties: dict[str, Any]

    def is_current(self) -> bool:
        """Check if this slice represents the current state.

        Returns
        -------
        bool
            True if valid_until is None
        """
        return self.valid_until is None

    def overlaps(self, other: TemporalSlice) -> bool:
        """Check if this slice's validity interval overlaps another.

        Parameters
        ----------
        other : TemporalSlice
            Another temporal slice to compare with

        Returns
        -------
        bool
            True if validity intervals overlap
        """
        if self.entity_uri != other.entity_uri:
            return False

        # Check interval overlap
        # [self.from, self.until) overlaps [other.from, other.until)
        self_end = self.valid_until if self.valid_until else datetime.max
        other_end = other.valid_until if other.valid_until else datetime.max

        return self.valid_from < other_end and other.valid_from < self_end

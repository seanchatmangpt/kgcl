"""Workflow event domain models with cryptographic event sourcing."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum, auto
from typing import Any


class EventType(Enum):
    """11 event types covering all v1 operations."""

    STATUS_CHANGE = auto()  # Task status transitions
    TOKEN_MOVE = auto()  # Token movement in Petri net
    SPLIT = auto()  # AND/XOR/OR split activation
    JOIN = auto()  # Synchronization at join
    CANCELLATION = auto()  # Task/region/case cancellation
    MI_SPAWN = auto()  # Multi-instance spawned
    MI_COMPLETE = auto()  # MI completion/partial join
    HOOK_EXECUTION = auto()  # Knowledge hook fired
    VALIDATION = auto()  # SHACL validation result
    TICK_START = auto()  # Tick execution started
    TICK_END = auto()  # Tick execution completed


@dataclass(frozen=True)
class WorkflowEvent:
    """Immutable workflow event with cryptographic linking.

    Events form a hash-linked chain providing tamper-evident audit trail.
    Each event includes causal dependencies and vector clock for distributed
    ordering.

    Parameters
    ----------
    event_id : str
        UUID v7 time-ordered identifier
    event_type : EventType
        Type of workflow event
    timestamp : datetime
        Event occurrence time (UTC)
    tick_number : int
        Workflow tick number when event occurred
    workflow_id : str
        Workflow instance identifier
    payload : dict[str, Any]
        Event-specific data
    caused_by : tuple[str, ...]
        Event IDs that causally precede this event
    vector_clock : tuple[tuple[str, int], ...]
        Lamport vector clock for distributed causality
    previous_hash : str
        SHA-256 hash of previous event in chain
    event_hash : str
        SHA-256 hash of this event's canonical form
    """

    event_id: str
    event_type: EventType
    timestamp: datetime
    tick_number: int
    workflow_id: str
    payload: dict[str, Any]
    caused_by: tuple[str, ...] = ()
    vector_clock: tuple[tuple[str, int], ...] = ()
    previous_hash: str = ""
    event_hash: str = field(default="", init=False)

    def __post_init__(self) -> None:
        """Compute event hash after initialization."""
        if not self.event_hash:
            computed_hash = self.compute_hash()
            object.__setattr__(self, "event_hash", computed_hash)

    @staticmethod
    def create(
        event_type: EventType,
        workflow_id: str,
        tick_number: int,
        payload: dict[str, Any],
        caused_by: tuple[str, ...] = (),
        vector_clock: tuple[tuple[str, int], ...] = (),
        previous_hash: str = "",
        timestamp: datetime | None = None,
    ) -> WorkflowEvent:
        """Create a new workflow event with generated ID and hash.

        Parameters
        ----------
        event_type : EventType
            Type of workflow event
        workflow_id : str
            Workflow instance identifier
        tick_number : int
            Workflow tick number
        payload : dict[str, Any]
            Event-specific data
        caused_by : tuple[str, ...], optional
            Causal predecessor event IDs
        vector_clock : tuple[tuple[str, int], ...], optional
            Lamport vector clock
        previous_hash : str, optional
            Hash of previous event in chain
        timestamp : datetime | None, optional
            Event time (defaults to now)

        Returns
        -------
        WorkflowEvent
            New immutable event with computed hash
        """
        event_id = str(uuid.uuid4())
        ts = timestamp if timestamp else datetime.now(UTC)

        # Create event without hash first
        event = WorkflowEvent(
            event_id=event_id,
            event_type=event_type,
            timestamp=ts,
            tick_number=tick_number,
            workflow_id=workflow_id,
            payload=payload,
            caused_by=caused_by,
            vector_clock=vector_clock,
            previous_hash=previous_hash,
        )

        return event

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of canonical event representation.

        Returns
        -------
        str
            64-character hex SHA-256 digest
        """
        # Create canonical representation
        canonical = {
            "event_id": self.event_id,
            "event_type": self.event_type.name,
            "timestamp": self.timestamp.isoformat(),
            "tick_number": self.tick_number,
            "workflow_id": self.workflow_id,
            "payload": self.payload,
            "caused_by": list(self.caused_by),
            "vector_clock": [list(vc) for vc in self.vector_clock],
            "previous_hash": self.previous_hash,
        }

        # Sort keys for deterministic serialization
        canonical_json = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EventChain:
    """Immutable chain of events with integrity verification.

    Events are linked via cryptographic hashes, forming a tamper-evident
    append-only log. Chain verification detects any modification to events.

    Parameters
    ----------
    workflow_id : str
        Workflow instance identifier
    events : tuple[WorkflowEvent, ...]
        Ordered sequence of events
    genesis_hash : str
        Hash of imaginary genesis event (all zeros)
    """

    workflow_id: str
    events: tuple[WorkflowEvent, ...]
    genesis_hash: str = "0" * 64

    def append(self, event: WorkflowEvent) -> EventChain:
        """Append event to chain, creating new immutable chain.

        Parameters
        ----------
        event : WorkflowEvent
            Event to append

        Returns
        -------
        EventChain
            New chain with event appended

        Raises
        ------
        ValueError
            If event's workflow_id doesn't match chain
        """
        if event.workflow_id != self.workflow_id:
            msg = f"Event workflow_id '{event.workflow_id}' doesn't match chain '{self.workflow_id}'"
            raise ValueError(msg)

        # Get hash of last event in chain
        last_hash = self.events[-1].event_hash if self.events else self.genesis_hash

        # Verify event's previous_hash matches
        if event.previous_hash != last_hash:
            msg = f"Event previous_hash '{event.previous_hash}' doesn't match chain tail '{last_hash}'"
            raise ValueError(msg)

        return EventChain(workflow_id=self.workflow_id, events=(*self.events, event), genesis_hash=self.genesis_hash)

    def verify(self) -> tuple[bool, str]:
        """Verify cryptographic integrity of event chain.

        Returns
        -------
        tuple[bool, str]
            (is_valid, error_message)
            is_valid is True if chain is valid, False otherwise
            error_message describes first integrity violation found
        """
        if not self.events:
            return (True, "")

        # Verify first event links to genesis
        first_event = self.events[0]
        if first_event.previous_hash != self.genesis_hash:
            return (
                False,
                f"First event previous_hash '{first_event.previous_hash}' doesn't match genesis '{self.genesis_hash}'",
            )

        # Verify each event's hash
        for i, event in enumerate(self.events):
            computed_hash = event.compute_hash()
            if event.event_hash != computed_hash:
                return (False, f"Event {i} hash mismatch: stored='{event.event_hash}' computed='{computed_hash}'")

        # Verify hash chain links
        for i in range(1, len(self.events)):
            prev_event = self.events[i - 1]
            curr_event = self.events[i]

            if curr_event.previous_hash != prev_event.event_hash:
                return (
                    False,
                    f"Event {i} previous_hash '{curr_event.previous_hash}' "
                    f"doesn't match event {i - 1} hash '{prev_event.event_hash}'",
                )

        return (True, "")

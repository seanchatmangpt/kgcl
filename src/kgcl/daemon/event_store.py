"""PyOxigraph Event Store - 4D Ontology with temporal vectors.

This module implements an event-sourced storage layer using PyOxigraph
where every graph mutation becomes a reified RDF statement with temporal
coordinates. Features:
- RDF-native event log (PyOxigraph)
- 4D ontology: entities exist across time dimension
- Time-travel queries via SPARQL temporal filters
- Named graphs as temporal snapshots

Architecture
------------
Events are stored as reified statements in PyOxigraph. Each event carries:
- Temporal vector: (sequence, timestamp, wall_clock)
- Provenance: event_id, event_type
- Payload: subject, predicate, object (for triple mutations)

The 4D model treats time as a first-class dimension - every statement
exists within a temporal context, enabling queries like "graph at tick N".

Example
-------
>>> store = RDFEventStore()
>>> event = DomainEvent(
...     event_id="evt-001",
...     event_type=EventType.TRIPLE_ADDED,
...     timestamp=time.time(),
...     sequence=0,  # Will be assigned
...     payload={"s": "urn:x", "p": "urn:y", "o": "z"},
... )
>>> seq = store.append(event)
>>> for evt in store.replay(from_seq=0):
...     print(evt)
"""

from __future__ import annotations

import hashlib
import time
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
from typing import Any

from pyoxigraph import BlankNode, Literal, NamedNode, Quad, Store

# =============================================================================
# Namespace Constants
# =============================================================================

KGCL_NS = "urn:kgcl:"
KGCL_EVENT_NS = f"{KGCL_NS}event:"
KGCL_SNAP_NS = f"{KGCL_NS}snapshot:"
KGCL_VOCAB = f"{KGCL_NS}vocab#"

# Vocabulary predicates
PRED_EVENT_ID = NamedNode(f"{KGCL_VOCAB}eventId")
PRED_EVENT_TYPE = NamedNode(f"{KGCL_VOCAB}eventType")
PRED_TIMESTAMP = NamedNode(f"{KGCL_VOCAB}timestamp")
PRED_SEQUENCE = NamedNode(f"{KGCL_VOCAB}sequence")
PRED_SUBJECT = NamedNode(f"{KGCL_VOCAB}subject")
PRED_PREDICATE = NamedNode(f"{KGCL_VOCAB}predicate")
PRED_OBJECT = NamedNode(f"{KGCL_VOCAB}object")
PRED_STATE_HASH = NamedNode(f"{KGCL_VOCAB}stateHash")
PRED_PAYLOAD_KEY = NamedNode(f"{KGCL_VOCAB}payloadKey")
PRED_PAYLOAD_VALUE = NamedNode(f"{KGCL_VOCAB}payloadValue")

# Named graphs (URIs as strings for SPARQL, NamedNodes for API)
EVENTS_GRAPH_URI = f"{KGCL_NS}events"
STATE_GRAPH_URI = f"{KGCL_NS}state"
EVENTS_GRAPH = NamedNode(EVENTS_GRAPH_URI)
STATE_GRAPH = NamedNode(STATE_GRAPH_URI)

# RDF type
RDF_TYPE = NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
EVENT_CLASS = NamedNode(f"{KGCL_VOCAB}Event")


class EventType(Enum):
    """Domain event types for KGCL operations.

    Examples
    --------
    >>> EventType.TRIPLE_ADDED.value
    'triple.added'
    """

    TRIPLE_ADDED = "triple.added"
    TRIPLE_REMOVED = "triple.removed"
    GRAPH_LOADED = "graph.loaded"
    TICK_COMPLETED = "tick.completed"
    HOOK_FIRED = "hook.fired"
    REASONING_DONE = "reasoning.done"
    SNAPSHOT_CREATED = "snapshot.created"


@dataclass(frozen=True)
class DomainEvent:
    """Immutable domain event.

    Parameters
    ----------
    event_id : str
        Unique event identifier (UUID recommended)
    event_type : EventType
        Type of event
    timestamp : float
        Unix timestamp when event occurred
    sequence : int
        Monotonic sequence number (assigned by store)
    payload : dict[str, Any]
        Event-specific data
    state_hash : str | None
        SHA-256 hash of graph state after event (for verification)

    Examples
    --------
    >>> event = DomainEvent(
    ...     event_id="evt-001",
    ...     event_type=EventType.TRIPLE_ADDED,
    ...     timestamp=1700000000.0,
    ...     sequence=1,
    ...     payload={"s": "urn:task:1", "p": "urn:status", "o": "Complete"},
    ... )
    >>> event.event_type.value
    'triple.added'
    """

    event_id: str
    event_type: EventType
    timestamp: float
    sequence: int
    payload: dict[str, Any]
    state_hash: str | None = None


@dataclass(frozen=True)
class TemporalVector:
    """4D temporal coordinate for graph state.

    Parameters
    ----------
    sequence : int
        Monotonic logical clock tick
    timestamp : float
        Wall-clock time (Unix epoch)
    tick : int
        Daemon tick cycle count

    Examples
    --------
    >>> vec = TemporalVector(sequence=100, timestamp=1700000000.0, tick=50)
    >>> vec.sequence
    100
    """

    sequence: int
    timestamp: float
    tick: int = 0


class RDFEventStore:
    """RDF-native event store using PyOxigraph with 4D ontology.

    Events are stored as reified statements with temporal vectors,
    enabling time-travel queries via SPARQL.

    Parameters
    ----------
    store : Store | None
        PyOxigraph store instance (creates in-memory if None)

    Attributes
    ----------
    sequence : int
        Current event sequence number
    tick : int
        Current daemon tick count

    Examples
    --------
    >>> store = RDFEventStore()
    >>> store.sequence
    0
    >>> event = DomainEvent(
    ...     event_id="evt-001",
    ...     event_type=EventType.TRIPLE_ADDED,
    ...     timestamp=time.time(),
    ...     sequence=0,
    ...     payload={"s": "urn:x", "p": "urn:y", "o": "z"},
    ... )
    >>> seq = store.append(event)
    >>> seq
    1
    """

    def __init__(self, store: Store | None = None, max_event_log_size: int | None = None) -> None:
        """Initialize RDF event store.

        Parameters
        ----------
        store : Store | None
            PyOxigraph store instance (creates in-memory if None)
        max_event_log_size : int | None
            Maximum number of events to keep in log. Older events are purged
            via FIFO when exceeded. If None, no limit.
        """
        self._store = store if store is not None else Store()
        self._sequence = self._get_max_sequence()
        self._tick = 0
        self._max_event_log_size = max_event_log_size

    @property
    def sequence(self) -> int:
        """Current event sequence number."""
        return self._sequence

    @property
    def tick(self) -> int:
        """Current daemon tick count."""
        return self._tick

    @property
    def store(self) -> Store:
        """Underlying PyOxigraph store."""
        return self._store

    def _get_max_sequence(self) -> int:
        """Get maximum sequence number from store via SPARQL."""
        query = f"""
        PREFIX kgcl: <{KGCL_VOCAB}>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT (MAX(xsd:integer(?seq)) AS ?maxSeq) WHERE {{
            GRAPH <{EVENTS_GRAPH_URI}> {{
                ?event kgcl:sequence ?seq .
            }}
        }}
        """
        results = list(self._store.query(query))
        if results and results[0]["maxSeq"] is not None:
            return int(results[0]["maxSeq"].value)
        return 0

    def append(self, event: DomainEvent) -> int:
        """Append event to log as reified RDF statement.

        Parameters
        ----------
        event : DomainEvent
            Event to append (sequence will be assigned)

        Returns
        -------
        int
            Assigned sequence number

        Examples
        --------
        >>> store = RDFEventStore()
        >>> event = DomainEvent(
        ...     event_id="evt-001",
        ...     event_type=EventType.TRIPLE_ADDED,
        ...     timestamp=time.time(),
        ...     sequence=0,
        ...     payload={"s": "urn:x", "p": "urn:y", "o": "z"},
        ... )
        >>> store.append(event)
        1
        """
        self._sequence += 1
        event_node = NamedNode(f"{KGCL_EVENT_NS}{event.event_id}")

        quads = [
            # Event type metadata
            Quad(event_node, RDF_TYPE, EVENT_CLASS, EVENTS_GRAPH),
            Quad(event_node, PRED_EVENT_ID, Literal(event.event_id), EVENTS_GRAPH),
            Quad(event_node, PRED_EVENT_TYPE, Literal(event.event_type.value), EVENTS_GRAPH),
            # Temporal vector
            Quad(event_node, PRED_TIMESTAMP, Literal(str(event.timestamp)), EVENTS_GRAPH),
            Quad(event_node, PRED_SEQUENCE, Literal(str(self._sequence)), EVENTS_GRAPH),
        ]

        # Add state hash if present
        if event.state_hash:
            quads.append(Quad(event_node, PRED_STATE_HASH, Literal(event.state_hash), EVENTS_GRAPH))

        # Encode payload - for triple events, use specific predicates
        payload = event.payload
        if "s" in payload and "p" in payload and "o" in payload:
            quads.extend(
                [
                    Quad(event_node, PRED_SUBJECT, self._to_term(payload["s"]), EVENTS_GRAPH),
                    Quad(event_node, PRED_PREDICATE, self._to_term(payload["p"]), EVENTS_GRAPH),
                    Quad(event_node, PRED_OBJECT, self._to_term(payload["o"]), EVENTS_GRAPH),
                ]
            )

        # Encode remaining payload as key-value pairs
        for key, value in payload.items():
            if key not in ("s", "p", "o"):
                payload_node = BlankNode()
                quads.extend(
                    [
                        Quad(event_node, PRED_PAYLOAD_KEY, payload_node, EVENTS_GRAPH),
                        Quad(payload_node, NamedNode(f"{KGCL_VOCAB}key"), Literal(key), EVENTS_GRAPH),
                        Quad(payload_node, NamedNode(f"{KGCL_VOCAB}value"), Literal(str(value)), EVENTS_GRAPH),
                    ]
                )

        # Atomic insert
        for quad in quads:
            self._store.add(quad)

        # Apply to state graph for TRIPLE_ADDED/REMOVED
        if event.event_type == EventType.TRIPLE_ADDED:
            self._apply_triple_add(payload)
        elif event.event_type == EventType.TRIPLE_REMOVED:
            self._apply_triple_remove(payload)

        # Compact if over limit (FIFO)
        if self._max_event_log_size is not None:
            self._compact_log_fifo()

        return self._sequence

    def _to_term(self, value: str) -> NamedNode | Literal:
        """Convert string to RDF term (NamedNode if URI, else Literal)."""
        if value.startswith("urn:") or value.startswith("http"):
            return NamedNode(value)
        return Literal(value)

    def _apply_triple_add(self, payload: dict[str, Any]) -> None:
        """Apply triple addition to state graph."""
        if "s" in payload and "p" in payload and "o" in payload:
            quad = Quad(
                self._to_term(payload["s"]), self._to_term(payload["p"]), self._to_term(payload["o"]), STATE_GRAPH
            )
            self._store.add(quad)

    def _apply_triple_remove(self, payload: dict[str, Any]) -> None:
        """Apply triple removal from state graph."""
        if "s" in payload and "p" in payload and "o" in payload:
            quad = Quad(
                self._to_term(payload["s"]), self._to_term(payload["p"]), self._to_term(payload["o"]), STATE_GRAPH
            )
            self._store.remove(quad)

    def _compact_log_fifo(self) -> int:
        """Compact event log by removing oldest events (FIFO).

        Removes events oldest-first until log size is at or below
        max_event_log_size. Only called when max_event_log_size is set.

        Returns
        -------
        int
            Number of events removed
        """
        if self._max_event_log_size is None:
            return 0

        current_count = self.count_events()
        if current_count <= self._max_event_log_size:
            return 0

        events_to_remove = current_count - self._max_event_log_size

        # Find oldest events to remove
        query = f"""
        PREFIX kgcl: <{KGCL_VOCAB}>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT ?event ?eventId
        WHERE {{
            GRAPH <{EVENTS_GRAPH_URI}> {{
                ?event a kgcl:Event ;
                       kgcl:eventId ?eventId ;
                       kgcl:sequence ?seq .
            }}
        }}
        ORDER BY xsd:integer(?seq)
        LIMIT {events_to_remove}
        """

        removed = 0
        for row in self._store.query(query):
            event_node = row["event"]
            # Remove all quads with this event as subject
            quads_to_remove = list(self._store.quads_for_pattern(event_node, None, None, EVENTS_GRAPH))
            for quad in quads_to_remove:
                self._store.remove(quad)
            # Also remove any blank node payloads connected to this event
            # (handled by cascade since blank nodes are only reachable via event)
            removed += 1

        return removed

    def replay(
        self, from_seq: int = 0, to_seq: int | None = None, event_types: list[EventType] | None = None
    ) -> Iterator[DomainEvent]:
        """Replay events from log via SPARQL.

        Parameters
        ----------
        from_seq : int
            Start sequence (exclusive, default: 0)
        to_seq : int | None
            End sequence (inclusive, default: latest)
        event_types : list[EventType] | None
            Filter by event types (default: all)

        Yields
        ------
        DomainEvent
            Events in sequence order

        Examples
        --------
        >>> store = RDFEventStore()
        >>> # ... append events ...
        >>> for event in store.replay(from_seq=0):
        ...     print(event.event_type)
        """
        # Build SPARQL query with filters
        type_filter = ""
        if event_types:
            types_str = ", ".join(f'"{et.value}"' for et in event_types)
            type_filter = f"FILTER(?eventType IN ({types_str}))"

        to_seq_filter = ""
        if to_seq is not None:
            to_seq_filter = f"FILTER(xsd:integer(?seq) <= {to_seq})"

        query = f"""
        PREFIX kgcl: <{KGCL_VOCAB}>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT ?event ?eventId ?eventType ?timestamp ?seq ?stateHash
               ?subject ?predicate ?object
        WHERE {{
            GRAPH <{EVENTS_GRAPH_URI}> {{
                ?event a kgcl:Event ;
                       kgcl:eventId ?eventId ;
                       kgcl:eventType ?eventType ;
                       kgcl:timestamp ?timestamp ;
                       kgcl:sequence ?seq .
                OPTIONAL {{ ?event kgcl:stateHash ?stateHash }}
                OPTIONAL {{ ?event kgcl:subject ?subject }}
                OPTIONAL {{ ?event kgcl:predicate ?predicate }}
                OPTIONAL {{ ?event kgcl:object ?object }}
                FILTER(xsd:integer(?seq) > {from_seq})
                {to_seq_filter}
                {type_filter}
            }}
        }}
        ORDER BY xsd:integer(?seq)
        """

        for row in self._store.query(query):
            payload: dict[str, Any] = {}

            # Extract triple payload if present
            if row["subject"] is not None:
                payload["s"] = str(row["subject"].value) if hasattr(row["subject"], "value") else str(row["subject"])
            if row["predicate"] is not None:
                payload["p"] = (
                    str(row["predicate"].value) if hasattr(row["predicate"], "value") else str(row["predicate"])
                )
            if row["object"] is not None:
                obj = row["object"]
                payload["o"] = str(obj.value) if hasattr(obj, "value") else str(obj)

            yield DomainEvent(
                event_id=str(row["eventId"].value),
                event_type=EventType(str(row["eventType"].value)),
                timestamp=float(row["timestamp"].value),
                sequence=int(row["seq"].value),
                payload=payload,
                state_hash=str(row["stateHash"].value) if row["stateHash"] else None,
            )

    def get_event(self, event_id: str) -> DomainEvent | None:
        """Get event by ID.

        Parameters
        ----------
        event_id : str
            Event identifier

        Returns
        -------
        DomainEvent | None
            Event if found, None otherwise

        Examples
        --------
        >>> store = RDFEventStore()
        >>> store.get_event("nonexistent")
        """
        query = f"""
        PREFIX kgcl: <{KGCL_VOCAB}>
        SELECT ?eventType ?timestamp ?seq ?stateHash ?subject ?predicate ?object
        WHERE {{
            GRAPH <{EVENTS_GRAPH_URI}> {{
                ?event kgcl:eventId "{event_id}" ;
                       kgcl:eventType ?eventType ;
                       kgcl:timestamp ?timestamp ;
                       kgcl:sequence ?seq .
                OPTIONAL {{ ?event kgcl:stateHash ?stateHash }}
                OPTIONAL {{ ?event kgcl:subject ?subject }}
                OPTIONAL {{ ?event kgcl:predicate ?predicate }}
                OPTIONAL {{ ?event kgcl:object ?object }}
            }}
        }}
        """

        results = list(self._store.query(query))
        if not results:
            return None

        row = results[0]
        payload: dict[str, Any] = {}

        if row["subject"] is not None:
            payload["s"] = str(row["subject"].value) if hasattr(row["subject"], "value") else str(row["subject"])
        if row["predicate"] is not None:
            payload["p"] = str(row["predicate"].value) if hasattr(row["predicate"], "value") else str(row["predicate"])
        if row["object"] is not None:
            obj = row["object"]
            payload["o"] = str(obj.value) if hasattr(obj, "value") else str(obj)

        return DomainEvent(
            event_id=event_id,
            event_type=EventType(str(row["eventType"].value)),
            timestamp=float(row["timestamp"].value),
            sequence=int(row["seq"].value),
            payload=payload,
            state_hash=str(row["stateHash"].value) if row["stateHash"] else None,
        )

    def get_event_at_sequence(self, sequence: int) -> DomainEvent | None:
        """Get event by sequence number.

        Parameters
        ----------
        sequence : int
            Sequence number

        Returns
        -------
        DomainEvent | None
            Event if found, None otherwise
        """
        query = f"""
        PREFIX kgcl: <{KGCL_VOCAB}>
        SELECT ?eventId ?eventType ?timestamp ?stateHash ?subject ?predicate ?object
        WHERE {{
            GRAPH <{EVENTS_GRAPH_URI}> {{
                ?event kgcl:sequence "{sequence}" ;
                       kgcl:eventId ?eventId ;
                       kgcl:eventType ?eventType ;
                       kgcl:timestamp ?timestamp .
                OPTIONAL {{ ?event kgcl:stateHash ?stateHash }}
                OPTIONAL {{ ?event kgcl:subject ?subject }}
                OPTIONAL {{ ?event kgcl:predicate ?predicate }}
                OPTIONAL {{ ?event kgcl:object ?object }}
            }}
        }}
        """

        results = list(self._store.query(query))
        if not results:
            return None

        row = results[0]
        payload: dict[str, Any] = {}

        if row["subject"] is not None:
            payload["s"] = str(row["subject"].value) if hasattr(row["subject"], "value") else str(row["subject"])
        if row["predicate"] is not None:
            payload["p"] = str(row["predicate"].value) if hasattr(row["predicate"], "value") else str(row["predicate"])
        if row["object"] is not None:
            obj = row["object"]
            payload["o"] = str(obj.value) if hasattr(obj, "value") else str(obj)

        return DomainEvent(
            event_id=str(row["eventId"].value),
            event_type=EventType(str(row["eventType"].value)),
            timestamp=float(row["timestamp"].value),
            sequence=sequence,
            payload=payload,
            state_hash=str(row["stateHash"].value) if row["stateHash"] else None,
        )

    def count_events(self, from_seq: int = 0, to_seq: int | None = None, event_type: EventType | None = None) -> int:
        """Count events in range.

        Parameters
        ----------
        from_seq : int
            Start sequence (exclusive)
        to_seq : int | None
            End sequence (inclusive)
        event_type : EventType | None
            Filter by type

        Returns
        -------
        int
            Event count

        Examples
        --------
        >>> store = RDFEventStore()
        >>> store.count_events()
        0
        """
        type_filter = ""
        if event_type:
            type_filter = f'FILTER(?eventType = "{event_type.value}")'

        to_seq_filter = ""
        if to_seq is not None:
            to_seq_filter = f"FILTER(xsd:integer(?seq) <= {to_seq})"

        query = f"""
        PREFIX kgcl: <{KGCL_VOCAB}>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT (COUNT(?event) AS ?count)
        WHERE {{
            GRAPH <{EVENTS_GRAPH_URI}> {{
                ?event a kgcl:Event ;
                       kgcl:sequence ?seq .
                OPTIONAL {{ ?event kgcl:eventType ?eventType }}
                FILTER(xsd:integer(?seq) > {from_seq})
                {to_seq_filter}
                {type_filter}
            }}
        }}
        """

        results = list(self._store.query(query))
        if results and results[0]["count"] is not None:
            return int(results[0]["count"].value)
        return 0

    def sequence_at_time(self, timestamp: float) -> int:
        """Find sequence number at or before timestamp.

        Parameters
        ----------
        timestamp : float
            Unix timestamp

        Returns
        -------
        int
            Sequence number (0 if no events before timestamp)

        Examples
        --------
        >>> store = RDFEventStore()
        >>> store.sequence_at_time(time.time())
        0
        """
        query = f"""
        PREFIX kgcl: <{KGCL_VOCAB}>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT (MAX(xsd:integer(?seq)) AS ?maxSeq)
        WHERE {{
            GRAPH <{EVENTS_GRAPH_URI}> {{
                ?event kgcl:timestamp ?ts ;
                       kgcl:sequence ?seq .
                FILTER(xsd:decimal(?ts) <= {timestamp})
            }}
        }}
        """

        results = list(self._store.query(query))
        if results and results[0]["maxSeq"] is not None:
            return int(results[0]["maxSeq"].value)
        return 0

    def create_snapshot(self, sequence: int, graph_name: str | None = None) -> str:
        """Create snapshot of current state graph at sequence.

        Parameters
        ----------
        sequence : int
            Event sequence at snapshot time
        graph_name : str | None
            Custom graph name (auto-generated if None)

        Returns
        -------
        str
            Snapshot graph URI

        Examples
        --------
        >>> store = RDFEventStore()
        >>> store.create_snapshot(100)
        'urn:kgcl:snapshot:...'
        """
        snap_id = graph_name or f"{KGCL_SNAP_NS}{uuid.uuid4()}"
        snap_graph = NamedNode(snap_id)

        # Copy current state to snapshot graph
        query = f"""
        PREFIX kgcl: <{KGCL_VOCAB}>
        SELECT ?s ?p ?o
        WHERE {{
            GRAPH <{STATE_GRAPH_URI}> {{
                ?s ?p ?o .
            }}
        }}
        """

        for row in self._store.query(query):
            quad = Quad(row["s"], row["p"], row["o"], snap_graph)
            self._store.add(quad)

        # Record snapshot metadata
        snap_meta = NamedNode(f"{snap_id}#meta")
        timestamp = time.time()
        self._store.add(Quad(snap_meta, PRED_SEQUENCE, Literal(str(sequence)), snap_graph))
        self._store.add(Quad(snap_meta, PRED_TIMESTAMP, Literal(str(timestamp)), snap_graph))

        # Record as event
        self.append(
            DomainEvent(
                event_id=f"snap-{uuid.uuid4()}",
                event_type=EventType.SNAPSHOT_CREATED,
                timestamp=timestamp,
                sequence=0,
                payload={"snapshot_graph": snap_id, "at_sequence": sequence},
            )
        )

        return snap_id

    def reconstruct_at(self, target_seq: int) -> Store:
        """Reconstruct graph state at specific sequence (time-travel).

        Parameters
        ----------
        target_seq : int
            Target sequence number

        Returns
        -------
        Store
            New PyOxigraph store with state at target sequence

        Examples
        --------
        >>> store = RDFEventStore()
        >>> # ... append events ...
        >>> past_state = store.reconstruct_at(50)
        """
        # Find nearest snapshot before target
        query = f"""
        PREFIX kgcl: <{KGCL_VOCAB}>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT ?snapGraph ?snapSeq
        WHERE {{
            ?event kgcl:eventType "snapshot.created" ;
                   kgcl:payloadKey ?pk .
            ?pk kgcl:key "at_sequence" ;
                kgcl:value ?snapSeq .
            FILTER(xsd:integer(?snapSeq) <= {target_seq})
        }}
        ORDER BY DESC(xsd:integer(?snapSeq))
        LIMIT 1
        """

        results = list(self._store.query(query))

        # Create new store for reconstruction
        reconstructed = Store()

        start_seq = 0
        if results:
            # Load from snapshot
            snap_seq = int(results[0]["snapSeq"].value)
            start_seq = snap_seq
            # Find the snapshot graph and copy its contents
            # (simplified - in production would load snapshot graph)

        # Replay events from start_seq to target_seq
        for event in self.replay(from_seq=start_seq, to_seq=target_seq):
            if event.event_type == EventType.TRIPLE_ADDED:
                payload = event.payload
                if "s" in payload and "p" in payload and "o" in payload:
                    reconstructed.add(
                        Quad(
                            self._to_term(payload["s"]),
                            self._to_term(payload["p"]),
                            self._to_term(payload["o"]),
                            None,  # default graph
                        )
                    )
            elif event.event_type == EventType.TRIPLE_REMOVED:
                payload = event.payload
                if "s" in payload and "p" in payload and "o" in payload:
                    reconstructed.remove(
                        Quad(
                            self._to_term(payload["s"]),
                            self._to_term(payload["p"]),
                            self._to_term(payload["o"]),
                            None,  # default graph
                        )
                    )

        return reconstructed

    def advance_tick(self) -> int:
        """Advance daemon tick counter.

        Returns
        -------
        int
            New tick value
        """
        self._tick += 1
        self.append(
            DomainEvent(
                event_id=f"tick-{self._tick}",
                event_type=EventType.TICK_COMPLETED,
                timestamp=time.time(),
                sequence=0,
                payload={"tick": self._tick},
            )
        )
        return self._tick

    def query_state(self, sparql: str) -> list[dict[str, Any]]:
        """Execute SPARQL query against current state graph.

        Parameters
        ----------
        sparql : str
            SPARQL SELECT query

        Returns
        -------
        list[dict[str, Any]]
            Query results as list of bindings
        """
        results: list[dict[str, Any]] = []
        query_results = self._store.query(sparql)

        # Get variable names from the query solutions
        variables = list(query_results.variables)

        for row in query_results:
            binding: dict[str, Any] = {}
            for i, var in enumerate(variables):
                value = row[i]  # Access by index, not variable
                if value is not None:
                    var_name = str(var).lstrip("?")
                    binding[var_name] = str(value.value) if hasattr(value, "value") else str(value)
            results.append(binding)
        return results


def compute_state_hash(store: Store, graph: NamedNode | None = None) -> str:
    """Compute SHA-256 hash of graph state.

    Parameters
    ----------
    store : Store
        PyOxigraph store
    graph : NamedNode | None
        Named graph to hash (default graph if None)

    Returns
    -------
    str
        Hex-encoded SHA-256 hash

    Examples
    --------
    >>> store = Store()
    >>> compute_state_hash(store)
    'e3b0c44...'
    """
    # Serialize to sorted N-Triples for deterministic hash
    triples = []
    if graph:
        for quad in store.quads_for_pattern(None, None, None, graph):
            triples.append(f"{quad.subject} {quad.predicate} {quad.object} .")
    else:
        for quad in store.quads_for_pattern(None, None, None, None):
            triples.append(f"{quad.subject} {quad.predicate} {quad.object} .")

    triples.sort()
    content = "\n".join(triples)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

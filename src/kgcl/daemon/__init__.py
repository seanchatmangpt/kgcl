"""KGCL Daemon - Long-running knowledge graph service.

This module provides a daemon architecture combining:
1. WASM-Native Performance - Sub-millisecond reasoning via warm sidecar
2. Event-Sourcing - PyOxigraph with 4D ontology, time-travel queries
3. Reactive Streaming - Delta reasoning, CDC, backpressure

Example
-------
>>> from kgcl.daemon import KGCLDaemon, DaemonConfig
>>> async with KGCLDaemon(DaemonConfig()) as daemon:
...     await daemon.add("urn:task:1", "urn:status", "Complete")
...     result = await daemon.query("?s ?p ?o")
"""

from __future__ import annotations

from kgcl.daemon.event_store import DomainEvent, EventType, RDFEventStore, TemporalVector, compute_state_hash
from kgcl.daemon.kgcld import DaemonConfig, DaemonState, KGCLDaemon, MutationReceipt, QueryResult

__all__ = [
    "DaemonConfig",
    "DaemonState",
    "DomainEvent",
    "EventType",
    "KGCLDaemon",
    "MutationReceipt",
    "QueryResult",
    "RDFEventStore",
    "TemporalVector",
    "compute_state_hash",
]

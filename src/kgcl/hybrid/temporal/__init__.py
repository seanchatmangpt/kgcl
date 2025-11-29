"""Temporal event sourcing for KGCL Hybrid Engine v2.

This module provides temporal event sourcing capabilities that wrap
the v1 HybridOrchestrator without modifications. Key features:

- **Event Store**: Append-only immutable event log with cryptographic chaining
- **Semantic Projector**: Derive current state from events (O(1) via cache)
- **Temporal Reasoning**: LTL operators (Always, Eventually, Until, Next)
- **Causal Tracking**: Vector clocks and "Why did this fire?" queries
- **Audit Export**: SOX, GDPR compliance reports (JSON/CSV)
- **Time-Travel API**: query_at_time(), get_causal_chain()

Usage:
    from kgcl.hybrid.temporal import (
        TemporalOrchestrator,
        create_temporal_orchestrator,
    )

    # Wrap v1 orchestrator
    v2 = create_temporal_orchestrator(v1_orchestrator, "my-workflow")
    result = v2.execute_tick()

    # Time-travel query
    state = v2.query_at_time(some_timestamp)
"""

from __future__ import annotations

from kgcl.hybrid.temporal.adapters.audit_exporters.csv_exporter import CSVAuditExporter
from kgcl.hybrid.temporal.adapters.audit_exporters.json_exporter import JSONAuditExporter
from kgcl.hybrid.temporal.adapters.caching_projector import CachingProjector
from kgcl.hybrid.temporal.adapters.causal_tracker_adapter import InMemoryCausalTracker

# Adapters (implementations)
from kgcl.hybrid.temporal.adapters.in_memory_event_store import InMemoryEventStore
from kgcl.hybrid.temporal.adapters.ltl_evaluator import LTLEvaluator
from kgcl.hybrid.temporal.adapters.tiered_event_store import CompactionPolicy, TieredEventStore

# Application services
from kgcl.hybrid.temporal.application.event_capture_hook import (
    EventCaptureHook,
    TickSnapshot,
    create_event_capture_hook,
)
from kgcl.hybrid.temporal.application.temporal_orchestrator import (
    CausalChainResult,
    HistoricalState,
    TemporalOrchestrator,
    TemporalTickResult,
    create_temporal_orchestrator,
)
from kgcl.hybrid.temporal.application.time_travel_query import (
    DiffResult,
    TimelineEntry,
    TimeTravelQuery,
    create_time_travel_query,
)

# Domain models
from kgcl.hybrid.temporal.domain.event import EventChain, EventType, WorkflowEvent
from kgcl.hybrid.temporal.domain.ltl_formula import LTLFormula, LTLOperator, LTLResult
from kgcl.hybrid.temporal.domain.temporal_slice import TemporalSlice
from kgcl.hybrid.temporal.domain.vector_clock import VectorClock
from kgcl.hybrid.temporal.ports.audit_exporter_port import AuditExporter, AuditReport, ExportFormat
from kgcl.hybrid.temporal.ports.causal_port import CausalExplanation, CausalGraph, CausalTracker

# Ports (protocols)
from kgcl.hybrid.temporal.ports.event_store_port import AppendResult, EventStore, QueryResult
from kgcl.hybrid.temporal.ports.projector_port import ProjectionResult, SemanticProjector
from kgcl.hybrid.temporal.ports.temporal_reasoner_port import TemporalReasoner

__all__ = [
    # Domain
    "EventChain",
    "EventType",
    "WorkflowEvent",
    "VectorClock",
    "LTLFormula",
    "LTLOperator",
    "LTLResult",
    "TemporalSlice",
    # Ports
    "AppendResult",
    "EventStore",
    "QueryResult",
    "ProjectionResult",
    "SemanticProjector",
    "TemporalReasoner",
    "AuditExporter",
    "AuditReport",
    "ExportFormat",
    "CausalExplanation",
    "CausalTracker",
    "CausalGraph",
    # Adapters
    "InMemoryEventStore",
    "CompactionPolicy",
    "TieredEventStore",
    "CachingProjector",
    "LTLEvaluator",
    "InMemoryCausalTracker",
    "JSONAuditExporter",
    "CSVAuditExporter",
    # Application
    "EventCaptureHook",
    "TickSnapshot",
    "create_event_capture_hook",
    "CausalChainResult",
    "HistoricalState",
    "TemporalOrchestrator",
    "TemporalTickResult",
    "create_temporal_orchestrator",
    "DiffResult",
    "TimelineEntry",
    "TimeTravelQuery",
    "create_time_travel_query",
]

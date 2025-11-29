"""Port interfaces for hybrid temporal engine."""

from __future__ import annotations

from kgcl.hybrid.temporal.ports.causal_port import CausalExplanation, CausalGraph, CausalityAnalyzer, CausalTracker
from kgcl.hybrid.temporal.ports.event_store_port import AppendResult, EventStore, QueryResult
from kgcl.hybrid.temporal.ports.projector_port import ProjectionResult, SemanticProjector, StateDiff
from kgcl.hybrid.temporal.ports.temporal_reasoner_port import (
    PropertyVerificationResult,
    TemporalProperty,
    TemporalReasoner,
)

__all__ = [
    "AppendResult",
    "CausalExplanation",
    "CausalGraph",
    "CausalTracker",
    "CausalityAnalyzer",
    "EventStore",
    "ProjectionResult",
    "PropertyVerificationResult",
    "QueryResult",
    "SemanticProjector",
    "StateDiff",
    "TemporalProperty",
    "TemporalReasoner",
]

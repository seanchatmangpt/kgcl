"""KGC Hybrid Engine - PyOxigraph + EYE Reasoner Architecture.

The hybrid engine provides a tick-based execution model where:
- PyOxigraph stores state (Matter - Inert RDF triples)
- N3 rules define logic (Physics - Force that transforms Matter via EYE)
- Python orchestrates ticks (Time - Manual Clock)
- ALL workflow logic is in N3 rules - NO Python if/else for reasoning

This implements "Hard Separation" between State (Oxigraph) and Logic (N3/EYE).

Architecture Layers
-------------------
1. **State Layer** (Oxigraph): Inert RDF triples stored in Rust
2. **Physics Layer** (N3/EYE): Declarative rules executed by EYE reasoner
3. **Time Layer** (Python): Manual tick controller
4. **Observability Layer** (OTEL): Tracing and metrics
5. **Provenance Layer** (Lockchain): Git-backed tick receipts

Components
----------
- `HybridEngine`: PyOxigraph + EYE reasoner engine (from hybrid_engine.py)
- `PhysicsResult`: Result from physics application
- `TickController`: Tick orchestration with hook system
- `OxigraphStore`: PyOxigraph wrapper with query/update
- `PHYSICS_ONTOLOGY`: N3 rules defining KGC verb physics
- `LockchainWriter`: Git-backed provenance chain
- `LockchainHook`: Automatic receipt writing on ticks

Examples
--------
>>> # PyOxigraph + EYE hybrid engine
>>> from kgcl.hybrid import HybridEngine
>>> engine = HybridEngine()
>>> engine.load_data(topology_ttl)
>>> result = engine.apply_physics()
>>>
>>> # New tick controller architecture
>>> from kgcl.hybrid import TickController, OxigraphStore
>>> from kgcl.hybrid import load_physics_ontology
>>> store = OxigraphStore()
>>> controller = TickController(store)
>>> physics = load_physics_ontology()
>>> store.load_rdf(physics, format="turtle")
>>>
>>> # With Lockchain provenance
>>> from kgcl.hybrid import LockchainHook, LockchainWriter
>>> writer = LockchainWriter(repo_path)
>>> controller.register_hook(LockchainHook(writer))
"""

from __future__ import annotations

# PyOxigraph + EYE hybrid engine
from kgcl.hybrid.hybrid_engine import HybridEngine, PhysicsResult

# Knowledge Hooks - Pure N3 Logic
from kgcl.hybrid.knowledge_hooks import (
    N3_HOOK_PHYSICS,
    HookAction,
    HookExecutor,
    HookPhase,
    HookReceipt,
    HookRegistry,
    KnowledgeHook,
)

# PyOxigraph-based architecture components
# Wrapped in try/except for graceful degradation if pyoxigraph not installed
try:
    from kgcl.hybrid.lockchain import LockchainHook, LockchainWriter, TickReceipt
    from kgcl.hybrid.oxigraph_store import (
        OxigraphStore,
        QueryError,
        QueryResult,
        StoreError,
        TransactionContext,
        UpdateError,
    )
    from kgcl.hybrid.physics_ontology import (
        PHYSICS_ONTOLOGY,
        STANDARD_PREFIXES,
        get_verb_rule,
        get_wcp_rule,
        list_all_patterns,
        list_all_verbs,
        load_physics_ontology,
    )
    from kgcl.hybrid.tick_controller import ProvenanceHook, ProvenanceRecord, TickController, TickHook, TickPhase
    from kgcl.hybrid.tick_controller import TickResult as NewTickResult

    _PYOXIGRAPH_AVAILABLE = True
    _PYOXIGRAPH_ERROR: str | None = None
except ImportError as e:
    _PYOXIGRAPH_AVAILABLE = False
    _PYOXIGRAPH_ERROR = str(e)
    # Define placeholder classes for type checking
    TickController = None  # type: ignore[assignment, misc]
    NewTickResult = None  # type: ignore[assignment, misc]
    TickPhase = None  # type: ignore[assignment, misc]
    TickHook = None  # type: ignore[assignment, misc]
    ProvenanceHook = None  # type: ignore[assignment, misc]
    ProvenanceRecord = None  # type: ignore[assignment, misc]
    OxigraphStore = None  # type: ignore[assignment, misc]
    QueryResult = None  # type: ignore[assignment, misc]
    TransactionContext = None  # type: ignore[assignment, misc]
    StoreError = None  # type: ignore[assignment, misc]
    QueryError = None  # type: ignore[assignment, misc]
    UpdateError = None  # type: ignore[assignment, misc]
    PHYSICS_ONTOLOGY = ""  # type: ignore[assignment]
    STANDARD_PREFIXES = ""  # type: ignore[assignment]
    load_physics_ontology = None  # type: ignore[assignment, misc]
    get_verb_rule = None  # type: ignore[assignment, misc]
    get_wcp_rule = None  # type: ignore[assignment, misc]
    list_all_verbs = None  # type: ignore[assignment, misc]
    list_all_patterns = None  # type: ignore[assignment, misc]
    TickReceipt = None  # type: ignore[assignment, misc]
    LockchainWriter = None  # type: ignore[assignment, misc]
    LockchainHook = None  # type: ignore[assignment, misc]

__all__ = [
    # PyOxigraph + EYE hybrid engine
    "HybridEngine",
    "PhysicsResult",
    # Knowledge Hooks - Pure N3 Logic
    "KnowledgeHook",
    "HookRegistry",
    "HookExecutor",
    "HookPhase",
    "HookAction",
    "HookReceipt",
    "N3_HOOK_PHYSICS",
    # Tick controller
    "TickController",
    "NewTickResult",
    "TickPhase",
    "TickHook",
    "ProvenanceHook",
    "ProvenanceRecord",
    # Oxigraph store
    "OxigraphStore",
    "QueryResult",
    "TransactionContext",
    "StoreError",
    "QueryError",
    "UpdateError",
    # Physics ontology
    "PHYSICS_ONTOLOGY",
    "STANDARD_PREFIXES",
    "load_physics_ontology",
    "get_verb_rule",
    "get_wcp_rule",
    "list_all_verbs",
    "list_all_patterns",
    # Lockchain
    "TickReceipt",
    "LockchainWriter",
    "LockchainHook",
]

__version__ = "2.0.0"

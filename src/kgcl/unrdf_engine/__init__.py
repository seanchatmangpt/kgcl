"""UNRDF Knowledge Engine - Universal Named Resource Description Framework.

A production-grade RDF triple store with SPARQL querying, transaction support,
provenance tracking, SHACL validation, hook-driven workflows, and external
capability execution.

Features
--------
- RDF triple store with SPARQL 1.1 support
- ACID transactions with rollback capability
- Full provenance tracking (who/when/why)
- SHACL validation
- Lifecycle hooks for ingestion, validation, and query execution
- Persistent hook registry with hot reload
- Feature materialization through hooks
- OpenTelemetry instrumentation
- Hook performance tracking with receipts

Examples
--------
Basic usage with hooks::

    from kgcl.unrdf_engine import (
        UnrdfEngine,
        PersistentHookRegistry,
        KnowledgeHook,
        HookPhase,
        IngestionPipeline,
    )

    # Create engine with hook support
    registry = PersistentHookRegistry(storage_path=Path("hooks.json"))
    engine = UnrdfEngine(file_path=Path("graph.ttl"), hook_registry=registry)


    # Define a validation hook
    class ValidationHook(KnowledgeHook):
        def __init__(self):
            super().__init__(name="validator", phases=[HookPhase.PRE_TRANSACTION])

        def execute(self, context):
            # Validate data before commit
            if not self.is_valid(context.delta):
                context.metadata["should_rollback"] = True
                context.metadata["rollback_reason"] = "Invalid data"


    # Register hook
    registry.register(ValidationHook())

    # Use ingestion pipeline
    pipeline = IngestionPipeline(engine)
    result = pipeline.ingest_json(
        data={"type": "Person", "name": "Alice"}, agent="api_service"
    )

    # Check hook receipts
    for receipt in result.hook_results:
        print(f"Hook {receipt.hook_id}: {receipt.success}")

"""

from kgcl.unrdf_engine.engine import ProvenanceRecord, Transaction, UnrdfEngine
from kgcl.unrdf_engine.externals import ExternalCapabilityBridge
from kgcl.unrdf_engine.hook_registry import HookMetadata, PersistentHookRegistry
from kgcl.unrdf_engine.hooks import (
    FeatureTemplateHook,
    HookContext,
    HookExecutor,
    HookPhase,
    HookRegistry,
    KnowledgeHook,
    Receipt,
    TriggerCondition,
    ValidationFailureHook,
)
from kgcl.unrdf_engine.ingestion import IngestionPipeline, IngestionResult
from kgcl.unrdf_engine.validation import ShaclValidator, ValidationResult

__all__ = [
    # External capabilities
    "ExternalCapabilityBridge",
    "FeatureTemplateHook",
    "HookContext",
    "HookExecutor",
    "HookMetadata",
    "HookPhase",
    "HookRegistry",
    # Ingestion
    "IngestionPipeline",
    "IngestionResult",
    # Hooks
    "KnowledgeHook",
    # Hook registry
    "PersistentHookRegistry",
    "ProvenanceRecord",
    "Receipt",
    # Validation
    "ShaclValidator",
    "Transaction",
    "TriggerCondition",
    # Core engine
    "UnrdfEngine",
    "ValidationFailureHook",
    "ValidationResult",
]

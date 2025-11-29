"""Ports layer - Abstract protocols defining component interfaces.

This module defines Protocol classes that specify the contracts between
the hybrid engine components. Adapters implement these protocols to
enable loose coupling and testability.

Ports (Abstract Interfaces)
---------------------------
RDFStore
    Protocol for RDF triple store operations
Reasoner
    Protocol for N3 reasoning engine
RulesProvider
    Protocol for providing physics rules
StateMutator
    Protocol for SPARQL UPDATE state mutations (overcomes monotonicity)
WorkflowValidator
    Protocol for SHACL constraint validation (pre/post conditions)
TransactionManager
    Protocol for ACID transactions with rollback

Design
------
Following hexagonal architecture (ports and adapters pattern):
- Ports define what the application needs (interfaces)
- Adapters provide how those needs are met (implementations)
- This enables swapping implementations (e.g., mock stores for testing)

Thesis Architecture
-------------------
The new ports (StateMutator, WorkflowValidator, TransactionManager) implement
the hybrid architecture from "Overcoming Monotonic Barriers in Workflow Execution":
- EYE infers recommendations (monotonic)
- SPARQL UPDATE executes mutations (non-monotonic)
- SHACL validates pre/post conditions (closed-world)
- Transactions enable rollback on failure
"""

from __future__ import annotations

from kgcl.hybrid.ports.mutator_port import MutationResult, StateMutation, StateMutator, Triple
from kgcl.hybrid.ports.reasoner_port import Reasoner, ReasoningOutput
from kgcl.hybrid.ports.rules_port import RulesProvider
from kgcl.hybrid.ports.store_port import RDFStore
from kgcl.hybrid.ports.transaction_port import (
    Snapshot,
    Transaction,
    TransactionError,
    TransactionManager,
    TransactionResult,
    TransactionState,
)
from kgcl.hybrid.ports.validator_port import (
    ValidationResult,
    ValidationSeverity,
    ValidationViolation,
    WorkflowValidator,
)

__all__ = [
    # Original ports
    "RDFStore",
    "Reasoner",
    "ReasoningOutput",
    "RulesProvider",
    # Mutation port (overcomes monotonicity)
    "StateMutator",
    "StateMutation",
    "MutationResult",
    "Triple",
    # Validation port (closed-world constraints)
    "WorkflowValidator",
    "ValidationResult",
    "ValidationViolation",
    "ValidationSeverity",
    # Transaction port (ACID with rollback)
    "TransactionManager",
    "Transaction",
    "TransactionResult",
    "TransactionState",
    "TransactionError",
    "Snapshot",
]

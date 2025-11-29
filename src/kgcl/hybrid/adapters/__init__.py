"""Adapters layer - Implementations of port protocols.

This module provides concrete implementations of the port protocols,
wrapping existing modules (OxigraphStore, EYEReasoner, wcp43_physics).

Adapters
--------
OxigraphAdapter
    Wraps OxigraphStore to implement RDFStore protocol
EYEAdapter
    Wraps EYEReasoner to implement Reasoner protocol
WCP43RulesAdapter
    Wraps wcp43_physics to implement RulesProvider protocol
SPARQLMutator
    Implements StateMutator using SPARQL UPDATE (overcomes monotonicity)
PySHACLValidator
    Implements WorkflowValidator using pySHACL (closed-world validation)
PyOxigraphTransactionManager
    Implements TransactionManager with snapshot rollback

Design
------
Adapters translate between the port protocols and existing implementations.
This allows the hybrid engine to depend on abstract interfaces while
using the well-tested existing modules for actual work.

Thesis Architecture
-------------------
The new adapters (SPARQLMutator, PySHACLValidator, PyOxigraphTransactionManager)
implement the hybrid architecture that achieves 100% WCP-43 coverage:
- SPARQLMutator: DELETE/INSERT operations solve monotonicity
- PySHACLValidator: Closed-world constraints ensure valid state
- PyOxigraphTransactionManager: Snapshot rollback ensures atomicity
"""

from __future__ import annotations

from kgcl.hybrid.adapters.eye_adapter import EYEAdapter
from kgcl.hybrid.adapters.oxigraph_adapter import OxigraphAdapter
from kgcl.hybrid.adapters.shacl_validator import NoOpValidator, PySHACLValidator, create_validator
from kgcl.hybrid.adapters.sparql_mutator import SPARQLMutator, create_mutator
from kgcl.hybrid.adapters.transaction_manager import PyOxigraphTransactionManager, create_transaction_manager
from kgcl.hybrid.adapters.wcp43_rules_adapter import WCP43RulesAdapter

__all__ = [
    # Original adapters
    "OxigraphAdapter",
    "EYEAdapter",
    "WCP43RulesAdapter",
    # Mutation adapter (SPARQL UPDATE)
    "SPARQLMutator",
    "create_mutator",
    # Validation adapter (pySHACL)
    "PySHACLValidator",
    "NoOpValidator",
    "create_validator",
    # Transaction adapter (snapshot rollback)
    "PyOxigraphTransactionManager",
    "create_transaction_manager",
]

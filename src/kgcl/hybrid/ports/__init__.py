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

Design
------
Following hexagonal architecture (ports and adapters pattern):
- Ports define what the application needs (interfaces)
- Adapters provide how those needs are met (implementations)
- This enables swapping implementations (e.g., mock stores for testing)
"""

from __future__ import annotations

from kgcl.hybrid.ports.reasoner_port import Reasoner, ReasoningOutput
from kgcl.hybrid.ports.rules_port import RulesProvider
from kgcl.hybrid.ports.store_port import RDFStore

__all__ = ["RDFStore", "Reasoner", "ReasoningOutput", "RulesProvider"]

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

Design
------
Adapters translate between the port protocols and existing implementations.
This allows the hybrid engine to depend on abstract interfaces while
using the well-tested existing modules for actual work.
"""

from __future__ import annotations

from kgcl.hybrid.adapters.eye_adapter import EYEAdapter
from kgcl.hybrid.adapters.oxigraph_adapter import OxigraphAdapter
from kgcl.hybrid.adapters.wcp43_rules_adapter import WCP43RulesAdapter

__all__ = ["OxigraphAdapter", "EYEAdapter", "WCP43RulesAdapter"]

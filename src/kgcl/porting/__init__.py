"""Semantic code porting tool using hybrid engine architecture.

This module provides a semantic, rule-based approach to code porting using:
- PyOxigraph: Store code structures as RDF (Matter)
- EYE Reasoner: Apply N3 rules for porting patterns (Physics)
- Python/Typer: Orchestration and CLI (Time)
- MCP Server: FastMCP pattern for IDE/agent integration
"""

from kgcl.porting.engine.porting_engine import PortingEngine
from kgcl.porting.ingestion.rdf_codebase import RDFCodebase

__all__ = ["PortingEngine", "RDFCodebase"]


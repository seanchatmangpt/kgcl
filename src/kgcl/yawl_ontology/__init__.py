"""YAWL Java codebase ontology generation and exploration.

This module generates RDF/Turtle ontologies from YAWL Java source code,
and provides high-performance SPARQL queries for architecture analysis
and Python stub generation.

Delta Detection
---------------
The delta detector module provides comprehensive analysis of differences
between Java YAWL implementation and Python conversion using multiple
detection methods:
- Structural analysis (classes, methods, signatures)
- Semantic fingerprinting (AST comparison)
- Call graph analysis
- Type flow tracking
- Exception pattern matching
- Test coverage mapping
- Dependency graph comparison
- Performance characteristics analysis
"""

from kgcl.yawl_ontology.delta_detector import DeltaDetector
from kgcl.yawl_ontology.explorer import YawlOntologyExplorer
from kgcl.yawl_ontology.generator import YawlOntologyGenerator
from kgcl.yawl_ontology.parser import JavaParser
from kgcl.yawl_ontology.stub_generator import StubGenerator

__all__ = [
    "YawlOntologyGenerator",
    "JavaParser",
    "YawlOntologyExplorer",
    "StubGenerator",
    "DeltaDetector",
]

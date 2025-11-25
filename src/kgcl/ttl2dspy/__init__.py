"""TTL2DSPy: Generate DSPy signatures from SHACL/TTL ontologies.

This module provides tools to parse RDF/TTL files with SHACL shapes and
automatically generate DSPy Signature classes for LLM-based workflows.
"""

from .parser import OntologyParser, SHACLShape, PropertyShape
from .generator import DSPyGenerator, SignatureDefinition
from .ultra import UltraOptimizer, CacheConfig
from .writer import ModuleWriter, WriteResult
from .cli import main

__version__ = "1.0.0"
__all__ = [
    "OntologyParser",
    "SHACLShape",
    "PropertyShape",
    "DSPyGenerator",
    "SignatureDefinition",
    "UltraOptimizer",
    "CacheConfig",
    "ModuleWriter",
    "WriteResult",
    "main",
]

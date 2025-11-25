"""TTL2DSPy: Generate DSPy signatures from SHACL/TTL ontologies.

This module provides tools to parse RDF/TTL files with SHACL shapes and
automatically generate DSPy Signature classes for LLM-based workflows.
"""

from .cli import main
from .generator import DSPyGenerator, SignatureDefinition
from .parser import OntologyParser, PropertyShape, SHACLShape
from .ultra import CacheConfig, UltraOptimizer
from .writer import ModuleWriter, WriteResult

__version__ = "1.0.0"
__all__ = [
    "CacheConfig",
    "DSPyGenerator",
    "ModuleWriter",
    "OntologyParser",
    "PropertyShape",
    "SHACLShape",
    "SignatureDefinition",
    "UltraOptimizer",
    "WriteResult",
    "main",
]

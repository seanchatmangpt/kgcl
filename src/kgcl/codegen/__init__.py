"""Ultra-Optimized DSPy Code Generation from RDF/SHACL Ontologies.

This package provides high-performance transpilation of RDF ontologies
with SHACL constraints into DSPy signature classes. Includes caching,
indexing, and OpenTelemetry instrumentation.

Key Features
------------
- Graph caching with LRU eviction and disk persistence
- SHACL pattern indexing for O(1) lookups
- String processing object pools to reduce allocations
- Parallel signature generation
- OpenTelemetry metrics and tracing

Modules
-------
cache : GraphCache for ultra-fast RDF graph caching
indexing : SHACLIndex for optimized SHACL pattern queries
string_pool : StringPool for cached string transformations
metrics : UltraMetrics for performance tracking
transpiler : Main TTL2DSPy transpiler with 80/20 optimizations
cli : Command-line interface

Examples
--------
>>> from kgcl.codegen.transpiler import UltraOptimizedTTL2DSPyTranspiler
>>> transpiler = UltraOptimizedTTL2DSPyTranspiler(cache_size=200)
>>> signatures = transpiler.ultra_build_signatures([Path("ontology.ttl")])
>>> module_code = transpiler.generate_ultra_module(signatures)
"""

from kgcl.codegen.cache import GraphCache
from kgcl.codegen.dspy_config import configure_dspy, get_configured_lm, is_dspy_configured
from kgcl.codegen.generators.dspy_generator import DSPySignatureGenerator
from kgcl.codegen.generators.python_generator import PythonModuleGenerator
from kgcl.codegen.generators.yawl_generator import YAWLSpecificationGenerator
from kgcl.codegen.indexing import SHACLIndex
from kgcl.codegen.metrics import UltraMetrics
from kgcl.codegen.orchestrator import CodeGenOrchestrator, GenerationConfig, OutputFormat
from kgcl.codegen.registry import GeneratorRegistry, get_registry, register_generator
from kgcl.codegen.string_pool import StringPool
from kgcl.codegen.transpiler import UltraOptimizedTTL2DSPyTranspiler

__all__ = [
    # Core transpiler components
    "GraphCache",
    "SHACLIndex",
    "StringPool",
    "UltraMetrics",
    "UltraOptimizedTTL2DSPyTranspiler",
    # DSPy configuration
    "configure_dspy",
    "get_configured_lm",
    "is_dspy_configured",
    # Generators
    "DSPySignatureGenerator",
    "YAWLSpecificationGenerator",
    "PythonModuleGenerator",
    # Orchestration
    "CodeGenOrchestrator",
    "GenerationConfig",
    "OutputFormat",
    # Registry
    "GeneratorRegistry",
    "get_registry",
    "register_generator",
]

__version__ = "1.0.0"

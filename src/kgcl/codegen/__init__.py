"""Unified code generation framework for KGCL.

This package provides a unified framework for generating code from various sources:
- RDF/TTL ontologies
- Java source files
- Configuration files

The framework follows the ports and adapters pattern with:
- Abstract base generators
- Pluggable parsers
- Unified template engine
- Validation layer
- Generator registry
"""

from __future__ import annotations

from kgcl.codegen.base.generator import BaseGenerator, GenerationResult
from kgcl.codegen.base.template_engine import TemplateEngine
from kgcl.codegen.registry import GeneratorRegistry, register_generator

__all__ = [
    "BaseGenerator",
    "GenerationResult",
    "TemplateEngine",
    "GeneratorRegistry",
    "register_generator",
]

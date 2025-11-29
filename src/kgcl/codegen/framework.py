"""Unified code generation framework exports.

This module provides the unified framework components that were migrated
from scattered generator implementations.
"""

from __future__ import annotations

from kgcl.codegen.base.generator import BaseGenerator, GenerationResult
from kgcl.codegen.base.template_engine import TemplateEngine
from kgcl.codegen.base.validator import ValidationError, Validator
from kgcl.codegen.registry import GeneratorRegistry, register_generator

__all__ = [
    "BaseGenerator",
    "GenerationResult",
    "TemplateEngine",
    "Validator",
    "ValidationError",
    "GeneratorRegistry",
    "register_generator",
]

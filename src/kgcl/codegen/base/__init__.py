"""Base classes and interfaces for code generation framework."""

from __future__ import annotations

from kgcl.codegen.base.generator import BaseGenerator, GenerationResult
from kgcl.codegen.base.template_engine import TemplateEngine
from kgcl.codegen.base.validator import ValidationError, Validator

__all__ = [
    "BaseGenerator",
    "GenerationResult",
    "TemplateEngine",
    "Validator",
    "ValidationError",
]

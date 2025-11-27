"""Projection engine - Core pipeline components for template rendering.

This module provides the engine components that orchestrate the projection
pipeline: frontmatter parsing, context building, and template rendering.

Components
----------
frontmatter_parser
    YAML frontmatter extraction and validation
context_builder
    SPARQL query execution and context mapping
projection_engine
    Main orchestrator coordinating the full pipeline

Examples
--------
>>> from kgcl.projection.engine import parse_template_file, ContextBuilder, ProjectionEngine
"""

from kgcl.projection.engine.bundle_renderer import BundleRenderer
from kgcl.projection.engine.context_builder import ContextBuilder, QueryContext
from kgcl.projection.engine.frontmatter_parser import (
    FRONTMATTER_DELIMITER,
    ParsedTemplate,
    build_template_descriptor,
    parse_template_file,
    validate_frontmatter,
)
from kgcl.projection.engine.projection_engine import ProjectionConfig, ProjectionEngine, TemplateRegistry

__all__ = [
    # Frontmatter parser
    "FRONTMATTER_DELIMITER",
    "ParsedTemplate",
    "parse_template_file",
    "validate_frontmatter",
    "build_template_descriptor",
    # Context builder
    "ContextBuilder",
    "QueryContext",
    # Projection engine
    "ProjectionEngine",
    "ProjectionConfig",
    "TemplateRegistry",
    # Bundle renderer
    "BundleRenderer",
]

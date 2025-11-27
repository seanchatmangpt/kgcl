"""KGCL Projection - Ontology-driven Jinja template projection.

This module provides the projection engine that transforms RDF graph data
into concrete artifacts (OpenAPI specs, Python code, Next.js scaffolds, docs)
using Jinja templates with YAML frontmatter declarations.

Implements A = μ_proj(O) where:
- O: RDF graph (ontology + instance data)
- μ_proj: Projection operator (this engine)
- A: Artifacts (generated code, configs, documentation)

Example
-------
>>> from kgcl.projection import ProjectionResult
>>> result = ProjectionResult(
...     template_id="api", version="1.0", content="# Generated", media_type="text/x-python", context_info={}
... )
>>> result.template_id
'api'
"""

from __future__ import annotations

from kgcl.projection.domain.bundle import BundleDescriptor, BundleTemplateEntry, ConflictMode, IterationSpec
from kgcl.projection.domain.descriptors import (
    N3Role,
    N3RuleDescriptor,
    OntologyConfig,
    QueryDescriptor,
    QuerySource,
    TemplateDescriptor,
    TemplateMetadata,
)
from kgcl.projection.domain.exceptions import (
    BundleError,
    BundleNotFoundError,
    BundleParseError,
    FrontmatterParseError,
    FrontmatterValidationError,
    GraphError,
    GraphNotFoundError,
    OutputConflictError,
    ProjectionError,
    QueryError,
    QueryExecutionError,
    QueryFileNotFoundError,
    SecurityError,
    TemplateError,
    TemplateNotFoundError,
    TemplateRenderError,
)
from kgcl.projection.domain.result import BundleFileResult, BundleResult, ProjectionResult
from kgcl.projection.engine import ProjectionEngine
from kgcl.projection.ports.graph_client import GraphClient, GraphRegistry
from kgcl.projection.ports.template_registry import BundleRegistry, InMemoryTemplateRegistry, TemplateRegistry

__all__ = [
    # Domain - Descriptors
    "N3Role",
    "N3RuleDescriptor",
    "OntologyConfig",
    "QueryDescriptor",
    "QuerySource",
    "TemplateDescriptor",
    "TemplateMetadata",
    # Domain - Results
    "BundleFileResult",
    "BundleResult",
    "ProjectionResult",
    # Domain - Bundle
    "BundleDescriptor",
    "BundleTemplateEntry",
    "ConflictMode",
    "IterationSpec",
    # Domain - Exceptions
    "BundleError",
    "BundleNotFoundError",
    "BundleParseError",
    "FrontmatterParseError",
    "FrontmatterValidationError",
    "GraphError",
    "GraphNotFoundError",
    "OutputConflictError",
    "ProjectionError",
    "QueryError",
    "QueryExecutionError",
    "QueryFileNotFoundError",
    "SecurityError",
    "TemplateError",
    "TemplateNotFoundError",
    "TemplateRenderError",
    # Engine
    "ProjectionEngine",
    # Ports
    "BundleRegistry",
    "GraphClient",
    "GraphRegistry",
    "InMemoryTemplateRegistry",
    "TemplateRegistry",
]

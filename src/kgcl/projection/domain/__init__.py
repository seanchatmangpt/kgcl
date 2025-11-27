"""Projection domain objects - Frozen dataclasses for projection specifications.

This module re-exports domain objects for template descriptors, results,
bundles, and exceptions.
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

__all__ = [
    # Descriptors
    "N3Role",
    "N3RuleDescriptor",
    "OntologyConfig",
    "QueryDescriptor",
    "QuerySource",
    "TemplateDescriptor",
    "TemplateMetadata",
    # Results
    "BundleFileResult",
    "BundleResult",
    "ProjectionResult",
    # Bundle
    "BundleDescriptor",
    "BundleTemplateEntry",
    "ConflictMode",
    "IterationSpec",
    # Exceptions
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
]

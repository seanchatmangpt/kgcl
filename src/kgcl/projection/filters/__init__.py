"""Jinja filters for KGCL projection layer.

This module provides safe, whitelisted filters for template rendering:
- String and collection manipulation (safe_filters)
- RDF URI and literal extraction (rdf_filters)
- Type mapping between XSD and language types (type_mapping)

All filters are pure functions with no side effects.
"""

from collections.abc import Callable
from typing import Any

from kgcl.projection.filters.rdf_filters import (
    RDF_FILTERS,
    literal_datatype,
    literal_lang,
    literal_value,
    uri_local_name,
    uri_namespace,
    uri_to_curie,
)
from kgcl.projection.filters.safe_filters import (
    SAFE_FILTERS,
    camel_case,
    group_by,
    indent,
    kebab_case,
    pascal_case,
    pluck,
    slugify,
    snake_case,
    sort_by,
    truncate,
    unique,
)
from kgcl.projection.filters.type_mapping import (
    TYPE_MAPPING_FILTERS,
    cardinality_to_python,
    cardinality_to_typescript,
    to_python_class,
    to_typescript_interface,
    xsd_to_openapi,
    xsd_to_python,
    xsd_to_typescript,
)

# Combined filter dictionary for Jinja environment
ALL_FILTERS: dict[str, Callable[..., Any]] = {**SAFE_FILTERS, **RDF_FILTERS, **TYPE_MAPPING_FILTERS}

__all__ = [
    # Safe filters
    "snake_case",
    "camel_case",
    "pascal_case",
    "kebab_case",
    "slugify",
    "truncate",
    "indent",
    "sort_by",
    "unique",
    "group_by",
    "pluck",
    "SAFE_FILTERS",
    # RDF filters
    "uri_local_name",
    "uri_namespace",
    "uri_to_curie",
    "literal_value",
    "literal_lang",
    "literal_datatype",
    "RDF_FILTERS",
    # Type mapping filters
    "xsd_to_python",
    "xsd_to_typescript",
    "xsd_to_openapi",
    "to_python_class",
    "to_typescript_interface",
    "cardinality_to_python",
    "cardinality_to_typescript",
    "TYPE_MAPPING_FILTERS",
    # Combined
    "ALL_FILTERS",
]

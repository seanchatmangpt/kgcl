"""Frontmatter parser - YAML frontmatter extraction and validation.

This module implements parsing and validation of YAML frontmatter from
Jinja template files, building TemplateDescriptor objects with all
metadata, queries, and N3 rules.

Examples
--------
>>> content = '''---
... id: http://example.org/api
... engine: jinja2
... language: python
... framework: fastapi
... version: 1.0.0
... ontology:
...   graph_id: main
... queries:
...   - name: entities
...     purpose: Fetch all entities
...     inline: SELECT ?s WHERE { ?s a ex:Entity }
... ---
... {% for e in entities %}{{ e.s }}{% endfor %}'''
>>> parsed = parse_template_file(content)
>>> parsed.frontmatter["id"]
'http://example.org/api'
>>> "entities" in parsed.body
True
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import yaml

from kgcl.projection.domain.descriptors import (
    N3RuleDescriptor,
    OntologyConfig,
    QueryDescriptor,
    QuerySource,
    TemplateDescriptor,
    TemplateMetadata,
    create_n3_rule_from_dict,
    create_query_from_dict,
)
from kgcl.projection.domain.exceptions import FrontmatterParseError, FrontmatterValidationError

__all__ = [
    "FRONTMATTER_DELIMITER",
    "ParsedTemplate",
    "parse_template_file",
    "validate_frontmatter",
    "build_template_descriptor",
]

FRONTMATTER_DELIMITER = "---"


@dataclass(frozen=True)
class ParsedTemplate:
    """Result of parsing a template file.

    Parameters
    ----------
    frontmatter : dict[str, Any]
        Parsed YAML frontmatter as dictionary.
    body : str
        Template body content (without frontmatter).

    Examples
    --------
    >>> pt = ParsedTemplate(frontmatter={"id": "test"}, body="content")
    >>> pt.frontmatter["id"]
    'test'
    """

    frontmatter: dict[str, Any]
    body: str


def parse_template_file(content: str) -> ParsedTemplate:
    """Extract YAML frontmatter and body from template content.

    Parameters
    ----------
    content : str
        Full template file content including frontmatter.

    Returns
    -------
    ParsedTemplate
        Parsed frontmatter and body.

    Raises
    ------
    FrontmatterParseError
        If frontmatter is missing or YAML parsing fails.

    Examples
    --------
    >>> content = '''---
    ... id: test
    ... ---
    ... body content'''
    >>> parsed = parse_template_file(content)
    >>> parsed.frontmatter["id"]
    'test'
    >>> parsed.body
    'body content'
    """
    lines = content.split("\n")

    # Check for frontmatter start
    if not lines or lines[0].strip() != FRONTMATTER_DELIMITER:
        msg = "Template must start with YAML frontmatter delimiter (---)"
        raise FrontmatterParseError("unknown", msg)

    # Find frontmatter end
    end_idx = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == FRONTMATTER_DELIMITER:
            end_idx = i
            break

    if end_idx == -1:
        msg = "Frontmatter closing delimiter (---) not found"
        raise FrontmatterParseError("unknown", msg)

    # Parse YAML frontmatter
    frontmatter_lines = lines[1:end_idx]
    frontmatter_str = "\n".join(frontmatter_lines)

    try:
        frontmatter_data = yaml.safe_load(frontmatter_str)
        if frontmatter_data is None:
            frontmatter_data = {}
        if not isinstance(frontmatter_data, dict):
            msg = f"Frontmatter must be a YAML mapping, got {type(frontmatter_data).__name__}"
            raise FrontmatterParseError("unknown", msg)
    except yaml.YAMLError as e:
        msg = f"Invalid YAML: {e}"
        raise FrontmatterParseError("unknown", msg) from e

    # Extract body (everything after closing delimiter)
    body_lines = lines[end_idx + 1 :]
    body = "\n".join(body_lines)

    return ParsedTemplate(frontmatter=frontmatter_data, body=body)


def validate_frontmatter(data: dict[str, Any], template_path: str) -> None:
    """Validate frontmatter against required schema.

    Parameters
    ----------
    data : dict[str, Any]
        Parsed frontmatter dictionary.
    template_path : str
        Path to template file (for error messages).

    Raises
    ------
    FrontmatterValidationError
        If required fields are missing or invalid.

    Examples
    --------
    >>> data = {
    ...     "id": "http://example.org/api",
    ...     "engine": "jinja2",
    ...     "language": "python",
    ...     "framework": "fastapi",
    ...     "version": "1.0.0",
    ...     "ontology": {"graph_id": "main"},
    ... }
    >>> validate_frontmatter(data, "api.j2")
    """
    required_fields = ["id", "engine", "language", "version", "ontology"]

    for field in required_fields:
        if field not in data:
            msg = "required field missing"
            raise FrontmatterValidationError(template_path, field, msg)
        if not data[field]:
            msg = "required field cannot be empty"
            raise FrontmatterValidationError(template_path, field, msg)

    # Validate ontology is a dict
    if not isinstance(data["ontology"], dict):
        msg = f"must be a mapping, got {type(data['ontology']).__name__}"
        raise FrontmatterValidationError(template_path, "ontology", msg)

    # Validate ontology.graph_id
    if "graph_id" not in data["ontology"]:
        msg = "ontology.graph_id is required"
        raise FrontmatterValidationError(template_path, "ontology", msg)

    # Validate queries if present
    if "queries" in data:
        if not isinstance(data["queries"], list):
            msg = f"must be a list, got {type(data['queries']).__name__}"
            raise FrontmatterValidationError(template_path, "queries", msg)

    # Validate n3_rules if present
    if "n3_rules" in data:
        if not isinstance(data["n3_rules"], list):
            msg = f"must be a list, got {type(data['n3_rules']).__name__}"
            raise FrontmatterValidationError(template_path, "n3_rules", msg)


def build_template_descriptor(
    frontmatter: dict[str, Any], body: str, template_path: str, query_loader: Callable[[str], str] | None = None
) -> TemplateDescriptor:
    """Build TemplateDescriptor from parsed frontmatter and body.

    Parameters
    ----------
    frontmatter : dict[str, Any]
        Validated frontmatter dictionary.
    body : str
        Template body content.
    template_path : str
        Path to template file.
    query_loader : Callable[[str], str] | None
        Optional function to load query content from file paths.
        Signature: (file_path: str) -> str

    Returns
    -------
    TemplateDescriptor
        Complete template descriptor.

    Examples
    --------
    >>> fm = {
    ...     "id": "http://example.org/api",
    ...     "engine": "jinja2",
    ...     "language": "python",
    ...     "framework": "fastapi",
    ...     "version": "1.0.0",
    ...     "ontology": {"graph_id": "main", "base_iri": "http://ex.org/"},
    ...     "queries": [{"name": "q1", "purpose": "test", "inline": "SELECT *"}],
    ... }
    >>> desc = build_template_descriptor(fm, "body", "test.j2")
    >>> desc.id
    'http://example.org/api'
    >>> len(desc.queries)
    1
    """
    # Build ontology config
    ont_data = frontmatter["ontology"]
    ontology = OntologyConfig(graph_id=str(ont_data["graph_id"]), base_iri=str(ont_data.get("base_iri", "")))

    # Build queries
    queries: list[QueryDescriptor] = []
    for q_data in frontmatter.get("queries", []):
        query = create_query_from_dict(q_data)

        # Load external query file if needed
        if query.source == QuerySource.FILE and query.file_path:
            if query_loader is None:
                msg = f"Query '{query.name}' requires file '{query.file_path}' but no query_loader provided"
                raise FrontmatterValidationError(template_path, "queries", msg)

            # Load file content
            try:
                file_content = query_loader(query.file_path)
            except Exception as e:
                msg = f"Failed to load query file '{query.file_path}': {e}"
                raise FrontmatterValidationError(template_path, "queries", msg) from e

            # Create new descriptor with loaded content
            query = QueryDescriptor(
                name=query.name,
                purpose=query.purpose,
                source=query.source,
                content=file_content,
                file_path=query.file_path,
            )

        queries.append(query)

    # Build N3 rules
    n3_rules: list[N3RuleDescriptor] = []
    for rule_data in frontmatter.get("n3_rules", []):
        rule = create_n3_rule_from_dict(rule_data)
        n3_rules.append(rule)

    # Build metadata
    meta_data = frontmatter.get("metadata", {})
    metadata = TemplateMetadata(
        author=str(meta_data.get("author", "")),
        description=str(meta_data.get("description", "")),
        tags=tuple(str(t) for t in meta_data.get("tags", [])),
    )

    # Build descriptor
    return TemplateDescriptor(
        id=str(frontmatter["id"]),
        engine=str(frontmatter["engine"]),
        language=str(frontmatter["language"]),
        framework=str(frontmatter.get("framework", "")),
        version=str(frontmatter["version"]),
        ontology=ontology,
        queries=tuple(queries),
        n3_rules=tuple(n3_rules),
        metadata=metadata,
        template_path=template_path,
        raw_content=body,
    )

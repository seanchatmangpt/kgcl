"""Projection domain descriptors - Template, Query, and N3 rule definitions.

This module defines frozen dataclasses for describing Jinja templates with
YAML frontmatter that declare SPARQL and N3 dependencies.

Examples
--------
>>> desc = QueryDescriptor(
...     name="all_entities",
...     purpose="Fetch entities for iteration",
...     source=QuerySource.INLINE,
...     content="SELECT ?s WHERE { ?s a ex:Entity }",
... )
>>> desc.name
'all_entities'
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class QuerySource(Enum):
    """Source type for SPARQL queries.

    Examples
    --------
    >>> QuerySource.INLINE.value
    'inline'
    """

    INLINE = "inline"
    FILE = "file"


class N3Role(Enum):
    """Role of N3 rules in projection pipeline.

    Examples
    --------
    >>> N3Role.PRECONDITION.value
    'precondition'
    """

    PRECONDITION = "precondition"
    INFERENCE = "inference"
    POSTCONDITION = "postcondition"


@dataclass(frozen=True)
class OntologyConfig:
    """Configuration for ontology graph binding.

    Parameters
    ----------
    graph_id : str
        Identifier for the graph client to use.
    base_iri : str
        Base IRI for relative URI resolution.

    Examples
    --------
    >>> cfg = OntologyConfig(graph_id="main", base_iri="http://example.org/")
    >>> cfg.graph_id
    'main'
    """

    graph_id: str
    base_iri: str = ""


@dataclass(frozen=True)
class TemplateMetadata:
    """Optional metadata for templates.

    Parameters
    ----------
    author : str
        Template author name.
    description : str
        Human-readable description.
    tags : tuple[str, ...]
        Categorization tags.

    Examples
    --------
    >>> meta = TemplateMetadata(author="team", description="API template")
    >>> meta.author
    'team'
    """

    author: str = ""
    description: str = ""
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class QueryDescriptor:
    """SPARQL query referenced in template frontmatter.

    Parameters
    ----------
    name : str
        Variable name for accessing query results in Jinja context.
    purpose : str
        Human-readable description of query purpose.
    source : QuerySource
        Whether query is inline or from file.
    content : str
        SPARQL query text.
    file_path : str | None
        Path to external query file (if source is FILE).

    Examples
    --------
    >>> q = QueryDescriptor(
    ...     name="entities",
    ...     purpose="Fetch all entities",
    ...     source=QuerySource.INLINE,
    ...     content="SELECT ?s WHERE { ?s a ex:Entity }",
    ... )
    >>> q.name
    'entities'
    """

    name: str
    purpose: str
    source: QuerySource
    content: str
    file_path: str | None = None

    def __post_init__(self) -> None:
        """Validate descriptor state."""
        if not self.name:
            msg = "Query name cannot be empty"
            raise ValueError(msg)
        # Content can be empty for FILE source (loaded later)
        if self.source == QuerySource.INLINE and not self.content:
            msg = "Query content cannot be empty for INLINE source"
            raise ValueError(msg)
        if self.source == QuerySource.FILE and not self.file_path:
            msg = "file_path required when source is FILE"
            raise ValueError(msg)


@dataclass(frozen=True)
class N3RuleDescriptor:
    """N3 rule set referenced in template frontmatter.

    Parameters
    ----------
    name : str
        Identifier for the rule set.
    file_path : str
        Path to the N3 rules file.
    role : N3Role
        When to apply rules in the pipeline.

    Examples
    --------
    >>> rule = N3RuleDescriptor(name="validation", file_path="rules/validate.n3", role=N3Role.PRECONDITION)
    >>> rule.role
    <N3Role.PRECONDITION: 'precondition'>
    """

    name: str
    file_path: str
    role: N3Role

    def __post_init__(self) -> None:
        """Validate descriptor state."""
        if not self.name:
            msg = "Rule name cannot be empty"
            raise ValueError(msg)
        if not self.file_path:
            msg = "Rule file_path cannot be empty"
            raise ValueError(msg)


@dataclass(frozen=True)
class TemplateDescriptor:
    """Complete descriptor for a template with parsed frontmatter.

    Represents the full specification of a Jinja template including
    its identity, target language/framework, ontology binding,
    declared queries, optional N3 rules, and metadata.

    Parameters
    ----------
    id : str
        Unique template identifier (typically URI).
    engine : str
        Template engine (e.g., "jinja2").
    language : str
        Target output language (e.g., "python", "typescript").
    framework : str
        Target framework (e.g., "fastapi", "nextjs").
    version : str
        Template version string.
    ontology : OntologyConfig
        Graph binding configuration.
    queries : tuple[QueryDescriptor, ...]
        Declared SPARQL queries.
    n3_rules : tuple[N3RuleDescriptor, ...]
        Optional N3 rule sets.
    metadata : TemplateMetadata
        Optional metadata.
    template_path : str
        Filesystem path to template file.
    raw_content : str
        Template body (without frontmatter).

    Examples
    --------
    >>> desc = TemplateDescriptor(
    ...     id="http://example.org/templates/api",
    ...     engine="jinja2",
    ...     language="python",
    ...     framework="fastapi",
    ...     version="1.0.0",
    ...     ontology=OntologyConfig(graph_id="main"),
    ...     queries=(),
    ...     n3_rules=(),
    ...     metadata=TemplateMetadata(),
    ...     template_path="/templates/api.j2",
    ...     raw_content="{% for e in entities %}...{% endfor %}",
    ... )
    >>> desc.language
    'python'
    """

    id: str
    engine: str
    language: str
    framework: str
    version: str
    ontology: OntologyConfig
    queries: tuple[QueryDescriptor, ...]
    n3_rules: tuple[N3RuleDescriptor, ...]
    metadata: TemplateMetadata
    template_path: str
    raw_content: str

    def __post_init__(self) -> None:
        """Validate descriptor state."""
        if not self.id:
            msg = "Template id cannot be empty"
            raise ValueError(msg)
        if not self.engine:
            msg = "Template engine cannot be empty"
            raise ValueError(msg)

    def get_query(self, name: str) -> QueryDescriptor | None:
        """Get query descriptor by name.

        Parameters
        ----------
        name : str
            Query name to find.

        Returns
        -------
        QueryDescriptor | None
            The query descriptor or None if not found.

        Examples
        --------
        >>> q = QueryDescriptor(name="test", purpose="", source=QuerySource.INLINE, content="SELECT *")
        >>> desc = TemplateDescriptor(
        ...     id="x",
        ...     engine="jinja2",
        ...     language="py",
        ...     framework="",
        ...     version="1.0",
        ...     ontology=OntologyConfig(graph_id="main"),
        ...     queries=(q,),
        ...     n3_rules=(),
        ...     metadata=TemplateMetadata(),
        ...     template_path="",
        ...     raw_content="",
        ... )
        >>> desc.get_query("test") is not None
        True
        """
        for query in self.queries:
            if query.name == name:
                return query
        return None

    def query_names(self) -> tuple[str, ...]:
        """Get all query names.

        Returns
        -------
        tuple[str, ...]
            Names of all declared queries.

        Examples
        --------
        >>> q1 = QueryDescriptor(name="a", purpose="", source=QuerySource.INLINE, content="SELECT *")
        >>> q2 = QueryDescriptor(name="b", purpose="", source=QuerySource.INLINE, content="SELECT *")
        >>> desc = TemplateDescriptor(
        ...     id="x",
        ...     engine="jinja2",
        ...     language="py",
        ...     framework="",
        ...     version="1.0",
        ...     ontology=OntologyConfig(graph_id="main"),
        ...     queries=(q1, q2),
        ...     n3_rules=(),
        ...     metadata=TemplateMetadata(),
        ...     template_path="",
        ...     raw_content="",
        ... )
        >>> desc.query_names()
        ('a', 'b')
        """
        return tuple(q.name for q in self.queries)


def create_query_from_dict(data: dict[str, Any]) -> QueryDescriptor:
    """Create QueryDescriptor from frontmatter dict.

    Parameters
    ----------
    data : dict[str, Any]
        Dictionary from parsed YAML with 'name', 'purpose',
        and either 'inline' or 'file' key.

    Returns
    -------
    QueryDescriptor
        Constructed descriptor.

    Raises
    ------
    ValueError
        If required fields are missing or both inline/file specified.

    Examples
    --------
    >>> d = {"name": "test", "purpose": "testing", "inline": "SELECT *"}
    >>> q = create_query_from_dict(d)
    >>> q.source
    <QuerySource.INLINE: 'inline'>
    """
    name = data.get("name", "")
    purpose = data.get("purpose", "")
    inline = data.get("inline")
    file_path = data.get("file")

    if inline and file_path:
        msg = f"Query '{name}' cannot have both 'inline' and 'file'"
        raise ValueError(msg)

    if inline:
        return QueryDescriptor(
            name=name, purpose=purpose, source=QuerySource.INLINE, content=str(inline), file_path=None
        )
    elif file_path:
        return QueryDescriptor(
            name=name,
            purpose=purpose,
            source=QuerySource.FILE,
            content="",  # Will be loaded later
            file_path=str(file_path),
        )
    else:
        msg = f"Query '{name}' must have either 'inline' or 'file'"
        raise ValueError(msg)


def create_n3_rule_from_dict(data: dict[str, Any]) -> N3RuleDescriptor:
    """Create N3RuleDescriptor from frontmatter dict.

    Parameters
    ----------
    data : dict[str, Any]
        Dictionary from parsed YAML with 'name', 'file', and 'role'.

    Returns
    -------
    N3RuleDescriptor
        Constructed descriptor.

    Examples
    --------
    >>> d = {"name": "validate", "file": "rules/v.n3", "role": "precondition"}
    >>> r = create_n3_rule_from_dict(d)
    >>> r.role
    <N3Role.PRECONDITION: 'precondition'>
    """
    name = data.get("name", "")
    file_path = data.get("file", "")
    role_str = data.get("role", "inference")

    try:
        role = N3Role(role_str)
    except ValueError:
        role = N3Role.INFERENCE

    return N3RuleDescriptor(name=name, file_path=file_path, role=role)

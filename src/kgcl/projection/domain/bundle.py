"""Bundle domain objects - Multi-file projection definitions.

This module defines frozen dataclasses for bundle specifications that
enable generating multiple files from a single projection run,
with support for iteration over query results.

Examples
--------
>>> spec = IterationSpec(query="all_entities", as_var="entity")
>>> entry = BundleTemplateEntry(template="api/service.j2", output="services/{{ entity.slug }}_service.py", iterate=spec)
>>> entry.has_iteration
True
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ConflictMode(Enum):
    """How to handle output file conflicts.

    Examples
    --------
    >>> ConflictMode.OVERWRITE.value
    'overwrite'
    """

    ERROR = "error"
    OVERWRITE = "overwrite"
    SKIP = "skip"


@dataclass(frozen=True)
class IterationSpec:
    """Specification for iterating over query results.

    When a bundle template entry has an iteration spec, the template
    is rendered once per row in the query results.

    Parameters
    ----------
    query : str
        Name of a declared query in the template, or inline SPARQL.
    as_var : str
        Variable name to bind each row in the Jinja context.

    Examples
    --------
    >>> spec = IterationSpec(query="all_users", as_var="user")
    >>> spec.query
    'all_users'
    >>> spec.as_var
    'user'
    """

    query: str
    as_var: str

    def __post_init__(self) -> None:
        """Validate iteration spec."""
        if not self.query:
            msg = "Iteration query cannot be empty"
            raise ValueError(msg)
        if not self.as_var:
            msg = "Iteration as_var cannot be empty"
            raise ValueError(msg)


@dataclass(frozen=True)
class BundleTemplateEntry:
    """Single template entry in a bundle definition.

    Each entry specifies a template to render and where to write output.
    The output path may contain Jinja expressions for dynamic paths,
    especially when combined with iteration.

    Parameters
    ----------
    template : str
        Path to the template file (relative to template root).
    output : str
        Output path pattern (may contain {{ expressions }}).
    iterate : IterationSpec | None
        Optional iteration spec for generating multiple files.

    Examples
    --------
    >>> entry = BundleTemplateEntry(template="api/openapi.j2", output="openapi.yaml")
    >>> entry.has_iteration
    False

    >>> entry_iter = BundleTemplateEntry(
    ...     template="api/service.j2",
    ...     output="services/{{ entity.slug }}.py",
    ...     iterate=IterationSpec(query="entities", as_var="entity"),
    ... )
    >>> entry_iter.has_iteration
    True
    """

    template: str
    output: str
    iterate: IterationSpec | None = None

    def __post_init__(self) -> None:
        """Validate entry."""
        if not self.template:
            msg = "Template path cannot be empty"
            raise ValueError(msg)
        if not self.output:
            msg = "Output path cannot be empty"
            raise ValueError(msg)

    @property
    def has_iteration(self) -> bool:
        """Check if this entry uses iteration.

        Returns
        -------
        bool
            True if iterate spec is set.

        Examples
        --------
        >>> e = BundleTemplateEntry("t.j2", "out.py")
        >>> e.has_iteration
        False
        """
        return self.iterate is not None

    @property
    def has_dynamic_output(self) -> bool:
        """Check if output path contains Jinja expressions.

        Returns
        -------
        bool
            True if output contains {{ }}.

        Examples
        --------
        >>> e = BundleTemplateEntry("t.j2", "{{ name }}.py")
        >>> e.has_dynamic_output
        True
        >>> e2 = BundleTemplateEntry("t.j2", "static.py")
        >>> e2.has_dynamic_output
        False
        """
        return "{{" in self.output and "}}" in self.output


@dataclass(frozen=True)
class BundleDescriptor:
    """Complete bundle definition for multi-file projection.

    A bundle groups multiple template entries that should be rendered
    together, optionally with shared parameters and iteration.

    Parameters
    ----------
    id : str
        Unique bundle identifier.
    templates : tuple[BundleTemplateEntry, ...]
        Template entries in the bundle.
    description : str
        Human-readable description.
    version : str
        Bundle version string.

    Examples
    --------
    >>> e1 = BundleTemplateEntry("api/openapi.j2", "openapi.yaml")
    >>> e2 = BundleTemplateEntry(
    ...     "api/service.j2", "services/{{ entity.slug }}_service.py", iterate=IterationSpec("entities", "entity")
    ... )
    >>> bundle = BundleDescriptor(
    ...     id="python-api", templates=(e1, e2), description="Generate Python API from ontology", version="1.0.0"
    ... )
    >>> bundle.template_count
    2
    """

    id: str
    templates: tuple[BundleTemplateEntry, ...]
    description: str = ""
    version: str = "1.0.0"

    def __post_init__(self) -> None:
        """Validate bundle."""
        if not self.id:
            msg = "Bundle id cannot be empty"
            raise ValueError(msg)
        if not self.templates:
            msg = "Bundle must have at least one template entry"
            raise ValueError(msg)

    @property
    def template_count(self) -> int:
        """Number of template entries.

        Returns
        -------
        int
            Count of template entries.

        Examples
        --------
        >>> e = BundleTemplateEntry("t.j2", "out.py")
        >>> b = BundleDescriptor("x", (e,))
        >>> b.template_count
        1
        """
        return len(self.templates)

    @property
    def has_iterations(self) -> bool:
        """Check if any template uses iteration.

        Returns
        -------
        bool
            True if any template entry has iteration.

        Examples
        --------
        >>> e = BundleTemplateEntry("t.j2", "out.py")
        >>> b = BundleDescriptor("x", (e,))
        >>> b.has_iterations
        False
        """
        return any(entry.has_iteration for entry in self.templates)

    def get_template_paths(self) -> tuple[str, ...]:
        """Get all unique template paths in the bundle.

        Returns
        -------
        tuple[str, ...]
            Template paths.

        Examples
        --------
        >>> e1 = BundleTemplateEntry("a.j2", "a.py")
        >>> e2 = BundleTemplateEntry("b.j2", "b.py")
        >>> b = BundleDescriptor("x", (e1, e2))
        >>> b.get_template_paths()
        ('a.j2', 'b.j2')
        """
        return tuple(entry.template for entry in self.templates)

    def get_iteration_queries(self) -> tuple[str, ...]:
        """Get all query names used for iteration.

        Returns
        -------
        tuple[str, ...]
            Query names from iteration specs.

        Examples
        --------
        >>> e1 = BundleTemplateEntry("a.j2", "a.py")
        >>> e2 = BundleTemplateEntry("b.j2", "{{ x }}.py", iterate=IterationSpec("q1", "x"))
        >>> e3 = BundleTemplateEntry("c.j2", "{{ y }}.py", iterate=IterationSpec("q2", "y"))
        >>> b = BundleDescriptor("x", (e1, e2, e3))
        >>> b.get_iteration_queries()
        ('q1', 'q2')
        """
        return tuple(entry.iterate.query for entry in self.templates if entry.iterate is not None)

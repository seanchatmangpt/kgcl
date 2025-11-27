"""Projection exceptions - Error hierarchy for projection operations.

This module defines a structured exception hierarchy for projection errors,
enabling precise error handling at different layers of the system.

Examples
--------
>>> try:
...     raise TemplateNotFoundError("api.j2")
... except ProjectionError as e:
...     print(f"Projection failed: {e}")
Projection failed: Template not found: api.j2
"""

from __future__ import annotations


class ProjectionError(Exception):
    """Base exception for all projection errors.

    All projection-related exceptions inherit from this class,
    allowing callers to catch all projection errors with a single except clause.

    Examples
    --------
    >>> try:
    ...     raise ProjectionError("Something went wrong")
    ... except ProjectionError as e:
    ...     str(e)
    'Something went wrong'
    """


class TemplateError(ProjectionError):
    """Base exception for template-related errors.

    Examples
    --------
    >>> raise TemplateError("Invalid template")
    Traceback (most recent call last):
        ...
    kgcl.projection.domain.exceptions.TemplateError: Invalid template
    """


class TemplateNotFoundError(TemplateError):
    """Template file does not exist.

    Parameters
    ----------
    template_name : str
        Name or path of the missing template.

    Examples
    --------
    >>> e = TemplateNotFoundError("api.j2")
    >>> str(e)
    'Template not found: api.j2'
    """

    def __init__(self, template_name: str) -> None:
        self.template_name = template_name
        super().__init__(f"Template not found: {template_name}")


class FrontmatterParseError(TemplateError):
    """Error parsing YAML frontmatter.

    Parameters
    ----------
    template_name : str
        Name of the template with invalid frontmatter.
    reason : str
        Description of the parse error.

    Examples
    --------
    >>> e = FrontmatterParseError("api.j2", "invalid YAML syntax")
    >>> str(e)
    "Frontmatter parse error in 'api.j2': invalid YAML syntax"
    """

    def __init__(self, template_name: str, reason: str) -> None:
        self.template_name = template_name
        self.reason = reason
        super().__init__(f"Frontmatter parse error in '{template_name}': {reason}")


class FrontmatterValidationError(TemplateError):
    """Frontmatter failed schema validation.

    Parameters
    ----------
    template_name : str
        Name of the template with invalid frontmatter.
    field : str
        Name of the invalid field.
    reason : str
        Description of the validation error.

    Examples
    --------
    >>> e = FrontmatterValidationError("api.j2", "engine", "required field missing")
    >>> str(e)
    "Frontmatter validation error in 'api.j2' field 'engine': required field missing"
    """

    def __init__(self, template_name: str, field: str, reason: str) -> None:
        self.template_name = template_name
        self.field = field
        self.reason = reason
        super().__init__(f"Frontmatter validation error in '{template_name}' field '{field}': {reason}")


class TemplateRenderError(TemplateError):
    """Error during Jinja template rendering.

    Parameters
    ----------
    template_name : str
        Name of the template that failed to render.
    reason : str
        Description of the render error.

    Examples
    --------
    >>> e = TemplateRenderError("api.j2", "undefined variable 'foo'")
    >>> str(e)
    "Template render error in 'api.j2': undefined variable 'foo'"
    """

    def __init__(self, template_name: str, reason: str) -> None:
        self.template_name = template_name
        self.reason = reason
        super().__init__(f"Template render error in '{template_name}': {reason}")


class QueryError(ProjectionError):
    """Base exception for query-related errors.

    Examples
    --------
    >>> raise QueryError("Query failed")
    Traceback (most recent call last):
        ...
    kgcl.projection.domain.exceptions.QueryError: Query failed
    """


class QueryExecutionError(QueryError):
    """SPARQL query execution failed.

    Parameters
    ----------
    query_name : str
        Name of the query that failed.
    sparql : str
        The SPARQL query that failed.
    reason : str
        Description of the execution error.

    Examples
    --------
    >>> e = QueryExecutionError("all_entities", "SELECT ?s", "parse error")
    >>> "all_entities" in str(e)
    True
    """

    def __init__(self, query_name: str, sparql: str, reason: str) -> None:
        self.query_name = query_name
        self.sparql = sparql
        self.reason = reason
        super().__init__(f"Query '{query_name}' execution failed: {reason}")


class QueryFileNotFoundError(QueryError):
    """External query file does not exist.

    Parameters
    ----------
    query_name : str
        Name of the query.
    file_path : str
        Path to the missing file.

    Examples
    --------
    >>> e = QueryFileNotFoundError("entities", "queries/entities.rq")
    >>> str(e)
    "Query file not found for 'entities': queries/entities.rq"
    """

    def __init__(self, query_name: str, file_path: str) -> None:
        self.query_name = query_name
        self.file_path = file_path
        super().__init__(f"Query file not found for '{query_name}': {file_path}")


class GraphError(ProjectionError):
    """Base exception for graph/store-related errors.

    Examples
    --------
    >>> raise GraphError("Graph unavailable")
    Traceback (most recent call last):
        ...
    kgcl.projection.domain.exceptions.GraphError: Graph unavailable
    """


class GraphNotFoundError(GraphError):
    """Requested graph client not found.

    Parameters
    ----------
    graph_id : str
        Identifier of the missing graph.

    Examples
    --------
    >>> e = GraphNotFoundError("secondary")
    >>> str(e)
    'Graph not found: secondary'
    """

    def __init__(self, graph_id: str) -> None:
        self.graph_id = graph_id
        super().__init__(f"Graph not found: {graph_id}")


class BundleError(ProjectionError):
    """Base exception for bundle-related errors.

    Examples
    --------
    >>> raise BundleError("Bundle failed")
    Traceback (most recent call last):
        ...
    kgcl.projection.domain.exceptions.BundleError: Bundle failed
    """


class BundleNotFoundError(BundleError):
    """Bundle definition file not found.

    Parameters
    ----------
    bundle_path : str
        Path to the missing bundle file.

    Examples
    --------
    >>> e = BundleNotFoundError("bundles/api.yaml")
    >>> str(e)
    'Bundle not found: bundles/api.yaml'
    """

    def __init__(self, bundle_path: str) -> None:
        self.bundle_path = bundle_path
        super().__init__(f"Bundle not found: {bundle_path}")


class BundleParseError(BundleError):
    """Error parsing bundle YAML definition.

    Parameters
    ----------
    bundle_path : str
        Path to the bundle file.
    reason : str
        Description of the parse error.

    Examples
    --------
    >>> e = BundleParseError("api.yaml", "invalid YAML")
    >>> str(e)
    "Bundle parse error in 'api.yaml': invalid YAML"
    """

    def __init__(self, bundle_path: str, reason: str) -> None:
        self.bundle_path = bundle_path
        self.reason = reason
        super().__init__(f"Bundle parse error in '{bundle_path}': {reason}")


class OutputConflictError(BundleError):
    """Output file already exists and conflict_mode is ERROR.

    Parameters
    ----------
    output_path : str
        Path to the conflicting file.

    Examples
    --------
    >>> e = OutputConflictError("services/api.py")
    >>> str(e)
    'Output file already exists: services/api.py'
    """

    def __init__(self, output_path: str) -> None:
        self.output_path = output_path
        super().__init__(f"Output file already exists: {output_path}")


class SecurityError(ProjectionError):
    """Security violation in template rendering.

    Parameters
    ----------
    reason : str
        Description of the security violation.

    Examples
    --------
    >>> e = SecurityError("Attempted access to __class__")
    >>> str(e)
    'Security violation: Attempted access to __class__'
    """

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Security violation: {reason}")


class ResourceLimitExceeded(ProjectionError):
    """Resource limit exceeded during projection.

    Parameters
    ----------
    resource : str
        Name of the resource that exceeded its limit.
    limit : int | float
        The configured limit value.
    actual : int | float
        The actual value that exceeded the limit.

    Examples
    --------
    >>> e = ResourceLimitExceeded("query_results", 10000, 50000)
    >>> str(e)
    'Resource limit exceeded for query_results: 50000 > 10000'
    """

    def __init__(self, resource: str, limit: int | float, actual: int | float) -> None:
        self.resource = resource
        self.limit = limit
        self.actual = actual
        super().__init__(f"Resource limit exceeded for {resource}: {actual} > {limit}")


class QueryTimeoutError(QueryError):
    """SPARQL query exceeded timeout.

    Parameters
    ----------
    query_name : str
        Name of the query that timed out.
    timeout_seconds : float
        The configured timeout value.

    Examples
    --------
    >>> e = QueryTimeoutError("all_entities", 30.0)
    >>> str(e)
    "Query 'all_entities' timed out after 30.0 seconds"
    """

    def __init__(self, query_name: str, timeout_seconds: float) -> None:
        self.query_name = query_name
        self.timeout_seconds = timeout_seconds
        super().__init__(f"Query '{query_name}' timed out after {timeout_seconds} seconds")


class N3ReasoningError(ProjectionError):
    """N3 reasoning failed during projection.

    Parameters
    ----------
    rule_name : str
        Name of the N3 rule set that failed.
    reason : str
        Description of the failure.

    Examples
    --------
    >>> e = N3ReasoningError("validation_rules", "subprocess timeout")
    >>> str(e)
    "N3 reasoning failed for 'validation_rules': subprocess timeout"
    """

    def __init__(self, rule_name: str, reason: str) -> None:
        self.rule_name = rule_name
        self.reason = reason
        super().__init__(f"N3 reasoning failed for '{rule_name}': {reason}")

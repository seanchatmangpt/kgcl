"""Tests for projection exceptions - Chicago School TDD.

Tests verify the exception hierarchy and message formatting.
"""

from __future__ import annotations

import pytest

from kgcl.projection.domain.exceptions import (
    BundleError,
    BundleNotFoundError,
    BundleParseError,
    FrontmatterParseError,
    FrontmatterValidationError,
    GraphError,
    GraphNotFoundError,
    N3ReasoningError,
    OutputConflictError,
    ProjectionError,
    QueryError,
    QueryExecutionError,
    QueryFileNotFoundError,
    QueryTimeoutError,
    ResourceLimitExceeded,
    SecurityError,
    TemplateError,
    TemplateNotFoundError,
    TemplateRenderError,
)

# =============================================================================
# Exception Hierarchy Tests
# =============================================================================


class TestExceptionHierarchy:
    """Tests for exception inheritance."""

    def test_projection_error_is_exception(self) -> None:
        """ProjectionError inherits from Exception."""
        assert issubclass(ProjectionError, Exception)

    def test_template_errors_inherit(self) -> None:
        """Template errors inherit from TemplateError and ProjectionError."""
        assert issubclass(TemplateError, ProjectionError)
        assert issubclass(TemplateNotFoundError, TemplateError)
        assert issubclass(FrontmatterParseError, TemplateError)
        assert issubclass(FrontmatterValidationError, TemplateError)
        assert issubclass(TemplateRenderError, TemplateError)

    def test_query_errors_inherit(self) -> None:
        """Query errors inherit from QueryError and ProjectionError."""
        assert issubclass(QueryError, ProjectionError)
        assert issubclass(QueryExecutionError, QueryError)
        assert issubclass(QueryFileNotFoundError, QueryError)

    def test_graph_errors_inherit(self) -> None:
        """Graph errors inherit from GraphError and ProjectionError."""
        assert issubclass(GraphError, ProjectionError)
        assert issubclass(GraphNotFoundError, GraphError)

    def test_bundle_errors_inherit(self) -> None:
        """Bundle errors inherit from BundleError and ProjectionError."""
        assert issubclass(BundleError, ProjectionError)
        assert issubclass(BundleNotFoundError, BundleError)
        assert issubclass(BundleParseError, BundleError)
        assert issubclass(OutputConflictError, BundleError)

    def test_security_error_inherits(self) -> None:
        """SecurityError inherits from ProjectionError."""
        assert issubclass(SecurityError, ProjectionError)


# =============================================================================
# ProjectionError Tests
# =============================================================================


class TestProjectionError:
    """Tests for base ProjectionError."""

    def test_message(self) -> None:
        """ProjectionError stores message."""
        e = ProjectionError("Something failed")
        assert str(e) == "Something failed"

    def test_catchable_as_exception(self) -> None:
        """Can catch as Exception."""
        with pytest.raises(Exception):
            raise ProjectionError("test")


# =============================================================================
# TemplateNotFoundError Tests
# =============================================================================


class TestTemplateNotFoundError:
    """Tests for TemplateNotFoundError."""

    def test_message_format(self) -> None:
        """Message includes template name."""
        e = TemplateNotFoundError("api.j2")
        assert str(e) == "Template not found: api.j2"

    def test_template_name_attribute(self) -> None:
        """Stores template_name attribute."""
        e = TemplateNotFoundError("api.j2")
        assert e.template_name == "api.j2"

    def test_catchable_as_template_error(self) -> None:
        """Can catch as TemplateError."""
        with pytest.raises(TemplateError):
            raise TemplateNotFoundError("x")


# =============================================================================
# FrontmatterParseError Tests
# =============================================================================


class TestFrontmatterParseError:
    """Tests for FrontmatterParseError."""

    def test_message_format(self) -> None:
        """Message includes template and reason."""
        e = FrontmatterParseError("api.j2", "invalid YAML")
        assert str(e) == "Frontmatter parse error in 'api.j2': invalid YAML"

    def test_attributes(self) -> None:
        """Stores template_name and reason attributes."""
        e = FrontmatterParseError("api.j2", "bad syntax")
        assert e.template_name == "api.j2"
        assert e.reason == "bad syntax"


# =============================================================================
# FrontmatterValidationError Tests
# =============================================================================


class TestFrontmatterValidationError:
    """Tests for FrontmatterValidationError."""

    def test_message_format(self) -> None:
        """Message includes template, field, and reason."""
        e = FrontmatterValidationError("api.j2", "engine", "required")
        assert str(e) == "Frontmatter validation error in 'api.j2' field 'engine': required"

    def test_attributes(self) -> None:
        """Stores template_name, field, and reason attributes."""
        e = FrontmatterValidationError("api.j2", "version", "must be string")
        assert e.template_name == "api.j2"
        assert e.field == "version"
        assert e.reason == "must be string"


# =============================================================================
# TemplateRenderError Tests
# =============================================================================


class TestTemplateRenderError:
    """Tests for TemplateRenderError."""

    def test_message_format(self) -> None:
        """Message includes template and reason."""
        e = TemplateRenderError("api.j2", "undefined variable")
        assert str(e) == "Template render error in 'api.j2': undefined variable"

    def test_attributes(self) -> None:
        """Stores template_name and reason attributes."""
        e = TemplateRenderError("api.j2", "syntax error")
        assert e.template_name == "api.j2"
        assert e.reason == "syntax error"


# =============================================================================
# QueryExecutionError Tests
# =============================================================================


class TestQueryExecutionError:
    """Tests for QueryExecutionError."""

    def test_message_format(self) -> None:
        """Message includes query name and reason."""
        e = QueryExecutionError("entities", "SELECT ?x", "parse error")
        assert "entities" in str(e)
        assert "execution failed" in str(e)

    def test_attributes(self) -> None:
        """Stores query_name, sparql, and reason attributes."""
        e = QueryExecutionError("q", "SELECT *", "error")
        assert e.query_name == "q"
        assert e.sparql == "SELECT *"
        assert e.reason == "error"


# =============================================================================
# QueryFileNotFoundError Tests
# =============================================================================


class TestQueryFileNotFoundError:
    """Tests for QueryFileNotFoundError."""

    def test_message_format(self) -> None:
        """Message includes query name and file path."""
        e = QueryFileNotFoundError("entities", "queries/entities.rq")
        assert str(e) == "Query file not found for 'entities': queries/entities.rq"

    def test_attributes(self) -> None:
        """Stores query_name and file_path attributes."""
        e = QueryFileNotFoundError("q", "path/to/q.rq")
        assert e.query_name == "q"
        assert e.file_path == "path/to/q.rq"


# =============================================================================
# GraphNotFoundError Tests
# =============================================================================


class TestGraphNotFoundError:
    """Tests for GraphNotFoundError."""

    def test_message_format(self) -> None:
        """Message includes graph_id."""
        e = GraphNotFoundError("secondary")
        assert str(e) == "Graph not found: secondary"

    def test_graph_id_attribute(self) -> None:
        """Stores graph_id attribute."""
        e = GraphNotFoundError("other")
        assert e.graph_id == "other"


# =============================================================================
# BundleNotFoundError Tests
# =============================================================================


class TestBundleNotFoundError:
    """Tests for BundleNotFoundError."""

    def test_message_format(self) -> None:
        """Message includes bundle path."""
        e = BundleNotFoundError("bundles/api.yaml")
        assert str(e) == "Bundle not found: bundles/api.yaml"

    def test_bundle_path_attribute(self) -> None:
        """Stores bundle_path attribute."""
        e = BundleNotFoundError("path/bundle.yaml")
        assert e.bundle_path == "path/bundle.yaml"


# =============================================================================
# BundleParseError Tests
# =============================================================================


class TestBundleParseError:
    """Tests for BundleParseError."""

    def test_message_format(self) -> None:
        """Message includes bundle path and reason."""
        e = BundleParseError("api.yaml", "invalid syntax")
        assert str(e) == "Bundle parse error in 'api.yaml': invalid syntax"

    def test_attributes(self) -> None:
        """Stores bundle_path and reason attributes."""
        e = BundleParseError("b.yaml", "missing field")
        assert e.bundle_path == "b.yaml"
        assert e.reason == "missing field"


# =============================================================================
# OutputConflictError Tests
# =============================================================================


class TestOutputConflictError:
    """Tests for OutputConflictError."""

    def test_message_format(self) -> None:
        """Message includes output path."""
        e = OutputConflictError("services/api.py")
        assert str(e) == "Output file already exists: services/api.py"

    def test_output_path_attribute(self) -> None:
        """Stores output_path attribute."""
        e = OutputConflictError("out.py")
        assert e.output_path == "out.py"


# =============================================================================
# SecurityError Tests
# =============================================================================


class TestSecurityError:
    """Tests for SecurityError."""

    def test_message_format(self) -> None:
        """Message includes reason."""
        e = SecurityError("Attempted access to __class__")
        assert str(e) == "Security violation: Attempted access to __class__"

    def test_reason_attribute(self) -> None:
        """Stores reason attribute."""
        e = SecurityError("blocked attribute")
        assert e.reason == "blocked attribute"


# =============================================================================
# ResourceLimitExceeded Tests
# =============================================================================


class TestResourceLimitExceeded:
    """Tests for ResourceLimitExceeded."""

    def test_message_format(self) -> None:
        """Message includes resource, limit, and actual."""
        e = ResourceLimitExceeded("query_results", 10000, 50000)
        assert str(e) == "Resource limit exceeded for query_results: 50000 > 10000"

    def test_attributes(self) -> None:
        """Stores resource, limit, and actual attributes."""
        e = ResourceLimitExceeded("iterations", 1000, 5000)
        assert e.resource == "iterations"
        assert e.limit == 1000
        assert e.actual == 5000

    def test_inherits_from_projection_error(self) -> None:
        """ResourceLimitExceeded inherits from ProjectionError."""
        assert issubclass(ResourceLimitExceeded, ProjectionError)

    def test_catchable_as_projection_error(self) -> None:
        """Can catch as ProjectionError."""
        with pytest.raises(ProjectionError):
            raise ResourceLimitExceeded("x", 1, 2)


# =============================================================================
# QueryTimeoutError Tests
# =============================================================================


class TestQueryTimeoutError:
    """Tests for QueryTimeoutError."""

    def test_message_format(self) -> None:
        """Message includes query name and timeout."""
        e = QueryTimeoutError("all_entities", 30.0)
        assert str(e) == "Query 'all_entities' timed out after 30.0 seconds"

    def test_attributes(self) -> None:
        """Stores query_name and timeout_seconds attributes."""
        e = QueryTimeoutError("my_query", 15.5)
        assert e.query_name == "my_query"
        assert e.timeout_seconds == 15.5

    def test_inherits_from_query_error(self) -> None:
        """QueryTimeoutError inherits from QueryError."""
        assert issubclass(QueryTimeoutError, QueryError)

    def test_catchable_as_query_error(self) -> None:
        """Can catch as QueryError."""
        with pytest.raises(QueryError):
            raise QueryTimeoutError("q", 1.0)


# =============================================================================
# N3ReasoningError Tests
# =============================================================================


class TestN3ReasoningError:
    """Tests for N3ReasoningError."""

    def test_message_format(self) -> None:
        """Message includes rule name and reason."""
        e = N3ReasoningError("validation_rules", "subprocess timeout")
        assert str(e) == "N3 reasoning failed for 'validation_rules': subprocess timeout"

    def test_attributes(self) -> None:
        """Stores rule_name and reason attributes."""
        e = N3ReasoningError("my_rules", "out of memory")
        assert e.rule_name == "my_rules"
        assert e.reason == "out of memory"

    def test_inherits_from_projection_error(self) -> None:
        """N3ReasoningError inherits from ProjectionError."""
        assert issubclass(N3ReasoningError, ProjectionError)

    def test_catchable_as_projection_error(self) -> None:
        """Can catch as ProjectionError."""
        with pytest.raises(ProjectionError):
            raise N3ReasoningError("rules", "failed")

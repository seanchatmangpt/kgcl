"""Tests for projection domain descriptors - Chicago School TDD.

Tests verify behavior of template, query, and N3 rule descriptors.
"""

from __future__ import annotations

import pytest

from kgcl.projection.domain.descriptors import (
    N3Role,
    N3RuleDescriptor,
    OntologyConfig,
    QueryDescriptor,
    QuerySource,
    TemplateDescriptor,
    TemplateMetadata,
    create_n3_rule_from_dict,
    create_query_from_dict,
)

# =============================================================================
# QuerySource Enum Tests
# =============================================================================


class TestQuerySource:
    """Tests for QuerySource enum."""

    def test_inline_value(self) -> None:
        """INLINE has expected value."""
        assert QuerySource.INLINE.value == "inline"

    def test_file_value(self) -> None:
        """FILE has expected value."""
        assert QuerySource.FILE.value == "file"


# =============================================================================
# N3Role Enum Tests
# =============================================================================


class TestN3Role:
    """Tests for N3Role enum."""

    def test_precondition_value(self) -> None:
        """PRECONDITION has expected value."""
        assert N3Role.PRECONDITION.value == "precondition"

    def test_inference_value(self) -> None:
        """INFERENCE has expected value."""
        assert N3Role.INFERENCE.value == "inference"

    def test_postcondition_value(self) -> None:
        """POSTCONDITION has expected value."""
        assert N3Role.POSTCONDITION.value == "postcondition"


# =============================================================================
# OntologyConfig Tests
# =============================================================================


class TestOntologyConfig:
    """Tests for OntologyConfig dataclass."""

    def test_create_with_graph_id(self) -> None:
        """Can create with just graph_id."""
        cfg = OntologyConfig(graph_id="main")
        assert cfg.graph_id == "main"
        assert cfg.base_iri == ""

    def test_create_with_base_iri(self) -> None:
        """Can create with base_iri."""
        cfg = OntologyConfig(graph_id="main", base_iri="http://example.org/")
        assert cfg.base_iri == "http://example.org/"

    def test_is_frozen(self) -> None:
        """OntologyConfig is immutable."""
        cfg = OntologyConfig(graph_id="main")
        with pytest.raises(AttributeError):
            cfg.graph_id = "other"  # type: ignore[misc]


# =============================================================================
# TemplateMetadata Tests
# =============================================================================


class TestTemplateMetadata:
    """Tests for TemplateMetadata dataclass."""

    def test_default_values(self) -> None:
        """Default values are empty."""
        meta = TemplateMetadata()
        assert meta.author == ""
        assert meta.description == ""
        assert meta.tags == ()

    def test_create_with_values(self) -> None:
        """Can create with all values."""
        meta = TemplateMetadata(author="team", description="API template", tags=("python", "api"))
        assert meta.author == "team"
        assert meta.description == "API template"
        assert meta.tags == ("python", "api")

    def test_is_frozen(self) -> None:
        """TemplateMetadata is immutable."""
        meta = TemplateMetadata()
        with pytest.raises(AttributeError):
            meta.author = "other"  # type: ignore[misc]


# =============================================================================
# QueryDescriptor Tests
# =============================================================================


class TestQueryDescriptor:
    """Tests for QueryDescriptor dataclass."""

    def test_create_inline_query(self) -> None:
        """Can create inline query descriptor."""
        q = QueryDescriptor(
            name="all_entities",
            purpose="Fetch entities",
            source=QuerySource.INLINE,
            content="SELECT ?s WHERE { ?s a ex:Entity }",
        )
        assert q.name == "all_entities"
        assert q.purpose == "Fetch entities"
        assert q.source == QuerySource.INLINE
        assert q.content == "SELECT ?s WHERE { ?s a ex:Entity }"
        assert q.file_path is None

    def test_create_file_query(self) -> None:
        """Can create file-based query descriptor."""
        q = QueryDescriptor(
            name="entities",
            purpose="Fetch entities",
            source=QuerySource.FILE,
            content="SELECT ?s WHERE { ?s a ex:Entity }",
            file_path="queries/entities.rq",
        )
        assert q.source == QuerySource.FILE
        assert q.file_path == "queries/entities.rq"

    def test_empty_name_raises(self) -> None:
        """Empty name raises ValueError."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            QueryDescriptor(name="", purpose="test", source=QuerySource.INLINE, content="SELECT *")

    def test_empty_content_for_inline_raises(self) -> None:
        """Empty content for INLINE source raises ValueError."""
        with pytest.raises(ValueError, match="content cannot be empty for INLINE"):
            QueryDescriptor(name="test", purpose="test", source=QuerySource.INLINE, content="")

    def test_empty_content_for_file_allowed(self) -> None:
        """Empty content for FILE source is allowed (loaded later)."""
        q = QueryDescriptor(
            name="test", purpose="test", source=QuerySource.FILE, content="", file_path="queries/test.rq"
        )
        assert q.content == ""

    def test_file_source_without_path_raises(self) -> None:
        """FILE source without file_path raises ValueError."""
        with pytest.raises(ValueError, match="file_path required"):
            QueryDescriptor(name="test", purpose="test", source=QuerySource.FILE, content="SELECT *", file_path=None)

    def test_is_frozen(self) -> None:
        """QueryDescriptor is immutable."""
        q = QueryDescriptor(name="test", purpose="test", source=QuerySource.INLINE, content="SELECT *")
        with pytest.raises(AttributeError):
            q.name = "other"  # type: ignore[misc]


# =============================================================================
# N3RuleDescriptor Tests
# =============================================================================


class TestN3RuleDescriptor:
    """Tests for N3RuleDescriptor dataclass."""

    def test_create_rule(self) -> None:
        """Can create N3 rule descriptor."""
        rule = N3RuleDescriptor(name="validation", file_path="rules/validate.n3", role=N3Role.PRECONDITION)
        assert rule.name == "validation"
        assert rule.file_path == "rules/validate.n3"
        assert rule.role == N3Role.PRECONDITION

    def test_empty_name_raises(self) -> None:
        """Empty name raises ValueError."""
        with pytest.raises(ValueError, match="Rule name cannot be empty"):
            N3RuleDescriptor(name="", file_path="rules/test.n3", role=N3Role.INFERENCE)

    def test_empty_file_path_raises(self) -> None:
        """Empty file_path raises ValueError."""
        with pytest.raises(ValueError, match="file_path cannot be empty"):
            N3RuleDescriptor(name="test", file_path="", role=N3Role.INFERENCE)

    def test_is_frozen(self) -> None:
        """N3RuleDescriptor is immutable."""
        rule = N3RuleDescriptor(name="test", file_path="rules/test.n3", role=N3Role.INFERENCE)
        with pytest.raises(AttributeError):
            rule.name = "other"  # type: ignore[misc]


# =============================================================================
# TemplateDescriptor Tests
# =============================================================================


class TestTemplateDescriptor:
    """Tests for TemplateDescriptor dataclass."""

    @pytest.fixture
    def sample_query(self) -> QueryDescriptor:
        """Sample query for tests."""
        return QueryDescriptor(
            name="entities",
            purpose="Fetch entities",
            source=QuerySource.INLINE,
            content="SELECT ?s WHERE { ?s a ex:Entity }",
        )

    @pytest.fixture
    def sample_descriptor(self, sample_query: QueryDescriptor) -> TemplateDescriptor:
        """Sample template descriptor for tests."""
        return TemplateDescriptor(
            id="http://example.org/templates/api",
            engine="jinja2",
            language="python",
            framework="fastapi",
            version="1.0.0",
            ontology=OntologyConfig(graph_id="main"),
            queries=(sample_query,),
            n3_rules=(),
            metadata=TemplateMetadata(author="team"),
            template_path="api.j2",
            raw_content="{% for e in entities %}...{% endfor %}",
        )

    def test_create_descriptor(self, sample_descriptor: TemplateDescriptor) -> None:
        """Can create template descriptor."""
        assert sample_descriptor.id == "http://example.org/templates/api"
        assert sample_descriptor.engine == "jinja2"
        assert sample_descriptor.language == "python"
        assert sample_descriptor.framework == "fastapi"
        assert sample_descriptor.version == "1.0.0"

    def test_empty_id_raises(self) -> None:
        """Empty id raises ValueError."""
        with pytest.raises(ValueError, match="id cannot be empty"):
            TemplateDescriptor(
                id="",
                engine="jinja2",
                language="py",
                framework="",
                version="1.0",
                ontology=OntologyConfig(graph_id="main"),
                queries=(),
                n3_rules=(),
                metadata=TemplateMetadata(),
                template_path="",
                raw_content="",
            )

    def test_empty_engine_raises(self) -> None:
        """Empty engine raises ValueError."""
        with pytest.raises(ValueError, match="engine cannot be empty"):
            TemplateDescriptor(
                id="x",
                engine="",
                language="py",
                framework="",
                version="1.0",
                ontology=OntologyConfig(graph_id="main"),
                queries=(),
                n3_rules=(),
                metadata=TemplateMetadata(),
                template_path="",
                raw_content="",
            )

    def test_get_query_found(self, sample_descriptor: TemplateDescriptor) -> None:
        """get_query returns query when found."""
        q = sample_descriptor.get_query("entities")
        assert q is not None
        assert q.name == "entities"

    def test_get_query_not_found(self, sample_descriptor: TemplateDescriptor) -> None:
        """get_query returns None when not found."""
        q = sample_descriptor.get_query("missing")
        assert q is None

    def test_query_names(self, sample_descriptor: TemplateDescriptor) -> None:
        """query_names returns all query names."""
        names = sample_descriptor.query_names()
        assert names == ("entities",)

    def test_is_frozen(self, sample_descriptor: TemplateDescriptor) -> None:
        """TemplateDescriptor is immutable."""
        with pytest.raises(AttributeError):
            sample_descriptor.id = "other"  # type: ignore[misc]


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestCreateQueryFromDict:
    """Tests for create_query_from_dict factory."""

    def test_create_inline_query(self) -> None:
        """Creates inline query from dict."""
        data = {"name": "test", "purpose": "testing", "inline": "SELECT * WHERE { ?s ?p ?o }"}
        q = create_query_from_dict(data)
        assert q.name == "test"
        assert q.source == QuerySource.INLINE
        assert q.content == "SELECT * WHERE { ?s ?p ?o }"

    def test_create_file_query(self) -> None:
        """Creates file query from dict."""
        data = {"name": "test", "purpose": "testing", "file": "queries/test.rq"}
        q = create_query_from_dict(data)
        assert q.source == QuerySource.FILE
        assert q.file_path == "queries/test.rq"
        assert q.content == ""  # Content loaded later

    def test_both_inline_and_file_raises(self) -> None:
        """Having both inline and file raises ValueError."""
        data = {"name": "test", "purpose": "testing", "inline": "SELECT *", "file": "queries/test.rq"}
        with pytest.raises(ValueError, match="cannot have both"):
            create_query_from_dict(data)

    def test_neither_inline_nor_file_raises(self) -> None:
        """Missing both inline and file raises ValueError."""
        data = {"name": "test", "purpose": "testing"}
        with pytest.raises(ValueError, match="must have either"):
            create_query_from_dict(data)


class TestCreateN3RuleFromDict:
    """Tests for create_n3_rule_from_dict factory."""

    def test_create_rule(self) -> None:
        """Creates N3 rule from dict."""
        data = {"name": "validate", "file": "rules/validate.n3", "role": "precondition"}
        rule = create_n3_rule_from_dict(data)
        assert rule.name == "validate"
        assert rule.file_path == "rules/validate.n3"
        assert rule.role == N3Role.PRECONDITION

    def test_default_role_is_inference(self) -> None:
        """Default role is INFERENCE."""
        data = {"name": "infer", "file": "rules/infer.n3"}
        rule = create_n3_rule_from_dict(data)
        assert rule.role == N3Role.INFERENCE

    def test_invalid_role_defaults_to_inference(self) -> None:
        """Invalid role defaults to INFERENCE."""
        data = {"name": "test", "file": "rules/test.n3", "role": "invalid"}
        rule = create_n3_rule_from_dict(data)
        assert rule.role == N3Role.INFERENCE

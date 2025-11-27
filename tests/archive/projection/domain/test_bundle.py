"""Tests for projection bundle domain objects - Chicago School TDD.

Tests verify behavior of bundle descriptors and iteration specs.
"""

from __future__ import annotations

import pytest

from kgcl.projection.domain.bundle import BundleDescriptor, BundleTemplateEntry, ConflictMode, IterationSpec

# =============================================================================
# ConflictMode Enum Tests
# =============================================================================


class TestConflictMode:
    """Tests for ConflictMode enum."""

    def test_error_value(self) -> None:
        """ERROR has expected value."""
        assert ConflictMode.ERROR.value == "error"

    def test_overwrite_value(self) -> None:
        """OVERWRITE has expected value."""
        assert ConflictMode.OVERWRITE.value == "overwrite"

    def test_skip_value(self) -> None:
        """SKIP has expected value."""
        assert ConflictMode.SKIP.value == "skip"


# =============================================================================
# IterationSpec Tests
# =============================================================================


class TestIterationSpec:
    """Tests for IterationSpec dataclass."""

    def test_create_spec(self) -> None:
        """Can create iteration spec."""
        spec = IterationSpec(query="all_users", as_var="user")
        assert spec.query == "all_users"
        assert spec.as_var == "user"

    def test_empty_query_raises(self) -> None:
        """Empty query raises ValueError."""
        with pytest.raises(ValueError, match="query cannot be empty"):
            IterationSpec(query="", as_var="x")

    def test_empty_as_var_raises(self) -> None:
        """Empty as_var raises ValueError."""
        with pytest.raises(ValueError, match="as_var cannot be empty"):
            IterationSpec(query="q", as_var="")

    def test_is_frozen(self) -> None:
        """IterationSpec is immutable."""
        spec = IterationSpec(query="q", as_var="v")
        with pytest.raises(AttributeError):
            spec.query = "other"  # type: ignore[misc]


# =============================================================================
# BundleTemplateEntry Tests
# =============================================================================


class TestBundleTemplateEntry:
    """Tests for BundleTemplateEntry dataclass."""

    def test_create_simple_entry(self) -> None:
        """Can create simple entry without iteration."""
        entry = BundleTemplateEntry(template="api/openapi.j2", output="openapi.yaml")
        assert entry.template == "api/openapi.j2"
        assert entry.output == "openapi.yaml"
        assert entry.iterate is None

    def test_create_with_iteration(self) -> None:
        """Can create entry with iteration."""
        spec = IterationSpec(query="entities", as_var="entity")
        entry = BundleTemplateEntry(
            template="api/service.j2", output="services/{{ entity.slug }}_service.py", iterate=spec
        )
        assert entry.iterate is not None
        assert entry.iterate.query == "entities"

    def test_empty_template_raises(self) -> None:
        """Empty template raises ValueError."""
        with pytest.raises(ValueError, match="Template path cannot be empty"):
            BundleTemplateEntry(template="", output="out.py")

    def test_empty_output_raises(self) -> None:
        """Empty output raises ValueError."""
        with pytest.raises(ValueError, match="Output path cannot be empty"):
            BundleTemplateEntry(template="t.j2", output="")

    def test_has_iteration_false(self) -> None:
        """has_iteration returns False when no iteration."""
        entry = BundleTemplateEntry(template="t.j2", output="out.py")
        assert entry.has_iteration is False

    def test_has_iteration_true(self) -> None:
        """has_iteration returns True when iteration set."""
        entry = BundleTemplateEntry(template="t.j2", output="out.py", iterate=IterationSpec("q", "v"))
        assert entry.has_iteration is True

    def test_has_dynamic_output_false(self) -> None:
        """has_dynamic_output returns False for static path."""
        entry = BundleTemplateEntry(template="t.j2", output="static.py")
        assert entry.has_dynamic_output is False

    def test_has_dynamic_output_true(self) -> None:
        """has_dynamic_output returns True for Jinja expressions."""
        entry = BundleTemplateEntry(template="t.j2", output="{{ name }}_{{ version }}.py")
        assert entry.has_dynamic_output is True

    def test_is_frozen(self) -> None:
        """BundleTemplateEntry is immutable."""
        entry = BundleTemplateEntry(template="t.j2", output="out.py")
        with pytest.raises(AttributeError):
            entry.template = "other.j2"  # type: ignore[misc]


# =============================================================================
# BundleDescriptor Tests
# =============================================================================


class TestBundleDescriptor:
    """Tests for BundleDescriptor dataclass."""

    @pytest.fixture
    def sample_entries(self) -> tuple[BundleTemplateEntry, ...]:
        """Sample entries for tests."""
        e1 = BundleTemplateEntry("api/openapi.j2", "openapi.yaml")
        e2 = BundleTemplateEntry(
            "api/service.j2", "services/{{ entity.slug }}_service.py", iterate=IterationSpec("entities", "entity")
        )
        return (e1, e2)

    def test_create_bundle(self, sample_entries: tuple[BundleTemplateEntry, ...]) -> None:
        """Can create bundle descriptor."""
        bundle = BundleDescriptor(
            id="python-api", templates=sample_entries, description="Generate Python API", version="1.0.0"
        )
        assert bundle.id == "python-api"
        assert bundle.description == "Generate Python API"
        assert bundle.version == "1.0.0"

    def test_empty_id_raises(self) -> None:
        """Empty id raises ValueError."""
        entry = BundleTemplateEntry("t.j2", "out.py")
        with pytest.raises(ValueError, match="id cannot be empty"):
            BundleDescriptor(id="", templates=(entry,))

    def test_empty_templates_raises(self) -> None:
        """Empty templates raises ValueError."""
        with pytest.raises(ValueError, match="must have at least one"):
            BundleDescriptor(id="x", templates=())

    def test_template_count(self, sample_entries: tuple[BundleTemplateEntry, ...]) -> None:
        """template_count returns entry count."""
        bundle = BundleDescriptor(id="x", templates=sample_entries)
        assert bundle.template_count == 2

    def test_has_iterations_false(self) -> None:
        """has_iterations returns False when no iterations."""
        e = BundleTemplateEntry("t.j2", "out.py")
        bundle = BundleDescriptor(id="x", templates=(e,))
        assert bundle.has_iterations is False

    def test_has_iterations_true(self, sample_entries: tuple[BundleTemplateEntry, ...]) -> None:
        """has_iterations returns True when any entry has iteration."""
        bundle = BundleDescriptor(id="x", templates=sample_entries)
        assert bundle.has_iterations is True

    def test_get_template_paths(self, sample_entries: tuple[BundleTemplateEntry, ...]) -> None:
        """get_template_paths returns all paths."""
        bundle = BundleDescriptor(id="x", templates=sample_entries)
        paths = bundle.get_template_paths()
        assert paths == ("api/openapi.j2", "api/service.j2")

    def test_get_iteration_queries(self, sample_entries: tuple[BundleTemplateEntry, ...]) -> None:
        """get_iteration_queries returns queries from iterations."""
        bundle = BundleDescriptor(id="x", templates=sample_entries)
        queries = bundle.get_iteration_queries()
        assert queries == ("entities",)

    def test_get_iteration_queries_empty(self) -> None:
        """get_iteration_queries returns empty when no iterations."""
        e = BundleTemplateEntry("t.j2", "out.py")
        bundle = BundleDescriptor(id="x", templates=(e,))
        assert bundle.get_iteration_queries() == ()

    def test_default_values(self) -> None:
        """Default values are set correctly."""
        e = BundleTemplateEntry("t.j2", "out.py")
        bundle = BundleDescriptor(id="x", templates=(e,))
        assert bundle.description == ""
        assert bundle.version == "1.0.0"

    def test_is_frozen(self, sample_entries: tuple[BundleTemplateEntry, ...]) -> None:
        """BundleDescriptor is immutable."""
        bundle = BundleDescriptor(id="x", templates=sample_entries)
        with pytest.raises(AttributeError):
            bundle.id = "other"  # type: ignore[misc]

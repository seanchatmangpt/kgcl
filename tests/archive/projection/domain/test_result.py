"""Tests for projection result types - Chicago School TDD.

Tests verify behavior of ProjectionResult and BundleResult dataclasses.
"""

from __future__ import annotations

import pytest

from kgcl.projection.domain.result import BundleFileResult, BundleResult, ProjectionResult

# =============================================================================
# ProjectionResult Tests
# =============================================================================


class TestProjectionResult:
    """Tests for ProjectionResult dataclass."""

    def test_create_result(self) -> None:
        """Can create projection result."""
        result = ProjectionResult(
            template_id="api",
            version="1.0.0",
            content="# Generated API",
            media_type="text/x-python",
            context_info={"query_count": 3, "render_time_ms": 12.5},
        )
        assert result.template_id == "api"
        assert result.version == "1.0.0"
        assert result.content == "# Generated API"
        assert result.media_type == "text/x-python"

    def test_create_with_none_values(self) -> None:
        """Can create with None version and media_type."""
        result = ProjectionResult(template_id="test", version=None, content="output", media_type=None, context_info={})
        assert result.version is None
        assert result.media_type is None

    def test_query_count_property(self) -> None:
        """query_count returns value from context_info."""
        result = ProjectionResult(
            template_id="x", version=None, content="", media_type=None, context_info={"query_count": 5}
        )
        assert result.query_count == 5

    def test_query_count_default_zero(self) -> None:
        """query_count returns 0 when not in context_info."""
        result = ProjectionResult(template_id="x", version=None, content="", media_type=None, context_info={})
        assert result.query_count == 0

    def test_render_time_property(self) -> None:
        """render_time_ms returns value from context_info."""
        result = ProjectionResult(
            template_id="x", version=None, content="", media_type=None, context_info={"render_time_ms": 12.5}
        )
        assert result.render_time_ms == 12.5

    def test_render_time_default_zero(self) -> None:
        """render_time_ms returns 0.0 when not in context_info."""
        result = ProjectionResult(template_id="x", version=None, content="", media_type=None, context_info={})
        assert result.render_time_ms == 0.0

    def test_with_content_creates_copy(self) -> None:
        """with_content creates new result with updated content."""
        original = ProjectionResult(
            template_id="x", version="1.0", content="old", media_type="text/plain", context_info={"key": "value"}
        )
        modified = original.with_content("new")

        assert modified.content == "new"
        assert modified.template_id == "x"
        assert modified.version == "1.0"
        assert original.content == "old"  # Original unchanged

    def test_is_frozen(self) -> None:
        """ProjectionResult is immutable."""
        result = ProjectionResult(template_id="x", version=None, content="", media_type=None, context_info={})
        with pytest.raises(AttributeError):
            result.template_id = "y"  # type: ignore[misc]


# =============================================================================
# BundleFileResult Tests
# =============================================================================


class TestBundleFileResult:
    """Tests for BundleFileResult dataclass."""

    @pytest.fixture
    def sample_projection(self) -> ProjectionResult:
        """Sample projection result for tests."""
        return ProjectionResult(
            template_id="svc", version="1.0", content="class Service: pass", media_type="text/x-python", context_info={}
        )

    def test_create_file_result(self, sample_projection: ProjectionResult) -> None:
        """Can create bundle file result."""
        bfr = BundleFileResult(
            output_path="services/user_service.py",
            result=sample_projection,
            iteration_context={"entity": {"slug": "user"}},
        )
        assert bfr.output_path == "services/user_service.py"
        assert bfr.result.content == "class Service: pass"
        assert bfr.iteration_context == {"entity": {"slug": "user"}}

    def test_create_without_iteration(self, sample_projection: ProjectionResult) -> None:
        """Can create without iteration context."""
        bfr = BundleFileResult(output_path="api.py", result=sample_projection)
        assert bfr.iteration_context is None

    def test_is_frozen(self, sample_projection: ProjectionResult) -> None:
        """BundleFileResult is immutable."""
        bfr = BundleFileResult(output_path="test.py", result=sample_projection)
        with pytest.raises(AttributeError):
            bfr.output_path = "other.py"  # type: ignore[misc]


# =============================================================================
# BundleResult Tests
# =============================================================================


class TestBundleResult:
    """Tests for BundleResult dataclass."""

    @pytest.fixture
    def sample_files(self) -> tuple[BundleFileResult, ...]:
        """Sample bundle file results for tests."""
        pr1 = ProjectionResult("a", "1.0", "content a", None, {})
        pr2 = ProjectionResult("b", "1.0", "content b", None, {})
        return (BundleFileResult("a.py", pr1, None), BundleFileResult("b.py", pr2, None))

    def test_create_bundle_result(self, sample_files: tuple[BundleFileResult, ...]) -> None:
        """Can create bundle result."""
        br = BundleResult(bundle_id="crud-bundle", files=sample_files, total_render_time_ms=50.0, dry_run=False)
        assert br.bundle_id == "crud-bundle"
        assert br.total_render_time_ms == 50.0
        assert br.dry_run is False

    def test_file_count_property(self, sample_files: tuple[BundleFileResult, ...]) -> None:
        """file_count returns number of files."""
        br = BundleResult("b", sample_files, 10.0)
        assert br.file_count == 2

    def test_file_count_empty(self) -> None:
        """file_count returns 0 for empty bundle."""
        br = BundleResult("b", (), 0.0)
        assert br.file_count == 0

    def test_output_paths_property(self, sample_files: tuple[BundleFileResult, ...]) -> None:
        """output_paths returns all paths."""
        br = BundleResult("b", sample_files, 10.0)
        assert br.output_paths == ("a.py", "b.py")

    def test_get_file_found(self, sample_files: tuple[BundleFileResult, ...]) -> None:
        """get_file returns file when found."""
        br = BundleResult("b", sample_files, 10.0)
        f = br.get_file("a.py")
        assert f is not None
        assert f.output_path == "a.py"

    def test_get_file_not_found(self, sample_files: tuple[BundleFileResult, ...]) -> None:
        """get_file returns None when not found."""
        br = BundleResult("b", sample_files, 10.0)
        f = br.get_file("missing.py")
        assert f is None

    def test_dry_run_default_false(self, sample_files: tuple[BundleFileResult, ...]) -> None:
        """dry_run defaults to False."""
        br = BundleResult("b", sample_files, 10.0)
        assert br.dry_run is False

    def test_is_frozen(self, sample_files: tuple[BundleFileResult, ...]) -> None:
        """BundleResult is immutable."""
        br = BundleResult("b", sample_files, 10.0)
        with pytest.raises(AttributeError):
            br.bundle_id = "other"  # type: ignore[misc]

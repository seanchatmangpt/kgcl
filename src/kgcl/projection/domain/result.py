"""Projection result types - Immutable results from template rendering.

This module defines frozen dataclasses for projection outputs including
single template results and bundle results with multiple files.

Examples
--------
>>> result = ProjectionResult(
...     template_id="http://example.org/api",
...     version="1.0.0",
...     content="# Generated API",
...     media_type="text/x-python",
...     context_info={"query_count": 3, "render_time_ms": 12.5},
... )
>>> result.template_id
'http://example.org/api'
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProjectionResult:
    """Immutable result of a single template projection.

    Parameters
    ----------
    template_id : str
        Identifier of the rendered template.
    version : str | None
        Template version if specified.
    content : str
        Rendered output content.
    media_type : str | None
        MIME type of the output (e.g., "text/x-python").
    context_info : dict[str, Any]
        Metadata about the rendering (query_count, render_time_ms, etc.).

    Examples
    --------
    >>> r = ProjectionResult(
    ...     template_id="test",
    ...     version="1.0",
    ...     content="output",
    ...     media_type="text/plain",
    ...     context_info={"render_time_ms": 5.0},
    ... )
    >>> r.content
    'output'
    """

    template_id: str
    version: str | None
    content: str
    media_type: str | None
    context_info: dict[str, Any] = field(default_factory=dict)

    @property
    def query_count(self) -> int:
        """Number of SPARQL queries executed.

        Returns
        -------
        int
            Query count from context_info or 0.

        Examples
        --------
        >>> r = ProjectionResult(
        ...     template_id="x", version=None, content="", media_type=None, context_info={"query_count": 5}
        ... )
        >>> r.query_count
        5
        """
        return int(self.context_info.get("query_count", 0))

    @property
    def render_time_ms(self) -> float:
        """Rendering time in milliseconds.

        Returns
        -------
        float
            Render time from context_info or 0.0.

        Examples
        --------
        >>> r = ProjectionResult(
        ...     template_id="x", version=None, content="", media_type=None, context_info={"render_time_ms": 12.5}
        ... )
        >>> r.render_time_ms
        12.5
        """
        return float(self.context_info.get("render_time_ms", 0.0))

    def with_content(self, new_content: str) -> ProjectionResult:
        """Create copy with new content.

        Parameters
        ----------
        new_content : str
            Replacement content.

        Returns
        -------
        ProjectionResult
            New result with updated content.

        Examples
        --------
        >>> r = ProjectionResult(template_id="x", version="1.0", content="old", media_type=None, context_info={})
        >>> r2 = r.with_content("new")
        >>> r2.content
        'new'
        >>> r.content  # Original unchanged
        'old'
        """
        return ProjectionResult(
            template_id=self.template_id,
            version=self.version,
            content=new_content,
            media_type=self.media_type,
            context_info=self.context_info,
        )


@dataclass(frozen=True)
class BundleFileResult:
    """Result for a single file in a bundle.

    Parameters
    ----------
    output_path : str
        Relative path where file should be written.
    result : ProjectionResult
        The projection result for this file.
    iteration_context : dict[str, Any] | None
        Context from iteration (if applicable).

    Examples
    --------
    >>> pr = ProjectionResult(
    ...     template_id="svc", version="1.0", content="class Svc: pass", media_type="text/x-python", context_info={}
    ... )
    >>> bfr = BundleFileResult(
    ...     output_path="services/user_service.py", result=pr, iteration_context={"entity": {"slug": "user"}}
    ... )
    >>> bfr.output_path
    'services/user_service.py'
    """

    output_path: str
    result: ProjectionResult
    iteration_context: dict[str, Any] | None = None


@dataclass(frozen=True)
class BundleResult:
    """Immutable result of rendering a multi-file bundle.

    Parameters
    ----------
    bundle_id : str
        Identifier of the rendered bundle.
    files : tuple[BundleFileResult, ...]
        Results for each generated file.
    total_render_time_ms : float
        Total time to render all files.
    dry_run : bool
        Whether this was a dry run (no files written).

    Examples
    --------
    >>> br = BundleResult(bundle_id="crud-bundle", files=(), total_render_time_ms=50.0, dry_run=False)
    >>> br.file_count
    0
    """

    bundle_id: str
    files: tuple[BundleFileResult, ...]
    total_render_time_ms: float
    dry_run: bool = False

    @property
    def file_count(self) -> int:
        """Number of files generated.

        Returns
        -------
        int
            Count of files in bundle result.

        Examples
        --------
        >>> pr = ProjectionResult("x", "1.0", "", None, {})
        >>> f1 = BundleFileResult("a.py", pr, None)
        >>> f2 = BundleFileResult("b.py", pr, None)
        >>> br = BundleResult("b", (f1, f2), 10.0)
        >>> br.file_count
        2
        """
        return len(self.files)

    @property
    def output_paths(self) -> tuple[str, ...]:
        """All output paths in the bundle.

        Returns
        -------
        tuple[str, ...]
            Paths of all generated files.

        Examples
        --------
        >>> pr = ProjectionResult("x", "1.0", "", None, {})
        >>> f1 = BundleFileResult("a.py", pr, None)
        >>> f2 = BundleFileResult("b.py", pr, None)
        >>> br = BundleResult("b", (f1, f2), 10.0)
        >>> br.output_paths
        ('a.py', 'b.py')
        """
        return tuple(f.output_path for f in self.files)

    def get_file(self, path: str) -> BundleFileResult | None:
        """Get file result by output path.

        Parameters
        ----------
        path : str
            Output path to find.

        Returns
        -------
        BundleFileResult | None
            The file result or None if not found.

        Examples
        --------
        >>> pr = ProjectionResult("x", "1.0", "content", None, {})
        >>> f = BundleFileResult("test.py", pr, None)
        >>> br = BundleResult("b", (f,), 10.0)
        >>> br.get_file("test.py") is not None
        True
        >>> br.get_file("missing.py") is None
        True
        """
        for file_result in self.files:
            if file_result.output_path == path:
                return file_result
        return None

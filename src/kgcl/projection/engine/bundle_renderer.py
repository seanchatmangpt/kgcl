"""BundleRenderer - Multi-file projection with iteration support.

This module provides bundle rendering that generates multiple files from
a single projection run, with support for iterating over query results.

Examples
--------
>>> from kgcl.projection.engine.projection_engine import ProjectionEngine
>>> from kgcl.projection.ports.template_registry import InMemoryTemplateRegistry
>>> from kgcl.projection.domain.bundle import BundleDescriptor, BundleTemplateEntry
>>> registry = InMemoryTemplateRegistry()
>>> proj_engine = ProjectionEngine(registry, {})
>>> renderer = BundleRenderer(proj_engine)
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jinja2 import Environment

from kgcl.projection.domain.bundle import ConflictMode
from kgcl.projection.domain.exceptions import ResourceLimitExceeded
from kgcl.projection.domain.result import BundleFileResult, BundleResult
from kgcl.projection.sandbox import create_projection_environment

if TYPE_CHECKING:
    from kgcl.projection.domain.bundle import BundleDescriptor, BundleTemplateEntry

__all__ = ["BundleRenderer"]


class BundleRenderer:
    """Renders multi-file bundles with iteration support.

    The bundle renderer coordinates rendering of multiple templates,
    handling file path resolution, iteration over query results,
    and conflict detection.

    Parameters
    ----------
    projection_engine : ProjectionEngine
        Engine for rendering individual templates.
    output_jinja_env : Environment | None
        Jinja environment for output path templates (uses sandboxed if None).

    Examples
    --------
    >>> from kgcl.projection.engine.projection_engine import ProjectionEngine
    >>> from kgcl.projection.ports.graph_client import GraphRegistry
    >>> from kgcl.projection.ports.template_registry import InMemoryTemplateRegistry
    >>> registry = InMemoryTemplateRegistry()
    >>> graphs = GraphRegistry()
    >>> proj_engine = ProjectionEngine(registry, graphs)
    >>> renderer = BundleRenderer(proj_engine)
    """

    def __init__(
        self,
        projection_engine: Any,  # ProjectionEngine from projection_engine module
        output_jinja_env: Environment | None = None,
        max_iteration: int | None = None,
    ) -> None:
        """Initialize bundle renderer.

        Parameters
        ----------
        projection_engine : ProjectionEngine
            Engine for rendering templates.
        output_jinja_env : Environment | None
            Environment for output path templates.
        max_iteration : int | None
            Maximum iterations per bundle entry. If None, no limit.
        """
        self._projection_engine = projection_engine
        self._template_registry: TemplateRegistry = projection_engine.template_registry  # type: ignore[assignment]
        self._output_env = output_jinja_env or create_projection_environment()
        self._max_iteration = max_iteration

    def render_bundle(
        self,
        bundle: BundleDescriptor,
        params: dict[str, Any] | None = None,
        output_dir: Path | None = None,
        conflict_mode: ConflictMode = ConflictMode.ERROR,
        dry_run: bool = False,
    ) -> BundleResult:
        """Render a multi-file bundle.

        Parameters
        ----------
        bundle : BundleDescriptor
            Bundle definition with templates.
        params : dict[str, Any] | None
            Parameters for rendering.
        output_dir : Path | None
            Base directory for output files (only used for writing).
        conflict_mode : ConflictMode
            How to handle output file conflicts.
        dry_run : bool
            If True, don't write files to disk.

        Returns
        -------
        BundleResult
            Result containing all generated files.

        Raises
        ------
        ValueError
            If conflict detected and mode is ERROR.

        Examples
        --------
        >>> from kgcl.projection.engine.projection_engine import ProjectionEngine
        >>> from kgcl.projection.ports.graph_client import GraphRegistry
        >>> from kgcl.projection.ports.template_registry import InMemoryTemplateRegistry
        >>> from kgcl.projection.domain.bundle import BundleDescriptor, BundleTemplateEntry
        >>> from kgcl.projection.domain.descriptors import TemplateDescriptor, OntologyConfig, TemplateMetadata
        >>> registry = InMemoryTemplateRegistry()
        >>> desc = TemplateDescriptor(
        ...     id="test",
        ...     engine="jinja2",
        ...     language="python",
        ...     framework="",
        ...     version="1.0",
        ...     ontology=OntologyConfig("main"),
        ...     queries=(),
        ...     n3_rules=(),
        ...     metadata=TemplateMetadata(),
        ...     template_path="test.j2",
        ...     raw_content="# {{ title }}",
        ... )
        >>> registry.add(desc)
        >>> entry = BundleTemplateEntry("test.j2", "output.py")
        >>> bundle_desc = BundleDescriptor("test-bundle", (entry,))
        >>> graphs = GraphRegistry()
        >>> engine = ProjectionEngine(registry, graphs)
        >>> renderer = BundleRenderer(engine)
        >>> result = renderer.render_bundle(bundle_desc, {"title": "Test"}, dry_run=True)
        >>> result.file_count
        1
        """
        start_time = time.perf_counter()
        user_params = params or {}
        all_files: list[BundleFileResult] = []

        # Render each template entry
        for entry in bundle.templates:
            file_results = self._render_entry(entry, user_params)
            all_files.extend(file_results)

        # Check for conflicts
        self._check_conflicts(all_files, conflict_mode)

        # Write files if not dry run
        if not dry_run and output_dir is not None:
            self._write_files(all_files, output_dir, conflict_mode)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return BundleResult(
            bundle_id=bundle.id, files=tuple(all_files), total_render_time_ms=elapsed_ms, dry_run=dry_run
        )

    def _render_entry(self, entry: BundleTemplateEntry, params: dict[str, Any]) -> list[BundleFileResult]:
        """Render a single bundle template entry.

        Parameters
        ----------
        entry : BundleTemplateEntry
            Entry to render.
        params : dict[str, Any]
            User parameters.

        Returns
        -------
        list[BundleFileResult]
            One or more file results (multiple if iteration).
        """
        if entry.has_iteration:
            return self._render_with_iteration(entry, params)
        else:
            return self._render_single(entry, params)

    def _render_single(self, entry: BundleTemplateEntry, params: dict[str, Any]) -> list[BundleFileResult]:
        """Render entry without iteration.

        Parameters
        ----------
        entry : BundleTemplateEntry
            Entry to render.
        params : dict[str, Any]
            Parameters.

        Returns
        -------
        list[BundleFileResult]
            Single file result.
        """
        # Load template descriptor
        descriptor = self._template_registry.get(entry.template)
        if descriptor is None:
            msg = f"Template not found: {entry.template}"
            raise ValueError(msg)

        # Render template using descriptor's ontology
        projection_result = self._projection_engine.render(entry.template, params)

        # Resolve output path
        output_path = self._resolve_output_path(entry.output, params)

        return [BundleFileResult(output_path=output_path, result=projection_result, iteration_context=None)]

    def _render_with_iteration(self, entry: BundleTemplateEntry, params: dict[str, Any]) -> list[BundleFileResult]:
        """Render entry with iteration over query results.

        Parameters
        ----------
        entry : BundleTemplateEntry
            Entry with iteration spec.
        params : dict[str, Any]
            Parameters.

        Returns
        -------
        list[BundleFileResult]
            File result per iteration.
        """
        if entry.iterate is None:
            return []

        # Load template to get ontology config
        descriptor = self._template_registry.get(entry.template)
        if descriptor is None:
            msg = f"Template not found: {entry.template}"
            raise ValueError(msg)

        # Execute iteration query against the template's graph
        graph_id = descriptor.ontology.graph_id
        graph_client = self._projection_engine.graph_clients.get(graph_id)
        if graph_client is None:
            msg = f"Graph not found: {graph_id}"
            raise ValueError(msg)

        iteration_results = graph_client.query(entry.iterate.query)

        # Check iteration limit
        if self._max_iteration is not None and len(iteration_results) > self._max_iteration:
            raise ResourceLimitExceeded(f"iterations:{entry.template}", self._max_iteration, len(iteration_results))

        files: list[BundleFileResult] = []
        for row in iteration_results:
            # Build context for this iteration
            iter_context = {entry.iterate.as_var: row}
            merged_params = {**params, **iter_context}

            # Render template with iteration context
            projection_result = self._projection_engine.render(entry.template, merged_params)

            # Resolve output path with iteration context
            output_path = self._resolve_output_path(entry.output, merged_params)

            files.append(
                BundleFileResult(output_path=output_path, result=projection_result, iteration_context=iter_context)
            )

        return files

    def _resolve_output_path(self, output_template: str, context: dict[str, Any]) -> str:
        """Resolve output path from template.

        Parameters
        ----------
        output_template : str
            Output path pattern (may contain {{ }}).
        context : dict[str, Any]
            Context for template variables.

        Returns
        -------
        str
            Resolved output path.

        Examples
        --------
        >>> from kgcl.projection.engine.projection_engine import ProjectionEngine
        >>> from kgcl.projection.ports.template_registry import InMemoryTemplateRegistry
        >>> registry = InMemoryTemplateRegistry()
        >>> engine = ProjectionEngine(registry, {})
        >>> renderer = BundleRenderer(engine)
        >>> renderer._resolve_output_path("{{ params.name }}.py", {"name": "test"})
        'test.py'
        """
        if "{{" in output_template and "}}" in output_template:
            # Dynamic path - render with Jinja
            # Wrap context in params to match projection engine pattern
            render_context = {"params": context}
            template = self._output_env.from_string(output_template)
            return template.render(**render_context)
        else:
            # Static path
            return output_template

    def _check_conflicts(self, files: list[BundleFileResult], conflict_mode: ConflictMode) -> None:
        """Check for output path conflicts.

        Parameters
        ----------
        files : list[BundleFileResult]
            Files to check.
        conflict_mode : ConflictMode
            How to handle conflicts.

        Raises
        ------
        ValueError
            If conflict detected and mode is ERROR.
        """
        if conflict_mode == ConflictMode.ERROR:
            paths_seen: set[str] = set()
            for file_result in files:
                if file_result.output_path in paths_seen:
                    msg = f"Output path conflict: {file_result.output_path}"
                    raise ValueError(msg)
                paths_seen.add(file_result.output_path)

    def _write_files(self, files: list[BundleFileResult], output_dir: Path, conflict_mode: ConflictMode) -> None:
        """Write files to disk.

        Parameters
        ----------
        files : list[BundleFileResult]
            Files to write.
        output_dir : Path
            Base output directory.
        conflict_mode : ConflictMode
            How to handle existing files.
        """
        for file_result in files:
            output_path = output_dir / file_result.output_path

            # Check if file exists
            if output_path.exists():
                if conflict_mode == ConflictMode.SKIP:
                    continue
                elif conflict_mode == ConflictMode.ERROR:
                    msg = f"File already exists: {output_path}"
                    raise ValueError(msg)
                # OVERWRITE mode - continue to write

            # Ensure parent directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write content
            output_path.write_text(file_result.result.content, encoding="utf-8")

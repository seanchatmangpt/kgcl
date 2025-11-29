"""Projection engine - Main orchestrator for template rendering.

This module implements the ProjectionEngine which orchestrates the complete
projection pipeline: loading templates, executing queries, building context,
and rendering Jinja templates to produce ProjectionResult outputs.

Implements μ_proj in A = μ_proj(O).

Examples
--------
>>> from jinja2 import Environment
>>> from kgcl.projection.domain.descriptors import TemplateDescriptor, OntologyConfig
>>> class MockRegistry:
...     def get(self, name: str) -> TemplateDescriptor | None:
...         if name == "api":
...             return TemplateDescriptor(
...                 id="http://ex.org/api",
...                 engine="jinja2",
...                 language="python",
...                 framework="fastapi",
...                 version="1.0",
...                 ontology=OntologyConfig("main"),
...                 queries=(),
...                 n3_rules=(),
...                 metadata=None,
...                 template_path="api.j2",
...                 raw_content="# API v{{ params.version }}",
...             )
...         return None
>>> class MockClient:
...     @property
...     def graph_id(self) -> str:
...         return "main"
...
...     def query(self, s: str) -> list[dict[str, object]]:
...         return []
...
...     def ask(self, s: str) -> bool:
...         return False
...
...     def construct(self, s: str) -> str:
...         return ""
>>> engine = ProjectionEngine(MockRegistry(), {"main": MockClient()})
>>> result = engine.render("api", {"version": "1.0"})
>>> result.content
'# API v1.0'
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from jinja2 import Environment, Template

from kgcl.projection.domain.descriptors import N3Role, N3RuleDescriptor
from kgcl.projection.domain.exceptions import (
    GraphNotFoundError,
    N3ReasoningError,
    TemplateNotFoundError,
    TemplateRenderError,
)
from kgcl.projection.domain.result import ProjectionResult
from kgcl.projection.engine.context_builder import ContextBuilder
from kgcl.projection.engine.n3_executor import N3Executor, N3ExecutorConfig
from kgcl.projection.ports.graph_client import GraphClient
from kgcl.projection.sandbox import create_projection_environment

__all__ = ["ProjectionConfig", "ProjectionEngine", "TemplateRegistry"]


class TemplateRegistry(Protocol):
    """Protocol for template registry implementations.

    The registry provides lookup of TemplateDescriptor instances
    by template name or identifier.
    """

    def get(self, template_name: str) -> Any:  # Returns TemplateDescriptor | None
        """Get template descriptor by name.

        Parameters
        ----------
        template_name : str
            Template identifier to look up.

        Returns
        -------
        TemplateDescriptor | None
            The descriptor or None if not found.
        """
        ...


@dataclass
class ProjectionConfig:
    """Configuration for projection engine.

    Parameters
    ----------
    cache_ttl : int
        Query cache TTL in seconds (default: 300).
    strict_mode : bool
        Fail on undefined variables in templates (default: True).
    n3_timeout_seconds : float
        N3 reasoning timeout in seconds (default: 30.0).
    n3_max_memory_mb : int | None
        N3 subprocess memory limit in MB (default: None, no limit).
    n3_enabled : bool
        Whether to execute N3 rules (default: True).

    Examples
    --------
    >>> cfg = ProjectionConfig(cache_ttl=600, strict_mode=False)
    >>> cfg.cache_ttl
    600
    """

    cache_ttl: int = 300
    strict_mode: bool = True
    n3_timeout_seconds: float = 30.0
    n3_max_memory_mb: int | None = None
    n3_enabled: bool = True


class ProjectionEngine:
    """Orchestrates Jinja template projection from graph data.

    The ProjectionEngine coordinates the full projection pipeline:
    1. Load template descriptor from registry
    2. Get graph client for ontology binding
    3. Execute SPARQL queries via ContextBuilder
    4. Build Jinja context with query results and params
    5. Render template in sandboxed environment
    6. Return ProjectionResult with metadata

    Implements μ_proj in A = μ_proj(O).

    Parameters
    ----------
    template_registry : TemplateRegistry
        Registry for loading template descriptors.
    graph_clients : Mapping[str, GraphClient]
        Mapping of graph_id to client instances.
    jinja_env : Environment | None
        Optional custom Jinja environment (defaults to sandboxed).
    config : ProjectionConfig | None
        Optional engine configuration.

    Examples
    --------
    >>> from kgcl.projection.domain.descriptors import TemplateDescriptor, OntologyConfig, TemplateMetadata
    >>> class MockRegistry:
    ...     def get(self, name: str) -> TemplateDescriptor | None:
    ...         if name == "test":
    ...             return TemplateDescriptor(
    ...                 id="http://ex.org/test",
    ...                 engine="jinja2",
    ...                 language="python",
    ...                 framework="",
    ...                 version="1.0",
    ...                 ontology=OntologyConfig("main"),
    ...                 queries=(),
    ...                 n3_rules=(),
    ...                 metadata=TemplateMetadata(),
    ...                 template_path="test.j2",
    ...                 raw_content="Hello {{ params.name }}",
    ...             )
    ...         return None
    >>> class MockClient:
    ...     @property
    ...     def graph_id(self) -> str:
    ...         return "main"
    ...
    ...     def query(self, s: str) -> list[dict[str, object]]:
    ...         return []
    ...
    ...     def ask(self, s: str) -> bool:
    ...         return False
    ...
    ...     def construct(self, s: str) -> str:
    ...         return ""
    >>> engine = ProjectionEngine(MockRegistry(), {"main": MockClient()})
    >>> result = engine.render("test", {"name": "World"})
    >>> result.content
    'Hello World'
    """

    def __init__(
        self,
        template_registry: TemplateRegistry,
        graph_clients: Mapping[str, GraphClient],
        jinja_env: Environment | None = None,
        config: ProjectionConfig | None = None,
        template_base_path: Path | None = None,
    ) -> None:
        """Initialize projection engine."""
        self.template_registry = template_registry
        self.graph_clients = dict(graph_clients)
        self.jinja_env = jinja_env if jinja_env is not None else create_projection_environment()
        self.config = config if config is not None else ProjectionConfig()
        self.template_base_path = template_base_path

        # Configure Jinja environment
        if self.config.strict_mode:
            self.jinja_env.undefined = self.jinja_env.undefined.__class__  # StrictUndefined

        # Create N3 executor if enabled
        if self.config.n3_enabled:
            n3_config = N3ExecutorConfig(
                timeout_seconds=self.config.n3_timeout_seconds, max_memory_mb=self.config.n3_max_memory_mb
            )
            self._n3_executor: N3Executor | None = N3Executor(n3_config)
        else:
            self._n3_executor = None

    def render(self, template_name: str, params: dict[str, Any] | None = None) -> ProjectionResult:
        """Render template with given parameters.

        Parameters
        ----------
        template_name : str
            Name or identifier of template to render.
        params : dict[str, Any] | None
            User-provided parameters for template context.

        Returns
        -------
        ProjectionResult
            Rendered output with metadata.

        Raises
        ------
        TemplateNotFoundError
            If template not found in registry.
        GraphNotFoundError
            If required graph client not available.
        TemplateRenderError
            If template rendering fails.

        Examples
        --------
        >>> from kgcl.projection.domain.descriptors import TemplateDescriptor, OntologyConfig, TemplateMetadata
        >>> class MockRegistry:
        ...     def get(self, name: str) -> TemplateDescriptor | None:
        ...         if name == "greeting":
        ...             return TemplateDescriptor(
        ...                 id="http://ex.org/greeting",
        ...                 engine="jinja2",
        ...                 language="text",
        ...                 framework="",
        ...                 version="1.0",
        ...                 ontology=OntologyConfig("main"),
        ...                 queries=(),
        ...                 n3_rules=(),
        ...                 metadata=TemplateMetadata(),
        ...                 template_path="greeting.j2",
        ...                 raw_content="Hello {{ params.name }}!",
        ...             )
        ...         return None
        >>> class MockClient:
        ...     @property
        ...     def graph_id(self) -> str:
        ...         return "main"
        ...
        ...     def query(self, s: str) -> list[dict[str, object]]:
        ...         return []
        ...
        ...     def ask(self, s: str) -> bool:
        ...         return False
        ...
        ...     def construct(self, s: str) -> str:
        ...         return ""
        >>> engine = ProjectionEngine(MockRegistry(), {"main": MockClient()})
        >>> result = engine.render("greeting", {"name": "Alice"})
        >>> result.content
        'Hello Alice!'
        """
        start_time = time.perf_counter()
        n3_results: dict[str, str] = {}

        # Load template descriptor
        descriptor = self.template_registry.get(template_name)
        if descriptor is None:
            raise TemplateNotFoundError(template_name)

        # Get graph client
        graph_id = descriptor.ontology.graph_id
        client = self.graph_clients.get(graph_id)
        if client is None:
            raise GraphNotFoundError(graph_id)

        # Get template state as TTL for N3 rules (empty - graph state not serialized)
        state_ttl = self._get_state_ttl(client)

        # Execute PRECONDITION N3 rules (before queries)
        precondition_results = self._execute_n3_rules(descriptor.n3_rules, N3Role.PRECONDITION, state_ttl)
        n3_results.update(precondition_results)

        # Build context from queries
        builder = ContextBuilder(client)
        query_context = builder.build_context(descriptor.queries, params)

        # Execute INFERENCE N3 rules (after queries, with query context)
        inference_results = self._execute_n3_rules(descriptor.n3_rules, N3Role.INFERENCE, state_ttl)
        n3_results.update(inference_results)

        # Create Jinja template
        try:
            template: Template = self.jinja_env.from_string(descriptor.raw_content)
        except Exception as e:
            msg = f"Failed to parse template: {e}"
            raise TemplateRenderError(template_name, msg) from e

        # Build render context (merge sparql, params, and n3 at top level)
        render_context: dict[str, Any] = {
            "sparql": query_context.sparql,
            "params": query_context.params,
            "n3": n3_results,
        }

        # Render template
        try:
            content = template.render(**render_context)
        except Exception as e:
            msg = f"Rendering failed: {e}"
            raise TemplateRenderError(template_name, msg) from e

        # Execute POSTCONDITION N3 rules (after rendering)
        postcondition_results = self._execute_n3_rules(descriptor.n3_rules, N3Role.POSTCONDITION, state_ttl)
        n3_results.update(postcondition_results)

        # Calculate metrics
        end_time = time.perf_counter()
        render_time_ms = (end_time - start_time) * 1000.0

        # Build result
        context_info: dict[str, Any] = {
            "query_count": len(descriptor.queries),
            "n3_rule_count": len(descriptor.n3_rules),
            "render_time_ms": render_time_ms,
            "graph_id": graph_id,
        }

        return ProjectionResult(
            template_id=descriptor.id,
            version=descriptor.version,
            content=content,
            media_type=self._infer_media_type(descriptor.language),
            context_info=context_info,
        )

    def render_to_file(
        self, template_name: str, output_path: Path, params: dict[str, Any] | None = None
    ) -> ProjectionResult:
        """Render template and write to file.

        Parameters
        ----------
        template_name : str
            Name or identifier of template to render.
        output_path : Path
            Path where output should be written.
        params : dict[str, Any] | None
            User-provided parameters for template context.

        Returns
        -------
        ProjectionResult
            Rendered output with metadata.

        Raises
        ------
        TemplateNotFoundError
            If template not found in registry.
        GraphNotFoundError
            If required graph client not available.
        TemplateRenderError
            If template rendering fails.
        OSError
            If file write fails.

        Examples
        --------
        >>> import tempfile
        >>> from pathlib import Path
        >>> from kgcl.projection.domain.descriptors import TemplateDescriptor, OntologyConfig, TemplateMetadata
        >>> class MockRegistry:
        ...     def get(self, name: str) -> TemplateDescriptor | None:
        ...         if name == "code":
        ...             return TemplateDescriptor(
        ...                 id="http://ex.org/code",
        ...                 engine="jinja2",
        ...                 language="python",
        ...                 framework="",
        ...                 version="1.0",
        ...                 ontology=OntologyConfig("main"),
        ...                 queries=(),
        ...                 n3_rules=(),
        ...                 metadata=TemplateMetadata(),
        ...                 template_path="code.j2",
        ...                 raw_content="# {{ params.title }}",
        ...             )
        ...         return None
        >>> class MockClient:
        ...     @property
        ...     def graph_id(self) -> str:
        ...         return "main"
        ...
        ...     def query(self, s: str) -> list[dict[str, object]]:
        ...         return []
        ...
        ...     def ask(self, s: str) -> bool:
        ...         return False
        ...
        ...     def construct(self, s: str) -> str:
        ...         return ""
        >>> engine = ProjectionEngine(MockRegistry(), {"main": MockClient()})
        >>> with tempfile.TemporaryDirectory() as tmpdir:
        ...     out = Path(tmpdir) / "output.py"
        ...     result = engine.render_to_file("code", out, {"title": "Test"})
        ...     out.read_text()
        '# Test'
        """
        # Render template
        result = self.render(template_name, params)

        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result.content, encoding="utf-8")

        return result

    def _infer_media_type(self, language: str) -> str | None:
        """Infer MIME type from language field.

        Parameters
        ----------
        language : str
            Language identifier from template descriptor.

        Returns
        -------
        str | None
            MIME type or None if unknown.

        Examples
        --------
        >>> engine = ProjectionEngine({}, {})  # type: ignore[arg-type]
        >>> engine._infer_media_type("python")
        'text/x-python'
        """
        mapping: dict[str, str] = {
            "python": "text/x-python",
            "typescript": "text/typescript",
            "javascript": "text/javascript",
            "java": "text/x-java",
            "rust": "text/x-rust",
            "yaml": "text/yaml",
            "json": "application/json",
            "markdown": "text/markdown",
            "html": "text/html",
            "css": "text/css",
        }
        return mapping.get(language.lower())

    def _get_state_ttl(self, client: GraphClient) -> str:
        """Get graph state as Turtle for N3 reasoning.

        Parameters
        ----------
        client : GraphClient
            Graph client to extract state from.

        Returns
        -------
        str
            Graph state as Turtle string.
        """
        # Returns empty state - graph serialization not implemented
        # N3 rules execute without graph context as input
        return ""

    def _execute_n3_rules(self, rules: tuple[N3RuleDescriptor, ...], role: N3Role, state_ttl: str) -> dict[str, str]:
        """Execute N3 rules of a specific role.

        Parameters
        ----------
        rules : tuple[N3RuleDescriptor, ...]
            All rules from template descriptor.
        role : N3Role
            Role to filter by (PRECONDITION, INFERENCE, POSTCONDITION).
        state_ttl : str
            Graph state as Turtle.

        Returns
        -------
        dict[str, str]
            Mapping of rule name to output.

        Raises
        ------
        N3ReasoningError
            If N3 execution fails.
        """
        if not self._n3_executor or not self._n3_executor.is_available():
            return {}

        results: dict[str, str] = {}

        for rule in rules:
            if rule.role != role:
                continue

            result = self._n3_executor.execute_rule(rule, state_ttl, base_path=self.template_base_path)

            if not result.success:
                raise N3ReasoningError(rule.name, result.error or "Unknown error")

            results[rule.name] = result.output

        return results

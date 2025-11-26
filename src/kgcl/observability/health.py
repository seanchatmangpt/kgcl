"""Health check system for KGCL observability.

Provides health check endpoints and diagnostic commands for monitoring
system health and connectivity.
"""

from __future__ import annotations

import hashlib
import logging
import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from rdflib import Graph

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health check status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """Health status of a system component.

    Attributes
    ----------
    name : str
        Component name
    status : HealthStatus
        Health status
    message : str
        Status message
    details : dict[str, Any]
        Additional details
    check_duration_ms : float
        Duration of health check in milliseconds

    """

    name: str
    status: HealthStatus
    message: str
    details: dict[str, Any]
    check_duration_ms: float


@dataclass
class SystemHealth:
    """Overall system health status.

    Attributes
    ----------
    status : HealthStatus
        Overall status
    components : list[ComponentHealth]
        Individual component health statuses
    timestamp : float
        Timestamp of health check

    """

    status: HealthStatus
    components: list[ComponentHealth]
    timestamp: float

    @property
    def is_healthy(self) -> bool:
        """Check if system is healthy."""
        return self.status == HealthStatus.HEALTHY

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns
        -------
        dict[str, Any]
            Dictionary representation

        """
        return {
            "status": self.status.value,
            "timestamp": self.timestamp,
            "components": [
                {
                    "name": comp.name,
                    "status": comp.status.value,
                    "message": comp.message,
                    "details": comp.details,
                    "check_duration_ms": comp.check_duration_ms,
                }
                for comp in self.components
            ],
        }


class HealthChecker:
    """Health checker for KGCL system components."""

    def __init__(self) -> None:
        """Initialize health checker."""
        self._checks: dict[str, Any] = {}

    def register_check(self, name: str, check_fn: Any) -> None:
        """Register a health check function.

        Parameters
        ----------
        name : str
            Component name
        check_fn : callable
            Health check function that returns (bool, str, dict)

        """
        self._checks[name] = check_fn

    def check_component(self, name: str) -> ComponentHealth:
        """Check health of a specific component.

        Parameters
        ----------
        name : str
            Component name

        Returns
        -------
        ComponentHealth
            Component health status

        """
        start_time = time.perf_counter()

        if name not in self._checks:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"No health check registered for {name}",
                details={},
                check_duration_ms=0.0,
            )

        try:
            is_healthy, message, details = self._checks[name]()
            duration_ms = (time.perf_counter() - start_time) * 1000

            status = HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY

            return ComponentHealth(
                name=name, status=status, message=message, details=details, check_duration_ms=duration_ms
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.exception(f"Health check failed for {name}")

            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check error: {e!s}",
                details={"error": str(e)},
                check_duration_ms=duration_ms,
            )

    def check_all(self) -> SystemHealth:
        """Check health of all registered components.

        Returns
        -------
        SystemHealth
            Overall system health

        """
        timestamp = time.time()
        components = [self.check_component(name) for name in self._checks]

        # Determine overall status
        if all(c.status == HealthStatus.HEALTHY for c in components):
            overall_status = HealthStatus.HEALTHY
        elif any(c.status == HealthStatus.UNHEALTHY for c in components):
            overall_status = HealthStatus.UNHEALTHY
        else:
            overall_status = HealthStatus.DEGRADED

        return SystemHealth(status=overall_status, components=components, timestamp=timestamp)


# Global health checker instance
_health_checker = HealthChecker()


def register_health_check(name: str, check_fn: Any) -> None:
    """Register a health check function.

    Parameters
    ----------
    name : str
        Component name
    check_fn : callable
        Health check function

    """
    _health_checker.register_check(name, check_fn)


def check_health() -> SystemHealth:
    """Check health of all system components.

    Returns
    -------
    SystemHealth
        Overall system health

    """
    return _health_checker.check_all()


def check_ollama_connectivity() -> tuple[bool, str, dict[str, Any]]:
    """Check connectivity to Ollama service.

    Returns
    -------
    tuple[bool, str, dict[str, Any]]
        (is_healthy, message, details)

    """
    try:
        import requests

        # Try to connect to Ollama
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        response.raise_for_status()

        models = response.json().get("models", [])

        return (True, f"Connected to Ollama ({len(models)} models available)", {"models": [m["name"] for m in models]})
    except requests.exceptions.ConnectionError:
        return (False, "Cannot connect to Ollama service", {"endpoint": "http://localhost:11434"})
    except Exception as e:
        return (False, f"Ollama health check failed: {e!s}", {"error": str(e)})


def check_graph_integrity() -> tuple[bool, str, dict[str, Any]]:
    """Check RDF graph integrity.

    Returns
    -------
    tuple[bool, str, dict[str, Any]]
        (is_healthy, message, details)

    """
    graph_path, search_paths = _resolve_graph_file()
    search_paths_str = [str(path) for path in search_paths]
    if graph_path is None:
        details = {"error": "graph_file_not_configured", "search_paths": search_paths_str}
        return (False, "Graph file not configured", details)

    if not graph_path.exists():
        details = {"error": "graph_file_not_found", "graph_file": str(graph_path), "search_paths": search_paths_str}
        return (False, "Configured graph file not found", details)

    try:
        graph = Graph()
        parse_kwargs = {}
        if graph_format := _infer_graph_format(graph_path):
            parse_kwargs["format"] = graph_format
        graph.parse(graph_path, **parse_kwargs)
    except Exception as exc:
        details = {"error": str(exc), "graph_file": str(graph_path), "search_paths": search_paths_str}
        return (False, "Failed to parse graph file", details)

    triple_count = len(graph)
    details = _build_graph_metrics(graph, graph_path, search_paths_str)

    if triple_count == 0:
        return (False, "Graph contains no triples", details)

    try:
        graph.query("ASK { ?s ?p ?o }")
    except Exception as exc:
        details["error"] = str(exc)
        return (False, "Graph query execution failed", details)

    warnings: list[str] = []
    namespaces = details.get("namespaces", {})
    if "sh" not in namespaces:
        warnings.append("SHACL namespace not declared")
    if not any("unrdf" in uri for uri in namespaces.values()):
        warnings.append("UNRDF namespace not declared")

    if warnings:
        details["warnings"] = warnings
        message = f"Graph integrity check passed with warnings ({triple_count} triples)"
    else:
        message = f"Graph integrity check passed ({triple_count} triples)"

    return (True, message, details)


def check_observability() -> tuple[bool, str, dict[str, Any]]:
    """Check observability configuration.

    Returns
    -------
    tuple[bool, str, dict[str, Any]]
        (is_healthy, message, details)

    """
    from kgcl.observability.config import ObservabilityConfig

    config = ObservabilityConfig.from_env()

    details = {
        "tracing_enabled": config.enable_tracing,
        "metrics_enabled": config.enable_metrics,
        "logging_enabled": config.enable_logging,
        "environment": config.environment.value,
    }

    if not (config.enable_tracing or config.enable_metrics or config.enable_logging):
        return (False, "All observability features are disabled", details)

    return (True, "Observability configured", details)


# Register default health checks
register_health_check("ollama", check_ollama_connectivity)
register_health_check("graph", check_graph_integrity)
register_health_check("observability", check_observability)


GRAPH_PATH_ENV = "KGCL_GRAPH_FILE"


def _resolve_graph_file() -> tuple[Path | None, list[Path]]:
    """Resolve graph file path from env/configured search locations."""
    search_paths: list[Path] = []

    env_path = os.getenv(GRAPH_PATH_ENV)
    if env_path:
        path = Path(env_path).expanduser()
        search_paths.append(path)
        return path, search_paths

    try:
        repo_root = Path(__file__).resolve().parents[3]
    except IndexError:
        repo_root = Path(__file__).resolve().parent

    candidates = [
        Path.cwd() / "graph.ttl",
        Path.home() / ".config" / "kgcl" / "graph.ttl",
        repo_root / "examples" / "sample_outputs" / "knowledge_graph.ttl",
    ]
    search_paths.extend(candidates)

    for candidate in candidates:
        if candidate.exists():
            return candidate, search_paths

    return None, search_paths


def _infer_graph_format(graph_path: Path) -> str | None:
    """Infer RDF serialization format from file extension."""
    suffix = graph_path.suffix.lower()
    return {
        ".ttl": "turtle",
        ".n3": "n3",
        ".nt": "nt",
        ".nq": "nquads",
        ".trig": "trig",
        ".xml": "xml",
        ".rdf": "xml",
    }.get(suffix)


def _compute_file_hash(graph_path: Path) -> str:
    """Compute SHA256 hash of the graph file for reproducibility."""
    hasher = hashlib.sha256()
    with graph_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _build_graph_metrics(graph: Graph, graph_path: Path, search_paths: list[str]) -> dict[str, Any]:
    """Build diagnostic metrics for the loaded RDF graph."""
    stat_result = graph_path.stat()
    namespaces = {prefix: str(uri) for prefix, uri in graph.namespace_manager.namespaces()}
    return {
        "graph_file": str(graph_path),
        "search_paths": search_paths,
        "triples": len(graph),
        "unique_subjects": len(set(graph.subjects())),
        "unique_predicates": len(set(graph.predicates())),
        "unique_objects": len(set(graph.objects())),
        "namespace_count": len(namespaces),
        "namespaces": namespaces,
        "size_bytes": stat_result.st_size,
        "last_modified": datetime.fromtimestamp(stat_result.st_mtime, tz=UTC).isoformat(),
        "sha256": _compute_file_hash(graph_path),
    }

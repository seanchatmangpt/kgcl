"""Core YAWL engine types and namespaces.

This module provides shared types, namespaces, and base classes used across
all YAWL pattern implementations.

Examples
--------
>>> from rdflib import Graph, URIRef
>>> graph = Graph()
>>> result = ExecutionResult(
...     success=True,
...     task=URIRef("urn:task:ProcessOrder"),
...     updates=[("urn:task:ProcessOrder", "yawl:status", "completed")],
... )
>>> assert result.success
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rdflib import Namespace, URIRef

# ============================================================================
# YAWL RDF Namespaces
# ============================================================================


class YawlNamespace:
    """YAWL RDF namespace definitions.

    Attributes
    ----------
    YAWL : Namespace
        Main YAWL schema namespace
    YAWL_RESOURCE : Namespace
        Resource perspective namespace
    YAWL_EXEC : Namespace
        Execution semantics namespace
    YAWL_PATTERN : Namespace
        Workflow patterns namespace
    KGC : Namespace
        KGC extensions namespace

    Examples
    --------
    >>> from rdflib import Graph, Literal
    >>> graph = Graph()
    >>> task = URIRef("urn:task:T1")
    >>> graph.add((task, YawlNamespace.YAWL.status, Literal("completed")))
    """

    YAWL = Namespace("http://www.yawlfoundation.org/yawlschema#")
    YAWL_RESOURCE = Namespace("http://www.yawlfoundation.org/yawlschema/resource#")
    YAWL_EXEC = Namespace("http://bitflow.ai/ontology/yawl/execution/v1#")
    YAWL_PATTERN = Namespace("http://bitflow.ai/ontology/yawl/patterns/v1#")
    KGC = Namespace("https://kgc.org/ns/")


# ============================================================================
# Execution Result Types
# ============================================================================


@dataclass(frozen=True)
class ExecutionResult:
    """Immutable result of YAWL pattern execution.

    This is the canonical result type returned by all pattern execute() methods.
    It captures whether execution succeeded, what task was executed, and any
    RDF updates or data mutations that occurred.

    Parameters
    ----------
    success : bool
        Whether execution succeeded
    task : URIRef
        Task that was executed
    updates : list[tuple[str, str, str]]
        RDF triples added during execution (subject, predicate, object)
    data_updates : dict[str, Any]
        Workflow data variable updates
    error : str | None
        Error message if execution failed

    Examples
    --------
    >>> from rdflib import URIRef
    >>> result = ExecutionResult(
    ...     success=True,
    ...     task=URIRef("urn:task:ApproveRequest"),
    ...     updates=[
    ...         ("urn:task:ApproveRequest", "yawl:status", "completed"),
    ...         ("urn:task:ApproveRequest", "yawl:completedBy", "user:alice"),
    ...     ],
    ...     data_updates={"approval_status": "approved"},
    ... )
    >>> assert result.success
    >>> assert len(result.updates) == 2
    """

    success: bool
    task: URIRef
    updates: list[tuple[str, str, str]] = field(default_factory=list)
    data_updates: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

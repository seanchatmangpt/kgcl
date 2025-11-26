"""Blood-Brain Barrier (BBB) Ingress Layer.

This module implements the Active Transport mechanism that converts external
JSON payloads into validated RDF QuadDeltas for the Atman engine.

The BBB follows the "Validation IS Execution" principle:
- If data conforms to SHACL shapes, execution proceeds
- If data violates SHACL shapes, execution halts
- NO Python if-statements validate business logic

The Three Laws (invariants.shacl.ttl):
1. TYPING: Every node must have rdf:type
2. HERMETICITY: Only known predicates, max 64 ops/batch
3. CHRONOLOGY: Time flows forward, hashes chain correctly

Examples
--------
>>> from kgcl.ingress import BBBIngress, TopologyViolationError
>>>
>>> bbb = BBBIngress()
>>>
>>> # Valid payload passes through
>>> valid_payload = {
...     "additions": [
...         {"s": "urn:task:A", "p": "rdf:type", "o": "yawl:Task"},
...         {"s": "urn:task:A", "p": "yawl:id", "o": "task-a"},
...     ]
... }
>>> delta = bbb.ingest(valid_payload)
>>> len(delta.additions) == 2
True
>>>
>>> # Invalid payload is rejected
>>> invalid_payload = {"additions": [{"s": "urn:task:A", "p": "unknown:predicate", "o": "value"}]}
>>> try:
...     bbb.ingest(invalid_payload)
... except TopologyViolationError as e:
...     "HERMETICITY" in str(e)
True
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pyshacl import validate as shacl_validate
from rdflib import Graph, Literal, Namespace, URIRef

logger = logging.getLogger(__name__)

# Namespaces
KGC = Namespace("http://bitflow.ai/ontology/kgc/v3#")
YAWL = Namespace("http://www.yawlfoundation.org/yawlschema#")
RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")

# Path to invariants SHACL shapes
INVARIANTS_PATH = Path(__file__).parent.parent.parent.parent / "ontology" / "invariants.shacl.ttl"

# Chatman Constant: Maximum operations per batch
CHATMAN_CONSTANT = 64


class TopologyViolationError(Exception):
    """Raised when data violates SHACL topology constraints.

    This exception indicates that the input data cannot be processed
    because it violates one or more of the Three Laws:
    - TYPING: Missing rdf:type
    - HERMETICITY: Unknown predicates or batch too large
    - CHRONOLOGY: Time paradox or hash chain broken

    Attributes
    ----------
    violations : list[str]
        Human-readable violation messages from SHACL validation.
    law : str
        Which law was violated (TYPING, HERMETICITY, CHRONOLOGY).
    """

    def __init__(self, message: str, violations: list[str] | None = None, law: str = "UNKNOWN") -> None:
        """Initialize TopologyViolationError.

        Parameters
        ----------
        message : str
            Human-readable error message.
        violations : list[str] | None
            List of SHACL violation messages.
        law : str
            Which fundamental law was violated.
        """
        super().__init__(message)
        self.violations = violations or []
        self.law = law


@dataclass(frozen=True)
class Triple:
    """An RDF triple (subject, predicate, object).

    Attributes
    ----------
    subject : str
        Subject URI or blank node.
    predicate : str
        Predicate URI.
    object : str
        Object URI, literal, or blank node.
    """

    subject: str
    predicate: str
    object: str

    def to_tuple(self) -> tuple[str, str, str]:
        """Convert to tuple format for QuadDelta.

        Returns
        -------
        tuple[str, str, str]
            (subject, predicate, object) tuple.
        """
        return (self.subject, self.predicate, self.object)


@dataclass(frozen=True)
class QuadDelta:
    """The Observation (O) in the Chatman Equation A = μ(O).

    Represents intent to mutate the knowledge graph. Immutable once created.
    Enforces the Chatman Constant (max 64 operations per batch).

    Attributes
    ----------
    additions : tuple[Triple, ...]
        Triples to add to the graph.
    removals : tuple[Triple, ...]
        Triples to remove from the graph.
    """

    additions: tuple[Triple, ...]
    removals: tuple[Triple, ...]

    def __post_init__(self) -> None:
        """Validate Chatman Constant constraint."""
        total = len(self.additions) + len(self.removals)
        if total > CHATMAN_CONSTANT:
            msg = f"HERMETICITY VIOLATION: Batch size {total} exceeds Chatman Constant ({CHATMAN_CONSTANT})"
            raise TopologyViolationError(msg, law="HERMETICITY")


# SHACL Shapes Cache
_shapes_cache: dict[Path, Graph] = {}
_shapes_cache_lock = threading.Lock()


def _get_cached_shapes(shapes_path: Path) -> Graph:
    """Load SHACL shapes with caching.

    Thread-safe implementation using double-checked locking.

    Parameters
    ----------
    shapes_path : Path
        Path to SHACL shapes file.

    Returns
    -------
    Graph
        Parsed SHACL shapes graph.
    """
    if shapes_path in _shapes_cache:
        return _shapes_cache[shapes_path]

    with _shapes_cache_lock:
        if shapes_path in _shapes_cache:
            return _shapes_cache[shapes_path]

        logger.debug("Loading SHACL shapes from %s", shapes_path)
        shapes = Graph()
        shapes.parse(shapes_path, format="turtle")
        _shapes_cache[shapes_path] = shapes
        return shapes


def _expand_prefix(uri: str) -> str:
    """Expand common prefixes to full URIs.

    Parameters
    ----------
    uri : str
        URI that may contain prefixes like "rdf:", "yawl:", "kgc:".

    Returns
    -------
    str
        Full URI with prefix expanded.
    """
    prefixes = {
        "rdf:": str(RDF),
        "rdfs:": "http://www.w3.org/2000/01/rdf-schema#",
        "yawl:": str(YAWL),
        "kgc:": str(KGC),
        "xsd:": "http://www.w3.org/2001/XMLSchema#",
        "owl:": "http://www.w3.org/2002/07/owl#",
    }

    for prefix, namespace in prefixes.items():
        if uri.startswith(prefix):
            return namespace + uri[len(prefix) :]

    return uri


def _to_rdf_term(value: str) -> URIRef | Literal:
    """Convert string to RDF term (URIRef or Literal).

    Heuristic: If it looks like a URI (contains :// or :), treat as URIRef.
    Otherwise, treat as Literal.

    Parameters
    ----------
    value : str
        String value to convert.

    Returns
    -------
    URIRef | Literal
        Appropriate RDF term.
    """
    expanded = _expand_prefix(value)
    if "://" in expanded or expanded.startswith("urn:"):
        return URIRef(expanded)
    if ":" in value and not value.startswith('"'):
        return URIRef(expanded)
    return Literal(value)


def lift_json_to_quads(payload: dict[str, Any]) -> QuadDelta:
    """Convert JSON payload to QuadDelta (LIFT phase).

    This is the first phase of the BBB: converting external JSON
    into internal RDF representation.

    Parameters
    ----------
    payload : dict[str, Any]
        JSON payload with "additions" and/or "removals" arrays.
        Each item must have "s", "p", "o" keys.

    Returns
    -------
    QuadDelta
        Validated delta ready for SHACL screening.

    Raises
    ------
    TopologyViolationError
        If payload structure is invalid or exceeds Chatman Constant.

    Examples
    --------
    >>> payload = {"additions": [{"s": "urn:task:A", "p": "rdf:type", "o": "yawl:Task"}]}
    >>> delta = lift_json_to_quads(payload)
    >>> len(delta.additions) == 1
    True
    """
    additions: list[Triple] = []
    removals: list[Triple] = []

    for item in payload.get("additions", []):
        if not all(k in item for k in ("s", "p", "o")):
            msg = f"TYPING VIOLATION: Triple missing s/p/o keys: {item}"
            raise TopologyViolationError(msg, law="TYPING")
        additions.append(Triple(subject=item["s"], predicate=item["p"], object=item["o"]))

    for item in payload.get("removals", []):
        if not all(k in item for k in ("s", "p", "o")):
            msg = f"TYPING VIOLATION: Triple missing s/p/o keys: {item}"
            raise TopologyViolationError(msg, law="TYPING")
        removals.append(Triple(subject=item["s"], predicate=item["p"], object=item["o"]))

    return QuadDelta(additions=tuple(additions), removals=tuple(removals))


def validate_topology(delta: QuadDelta, shapes_path: Path | None = None) -> tuple[bool, list[str]]:
    """Validate QuadDelta against SHACL shapes (SCREEN phase).

    This is the second phase of the BBB: checking that the proposed
    mutations conform to the Three Laws encoded in invariants.shacl.ttl.

    Parameters
    ----------
    delta : QuadDelta
        The delta to validate.
    shapes_path : Path | None
        Path to SHACL shapes file. Defaults to invariants.shacl.ttl.

    Returns
    -------
    tuple[bool, list[str]]
        (conforms, violations) where conforms is True if valid,
        and violations is a list of error messages.

    Examples
    --------
    >>> delta = QuadDelta(additions=(Triple("urn:task:A", "rdf:type", "yawl:Task"),), removals=())
    >>> conforms, violations = validate_topology(delta)
    >>> conforms
    True
    """
    if shapes_path is None:
        shapes_path = INVARIANTS_PATH

    # Build data graph from delta
    data_graph = Graph()
    for triple in delta.additions:
        s = _to_rdf_term(triple.subject)
        p = URIRef(_expand_prefix(triple.predicate))
        o = _to_rdf_term(triple.object)
        data_graph.add((s, p, o))

    # Get cached shapes
    shapes_graph = _get_cached_shapes(shapes_path)

    # Run SHACL validation
    conforms, results_graph, results_text = shacl_validate(
        data_graph=data_graph, shacl_graph=shapes_graph, inference="rdfs", abort_on_first=False
    )

    violations: list[str] = []
    if not conforms:
        # Extract violation messages from results graph
        for line in results_text.split("\n"):
            line = line.strip()
            if line and "Violation" in line:
                violations.append(line)
            elif line and "Message:" in line:
                violations.append(line.replace("Message:", "").strip())

    return conforms, violations


class BBBIngress:
    """Blood-Brain Barrier Ingress Layer.

    Implements Active Transport: LIFT → SCREEN → PASS/REJECT.

    The BBB is the gatekeeper between the outside world (JSON) and
    the knowledge graph (RDF). It ensures that only valid topology
    can enter the system.

    Attributes
    ----------
    shapes_path : Path
        Path to SHACL shapes file for validation.

    Examples
    --------
    >>> bbb = BBBIngress()
    >>>
    >>> # Ingest JSON payload
    >>> payload = {
    ...     "additions": [
    ...         {"s": "urn:task:A", "p": "rdf:type", "o": "yawl:Task"},
    ...         {"s": "urn:task:A", "p": "yawl:id", "o": "task-a"},
    ...     ]
    ... }
    >>> delta = bbb.ingest(payload)
    >>> len(delta.additions) == 2
    True
    """

    def __init__(self, shapes_path: Path | None = None) -> None:
        """Initialize BBB Ingress.

        Parameters
        ----------
        shapes_path : Path | None
            Path to SHACL shapes file. Defaults to invariants.shacl.ttl.
        """
        self.shapes_path = shapes_path or INVARIANTS_PATH

    def ingest(self, payload: dict[str, Any]) -> QuadDelta:
        """Ingest JSON payload through the Blood-Brain Barrier.

        Performs the full BBB pipeline:
        1. LIFT: Convert JSON to QuadDelta
        2. SCREEN: Validate against SHACL shapes
        3. PASS/REJECT: Return delta or raise exception

        Parameters
        ----------
        payload : dict[str, Any]
            JSON payload with "additions" and/or "removals".

        Returns
        -------
        QuadDelta
            Validated delta ready for Atman processing.

        Raises
        ------
        TopologyViolationError
            If payload violates any of the Three Laws.
        """
        # Phase 1: LIFT
        logger.debug("BBB LIFT: Converting JSON to QuadDelta")
        delta = lift_json_to_quads(payload)

        # Phase 2: SCREEN
        logger.debug("BBB SCREEN: Validating against SHACL shapes")
        conforms, violations = validate_topology(delta, self.shapes_path)

        # Phase 3: PASS or REJECT
        if not conforms:
            # Determine which law was violated
            law = "UNKNOWN"
            for v in violations:
                if "TYPING" in v:
                    law = "TYPING"
                    break
                if "HERMETICITY" in v:
                    law = "HERMETICITY"
                    break
                if "CHRONOLOGY" in v:
                    law = "CHRONOLOGY"
                    break

            msg = f"BBB REJECT: Topology violates {law} law"
            logger.warning(msg)
            raise TopologyViolationError(msg, violations=violations, law=law)

        logger.debug("BBB PASS: Topology conforms to Three Laws")
        return delta

    def ingest_json_string(self, json_string: str) -> QuadDelta:
        """Ingest JSON string through the Blood-Brain Barrier.

        Convenience method that parses JSON string before ingestion.

        Parameters
        ----------
        json_string : str
            JSON string representing the payload.

        Returns
        -------
        QuadDelta
            Validated delta.

        Raises
        ------
        TopologyViolationError
            If payload violates any of the Three Laws.
        json.JSONDecodeError
            If JSON string is malformed.
        """
        payload = json.loads(json_string)
        return self.ingest(payload)

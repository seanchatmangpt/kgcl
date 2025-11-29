"""UNRDF adapter for YAWL workflow events.

Bridges YAWL workflow execution with UNRDF knowledge hooks.
Converts YAWL events to UNRDF hook format for knowledge-driven workflows.

Key Features:
    - Convert YAWL events to UNRDF hook events
    - Store YAWL execution state in RDF graphs
    - Trigger UNRDF hooks on workflow state changes
    - Support provenance tracking with PROV-O

Java Parity:
    - Maps to Java YAWL engine event system
    - Supports same event types as Java implementation
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class YAWLEventType(Enum):
    """YAWL workflow event types.

    Maps to Java YAWL engine event system.

    Parameters
    ----------
    value : str
        Event type identifier

    Examples
    --------
    >>> event_type = YAWLEventType.CASE_STARTED
    >>> event_type.value
    'case_started'
    """

    CASE_STARTED = "case_started"
    CASE_COMPLETED = "case_completed"
    CASE_CANCELLED = "case_cancelled"
    CASE_SUSPENDED = "case_suspended"
    CASE_RESUMED = "case_resumed"

    TASK_ENABLED = "task_enabled"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_CANCELLED = "task_cancelled"
    TASK_FAILED = "task_failed"
    TASK_TIMED_OUT = "task_timed_out"

    WORKITEM_CREATED = "workitem_created"
    WORKITEM_ALLOCATED = "workitem_allocated"
    WORKITEM_STARTED = "workitem_started"
    WORKITEM_COMPLETED = "workitem_completed"
    WORKITEM_CANCELLED = "workitem_cancelled"

    TOKEN_CREATED = "token_created"
    TOKEN_MOVED = "token_moved"
    TOKEN_CONSUMED = "token_consumed"
    TOKEN_SPLIT = "token_split"
    TOKEN_JOINED = "token_joined"

    VARIABLE_CHANGED = "variable_changed"
    TIMER_FIRED = "timer_fired"
    EXCEPTION_RAISED = "exception_raised"


@dataclass(frozen=True)
class YAWLEvent:
    """YAWL workflow event.

    Represents a state change in the workflow engine.

    Parameters
    ----------
    event_type : YAWLEventType
        Type of event
    case_id : str
        Case identifier
    timestamp : float
        Event timestamp (Unix epoch)
    spec_id : str
        Specification identifier
    task_id : str
        Task identifier (if applicable)
    workitem_id : str
        Work item identifier (if applicable)
    data : dict[str, Any]
        Event data payload

    Examples
    --------
    >>> event = YAWLEvent(
    ...     event_type=YAWLEventType.TASK_COMPLETED,
    ...     case_id="case-001",
    ...     timestamp=time.time(),
    ...     spec_id="maketrip",
    ...     task_id="register",
    ... )
    """

    event_type: YAWLEventType
    case_id: str
    timestamp: float
    spec_id: str = ""
    task_id: str = ""
    workitem_id: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary.

        Returns
        -------
        dict[str, Any]
            Event as dictionary
        """
        return {
            "event_type": self.event_type.value,
            "case_id": self.case_id,
            "timestamp": self.timestamp,
            "spec_id": self.spec_id,
            "task_id": self.task_id,
            "workitem_id": self.workitem_id,
            "data": self.data,
        }


@dataclass(frozen=True)
class UNRDFHookEvent:
    """UNRDF hook event format.

    Compatible with UNRDF knowledge engine hook system.

    Parameters
    ----------
    name : str
        Hook name
    payload : dict[str, Any]
        Event payload
    context : dict[str, Any]
        Execution context

    Examples
    --------
    >>> hook_event = UNRDFHookEvent(
    ...     name="yawl:task_completed", payload={"task_id": "register"}, context={"graph": "yawl:execution"}
    ... )
    """

    name: str
    payload: dict[str, Any]
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to UNRDF hook event format.

        Returns
        -------
        dict[str, Any]
            Hook event as dictionary
        """
        return {"name": self.name, "payload": self.payload, "context": self.context}


@dataclass(frozen=True)
class ProvenanceRecord:
    """PROV-O provenance record.

    Tracks workflow execution for audit and traceability.

    Parameters
    ----------
    entity_id : str
        Entity being tracked
    activity_id : str
        Activity that generated/used entity
    agent_id : str
        Agent responsible for activity
    timestamp : float
        Record timestamp
    generation_time : float | None
        When entity was generated
    usage_time : float | None
        When entity was used
    attributes : dict[str, Any]
        Additional provenance attributes

    Examples
    --------
    >>> record = ProvenanceRecord(
    ...     entity_id="workitem:001", activity_id="task:register", agent_id="user:admin", timestamp=time.time()
    ... )
    """

    entity_id: str
    activity_id: str
    agent_id: str
    timestamp: float
    generation_time: float | None = None
    usage_time: float | None = None
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class UNRDFAdapter:
    """Adapter for YAWL-UNRDF integration.

    Converts YAWL workflow events to UNRDF hook events
    and manages RDF graph storage for workflow state.

    Parameters
    ----------
    base_uri : str
        Base URI for generated RDF
    graph_name : str
        Named graph for workflow data

    Examples
    --------
    >>> adapter = UNRDFAdapter()
    >>> event = YAWLEvent(event_type=YAWLEventType.TASK_COMPLETED, case_id="case-001", timestamp=time.time())
    >>> hook_event = adapter.yawl_to_hook(event)
    >>> hook_event.name
    'yawl:task_completed'
    """

    base_uri: str = "http://kgcl.dev/yawl/execution/"
    graph_name: str = "http://kgcl.dev/graph/yawl/execution"

    # RDF namespaces
    YAWL_NS: str = "http://kgcl.dev/ontology/yawl/core/v1#"
    PROV_NS: str = "http://www.w3.org/ns/prov#"
    XSD_NS: str = "http://www.w3.org/2001/XMLSchema#"
    RDF_NS: str = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"

    _event_history: list[YAWLEvent] = field(default_factory=list)
    _provenance: list[ProvenanceRecord] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Initialize adapter state."""
        if not hasattr(self, "_event_history") or self._event_history is None:
            object.__setattr__(self, "_event_history", [])
        if not hasattr(self, "_provenance") or self._provenance is None:
            object.__setattr__(self, "_provenance", [])

    def yawl_to_hook(self, event: YAWLEvent) -> UNRDFHookEvent:
        """Convert YAWL event to UNRDF hook event.

        Parameters
        ----------
        event : YAWLEvent
            YAWL workflow event

        Returns
        -------
        UNRDFHookEvent
            UNRDF hook event format
        """
        hook_name = f"yawl:{event.event_type.value}"

        payload = {
            "case_id": event.case_id,
            "spec_id": event.spec_id,
            "timestamp": event.timestamp,
            "event_type": event.event_type.value,
        }

        if event.task_id:
            payload["task_id"] = event.task_id
        if event.workitem_id:
            payload["workitem_id"] = event.workitem_id
        if event.data:
            payload["data"] = event.data

        context = {
            "graph": self.graph_name,
            "base_uri": self.base_uri,
            "namespaces": {"yawl": self.YAWL_NS, "prov": self.PROV_NS, "xsd": self.XSD_NS},
        }

        return UNRDFHookEvent(name=hook_name, payload=payload, context=context)

    def hook_to_yawl(self, hook_event: UNRDFHookEvent) -> YAWLEvent | None:
        """Convert UNRDF hook event to YAWL event.

        Parameters
        ----------
        hook_event : UNRDFHookEvent
            UNRDF hook event

        Returns
        -------
        YAWLEvent | None
            YAWL event or None if not a YAWL hook
        """
        if not hook_event.name.startswith("yawl:"):
            return None

        event_type_str = hook_event.name.replace("yawl:", "")
        try:
            event_type = YAWLEventType(event_type_str)
        except ValueError:
            return None

        payload = hook_event.payload
        return YAWLEvent(
            event_type=event_type,
            case_id=payload.get("case_id", ""),
            timestamp=payload.get("timestamp", time.time()),
            spec_id=payload.get("spec_id", ""),
            task_id=payload.get("task_id", ""),
            workitem_id=payload.get("workitem_id", ""),
            data=payload.get("data", {}),
        )

    def record_event(self, event: YAWLEvent) -> None:
        """Record event in history.

        Parameters
        ----------
        event : YAWLEvent
            Event to record
        """
        self._event_history.append(event)

    def get_event_history(self, case_id: str | None = None) -> list[YAWLEvent]:
        """Get event history.

        Parameters
        ----------
        case_id : str | None
            Filter by case ID

        Returns
        -------
        list[YAWLEvent]
            List of events
        """
        if case_id is None:
            return list(self._event_history)
        return [e for e in self._event_history if e.case_id == case_id]

    def add_provenance(self, event: YAWLEvent, agent_id: str = "system") -> ProvenanceRecord:
        """Create provenance record for event.

        Parameters
        ----------
        event : YAWLEvent
            Source event
        agent_id : str
            Agent identifier

        Returns
        -------
        ProvenanceRecord
            Provenance record
        """
        entity_id = f"{self.base_uri}event/{event.case_id}/{event.timestamp}"
        activity_id = f"{self.base_uri}activity/{event.event_type.value}"

        record = ProvenanceRecord(
            entity_id=entity_id,
            activity_id=activity_id,
            agent_id=f"{self.base_uri}agent/{agent_id}",
            timestamp=event.timestamp,
            generation_time=event.timestamp,
            attributes={"event_type": event.event_type.value, "case_id": event.case_id, "task_id": event.task_id},
        )
        self._provenance.append(record)
        return record

    def get_provenance(self, case_id: str | None = None) -> list[ProvenanceRecord]:
        """Get provenance records.

        Parameters
        ----------
        case_id : str | None
            Filter by case ID

        Returns
        -------
        list[ProvenanceRecord]
            List of provenance records
        """
        if case_id is None:
            return list(self._provenance)
        return [p for p in self._provenance if p.attributes.get("case_id") == case_id]

    def event_to_rdf(self, event: YAWLEvent) -> list[tuple[str, str, str, str]]:
        """Convert event to RDF quads.

        Parameters
        ----------
        event : YAWLEvent
            Event to convert

        Returns
        -------
        list[tuple[str, str, str, str]]
            List of (subject, predicate, object, graph) tuples
        """
        event_uri = f"{self.base_uri}event/{event.case_id}/{int(event.timestamp * 1000)}"
        graph = self.graph_name
        quads = []

        # Type
        quads.append((event_uri, f"{self.RDF_NS}type", f"{self.YAWL_NS}YEvent", graph))

        # Event type
        quads.append((event_uri, f"{self.YAWL_NS}eventType", event.event_type.value, graph))

        # Case ID
        quads.append((event_uri, f"{self.YAWL_NS}caseId", event.case_id, graph))

        # Timestamp
        quads.append((event_uri, f"{self.PROV_NS}generatedAtTime", f"{event.timestamp}^^{self.XSD_NS}double", graph))

        # Optional fields
        if event.spec_id:
            quads.append((event_uri, f"{self.YAWL_NS}specificationId", event.spec_id, graph))
        if event.task_id:
            quads.append((event_uri, f"{self.YAWL_NS}taskId", event.task_id, graph))
        if event.workitem_id:
            quads.append((event_uri, f"{self.YAWL_NS}workItemId", event.workitem_id, graph))

        return quads

    def provenance_to_rdf(self, record: ProvenanceRecord) -> list[tuple[str, str, str, str]]:
        """Convert provenance record to RDF quads.

        Parameters
        ----------
        record : ProvenanceRecord
            Provenance record

        Returns
        -------
        list[tuple[str, str, str, str]]
            List of (subject, predicate, object, graph) quads
        """
        graph = self.graph_name
        quads = []

        # Entity
        quads.append((record.entity_id, f"{self.RDF_NS}type", f"{self.PROV_NS}Entity", graph))

        # Activity
        quads.append((record.activity_id, f"{self.RDF_NS}type", f"{self.PROV_NS}Activity", graph))

        # Agent
        quads.append((record.agent_id, f"{self.RDF_NS}type", f"{self.PROV_NS}Agent", graph))

        # wasGeneratedBy
        quads.append((record.entity_id, f"{self.PROV_NS}wasGeneratedBy", record.activity_id, graph))

        # wasAssociatedWith
        quads.append((record.activity_id, f"{self.PROV_NS}wasAssociatedWith", record.agent_id, graph))

        # Generation time
        if record.generation_time:
            quads.append(
                (
                    record.entity_id,
                    f"{self.PROV_NS}generatedAtTime",
                    f"{record.generation_time}^^{self.XSD_NS}double",
                    graph,
                )
            )

        return quads

    def generate_hook_definition(self, event_type: YAWLEventType, condition_file: str | None = None) -> dict[str, Any]:
        """Generate UNRDF hook definition for YAWL event type.

        Parameters
        ----------
        event_type : YAWLEventType
            Event type to create hook for
        condition_file : str | None
            Optional SPARQL condition file

        Returns
        -------
        dict[str, Any]
            Hook definition compatible with UNRDF defineHook
        """
        hook_def: dict[str, Any] = {
            "meta": {
                "name": f"yawl:{event_type.value}",
                "description": f"YAWL workflow hook for {event_type.value} events",
                "ontology": ["yawl", "prov"],
            },
            "channel": {"graphs": [self.graph_name], "view": "after"},
            "deterministic": True,
            "receipting": "lockchain",
        }

        # Add condition reference if provided
        if condition_file:
            content_hash = self._hash_file_reference(condition_file)
            hook_def["when"] = {
                "kind": "sparql-ask",
                "ref": {
                    "uri": f"file://{condition_file}",
                    "sha256": content_hash,
                    "mediaType": "application/sparql-query",
                },
            }

        return hook_def

    def _hash_file_reference(self, filepath: str) -> str:
        """Generate SHA-256 hash for file reference.

        Parameters
        ----------
        filepath : str
            File path

        Returns
        -------
        str
            SHA-256 hash (placeholder for content-addressing)
        """
        # Hash the file path (content-based hashing would require file read)
        return hashlib.sha256(filepath.encode()).hexdigest()

    def to_json_ld(self, events: list[YAWLEvent]) -> dict[str, Any]:
        """Convert events to JSON-LD format.

        Parameters
        ----------
        events : list[YAWLEvent]
            Events to convert

        Returns
        -------
        dict[str, Any]
            JSON-LD document
        """
        context = {
            "@base": self.base_uri,
            "yawl": self.YAWL_NS,
            "prov": self.PROV_NS,
            "xsd": self.XSD_NS,
            "eventType": "yawl:eventType",
            "caseId": "yawl:caseId",
            "specId": "yawl:specificationId",
            "taskId": "yawl:taskId",
            "workitemId": "yawl:workItemId",
            "timestamp": {"@id": "prov:generatedAtTime", "@type": "xsd:double"},
        }

        graph = []
        for event in events:
            event_obj = {
                "@id": f"event/{event.case_id}/{int(event.timestamp * 1000)}",
                "@type": "yawl:YEvent",
                "eventType": event.event_type.value,
                "caseId": event.case_id,
                "timestamp": event.timestamp,
            }
            if event.spec_id:
                event_obj["specId"] = event.spec_id
            if event.task_id:
                event_obj["taskId"] = event.task_id
            if event.workitem_id:
                event_obj["workitemId"] = event.workitem_id
            graph.append(event_obj)

        return {"@context": context, "@graph": graph}

    def from_json_ld(self, doc: dict[str, Any]) -> list[YAWLEvent]:
        """Parse events from JSON-LD format.

        Parameters
        ----------
        doc : dict[str, Any]
            JSON-LD document

        Returns
        -------
        list[YAWLEvent]
            Parsed events
        """
        events = []
        graph = doc.get("@graph", [])

        for item in graph:
            event_type_str = item.get("eventType", "")
            try:
                event_type = YAWLEventType(event_type_str)
            except ValueError:
                continue

            events.append(
                YAWLEvent(
                    event_type=event_type,
                    case_id=item.get("caseId", ""),
                    timestamp=item.get("timestamp", time.time()),
                    spec_id=item.get("specId", ""),
                    task_id=item.get("taskId", ""),
                    workitem_id=item.get("workitemId", ""),
                )
            )

        return events

    def export_event_log(self, case_id: str | None = None, format: str = "json") -> str:
        """Export event log.

        Parameters
        ----------
        case_id : str | None
            Filter by case ID
        format : str
            Output format ('json' or 'jsonld')

        Returns
        -------
        str
            Serialized event log
        """
        events = self.get_event_history(case_id)

        if format == "jsonld":
            return json.dumps(self.to_json_ld(events), indent=2)

        return json.dumps([e.to_dict() for e in events], indent=2)

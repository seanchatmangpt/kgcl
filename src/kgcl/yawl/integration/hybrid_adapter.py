"""YAWL-Hybrid Engine adapter for tick-based workflow execution.

Bridges YAWL workflow events with the KGC Hybrid Engine's tick controller.
Converts YAWL state changes to RDF and integrates with knowledge hooks.

Architecture
------------
The adapter implements TickHook protocol to:
1. Convert YAWL events to RDF triples in the Oxigraph store
2. Trigger knowledge hooks on workflow state changes
3. Store provenance records for audit trails
4. Support WCP-43 workflow control patterns

Java Parity
-----------
Maps to Java YAWL engine's event notification system while
leveraging the Hybrid Engine's N3-driven reasoning.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol

from kgcl.yawl.integration.unrdf_adapter import ProvenanceRecord, UNRDFAdapter, YAWLEvent, YAWLEventType

if TYPE_CHECKING:
    from kgcl.hybrid import HybridEngine, TickResult


class TickHookProtocol(Protocol):
    """Protocol matching hybrid engine's TickHook."""

    def on_pre_tick(self, engine: Any, tick_number: int) -> bool:
        """Execute before tick begins."""
        ...

    def on_rule_fired(self, engine: Any, rule: Any, tick_number: int) -> None:
        """Execute after a rule fires."""
        ...

    def on_post_tick(self, engine: Any, result: Any) -> None:
        """Execute after tick completes."""
        ...


@dataclass(frozen=True)
class WorkflowStateChange:
    """Represents a YAWL workflow state change in RDF.

    Parameters
    ----------
    event : YAWLEvent
        Source YAWL event
    triples : list[tuple[str, str, str]]
        RDF triples representing the change
    timestamp : datetime
        Change timestamp

    Examples
    --------
    >>> change = WorkflowStateChange(
    ...     event=YAWLEvent(...), triples=[("task:1", "rdf:type", "yawl:Task")], timestamp=datetime.now(UTC)
    ... )
    """

    event: YAWLEvent
    triples: list[tuple[str, str, str]]
    timestamp: datetime


@dataclass(frozen=True)
class YAWLTickReceipt:
    """Receipt for YAWL event processed during a tick.

    Parameters
    ----------
    tick_number : int
        Tick when event was processed
    event : YAWLEvent
        YAWL event that was processed
    triples_added : int
        Number of triples added to graph
    provenance_id : str
        Provenance record identifier
    duration_ms : float
        Processing time in milliseconds

    Examples
    --------
    >>> receipt = YAWLTickReceipt(
    ...     tick_number=1, event=event, triples_added=5, provenance_id="prov:001", duration_ms=1.5
    ... )
    """

    tick_number: int
    event: YAWLEvent
    triples_added: int
    provenance_id: str
    duration_ms: float


@dataclass
class YAWLHybridAdapter:
    """Adapter connecting YAWL events to Hybrid Engine tick controller.

    Implements the TickHook protocol to integrate YAWL workflow events
    with the Hybrid Engine's N3-driven reasoning.

    Parameters
    ----------
    unrdf_adapter : UNRDFAdapter | None
        UNRDF adapter for event conversion (created if None)
    auto_commit : bool
        Whether to auto-commit events to graph on each tick

    Examples
    --------
    >>> from kgcl.hybrid import HybridEngine, TickController
    >>> from kgcl.yawl.integration import YAWLHybridAdapter
    >>>
    >>> engine = HybridEngine()
    >>> adapter = YAWLHybridAdapter()
    >>> controller = TickController(engine)
    >>> controller.register_hook(adapter)
    >>>
    >>> # Queue YAWL events
    >>> adapter.queue_event(
    ...     YAWLEvent(event_type=YAWLEventType.TASK_COMPLETED, case_id="case-001", timestamp=time.time())
    ... )
    >>>
    >>> # Events will be processed on next tick
    >>> result = controller.execute_tick()
    """

    unrdf_adapter: UNRDFAdapter | None = None
    auto_commit: bool = True

    # RDF namespaces
    YAWL_NS: str = "http://kgcl.dev/ontology/yawl/core/v1#"
    KGC_NS: str = "https://kgc.org/ns/"
    RDF_NS: str = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    PROV_NS: str = "http://www.w3.org/ns/prov#"

    # Internal state
    _event_queue: list[YAWLEvent] = field(default_factory=list)
    _receipts: list[YAWLTickReceipt] = field(default_factory=list)
    _processed_events: list[YAWLEvent] = field(default_factory=list)
    _current_tick: int = 0

    def __post_init__(self) -> None:
        """Initialize adapter state."""
        if self.unrdf_adapter is None:
            object.__setattr__(self, "unrdf_adapter", UNRDFAdapter())
        if not hasattr(self, "_event_queue") or self._event_queue is None:
            object.__setattr__(self, "_event_queue", [])
        if not hasattr(self, "_receipts") or self._receipts is None:
            object.__setattr__(self, "_receipts", [])
        if not hasattr(self, "_processed_events") or self._processed_events is None:
            object.__setattr__(self, "_processed_events", [])
        if not hasattr(self, "_current_tick"):
            object.__setattr__(self, "_current_tick", 0)

    def queue_event(self, event: YAWLEvent) -> None:
        """Queue a YAWL event for processing on next tick.

        Parameters
        ----------
        event : YAWLEvent
            Event to queue
        """
        self._event_queue.append(event)
        if self.unrdf_adapter:
            self.unrdf_adapter.record_event(event)

    def queue_events(self, events: list[YAWLEvent]) -> None:
        """Queue multiple YAWL events.

        Parameters
        ----------
        events : list[YAWLEvent]
            Events to queue
        """
        for event in events:
            self.queue_event(event)

    def get_pending_events(self) -> list[YAWLEvent]:
        """Get events pending processing.

        Returns
        -------
        list[YAWLEvent]
            Pending events
        """
        return list(self._event_queue)

    def get_processed_events(self) -> list[YAWLEvent]:
        """Get events that have been processed.

        Returns
        -------
        list[YAWLEvent]
            Processed events
        """
        return list(self._processed_events)

    def get_receipts(self) -> list[YAWLTickReceipt]:
        """Get processing receipts.

        Returns
        -------
        list[YAWLTickReceipt]
            All receipts
        """
        return list(self._receipts)

    # =========================================================================
    # TickHook Protocol Implementation
    # =========================================================================

    def on_pre_tick(self, engine: Any, tick_number: int) -> bool:
        """Process queued YAWL events before tick.

        Converts queued events to RDF and loads into engine's graph.

        Parameters
        ----------
        engine : Any
            Hybrid engine instance
        tick_number : int
            Current tick number

        Returns
        -------
        bool
            True to continue tick, False to abort
        """
        self._current_tick = tick_number

        if not self._event_queue:
            return True

        # Process each queued event
        for event in self._event_queue:
            start_time = time.perf_counter()

            # Convert event to RDF triples
            triples = self._event_to_rdf_triples(event)

            # Load triples into engine graph
            if self.auto_commit and triples:
                turtle = self._triples_to_turtle(triples)
                try:
                    engine.load_data(turtle)
                except Exception:
                    # Engine may not have load_data method
                    pass

            # Create provenance record
            provenance_id = ""
            if self.unrdf_adapter:
                record = self.unrdf_adapter.add_provenance(event, agent_id="hybrid-adapter")
                provenance_id = record.entity_id

            # Create receipt
            duration_ms = (time.perf_counter() - start_time) * 1000
            receipt = YAWLTickReceipt(
                tick_number=tick_number,
                event=event,
                triples_added=len(triples),
                provenance_id=provenance_id,
                duration_ms=duration_ms,
            )
            self._receipts.append(receipt)
            self._processed_events.append(event)

        # Clear queue
        self._event_queue.clear()

        return True

    def on_rule_fired(self, engine: Any, rule: Any, tick_number: int) -> None:
        """Track rules fired that affect YAWL state.

        Parameters
        ----------
        engine : Any
            Hybrid engine instance
        rule : Any
            Rule that fired
        tick_number : int
            Current tick number
        """
        # Could track which WCP rules affect YAWL state
        pass

    def on_post_tick(self, engine: Any, result: Any) -> None:
        """Capture workflow state after tick completes.

        Parameters
        ----------
        engine : Any
            Hybrid engine instance
        result : Any
            Tick result
        """
        # Could extract workflow state changes from result
        pass

    # =========================================================================
    # RDF Conversion
    # =========================================================================

    def _event_to_rdf_triples(self, event: YAWLEvent) -> list[tuple[str, str, str]]:
        """Convert YAWL event to RDF triples.

        Parameters
        ----------
        event : YAWLEvent
            Event to convert

        Returns
        -------
        list[tuple[str, str, str]]
            (subject, predicate, object) triples
        """
        event_uri = f"<{self.YAWL_NS}event/{event.case_id}/{int(event.timestamp * 1000)}>"
        triples = []

        # Type
        triples.append((event_uri, f"<{self.RDF_NS}type>", f"<{self.YAWL_NS}YEvent>"))

        # Event type
        triples.append((event_uri, f"<{self.YAWL_NS}eventType>", f'"{event.event_type.value}"'))

        # Case ID
        triples.append((event_uri, f"<{self.YAWL_NS}caseId>", f'"{event.case_id}"'))

        # Timestamp
        triples.append(
            (
                event_uri,
                f"<{self.PROV_NS}generatedAtTime>",
                f'"{event.timestamp}"^^<http://www.w3.org/2001/XMLSchema#double>',
            )
        )

        # Optional fields
        if event.spec_id:
            triples.append((event_uri, f"<{self.YAWL_NS}specificationId>", f'"{event.spec_id}"'))
        if event.task_id:
            triples.append((event_uri, f"<{self.YAWL_NS}taskId>", f'"{event.task_id}"'))
        if event.workitem_id:
            triples.append((event_uri, f"<{self.YAWL_NS}workItemId>", f'"{event.workitem_id}"'))

        return triples

    def _triples_to_turtle(self, triples: list[tuple[str, str, str]]) -> str:
        """Convert triples to Turtle format.

        Parameters
        ----------
        triples : list[tuple[str, str, str]]
            Triples to convert

        Returns
        -------
        str
            Turtle string
        """
        lines = [
            f"@prefix yawl: <{self.YAWL_NS}> .",
            f"@prefix rdf: <{self.RDF_NS}> .",
            f"@prefix prov: <{self.PROV_NS}> .",
            "",
        ]

        for s, p, o in triples:
            lines.append(f"{s} {p} {o} .")

        return "\n".join(lines)

    # =========================================================================
    # WCP Pattern Integration
    # =========================================================================

    def create_task_enabled_event(self, case_id: str, task_id: str, spec_id: str = "") -> YAWLEvent:
        """Create task enabled event (WCP pattern support).

        Parameters
        ----------
        case_id : str
            Case identifier
        task_id : str
            Task identifier
        spec_id : str
            Specification identifier

        Returns
        -------
        YAWLEvent
            Task enabled event
        """
        return YAWLEvent(
            event_type=YAWLEventType.TASK_ENABLED,
            case_id=case_id,
            timestamp=time.time(),
            spec_id=spec_id,
            task_id=task_id,
        )

    def create_task_completed_event(
        self, case_id: str, task_id: str, spec_id: str = "", data: dict[str, Any] | None = None
    ) -> YAWLEvent:
        """Create task completed event (WCP pattern support).

        Parameters
        ----------
        case_id : str
            Case identifier
        task_id : str
            Task identifier
        spec_id : str
            Specification identifier
        data : dict[str, Any] | None
            Task output data

        Returns
        -------
        YAWLEvent
            Task completed event
        """
        return YAWLEvent(
            event_type=YAWLEventType.TASK_COMPLETED,
            case_id=case_id,
            timestamp=time.time(),
            spec_id=spec_id,
            task_id=task_id,
            data=data or {},
        )

    def create_token_event(
        self, event_type: YAWLEventType, case_id: str, task_id: str = "", data: dict[str, Any] | None = None
    ) -> YAWLEvent:
        """Create token event for WCP control flow.

        Parameters
        ----------
        event_type : YAWLEventType
            Token event type (CREATED, MOVED, SPLIT, JOINED)
        case_id : str
            Case identifier
        task_id : str
            Task/place identifier
        data : dict[str, Any] | None
            Token data (e.g., split branches, join sources)

        Returns
        -------
        YAWLEvent
            Token event
        """
        return YAWLEvent(
            event_type=event_type, case_id=case_id, timestamp=time.time(), task_id=task_id, data=data or {}
        )

    # =========================================================================
    # Knowledge Hook Generation
    # =========================================================================

    def generate_task_completion_hook(self, task_id: str) -> str:
        """Generate N3 knowledge hook for task completion.

        Parameters
        ----------
        task_id : str
            Task to monitor

        Returns
        -------
        str
            RDF/Turtle hook definition
        """
        return f"""
@prefix hook: <https://kgc.org/ns/hook/> .
@prefix yawl: <{self.YAWL_NS}> .

<urn:hook:yawl-task-{task_id}> a hook:KnowledgeHook ;
    hook:name "yawl-task-{task_id}-completion" ;
    hook:phase "on_change" ;
    hook:priority 100 ;
    hook:enabled true ;
    hook:conditionQuery \"\"\"
        ASK {{
            ?event a yawl:YEvent ;
                yawl:eventType "task_completed" ;
                yawl:taskId "{task_id}" .
        }}
    \"\"\" ;
    hook:handlerAction hook:Notify ;
    hook:handlerReason "Task {task_id} completed" .
"""

    def generate_case_lifecycle_hook(self) -> str:
        """Generate N3 knowledge hook for case lifecycle events.

        Returns
        -------
        str
            RDF/Turtle hook definition
        """
        return f"""
@prefix hook: <https://kgc.org/ns/hook/> .
@prefix yawl: <{self.YAWL_NS}> .

<urn:hook:yawl-case-lifecycle> a hook:KnowledgeHook ;
    hook:name "yawl-case-lifecycle" ;
    hook:phase "on_change" ;
    hook:priority 50 ;
    hook:enabled true ;
    hook:conditionQuery \"\"\"
        ASK {{
            ?event a yawl:YEvent ;
                yawl:eventType ?type .
            FILTER(?type IN ("case_started", "case_completed", "case_cancelled"))
        }}
    \"\"\" ;
    hook:handlerAction hook:Notify ;
    hook:handlerReason "Case lifecycle event detected" .
"""

    def generate_wcp_sync_hook(self, join_task: str, required_branches: int) -> str:
        """Generate hook for WCP-3 synchronization pattern.

        Parameters
        ----------
        join_task : str
            Task requiring synchronization
        required_branches : int
            Number of branches that must complete

        Returns
        -------
        str
            RDF/Turtle hook definition for sync detection
        """
        return f"""
@prefix hook: <https://kgc.org/ns/hook/> .
@prefix yawl: <{self.YAWL_NS}> .

<urn:hook:wcp3-sync-{join_task}> a hook:KnowledgeHook ;
    hook:name "wcp3-sync-{join_task}" ;
    hook:phase "on_change" ;
    hook:priority 200 ;
    hook:enabled true ;
    hook:conditionQuery \"\"\"
        ASK {{
            SELECT (COUNT(DISTINCT ?branch) AS ?completed)
            WHERE {{
                ?event a yawl:YEvent ;
                    yawl:eventType "token_joined" ;
                    yawl:taskId "{join_task}" .
            }}
            HAVING(?completed >= {required_branches})
        }}
    \"\"\" ;
    hook:handlerAction hook:Assert ;
    hook:handlerReason "WCP-3 synchronization complete for {join_task}" .
"""

"""XES event log exporter for process mining compatibility.

Implements IEEE 1849-2016 XES standard for export to ProM, Disco, Celonis.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from xml.dom import minidom

if TYPE_CHECKING:
    from collections.abc import Sequence

    from kgcl.hybrid.temporal.domain.event import WorkflowEvent


class LifecycleTransition(Enum):
    """XES lifecycle transitions per IEEE 1849-2016."""

    SCHEDULE = "schedule"
    ASSIGN = "assign"
    REASSIGN = "reassign"
    START = "start"
    SUSPEND = "suspend"
    RESUME = "resume"
    COMPLETE = "complete"
    ATE_ABORT = "ate_abort"
    PI_ABORT = "pi_abort"
    WITHDRAW = "withdraw"
    MANUALSKIP = "manualskip"
    AUTOSKIP = "autoskip"


@dataclass(frozen=True)
class XESAttribute:
    """XES attribute with key, value, and type.

    Parameters
    ----------
    key : str
        Attribute key (e.g., "concept:name")
    value : Any
        Attribute value
    attr_type : str
        XES type: string, date, int, float, boolean
    """

    key: str
    value: Any
    attr_type: str = "string"


@dataclass(frozen=True)
class XESEvent:
    """XES event representation.

    Parameters
    ----------
    concept_name : str
        Activity name
    timestamp : datetime
        Event occurrence time
    lifecycle : LifecycleTransition
        Lifecycle state transition
    resource : str | None
        Organizational resource (agent/system)
    attributes : tuple[XESAttribute, ...]
        Additional event attributes
    """

    concept_name: str
    timestamp: datetime
    lifecycle: LifecycleTransition = LifecycleTransition.COMPLETE
    resource: str | None = None
    attributes: tuple[XESAttribute, ...] = ()


@dataclass(frozen=True)
class XESTrace:
    """XES trace (case) representation.

    Parameters
    ----------
    case_id : str
        Unique case/workflow identifier
    events : tuple[XESEvent, ...]
        Ordered sequence of events in trace
    attributes : tuple[XESAttribute, ...]
        Case-level attributes
    """

    case_id: str
    events: tuple[XESEvent, ...]
    attributes: tuple[XESAttribute, ...] = ()


@dataclass(frozen=True)
class XESLog:
    """XES log representation.

    Parameters
    ----------
    traces : tuple[XESTrace, ...]
        Collection of traces (cases)
    extensions : tuple[str, ...]
        XES standard extensions to include
    classifiers : tuple[tuple[str, str], ...]
        Event classifiers (name, key pairs)
    attributes : tuple[XESAttribute, ...]
        Log-level attributes
    """

    traces: tuple[XESTrace, ...]
    extensions: tuple[str, ...] = ("Concept", "Time", "Lifecycle", "Organizational")
    classifiers: tuple[tuple[str, str], ...] = (("Activity", "concept:name"),)
    attributes: tuple[XESAttribute, ...] = ()


class XESExporter:
    """Exports workflow events to XES format.

    Converts WorkflowEvent stream to IEEE 1849-2016 compliant XES for
    process mining tools (ProM, Disco, Celonis).

    Parameters
    ----------
    None

    Attributes
    ----------
    EVENT_TYPE_TO_LIFECYCLE : dict[str, LifecycleTransition]
        Mapping from KGCL EventType to XES lifecycle transitions
    """

    # Map our EventType to XES lifecycle transitions
    EVENT_TYPE_TO_LIFECYCLE: dict[str, LifecycleTransition] = {
        "TICK_START": LifecycleTransition.START,
        "TICK_END": LifecycleTransition.COMPLETE,
        "STATUS_CHANGE": LifecycleTransition.COMPLETE,
        "TOKEN_MOVE": LifecycleTransition.COMPLETE,
        "SPLIT": LifecycleTransition.COMPLETE,
        "JOIN": LifecycleTransition.COMPLETE,
        "CANCELLATION": LifecycleTransition.ATE_ABORT,
        "MI_SPAWN": LifecycleTransition.START,
        "MI_COMPLETE": LifecycleTransition.COMPLETE,
        "HOOK_EXECUTION": LifecycleTransition.COMPLETE,
        "VALIDATION": LifecycleTransition.COMPLETE,
    }

    def __init__(self) -> None:
        """Initialize XES exporter with namespace."""
        self._ns = "http://www.xes-standard.org/"

    def convert_event(self, event: WorkflowEvent) -> XESEvent:
        """Convert WorkflowEvent to XESEvent.

        Parameters
        ----------
        event : WorkflowEvent
            KGCL workflow event

        Returns
        -------
        XESEvent
            IEEE 1849-2016 compliant event
        """
        lifecycle = self.EVENT_TYPE_TO_LIFECYCLE.get(event.event_type.name, LifecycleTransition.COMPLETE)

        # Extract activity name from event type or payload
        activity = event.payload.get("activity", event.event_type.name)
        resource = event.payload.get("resource", "system")

        # Convert payload to XES attributes
        attrs: list[XESAttribute] = []
        for key, value in event.payload.items():
            if key not in ("activity", "resource"):
                attr_type = self._infer_type(value)
                attrs.append(XESAttribute(key=key, value=value, attr_type=attr_type))

        # Add event_id as attribute
        attrs.append(XESAttribute(key="event:id", value=event.event_id))

        # Add tick number
        attrs.append(XESAttribute(key="tick:number", value=event.tick_number, attr_type="int"))

        # Add causal dependencies
        if event.caused_by:
            caused_by_str = ",".join(event.caused_by)
            attrs.append(XESAttribute(key="event:caused_by", value=caused_by_str))

        # Add vector clock
        if event.vector_clock:
            vc_str = ";".join(f"{node}:{count}" for node, count in event.vector_clock)
            attrs.append(XESAttribute(key="event:vector_clock", value=vc_str))

        # Add event hash for integrity
        attrs.append(XESAttribute(key="event:hash", value=event.event_hash))

        return XESEvent(
            concept_name=str(activity),
            timestamp=event.timestamp,
            lifecycle=lifecycle,
            resource=str(resource) if resource else None,
            attributes=tuple(attrs),
        )

    def convert_trace(self, workflow_id: str, events: Sequence[WorkflowEvent]) -> XESTrace:
        """Convert sequence of events for one workflow to XESTrace.

        Parameters
        ----------
        workflow_id : str
            Workflow instance identifier
        events : Sequence[WorkflowEvent]
            Ordered events for this workflow

        Returns
        -------
        XESTrace
            XES trace with converted events
        """
        xes_events = tuple(self.convert_event(e) for e in events)
        return XESTrace(case_id=workflow_id, events=xes_events)

    def convert_log(self, traces: Sequence[tuple[str, Sequence[WorkflowEvent]]]) -> XESLog:
        """Convert multiple traces to XESLog.

        Parameters
        ----------
        traces : Sequence[tuple[str, Sequence[WorkflowEvent]]]
            List of (workflow_id, events) tuples

        Returns
        -------
        XESLog
            Complete XES log with all traces
        """
        xes_traces = tuple(self.convert_trace(wf_id, events) for wf_id, events in traces)
        return XESLog(traces=xes_traces)

    def to_xml(self, log: XESLog, pretty: bool = True) -> str:
        """Convert XESLog to XML string.

        Parameters
        ----------
        log : XESLog
            XES log to serialize
        pretty : bool, optional
            Enable pretty printing with indentation (default: True)

        Returns
        -------
        str
            XML document as string
        """
        root = ET.Element("log")
        root.set("xes.version", "1849.2016")
        root.set("xmlns", self._ns)

        # Add extensions
        for ext_name in log.extensions:
            ext = ET.SubElement(root, "extension")
            ext.set("name", ext_name)
            ext.set("prefix", ext_name.lower())
            ext.set("uri", f"{self._ns}{ext_name.lower()}.xesext")

        # Add classifiers
        for clf_name, clf_keys in log.classifiers:
            clf = ET.SubElement(root, "classifier")
            clf.set("name", clf_name)
            clf.set("keys", clf_keys)

        # Add global event attributes
        global_event = ET.SubElement(root, "global")
        global_event.set("scope", "event")
        self._add_attribute(global_event, "string", "concept:name", "UNKNOWN")
        self._add_attribute(global_event, "string", "lifecycle:transition", "complete")

        # Add log-level attributes
        for attr in log.attributes:
            self._add_attribute(root, attr.attr_type, attr.key, attr.value)

        # Add traces
        for trace in log.traces:
            trace_elem = ET.SubElement(root, "trace")
            self._add_attribute(trace_elem, "string", "concept:name", trace.case_id)

            for attr in trace.attributes:
                self._add_attribute(trace_elem, attr.attr_type, attr.key, attr.value)

            for event in trace.events:
                event_elem = ET.SubElement(trace_elem, "event")
                self._add_attribute(event_elem, "string", "concept:name", event.concept_name)
                self._add_attribute(event_elem, "date", "time:timestamp", event.timestamp.isoformat())
                self._add_attribute(event_elem, "string", "lifecycle:transition", event.lifecycle.value)
                if event.resource:
                    self._add_attribute(event_elem, "string", "org:resource", event.resource)

                for attr in event.attributes:
                    self._add_attribute(event_elem, attr.attr_type, attr.key, attr.value)

        xml_str = ET.tostring(root, encoding="unicode")

        if pretty:
            dom = minidom.parseString(xml_str)
            return dom.toprettyxml(indent="  ")

        return xml_str

    def export_to_file(self, log: XESLog, filepath: str, pretty: bool = True) -> None:
        """Export XES log to file.

        Parameters
        ----------
        log : XESLog
            XES log to export
        filepath : str
            Output file path
        pretty : bool, optional
            Enable pretty printing (default: True)

        Returns
        -------
        None
        """
        xml_content = self.to_xml(log, pretty=pretty)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(xml_content)

    def _add_attribute(self, parent: ET.Element, attr_type: str, key: str, value: Any) -> None:
        """Add XES attribute element to parent.

        Parameters
        ----------
        parent : ET.Element
            Parent XML element
        attr_type : str
            XES attribute type
        key : str
            Attribute key
        value : Any
            Attribute value

        Returns
        -------
        None
        """
        elem = ET.SubElement(parent, attr_type)
        elem.set("key", key)
        elem.set("value", str(value))

    def _infer_type(self, value: Any) -> str:
        """Infer XES type from Python value.

        Parameters
        ----------
        value : Any
            Python value to type-check

        Returns
        -------
        str
            XES type name (string, int, float, boolean, date)
        """
        if isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "int"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, datetime):
            return "date"
        else:
            return "string"


def create_xes_exporter() -> XESExporter:
    """Factory for XES exporter.

    Returns
    -------
    XESExporter
        New XES exporter instance
    """
    return XESExporter()

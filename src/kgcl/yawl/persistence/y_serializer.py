"""Serialization for YAWL entities.

Provides JSON/dict serialization and deserialization for
specifications, cases, and related entities.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from kgcl.yawl.elements.y_specification import YSpecification
    from kgcl.yawl.engine.y_case import YCase


def _serialize_value(value: Any) -> Any:
    """Serialize a single value.

    Parameters
    ----------
    value : Any
        Value to serialize

    Returns
    -------
    Any
        Serialized value
    """
    if isinstance(value, datetime):
        return value.isoformat()
    elif isinstance(value, Enum):
        return value.name
    elif isinstance(value, set):
        return list(value)
    elif isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_serialize_value(v) for v in value]
    elif hasattr(value, "__dataclass_fields__"):
        return _serialize_dataclass(value)
    else:
        return value


def _serialize_dataclass(obj: Any) -> dict[str, Any]:
    """Serialize a dataclass to dict.

    Parameters
    ----------
    obj : Any
        Dataclass instance

    Returns
    -------
    dict[str, Any]
        Serialized dict
    """
    result = {}
    for field_name in obj.__dataclass_fields__:
        if field_name.startswith("_"):
            continue
        value = getattr(obj, field_name)
        result[field_name] = _serialize_value(value)
    return result


@dataclass
class YSpecificationSerializer:
    """Serializer for YSpecification.

    Converts specifications to/from dict/JSON representation.

    Examples
    --------
    >>> serializer = YSpecificationSerializer()
    >>> data = serializer.to_dict(spec)
    >>> json_str = serializer.to_json(spec)
    """

    def to_dict(self, spec: YSpecification) -> dict[str, Any]:
        """Convert specification to dictionary.

        Parameters
        ----------
        spec : YSpecification
            Specification to convert

        Returns
        -------
        dict[str, Any]
            Dictionary representation
        """
        data = {
            "id": spec.id,
            "name": spec.name,
            "documentation": spec.documentation,
            "status": spec.status.name,
            "root_net_id": spec.root_net_id,
            "schema": spec.schema,
            "attributes": spec.attributes,
            "data_type_definitions": spec.data_type_definitions,
        }

        # Metadata
        data["metadata"] = _serialize_dataclass(spec.metadata)

        # Nets
        data["nets"] = {}
        for net_id, net in spec.nets.items():
            data["nets"][net_id] = self._serialize_net(net)

        # Decompositions (excluding nets which are also decompositions)
        data["decompositions"] = {}
        for decomp_id, decomp in spec.decompositions.items():
            if decomp_id not in spec.nets:
                data["decompositions"][decomp_id] = _serialize_dataclass(decomp)

        return data

    def _serialize_net(self, net: Any) -> dict[str, Any]:
        """Serialize a net.

        Parameters
        ----------
        net : YNet
            Net to serialize

        Returns
        -------
        dict[str, Any]
            Serialized net
        """
        data = {"id": net.id, "name": net.name, "local_variables": net.local_variables}

        # Input/output conditions
        if net.input_condition:
            data["input_condition_id"] = net.input_condition.id
        if net.output_condition:
            data["output_condition_id"] = net.output_condition.id

        # Conditions
        data["conditions"] = {cid: _serialize_dataclass(cond) for cid, cond in net.conditions.items()}

        # Tasks
        data["tasks"] = {tid: _serialize_dataclass(task) for tid, task in net.tasks.items()}

        # Flows
        data["flows"] = {fid: _serialize_dataclass(flow) for fid, flow in net.flows.items()}

        return data

    def to_json(self, spec: YSpecification, indent: int = 2) -> str:
        """Convert specification to JSON string.

        Parameters
        ----------
        spec : YSpecification
            Specification to convert
        indent : int
            JSON indentation

        Returns
        -------
        str
            JSON string
        """
        return json.dumps(self.to_dict(spec), indent=indent, default=str)

    def from_dict(self, data: dict[str, Any]) -> YSpecification:
        """Create specification from dictionary.

        Parameters
        ----------
        data : dict[str, Any]
            Dictionary representation

        Returns
        -------
        YSpecification
            Deserialized specification

        Notes
        -----
        This is a simplified implementation. Full deserialization
        would need to reconstruct all nested objects properly.
        """
        from kgcl.yawl.elements.y_specification import SpecificationStatus, YMetaData, YSpecification

        spec = YSpecification(
            id=data["id"],
            name=data.get("name", ""),
            documentation=data.get("documentation", ""),
            status=SpecificationStatus[data.get("status", "EDITING")],
            root_net_id=data.get("root_net_id"),
            schema=data.get("schema", ""),
            attributes=data.get("attributes", {}),
            data_type_definitions=data.get("data_type_definitions", {}),
        )

        # Deserialize nets
        if "nets" in data:
            for net_id, net_data in data["nets"].items():
                net = self._deserialize_net(net_data)
                spec.add_net(net)
                if net_id == data.get("root_net_id"):
                    spec.set_root_net(net)

        return spec

    def _deserialize_net(self, data: dict[str, Any]) -> Any:
        """Deserialize a net.

        Parameters
        ----------
        data : dict[str, Any]
            Net data

        Returns
        -------
        YNet
            Deserialized net
        """
        from kgcl.yawl.elements.y_condition import ConditionType, YCondition
        from kgcl.yawl.elements.y_flow import YFlow
        from kgcl.yawl.elements.y_net import YNet
        from kgcl.yawl.elements.y_task import JoinType, SplitType, YTask

        net = YNet(id=data["id"], name=data.get("name", ""), local_variables=data.get("local_variables", {}))

        # Conditions
        for cid, cond_data in data.get("conditions", {}).items():
            cond = YCondition(
                id=cond_data["id"],
                name=cond_data.get("name", ""),
                condition_type=ConditionType[cond_data.get("condition_type", "EXPLICIT")],
            )
            net.add_condition(cond)

        # Tasks
        for tid, task_data in data.get("tasks", {}).items():
            task = YTask(
                id=task_data["id"],
                name=task_data.get("name", ""),
                split_type=SplitType[task_data.get("split_type", "AND")],
                join_type=JoinType[task_data.get("join_type", "XOR")],
                decomposition_id=task_data.get("decomposition_id"),
                cancellation_set=set(task_data.get("cancellation_set", [])),
                flow_predicates=task_data.get("flow_predicates", {}),
            )
            net.add_task(task)

        # Flows
        for fid, flow_data in data.get("flows", {}).items():
            flow = YFlow(
                id=flow_data["id"],
                source_id=flow_data["source_id"],
                target_id=flow_data["target_id"],
                predicate=flow_data.get("predicate"),
                ordering=flow_data.get("ordering", 0),
                is_default=flow_data.get("is_default", False),
            )
            net.add_flow(flow)

        return net

    def from_json(self, json_str: str) -> YSpecification:
        """Create specification from JSON string.

        Parameters
        ----------
        json_str : str
            JSON string

        Returns
        -------
        YSpecification
            Deserialized specification
        """
        data = json.loads(json_str)
        return self.from_dict(data)


@dataclass
class YCaseSerializer:
    """Serializer for YCase.

    Converts cases to/from dict/JSON representation.

    Examples
    --------
    >>> serializer = YCaseSerializer()
    >>> data = serializer.to_dict(case)
    >>> json_str = serializer.to_json(case)
    """

    def to_dict(self, case: YCase) -> dict[str, Any]:
        """Convert case to dictionary.

        Parameters
        ----------
        case : YCase
            Case to convert

        Returns
        -------
        dict[str, Any]
            Dictionary representation
        """
        data = {
            "id": case.id,
            "specification_id": case.specification_id,
            "root_net_id": case.root_net_id,
            "status": case.status.name,
            "created": case.created.isoformat() if case.created else None,
            "started": case.started.isoformat() if case.started else None,
            "completed": case.completed.isoformat() if case.completed else None,
            "parent_case_id": case.parent_case_id,
            "sub_cases": case.sub_cases,
        }

        # Data
        data["data"] = {
            "variables": case.data.variables,
            "input_data": case.data.input_data,
            "output_data": case.data.output_data,
        }

        # Work items
        data["work_items"] = {}
        for wi_id, wi in case.work_items.items():
            data["work_items"][wi_id] = self._serialize_work_item(wi)

        # Logs
        data["logs"] = [
            {"timestamp": log.timestamp.isoformat(), "event": log.event, "detail": log.detail, "data": log.data}
            for log in case.logs
        ]

        return data

    def _serialize_work_item(self, wi: Any) -> dict[str, Any]:
        """Serialize a work item.

        Parameters
        ----------
        wi : YWorkItem
            Work item to serialize

        Returns
        -------
        dict[str, Any]
            Serialized work item
        """
        return {
            "id": wi.id,
            "case_id": wi.case_id,
            "task_id": wi.task_id,
            "specification_id": wi.specification_id,
            "net_id": wi.net_id,
            "status": wi.status.name,
            "created": wi.created.isoformat() if wi.created else None,
            "enabled_time": wi.enabled_time.isoformat() if wi.enabled_time else None,
            "fired_time": wi.fired_time.isoformat() if wi.fired_time else None,
            "started_time": wi.started_time.isoformat() if wi.started_time else None,
            "completed_time": wi.completed_time.isoformat() if wi.completed_time else None,
            "resource_id": wi.resource_id,
            "offered_to": list(wi.offered_to),
            "data_input": wi.data_input,
            "data_output": wi.data_output,
            "parent_id": wi.parent_id,
            "children": wi.children,
        }

    def to_json(self, case: YCase, indent: int = 2) -> str:
        """Convert case to JSON string.

        Parameters
        ----------
        case : YCase
            Case to convert
        indent : int
            JSON indentation

        Returns
        -------
        str
            JSON string
        """
        return json.dumps(self.to_dict(case), indent=indent, default=str)

    def from_dict(self, data: dict[str, Any]) -> YCase:
        """Create case from dictionary.

        Parameters
        ----------
        data : dict[str, Any]
            Dictionary representation

        Returns
        -------
        YCase
            Deserialized case
        """
        from kgcl.yawl.engine.y_case import CaseData, CaseStatus, YCase

        case = YCase(
            id=data["id"],
            specification_id=data["specification_id"],
            root_net_id=data["root_net_id"],
            status=CaseStatus[data.get("status", "CREATED")],
            parent_case_id=data.get("parent_case_id"),
            sub_cases=data.get("sub_cases", []),
        )

        # Timestamps
        if data.get("created"):
            case.created = datetime.fromisoformat(data["created"])
        if data.get("started"):
            case.started = datetime.fromisoformat(data["started"])
        if data.get("completed"):
            case.completed = datetime.fromisoformat(data["completed"])

        # Data
        if "data" in data:
            case.data = CaseData(
                variables=data["data"].get("variables", {}),
                input_data=data["data"].get("input_data", {}),
                output_data=data["data"].get("output_data", {}),
            )

        return case

    def from_json(self, json_str: str) -> YCase:
        """Create case from JSON string.

        Parameters
        ----------
        json_str : str
            JSON string

        Returns
        -------
        YCase
            Deserialized case
        """
        data = json.loads(json_str)
        return self.from_dict(data)

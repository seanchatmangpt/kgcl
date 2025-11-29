"""Log predicate parser for work items (mirrors Java YLogPredicateWorkItemParser).

Parses log predicates against work item context.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kgcl.yawl.util.parser import YPredicateParser

if TYPE_CHECKING:
    from kgcl.yawl.engine.y_work_item import YWorkItem


class YLogPredicateWorkItemParser(YPredicateParser):
    """Parser for log predicates against work items (mirrors Java YLogPredicateWorkItemParser).

    Extends YPredicateParser to resolve work item-specific predicates.

    Parameters
    ----------
    work_item : YWorkItem
        Work item to parse predicates against

    Examples
    --------
    >>> from kgcl.yawl.engine.y_work_item import YWorkItem
    >>> item = YWorkItem(...)
    >>> parser = YLogPredicateWorkItemParser(item)
    >>> result = parser.parse("${item:id}")
    >>> result == item.get_id_string()
    True
    """

    def __init__(self, work_item: YWorkItem) -> None:
        """Initialize parser with work item.

        Java signature: YLogPredicateWorkItemParser(YWorkItem item)

        Parameters
        ----------
        work_item : YWorkItem
            Work item to parse against
        """
        super().__init__()
        self._work_item = work_item

    def value_of(self, predicate: str) -> str:
        """Resolve predicate value.

        Java signature: protected String valueOf(String predicate)

        Parameters
        ----------
        predicate : str
            Predicate string to resolve

        Returns
        -------
        str
            Resolved value or "n/a" if not found
        """
        resolved = "n/a"

        if predicate == "${item:id}":
            resolved = self._work_item.get_id_string()
        elif predicate == "${task:id}":
            resolved = self._work_item.get_task_id()
        elif predicate == "${spec:name}":
            resolved = self._work_item.get_spec_name() if hasattr(self._work_item, "get_spec_name") else "n/a"
        elif predicate == "${task:name}":
            task = self._work_item.get_task() if hasattr(self._work_item, "get_task") else None
            resolved = task.get_name() if task and hasattr(task, "get_name") else "n/a"
        elif predicate == "${spec:version}":
            spec_id = self._work_item.get_specification_id()
            resolved = (
                spec_id.get_version_as_string()
                if hasattr(spec_id, "get_version_as_string")
                else str(spec_id.version if hasattr(spec_id, "version") else "")
            )
        elif predicate == "${spec:key}":
            spec_id = self._work_item.get_specification_id()
            resolved = (
                spec_id.get_identifier()
                if hasattr(spec_id, "get_identifier")
                else (spec_id.identifier if hasattr(spec_id, "identifier") else "")
            )
        elif predicate == "${item:handlingservice:name}":
            client = self._work_item.get_external_client() if hasattr(self._work_item, "get_external_client") else None
            if client and hasattr(client, "get_user_name"):
                resolved = client.get_user_name()
        elif predicate == "${item:handlingservice:uri}":
            client = self._work_item.get_external_client() if hasattr(self._work_item, "get_external_client") else None
            if client and hasattr(client, "get_uri"):
                resolved = client.get_uri()
        elif predicate == "${item:handlingservice:doco}":
            client = self._work_item.get_external_client() if hasattr(self._work_item, "get_external_client") else None
            if client and hasattr(client, "get_documentation"):
                resolved = client.get_documentation()
        elif predicate == "${item:codelet}":
            resolved = self._work_item.get_codelet() if hasattr(self._work_item, "get_codelet") else "n/a"
        elif predicate == "${item:customform}":
            url = self._work_item.get_custom_form_url() if hasattr(self._work_item, "get_custom_form_url") else None
            if url:
                resolved = str(url)
        elif predicate == "${item:enabledtime}":
            time = self._work_item.get_enablement_time() if hasattr(self._work_item, "get_enablement_time") else None
            if time:
                resolved = self.date_time_string(int(time.timestamp() * 1000) if hasattr(time, "timestamp") else 0)
        elif predicate == "${item:firedtime}":
            time = self._work_item.get_firing_time() if hasattr(self._work_item, "get_firing_time") else None
            if time:
                resolved = self.date_time_string(int(time.timestamp() * 1000) if hasattr(time, "timestamp") else 0)
        elif predicate == "${item:startedtime}":
            time = self._work_item.get_start_time() if hasattr(self._work_item, "get_start_time") else None
            if time:
                resolved = self.date_time_string(int(time.timestamp() * 1000) if hasattr(time, "timestamp") else 0)
        elif predicate == "${item:status}":
            status = self._work_item.get_status() if hasattr(self._work_item, "get_status") else None
            resolved = str(status) if status else "n/a"
        elif predicate == "${task:doco}":
            task = self._work_item.get_task() if hasattr(self._work_item, "get_task") else None
            resolved = (
                task.get_documentation_pre_parsed() if task and hasattr(task, "get_documentation_pre_parsed") else "n/a"
            )
        elif predicate == "${task:decomposition:name}":
            task = self._work_item.get_task() if hasattr(self._work_item, "get_task") else None
            if task and hasattr(task, "get_decomposition_prototype"):
                decomp = task.get_decomposition_prototype()
                resolved = decomp.get_id() if decomp and hasattr(decomp, "get_id") else "n/a"
        elif predicate == "${item:timer:status}":
            resolved = self._work_item.get_timer_status() if hasattr(self._work_item, "get_timer_status") else "n/a"
        elif predicate == "${item:timer:expiry}":
            expiry = self._work_item.get_timer_expiry() if hasattr(self._work_item, "get_timer_expiry") else 0
            resolved = self.date_time_string(expiry) if expiry > 0 else "Nil"
        elif predicate.startswith("${item:attribute:"):
            attrs = self._work_item.get_attributes() if hasattr(self._work_item, "get_attributes") else None
            resolved = self.get_attribute_value(attrs, predicate) if attrs else "n/a"
        elif predicate.startswith("${expression:"):
            data = self._work_item.get_data_element() if hasattr(self._work_item, "get_data_element") else None
            resolved = self.evaluate_query(predicate, data) if data else "n/a"
        else:
            resolved = super().value_of(predicate)

        if resolved is None or resolved == "null" or resolved == predicate:
            resolved = "n/a"

        return resolved

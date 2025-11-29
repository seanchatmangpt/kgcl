"""Parameter definitions cache (mirrors Java ParamsDefinitions).

Caches task parameter schemas to avoid repeated lookups.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParamsDefinitions:
    """Cache for task parameter schemas (mirrors Java ParamsDefinitions).

    Caches YParametersSchema objects by task ID to avoid repeated lookups
    when generating output skeletons or validating data.

    Parameters
    ----------
    _name_to_decomposition_id_maps_to_parameter_tuple : dict[str, Any]
        Map from task ID to YParametersSchema

    Examples
    --------
    >>> params_defs = ParamsDefinitions()
    >>> schema = YParametersSchema(...)
    >>> params_defs.set_params_for_task("Task1", schema)
    >>> retrieved = params_defs.get_params_for_task("Task1")
    >>> retrieved == schema
    True
    """

    _name_to_decomposition_id_maps_to_parameter_tuple: dict[str, Any] = field(default_factory=dict, repr=False)

    def get_params_for_task(self, task_id: str) -> Any | None:
        """Get parameter schema for task.

        Java signature: YParametersSchema getParamsForTask(String taskID)

        Parameters
        ----------
        task_id : str
            Task ID

        Returns
        -------
        Any | None
            Parameter schema or None if not cached

        Notes
        -----
        Mirrors Java YAWL ParamsDefinitions.getParamsForTask()
        """
        return self._name_to_decomposition_id_maps_to_parameter_tuple.get(task_id)

    def set_params_for_task(self, task_id: str, parameter_tuple: Any) -> None:
        """Set parameter schema for task.

        Java signature: void setParamsForTask(String taskID, YParametersSchema parameterTuple)

        Parameters
        ----------
        task_id : str
            Task ID
        parameter_tuple : Any
            Parameter schema (YParametersSchema)

        Notes
        -----
        Mirrors Java YAWL ParamsDefinitions.setParamsForTask()
        """
        self._name_to_decomposition_id_maps_to_parameter_tuple[task_id] = parameter_tuple

    def clear(self) -> None:
        """Clear all cached parameter schemas."""
        self._name_to_decomposition_id_maps_to_parameter_tuple.clear()

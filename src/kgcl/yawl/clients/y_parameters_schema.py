"""Parameter schema for task I/O (mirrors Java YParametersSchema).

Container for input and output parameters of a task or net.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from kgcl.yawl.elements.y_decomposition import YParameter


@dataclass
class YParametersSchema:
    """Parameter schema container (mirrors Java YParametersSchema).

    Container for the parameters of a task or net, separating
    input and output parameters.

    Parameters
    ----------
    input_params : dict[str, YParameter]
        Map of input parameter name to parameter
    output_params : dict[str, YParameter]
        Map of output parameter name to parameter
    formal_input_param : str | None
        Formal input parameter name (for MI tasks)

    Examples
    --------
    >>> from kgcl.yawl.elements.y_decomposition import YParameter
    >>> schema = YParametersSchema()
    >>> param = YParameter(name="customerId", data_type="string")
    >>> schema.set_input_param(param)
    >>> len(schema.get_input_params())
    1
    """

    input_params: dict[str, Any] = field(default_factory=dict)
    output_params: dict[str, Any] = field(default_factory=dict)
    formal_input_param: str | None = None

    def get_input_params(self) -> list[Any]:
        """Get input parameters as sorted list.

        Java signature: List<YParameter> getInputParams()

        Returns
        -------
        list[Any]
            Sorted list of input parameters

        Notes
        -----
        Mirrors Java YAWL YParametersSchema.getInputParams()
        """
        result = list(self.input_params.values())
        result.sort(key=lambda p: getattr(p, "ordering", 0) if hasattr(p, "ordering") else 0)
        return result

    def get_output_params(self) -> list[Any]:
        """Get output parameters as sorted list.

        Java signature: List<YParameter> getOutputParams()

        Returns
        -------
        list[Any]
            Sorted list of output parameters

        Notes
        -----
        Mirrors Java YAWL YParametersSchema.getOutputParams()
        """
        result = list(self.output_params.values())
        result.sort(key=lambda p: getattr(p, "ordering", 0) if hasattr(p, "ordering") else 0)
        return result

    def get_input_only_params(self) -> list[Any]:
        """Get input-only parameters.

        Java signature: List<YParameter> getInputOnlyParams()

        Returns
        -------
        list[Any]
            Parameters that are input but not output

        Notes
        -----
        Mirrors Java YAWL YParametersSchema.getInputOnlyParams()
        """
        input_only: list[Any] = []
        for param in self.get_input_params():
            param_name = (
                param.name if hasattr(param, "name") else (param.get_name() if hasattr(param, "get_name") else "")
            )
            if param_name not in self.output_params:
                input_only.append(param)
        return input_only

    def get_output_only_params(self) -> list[Any]:
        """Get output-only parameters.

        Java signature: List<YParameter> getOutputOnlyParams()

        Returns
        -------
        list[Any]
            Parameters that are output but not input

        Notes
        -----
        Mirrors Java YAWL YParametersSchema.getOutputOnlyParams()
        """
        output_only: list[Any] = []
        for param in self.get_output_params():
            param_name = (
                param.name if hasattr(param, "name") else (param.get_name() if hasattr(param, "get_name") else "")
            )
            if param_name not in self.input_params:
                output_only.append(param)
        return output_only

    def get_input_output_params(self) -> list[Any]:
        """Get input-output parameters.

        Java signature: List<YParameter> getInputOutputParams()

        Returns
        -------
        list[Any]
            Parameters that are both input and output

        Notes
        -----
        Mirrors Java YAWL YParametersSchema.getInputOutputParams()
        """
        input_output: list[Any] = []
        for param in self.get_input_params():
            param_name = (
                param.name if hasattr(param, "name") else (param.get_name() if hasattr(param, "get_name") else "")
            )
            if param_name in self.output_params:
                input_output.append(param)
        return input_output

    def get_combined_params(self) -> list[Any]:
        """Get all parameters (input and output).

        Java signature: List<YParameter> getCombinedParams()

        Returns
        -------
        list[Any]
            Combined sorted list of all parameters

        Notes
        -----
        Mirrors Java YAWL YParametersSchema.getCombinedParams()
        """
        result = self.get_input_params().copy()
        result.extend(self.get_output_only_params())
        result.sort(key=lambda p: getattr(p, "ordering", 0) if hasattr(p, "ordering") else 0)
        return result

    def set_input_param(self, parameter: Any) -> None:
        """Set input parameter.

        Java signature: void setInputParam(YParameter parameter)

        Parameters
        ----------
        parameter : Any
            Input parameter

        Raises
        ------
        ValueError
            If parameter is not an input parameter

        Notes
        -----
        Mirrors Java YAWL YParametersSchema.setInputParam()
        """
        param_name = (
            parameter.name
            if hasattr(parameter, "name")
            else (parameter.get_name() if hasattr(parameter, "get_name") else "")
        )
        if not param_name:
            raise ValueError("Parameter must have a name")
        self.input_params[param_name] = parameter

    def set_output_param(self, parameter: Any) -> None:
        """Set output parameter.

        Java signature: void setOutputParam(YParameter parameter)

        Parameters
        ----------
        parameter : Any
            Output parameter

        Raises
        ------
        ValueError
            If parameter is not an output parameter

        Notes
        -----
        Mirrors Java YAWL YParametersSchema.setOutputParam()
        """
        param_name = (
            parameter.name
            if hasattr(parameter, "name")
            else (parameter.get_name() if hasattr(parameter, "get_name") else "")
        )
        if not param_name:
            raise ValueError("Parameter must have a name")
        self.output_params[param_name] = parameter

    def set_formal_input_param(self, formal_input_param: str) -> None:
        """Set formal input parameter name (for MI tasks).

        Java signature: void setFormalInputParam(String formalInputParam)

        Parameters
        ----------
        formal_input_param : str
            Formal input parameter name

        Notes
        -----
        Mirrors Java YAWL YParametersSchema.setFormalInputParam()
        """
        self.formal_input_param = formal_input_param

    def get_formal_input_param(self) -> Any | None:
        """Get formal input parameter (for MI tasks).

        Java signature: YParameter getFormalInputParam()

        Returns
        -------
        Any | None
            Formal input parameter or None

        Notes
        -----
        Mirrors Java YAWL YParametersSchema.getFormalInputParam()
        """
        if self.formal_input_param:
            return self.input_params.get(self.formal_input_param)
        return None

    def __str__(self) -> str:
        """String representation."""
        result_parts: list[str] = []
        for param in self.get_input_params():
            if hasattr(param, "to_summary_xml"):
                result_parts.append(param.to_summary_xml())
            elif hasattr(param, "__str__"):
                result_parts.append(str(param))
        for param in self.get_output_params():
            if hasattr(param, "to_summary_xml"):
                result_parts.append(param.to_summary_xml())
            elif hasattr(param, "__str__"):
                result_parts.append(str(param))
        return "".join(result_parts)

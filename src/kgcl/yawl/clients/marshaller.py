"""Marshaller utility for XML serialization/deserialization (mirrors Java Marshaller).

Provides utilities for converting between YAWL objects and XML representations.
"""

from __future__ import annotations

from typing import Any
from xml.sax import saxutils


class Marshaller:
    """Marshaller utility class (mirrors Java Marshaller).

    Provides static methods for XML serialization and deserialization
    of YAWL objects.

    Examples
    --------
    >>> from kgcl.yawl.elements.y_decomposition import YParameter
    >>> param = YParameter(name="result", data_type="string")
    >>> xml = Marshaller.present_param(param)
    >>> "result" in xml
    True
    """

    @staticmethod
    def get_output_params_in_xml(param_schema: Any | None, data_space_root_element_name: str) -> str:
        """Get output parameters as XML skeleton.

        Java signature: String getOutputParamsInXML(YParametersSchema paramSchema, String dataSpaceRootElementNm)

        Parameters
        ----------
        param_schema : Any | None
            Parameter schema with output parameters
        data_space_root_element_name : str
            Root element name for data space

        Returns
        -------
        str
            XML string with output parameter skeleton

        Notes
        -----
        Mirrors Java YAWL Marshaller.getOutputParamsInXML()
        Generates XML skeleton from output parameters

        Examples
        --------
        >>> schema = YParametersSchema(output_params=[YParameter(name="result")])
        >>> xml = Marshaller.get_output_params_in_xml(schema, "output")
        >>> "<output>" in xml
        True
        """
        result_parts: list[str] = []
        result_parts.append(f"<{data_space_root_element_name}>")

        if param_schema is not None:
            output_params = []
            if hasattr(param_schema, "get_output_params"):
                output_params = param_schema.get_output_params()
            elif hasattr(param_schema, "output_params"):
                output_params = param_schema.output_params
            elif isinstance(param_schema, dict) and "output_params" in param_schema:
                output_params = param_schema["output_params"]

            for param in output_params:
                result_parts.append(Marshaller.present_param(param))

        result_parts.append(f"</{data_space_root_element_name}>")
        return "".join(result_parts)

    @staticmethod
    def present_param(param: Any) -> str:
        """Present parameter as XML element with comments.

        Java signature: String presentParam(YParameter param)

        Parameters
        ----------
        param : Any
            Parameter object (YParameter)

        Returns
        -------
        str
            XML string with parameter element and documentation

        Notes
        -----
        Mirrors Java YAWL Marshaller.presentParam()
        Creates XML element with comments about data type, mandatory status, etc.

        Examples
        --------
        >>> param = YParameter(name="customerId", data_type="string", is_mandatory=True)
        >>> xml = Marshaller.present_param(param)
        >>> "customerId" in xml
        True
        """
        result_parts: list[str] = []
        result_parts.append("\n  <!--")

        data_type = None
        if hasattr(param, "get_data_type_name"):
            data_type = param.get_data_type_name()
        elif hasattr(param, "data_type"):
            data_type = param.data_type
        elif hasattr(param, "get_data_type"):
            data_type = param.get_data_type()

        if data_type:
            result_parts.append(f"Data Type:     {data_type}")

        is_mandatory = False
        if hasattr(param, "is_mandatory"):
            is_mandatory = param.is_mandatory
        elif hasattr(param, "get_is_mandatory"):
            is_mandatory = param.get_is_mandatory()

        result_parts.append(f"\n      Is Mandatory:  {is_mandatory}")

        documentation = None
        if hasattr(param, "get_documentation"):
            documentation = param.get_documentation()
        elif hasattr(param, "documentation"):
            documentation = param.documentation

        if documentation:
            result_parts.append(f"\n      Documentation: {saxutils.escape(str(documentation))}")

        result_parts.append("-->\n  ")

        param_name = None
        if hasattr(param, "get_preferred_name"):
            param_name = param.get_preferred_name()
        elif hasattr(param, "name"):
            param_name = param.name
        elif hasattr(param, "get_name"):
            param_name = param.get_name()

        if param_name:
            escaped_name = saxutils.escape(param_name)
            result_parts.append(f"<{escaped_name}></{escaped_name}>")
        else:
            result_parts.append("<param></param>")

        return "".join(result_parts)

    @staticmethod
    def unmarshal_task_information(task_info_as_xml: str) -> Any:
        """Unmarshal task information from XML.

        Java signature: TaskInformation unmarshalTaskInformation(String taskInfoAsXML)

        Parameters
        ----------
        task_info_as_xml : str
            XML string with task information

        Returns
        -------
        Any
            TaskInformation object

        Notes
        -----
        Mirrors Java YAWL Marshaller.unmarshalTaskInformation()
        Parses XML to extract task metadata and parameter schemas
        """
        from xml.etree import ElementTree as ET

        from kgcl.yawl.clients.models import TaskInformation, YSpecificationID

        try:
            root = ET.fromstring(task_info_as_xml)

            if root.tag == "response":
                root = root.find("taskInfo")
                if root is None:
                    root = ET.fromstring(task_info_as_xml)

            task_id = root.findtext("taskID") or ""
            task_name = root.findtext("taskName") or ""
            task_documentation = root.findtext("taskDocumentation") or ""
            decomposition_id = root.findtext("decompositionID") or ""

            spec_elem = root.find("specification")
            spec_id = YSpecificationID(uri="", version="", identifier="")
            if spec_elem is not None:
                spec_uri = spec_elem.findtext("uri") or ""
                spec_version = spec_elem.findtext("version") or ""
                spec_id = YSpecificationID(uri=spec_uri, version=spec_version, identifier="")

            input_params: dict[str, Any] = {}
            output_params: dict[str, Any] = {}

            params_elem = root.find("params")
            if params_elem is not None:
                from kgcl.yawl.elements.y_decomposition import YParameter

                for param_elem in params_elem.findall("param"):
                    param_name = param_elem.get("name") or param_elem.findtext("name") or ""
                    if not param_name:
                        continue

                    param_type = param_elem.get("type") or param_elem.findtext("type") or "string"
                    usage = param_elem.get("usage") or param_elem.findtext("usage") or "input"
                    is_input = usage in ("input", "inputOutput")
                    is_output = usage in ("output", "inputOutput")

                    is_mandatory = param_elem.get("mandatory", "true").lower() == "true"
                    if param_elem.findtext("mandatory"):
                        is_mandatory = param_elem.findtext("mandatory").lower() == "true"

                    param = YParameter(
                        name=param_name,
                        data_type=param_type,
                        is_mandatory=is_mandatory,
                        documentation=param_elem.findtext("documentation") or "",
                    )

                    if is_input:
                        input_params[param_name] = param
                    if is_output:
                        output_params[param_name] = param

            return TaskInformation(
                task_id=task_id,
                task_name=task_name,
                spec_id=spec_id,
                decomposition_id=decomposition_id,
                input_params=input_params,
                output_params=output_params,
                documentation=task_documentation,
            )
        except Exception:
            return TaskInformation(
                task_id="", task_name="", spec_id=YSpecificationID(uri="", version="", identifier="")
            )

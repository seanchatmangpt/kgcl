"""Marshals & Unmarshals specifications (mirrors Java YMarshal).

Provides methods for converting YAWL specifications to/from XML,
with optional schema validation.
"""

from __future__ import annotations

from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element

from kgcl.yawl.exceptions import YSyntaxException
from kgcl.yawl.util.xml import jdom_util


class YMarshal:
    """Marshals & Unmarshals specifications (mirrors Java YMarshal).

    Provides static methods for converting between YAWL specifications
    and XML representations.

    Examples
    --------
    >>> xml_str = "<specificationSet>...</specificationSet>"
    >>> specs = YMarshal.unmarshal_specifications(xml_str)
    >>> xml = YMarshal.marshal(specs[0])
    """

    @staticmethod
    def unmarshal_specifications(spec_str: str, schema_validate: bool = True) -> list[Any]:
        """Build list of specification objects from XML string.

        Parameters
        ----------
        spec_str : str
            XML string describing the specification set
        schema_validate : bool
            When True, validates specifications against schema while parsing

        Returns
        -------
        list[Any]
            List of YSpecification objects

        Raises
        ------
        YSyntaxException
            If XML is invalid or fails schema validation

        Notes
        -----
        Java signature: static List<YSpecification> unmarshalSpecifications(String specStr, boolean schemaValidate) throws YSyntaxException
        """
        from kgcl.yawl.elements.y_specification import YSpecification

        # Parse XML string to document
        try:
            root = ET.fromstring(spec_str)
        except ET.ParseError as e:
            raise YSyntaxException(f"Invalid XML specification: {e}") from e

        # Get version from root element
        version_attr = root.get("version")
        # Version attribute was not mandatory in version 2
        # Missing version number would likely be version 2
        if version_attr is None:
            from kgcl.yawl.schema.y_schema_version import YSchemaVersion

            version = YSchemaVersion.BETA2
        else:
            from kgcl.yawl.schema.y_schema_version import YSchemaVersion

            version = YSchemaVersion.from_string(version_attr)

        # Strip layout element if present (engine doesn't use it)
        layout_elem = root.find(".//{http://www.yawlfoundation.org/yawlschema}layout")
        if layout_elem is not None:
            parent = layout_elem.getparent()
            if parent is not None:
                parent.remove(layout_elem)

        # Validate against schema if requested
        if schema_validate:
            from kgcl.yawl.schema.schema_handler import SchemaHandler

            validator = SchemaHandler(version.get_schema_url())
            if not validator.compile_and_validate(spec_str):
                raise YSyntaxException(
                    "The specification file failed to verify against YAWL's Schema:\n"
                    + validator.get_concatenated_message()
                )

        # Build specifications
        specifications: list[YSpecification] = []
        namespace = root.tag.split("}")[0].strip("{") if "}" in root.tag else ""

        # Parse each specification element
        for spec_elem in root.findall(".//{http://www.yawlfoundation.org/yawlschema}specification"):
            from kgcl.yawl.unmarshal.y_specification_parser import YSpecificationParser

            spec_parser = YSpecificationParser(spec_elem, version)
            specifications.append(spec_parser.get_specification())

        return specifications

    @staticmethod
    def marshal(specification_list: list[Any] | Any, version: Any | None = None) -> str:
        """Build XML Document from list of specifications.

        Parameters
        ----------
        specification_list : list[Any] | Any
            List of specifications or single specification
        version : Any | None
            Schema version to use (if None, uses first spec's version)

        Returns
        -------
        str
            XML Document rendered as string

        Notes
        -----
        Java signature: static String marshal(List<YSpecification> specificationList, YSchemaVersion version)
        """
        from kgcl.yawl.elements.y_specification import YSpecification

        # Handle single specification
        if isinstance(specification_list, YSpecification):
            spec_list = [specification_list]
            version = specification_list.get_schema_version()
        else:
            spec_list = specification_list
            if version is None and spec_list:
                version = spec_list[0].get_schema_version()

        if version is None:
            from kgcl.yawl.schema.y_schema_version import YSchemaVersion

            version = YSchemaVersion.BETA3

        # Build XML
        xml_parts: list[str] = []
        xml_parts.append(version.get_header())

        for specification in spec_list:
            xml_parts.append(specification.to_xml())

        xml_parts.append("</specificationSet>")

        xml_str = "".join(xml_parts)
        return jdom_util.format_xml_string_as_document(xml_str)

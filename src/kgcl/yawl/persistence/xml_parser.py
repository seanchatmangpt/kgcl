"""XML parser for YAWL specifications.

Parses YAWL XML format into Python domain objects.
Mirrors Java's YMarshal functionality.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ParseResult:
    """Result of parsing a YAWL specification.

    Parameters
    ----------
    success : bool
        Whether parsing succeeded
    specification : Any | None
        Parsed specification
    errors : list[str]
        Parsing errors
    warnings : list[str]
        Parsing warnings
    """

    success: bool
    specification: Any | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class XMLParser:
    """Parser for YAWL XML specifications.

    Converts YAWL XML format to Python domain objects.

    Parameters
    ----------
    namespace : str
        XML namespace for YAWL elements
    strict_mode : bool
        Whether to fail on unknown elements
    """

    namespace: str = "http://www.yawlfoundation.org/yawlschema"
    strict_mode: bool = False

    def parse_file(self, path: str | Path) -> ParseResult:
        """Parse YAWL specification from file.

        Parameters
        ----------
        path : str | Path
            Path to XML file

        Returns
        -------
        ParseResult
            Parsing result
        """
        try:
            tree = ET.parse(path)
            root = tree.getroot()
            return self._parse_specification(root)
        except ET.ParseError as e:
            return ParseResult(success=False, errors=[f"XML parse error: {e}"])
        except OSError as e:
            return ParseResult(success=False, errors=[f"File error: {e}"])

    def parse_string(self, xml_content: str) -> ParseResult:
        """Parse YAWL specification from string.

        Parameters
        ----------
        xml_content : str
            XML content

        Returns
        -------
        ParseResult
            Parsing result
        """
        try:
            root = ET.fromstring(xml_content)
            return self._parse_specification(root)
        except ET.ParseError as e:
            return ParseResult(success=False, errors=[f"XML parse error: {e}"])

    def _parse_specification(self, root: ET.Element) -> ParseResult:
        """Parse specification from XML element.

        Parameters
        ----------
        root : ET.Element
            Root XML element

        Returns
        -------
        ParseResult
            Parsing result
        """
        from kgcl.yawl.elements.y_specification import YMetaData, YSpecification, YSpecificationVersion

        errors: list[str] = []
        warnings: list[str] = []

        # Get specification attributes
        spec_id = root.get("id", "")
        uri = root.get("uri", spec_id)
        version_str = root.get("version", "1.0")

        if not spec_id:
            errors.append("Specification ID is required")
            return ParseResult(success=False, errors=errors)

        # Parse version
        version_parts = version_str.split(".")
        major = int(version_parts[0]) if version_parts else 1
        minor = int(version_parts[1]) if len(version_parts) > 1 else 0

        # Create metadata with URI
        metadata = YMetaData(unique_id=uri, version=YSpecificationVersion(major=major, minor=minor))

        # Create specification
        spec = YSpecification(
            id=spec_id,
            name=self._get_child_text(root, "name", spec_id),
            documentation=self._get_child_text(root, "documentation", ""),
            metadata=metadata,
        )

        # Parse metadata
        meta_elem = self._find_child(root, "metaData")
        if meta_elem is not None:
            self._parse_metadata(meta_elem, spec)

        # Parse decompositions
        decomp_elem = self._find_child(root, "decomposition")
        while decomp_elem is not None:
            try:
                self._parse_decomposition(decomp_elem, spec)
            except ValueError as e:
                if self.strict_mode:
                    errors.append(str(e))
                else:
                    warnings.append(str(e))
            decomp_elem = self._find_next_sibling(root, decomp_elem, "decomposition")

        if errors:
            return ParseResult(success=False, errors=errors, warnings=warnings)

        return ParseResult(success=True, specification=spec, warnings=warnings)

    def _parse_metadata(self, elem: ET.Element, spec: Any) -> None:
        """Parse metadata section.

        Parameters
        ----------
        elem : ET.Element
            Metadata element
        spec : Any
            Specification to populate
        """
        spec.authors = self._get_child_text(elem, "creator", "")

    def _parse_decomposition(self, elem: ET.Element, spec: Any) -> None:
        """Parse decomposition element.

        Parameters
        ----------
        elem : ET.Element
            Decomposition element
        spec : Any
            Specification to populate
        """
        from kgcl.yawl.elements.y_decomposition import DecompositionType, YWebServiceGateway

        decomp_id = elem.get("id", "")
        is_root = elem.get("isRootNet", "false").lower() == "true"

        # Check if it's a net decomposition (has processControlElements)
        if self._find_child(elem, "processControlElements") is not None:
            # Parse the net - nets are their own decompositions
            net = self._parse_net(elem, spec)
            if net:
                spec.add_net(net)
                if is_root:
                    spec.root_net_id = net.id
        else:
            # Service/manual decomposition
            decomp = YWebServiceGateway(id=decomp_id, name=decomp_id)
            spec.add_decomposition(decomp)

    def _parse_net(self, elem: ET.Element, spec: Any) -> Any:
        """Parse net element.

        Parameters
        ----------
        elem : ET.Element
            Net element
        spec : Any
            Parent specification

        Returns
        -------
        Any
            Parsed net or None
        """
        from kgcl.yawl.elements.y_condition import YCondition
        from kgcl.yawl.elements.y_flow import YFlow
        from kgcl.yawl.elements.y_input_output_condition import YInputCondition, YOutputCondition
        from kgcl.yawl.elements.y_net import YNet
        from kgcl.yawl.elements.y_task import JoinType, SplitType, YTask

        net_id = elem.get("id", "")
        net = YNet(id=net_id, name=net_id)

        # Parse process control elements
        pce = self._find_child(elem, "processControlElements")
        if pce is None:
            return net

        # Parse input condition
        input_elem = self._find_child(pce, "inputCondition")
        if input_elem is not None:
            input_cond = YInputCondition(id=input_elem.get("id", "InputCondition"))
            net.input_condition = input_cond

        # Parse output condition
        output_elem = self._find_child(pce, "outputCondition")
        if output_elem is not None:
            output_cond = YOutputCondition(id=output_elem.get("id", "OutputCondition"))
            net.output_condition = output_cond

        # Parse conditions
        for cond_elem in pce.findall(".//condition"):
            cond = YCondition(id=cond_elem.get("id", ""), name=self._get_child_text(cond_elem, "name", ""))
            net.add_condition(cond)

        # Parse tasks
        for task_elem in pce.findall(".//task"):
            task = self._parse_task(task_elem)
            if task:
                net.add_task(task)

        # Parse flows
        flow_counter = 0
        for task_elem in pce.findall(".//task"):
            task_id = task_elem.get("id", "")
            for flow_elem in task_elem.findall(".//flowsInto"):
                target = self._get_child_text(flow_elem, "nextElementRef", "")
                if target:
                    flow_id = f"flow_{flow_counter}"
                    flow_counter += 1
                    flow = YFlow(id=flow_id, source_id=task_id, target_id=target)
                    # Check for predicate
                    pred = self._get_child_text(flow_elem, "predicate", "")
                    if pred:
                        flow.predicate = pred
                    net.add_flow(flow)

        return net

    def _parse_task(self, elem: ET.Element) -> Any:
        """Parse task element.

        Parameters
        ----------
        elem : ET.Element
            Task element

        Returns
        -------
        Any
            Parsed task or None
        """
        from kgcl.yawl.elements.y_atomic_task import YAtomicTask
        from kgcl.yawl.elements.y_task import JoinType, SplitType

        task_id = elem.get("id", "")
        name = self._get_child_text(elem, "name", task_id)

        task = YAtomicTask(id=task_id, name=name)

        # Parse join/split
        join_elem = self._find_child(elem, "join")
        if join_elem is not None:
            join_code = join_elem.get("code", "xor")
            task.join_type = self._parse_join_type(join_code)

        split_elem = self._find_child(elem, "split")
        if split_elem is not None:
            split_code = split_elem.get("code", "and")
            task.split_type = self._parse_split_type(split_code)

        # Parse decomposition reference
        decomp_to = elem.get("decomposesTo", "")
        if decomp_to:
            task.decomposition_id = decomp_to

        return task

    def _parse_join_type(self, code: str) -> Any:
        """Parse join type code.

        Parameters
        ----------
        code : str
            Join type code

        Returns
        -------
        Any
            JoinType enum
        """
        from kgcl.yawl.elements.y_task import JoinType

        code = code.lower()
        if code == "xor":
            return JoinType.XOR
        if code == "or":
            return JoinType.OR
        if code == "and":
            return JoinType.AND
        return JoinType.XOR

    def _parse_split_type(self, code: str) -> Any:
        """Parse split type code.

        Parameters
        ----------
        code : str
            Split type code

        Returns
        -------
        Any
            SplitType enum
        """
        from kgcl.yawl.elements.y_task import SplitType

        code = code.lower()
        if code == "xor":
            return SplitType.XOR
        if code == "or":
            return SplitType.OR
        if code == "and":
            return SplitType.AND
        return SplitType.AND

    def _find_child(self, elem: ET.Element, tag: str) -> ET.Element | None:
        """Find child element by tag.

        Parameters
        ----------
        elem : ET.Element
            Parent element
        tag : str
            Tag name

        Returns
        -------
        ET.Element | None
            Child element or None
        """
        # Try with namespace
        child = elem.find(f"{{{self.namespace}}}{tag}")
        if child is not None:
            return child
        # Try without namespace
        return elem.find(tag)

    def _find_next_sibling(self, parent: ET.Element, current: ET.Element, tag: str) -> ET.Element | None:
        """Find next sibling with tag.

        Parameters
        ----------
        parent : ET.Element
            Parent element
        current : ET.Element
            Current element
        tag : str
            Tag to find

        Returns
        -------
        ET.Element | None
            Next sibling or None
        """
        found_current = False
        for child in parent:
            if child is current:
                found_current = True
                continue
            if found_current:
                if child.tag.endswith(tag) or child.tag == tag:
                    return child
        return None

    def _get_child_text(self, elem: ET.Element, tag: str, default: str = "") -> str:
        """Get text content of child element.

        Parameters
        ----------
        elem : ET.Element
            Parent element
        tag : str
            Child tag
        default : str
            Default value

        Returns
        -------
        str
            Text content
        """
        child = self._find_child(elem, tag)
        if child is not None and child.text:
            return child.text
        return default

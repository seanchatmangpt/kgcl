"""XML writer for YAWL specifications.

Writes Python domain objects to YAWL XML format.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from kgcl.yawl.elements.y_specification import YSpecification


@dataclass
class XMLWriter:
    """Writer for YAWL XML specifications.

    Converts Python domain objects to YAWL XML format.

    Parameters
    ----------
    namespace : str
        XML namespace for YAWL elements
    indent : bool
        Whether to indent output
    """

    namespace: str = "http://www.yawlfoundation.org/yawlschema"
    indent: bool = True

    def write_file(self, spec: YSpecification, path: str | Path) -> bool:
        """Write specification to file.

        Parameters
        ----------
        spec : YSpecification
            Specification to write
        path : str | Path
            Output path

        Returns
        -------
        bool
            True if successful
        """
        try:
            xml_content = self.write_string(spec)
            Path(path).write_text(xml_content, encoding="utf-8")
            return True
        except OSError:
            return False

    def write_string(self, spec: YSpecification) -> str:
        """Write specification to XML string.

        Parameters
        ----------
        spec : YSpecification
            Specification to write

        Returns
        -------
        str
            XML content
        """
        root = self._create_specification_element(spec)

        # Add metadata
        self._add_metadata(root, spec)

        # Add decompositions
        for decomp in spec.decompositions.values():
            self._add_decomposition(root, decomp, spec)

        # Convert to string
        if self.indent:
            self._indent_element(root)

        return ET.tostring(root, encoding="unicode", xml_declaration=True)

    def _create_specification_element(self, spec: YSpecification) -> ET.Element:
        """Create root specification element.

        Parameters
        ----------
        spec : YSpecification
            Specification

        Returns
        -------
        ET.Element
            Root element
        """
        root = ET.Element("specificationSet")
        root.set("xmlns", self.namespace)

        spec_elem = ET.SubElement(root, "specification")
        spec_elem.set("id", spec.id)
        spec_elem.set("uri", spec.uri)
        spec_elem.set("version", spec.version)

        # Add name
        name_elem = ET.SubElement(spec_elem, "name")
        name_elem.text = spec.name

        # Add documentation
        if spec.documentation:
            doc_elem = ET.SubElement(spec_elem, "documentation")
            doc_elem.text = spec.documentation

        return root

    def _add_metadata(self, root: ET.Element, spec: YSpecification) -> None:
        """Add metadata section.

        Parameters
        ----------
        root : ET.Element
            Root element
        spec : YSpecification
            Specification
        """
        spec_elem = root.find("specification")
        if spec_elem is None:
            return

        meta = ET.SubElement(spec_elem, "metaData")

        if spec.authors:
            creator = ET.SubElement(meta, "creator")
            creator.text = spec.authors

    def _add_decomposition(self, root: ET.Element, decomp: Any, spec: YSpecification) -> None:
        """Add decomposition element.

        Parameters
        ----------
        root : ET.Element
            Root element
        decomp : Any
            Decomposition
        spec : YSpecification
            Specification
        """
        from kgcl.yawl.elements.y_decomposition import DecompositionType

        spec_elem = root.find("specification")
        if spec_elem is None:
            return

        decomp_elem = ET.SubElement(spec_elem, "decomposition")
        decomp_elem.set("id", decomp.id)
        decomp_elem.set("xsi:type", "NetFactsType")  # Simplified

        if decomp.is_root_net:
            decomp_elem.set("isRootNet", "true")

        # If it's a net decomposition, add process control elements
        if decomp.decomposition_type == DecompositionType.NET:
            net = spec.nets.get(decomp.id)
            if net:
                self._add_net_content(decomp_elem, net)

    def _add_net_content(self, parent: ET.Element, net: Any) -> None:
        """Add net content to decomposition.

        Parameters
        ----------
        parent : ET.Element
            Parent element
        net : Any
            Net to add
        """
        pce = ET.SubElement(parent, "processControlElements")

        # Add input condition
        if net.input_condition:
            input_elem = ET.SubElement(pce, "inputCondition")
            input_elem.set("id", net.input_condition.id)

        # Add tasks
        for task in net.tasks.values():
            self._add_task(pce, task, net)

        # Add conditions
        for cond in net.conditions.values():
            cond_elem = ET.SubElement(pce, "condition")
            cond_elem.set("id", cond.id)
            if cond.name:
                name_elem = ET.SubElement(cond_elem, "name")
                name_elem.text = cond.name

        # Add output condition
        if net.output_condition:
            output_elem = ET.SubElement(pce, "outputCondition")
            output_elem.set("id", net.output_condition.id)

    def _add_task(self, parent: ET.Element, task: Any, net: Any) -> None:
        """Add task element.

        Parameters
        ----------
        parent : ET.Element
            Parent element
        task : Any
            Task to add
        net : Any
            Parent net
        """
        from kgcl.yawl.elements.y_task import JoinType, SplitType

        task_elem = ET.SubElement(parent, "task")
        task_elem.set("id", task.id)

        # Add name
        if task.name:
            name_elem = ET.SubElement(task_elem, "name")
            name_elem.text = task.name

        # Add join
        join_elem = ET.SubElement(task_elem, "join")
        join_elem.set("code", self._join_type_to_code(task.join_type))

        # Add split
        split_elem = ET.SubElement(task_elem, "split")
        split_elem.set("code", self._split_type_to_code(task.split_type))

        # Add flows
        for flow in net.flows.values():
            if flow.source_id == task.id:
                flow_elem = ET.SubElement(task_elem, "flowsInto")
                ref_elem = ET.SubElement(flow_elem, "nextElementRef")
                ref_elem.set("id", flow.target_id)

                if flow.predicate:
                    pred_elem = ET.SubElement(flow_elem, "predicate")
                    pred_elem.text = flow.predicate

        # Add decomposition reference
        if task.decomposition_id:
            task_elem.set("decomposesTo", task.decomposition_id)

    def _join_type_to_code(self, join_type: Any) -> str:
        """Convert join type to code.

        Parameters
        ----------
        join_type : Any
            JoinType enum

        Returns
        -------
        str
            Code string
        """
        from kgcl.yawl.elements.y_task import JoinType

        if join_type == JoinType.AND:
            return "and"
        if join_type == JoinType.OR:
            return "or"
        return "xor"

    def _split_type_to_code(self, split_type: Any) -> str:
        """Convert split type to code.

        Parameters
        ----------
        split_type : Any
            SplitType enum

        Returns
        -------
        str
            Code string
        """
        from kgcl.yawl.elements.y_task import SplitType

        if split_type == SplitType.XOR:
            return "xor"
        if split_type == SplitType.OR:
            return "or"
        return "and"

    def _indent_element(self, elem: ET.Element, level: int = 0) -> None:
        """Indent XML element for pretty printing.

        Parameters
        ----------
        elem : ET.Element
            Element to indent
        level : int
            Current indent level
        """
        indent = "\n" + "  " * level
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = indent + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = indent
            for child in elem:
                self._indent_element(child, level + 1)
            if not child.tail or not child.tail.strip():
                child.tail = indent
        elif level and (not elem.tail or not elem.tail.strip()):
            elem.tail = indent

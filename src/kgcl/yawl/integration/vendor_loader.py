"""Vendor specification loader for YAWL v5.2 example specs.

Loads specifications from vendors/yawl-v5.2/exampleSpecs/xml directory.
Handles legacy YAWL XML namespaces (http://www.citi.qut.edu.au/yawl).

Java Parity:
    - Loads same XML format as Java YAWL engine
    - Supports Beta2-7 specifications
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class VendorSpec:
    """Loaded vendor specification.

    Parameters
    ----------
    uri : str
        Specification URI
    name : str
        Specification name
    documentation : str
        Specification documentation
    root_net_id : str
        Root net identifier
    tasks : list[dict[str, Any]]
        List of task definitions
    conditions : list[dict[str, Any]]
        List of condition definitions
    flows : list[dict[str, Any]]
        List of flow definitions
    variables : list[dict[str, Any]]
        List of variable definitions
    decompositions : list[dict[str, Any]]
        List of decomposition definitions
    """

    uri: str
    name: str
    documentation: str = ""
    root_net_id: str = ""
    tasks: list[dict[str, Any]] = field(default_factory=list)
    conditions: list[dict[str, Any]] = field(default_factory=list)
    flows: list[dict[str, Any]] = field(default_factory=list)
    variables: list[dict[str, Any]] = field(default_factory=list)
    decompositions: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class VendorSpecLoader:
    """Loader for YAWL v5.2 vendor specifications.

    Loads specifications from the vendors/yawl-v5.2 directory.

    Parameters
    ----------
    vendor_path : Path | None
        Path to vendor directory (defaults to vendors/yawl-v5.2)

    Examples
    --------
    >>> loader = VendorSpecLoader()
    >>> specs = loader.list_specs()
    >>> spec = loader.load_spec("maketrip1.xml")
    """

    vendor_path: Path | None = None
    _default_vendor: str = "vendors/yawl-v5.2"
    _legacy_namespace: str = "http://www.citi.qut.edu.au/yawl"

    def __post_init__(self) -> None:
        """Initialize vendor path."""
        if self.vendor_path is None:
            # Find vendors directory relative to project root
            current = Path(__file__).resolve()
            for parent in current.parents:
                vendor_dir = parent / self._default_vendor
                if vendor_dir.exists():
                    self.vendor_path = vendor_dir
                    break
            if self.vendor_path is None:
                self.vendor_path = Path(self._default_vendor)

    @property
    def specs_path(self) -> Path:
        """Get path to example specs directory.

        Returns
        -------
        Path
            Path to exampleSpecs/xml directory
        """
        return self.vendor_path / "exampleSpecs" / "xml" / "Beta2-7"

    def list_specs(self) -> list[str]:
        """List available specification files.

        Returns
        -------
        list[str]
            List of XML specification filenames
        """
        if not self.specs_path.exists():
            return []
        return [f.name for f in self.specs_path.glob("*.xml")]

    def load_spec(self, filename: str) -> VendorSpec | None:
        """Load specification from file.

        Parameters
        ----------
        filename : str
            XML filename to load

        Returns
        -------
        VendorSpec | None
            Loaded specification or None if failed
        """
        filepath = self.specs_path / filename
        if not filepath.exists():
            return None

        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            return self._parse_spec(root)
        except ET.ParseError:
            return None

    def load_all_specs(self) -> list[VendorSpec]:
        """Load all available specifications.

        Returns
        -------
        list[VendorSpec]
            List of loaded specifications
        """
        specs = []
        for filename in self.list_specs():
            spec = self.load_spec(filename)
            if spec:
                specs.append(spec)
        return specs

    def _parse_spec(self, root: ET.Element) -> VendorSpec:
        """Parse specification from XML root.

        Parameters
        ----------
        root : ET.Element
            Root element (specificationSet or specification)

        Returns
        -------
        VendorSpec
            Parsed specification
        """
        # Handle specificationSet wrapper
        spec_elem = self._find_element(root, "specification")
        if spec_elem is None:
            spec_elem = root

        uri = spec_elem.get("uri", "")
        name = self._get_text(spec_elem, "name", uri)
        documentation = self._get_text(spec_elem, "documentation", "")

        # Parse root net
        root_net = self._find_element(spec_elem, "rootNet")
        root_net_id = root_net.get("id", "") if root_net is not None else ""

        # Parse components
        tasks = self._parse_tasks(spec_elem)
        conditions = self._parse_conditions(spec_elem)
        flows = self._parse_flows(spec_elem)
        variables = self._parse_variables(spec_elem)
        decompositions = self._parse_decompositions(spec_elem)

        return VendorSpec(
            uri=uri,
            name=name,
            documentation=documentation,
            root_net_id=root_net_id,
            tasks=tasks,
            conditions=conditions,
            flows=flows,
            variables=variables,
            decompositions=decompositions,
        )

    def _parse_tasks(self, spec_elem: ET.Element) -> list[dict[str, Any]]:
        """Parse all tasks from specification.

        Parameters
        ----------
        spec_elem : ET.Element
            Specification element

        Returns
        -------
        list[dict[str, Any]]
            List of task definitions
        """
        tasks = []
        for task_elem in spec_elem.iter():
            if task_elem.tag.endswith("task") or task_elem.tag == "task":
                task_id = task_elem.get("id", "")
                if task_id:
                    task = {
                        "id": task_id,
                        "name": self._get_text(task_elem, "name", task_id),
                        "join": self._get_join_split(task_elem, "join"),
                        "split": self._get_join_split(task_elem, "split"),
                        "decomposesTo": self._get_text(task_elem, "decomposesTo", ""),
                    }
                    tasks.append(task)
        return tasks

    def _parse_conditions(self, spec_elem: ET.Element) -> list[dict[str, Any]]:
        """Parse all conditions from specification.

        Parameters
        ----------
        spec_elem : ET.Element
            Specification element

        Returns
        -------
        list[dict[str, Any]]
            List of condition definitions
        """
        conditions = []

        # Input conditions
        for elem in spec_elem.iter():
            if elem.tag.endswith("inputCondition") or elem.tag == "inputCondition":
                conditions.append(
                    {"id": elem.get("id", ""), "type": "input", "name": self._get_text(elem, "name", "Start")}
                )

        # Output conditions
        for elem in spec_elem.iter():
            if elem.tag.endswith("outputCondition") or elem.tag == "outputCondition":
                conditions.append(
                    {"id": elem.get("id", ""), "type": "output", "name": self._get_text(elem, "name", "End")}
                )

        # Regular conditions
        for elem in spec_elem.iter():
            if (
                (elem.tag.endswith("condition") or elem.tag == "condition")
                and not elem.tag.endswith("inputCondition")
                and not elem.tag.endswith("outputCondition")
            ):
                conditions.append(
                    {"id": elem.get("id", ""), "type": "implicit", "name": self._get_text(elem, "name", "")}
                )

        return conditions

    def _parse_flows(self, spec_elem: ET.Element) -> list[dict[str, Any]]:
        """Parse all flows from specification.

        Parameters
        ----------
        spec_elem : ET.Element
            Specification element

        Returns
        -------
        list[dict[str, Any]]
            List of flow definitions
        """
        flows = []
        flow_id = 0

        # Find flows from tasks and conditions
        for elem in spec_elem.iter():
            source_id = elem.get("id", "")
            if not source_id:
                continue

            for flow_elem in elem:
                if flow_elem.tag.endswith("flowsInto") or flow_elem.tag == "flowsInto":
                    target_ref = self._find_element(flow_elem, "nextElementRef")
                    if target_ref is not None:
                        target_id = target_ref.get("id", "")
                        predicate = self._get_text(flow_elem, "predicate", "")
                        is_default = self._find_element(flow_elem, "isDefaultFlow") is not None

                        flows.append(
                            {
                                "id": f"flow_{flow_id}",
                                "source": source_id,
                                "target": target_id,
                                "predicate": predicate,
                                "isDefault": is_default,
                            }
                        )
                        flow_id += 1

        return flows

    def _parse_variables(self, spec_elem: ET.Element) -> list[dict[str, Any]]:
        """Parse all variables from specification.

        Parameters
        ----------
        spec_elem : ET.Element
            Specification element

        Returns
        -------
        list[dict[str, Any]]
            List of variable definitions
        """
        variables = []

        for elem in spec_elem.iter():
            if elem.tag.endswith("localVariable") or elem.tag == "localVariable":
                name = elem.get("name", "")
                if name:
                    var_type = self._get_text(elem, "type", "xs:string")
                    initial_value = self._get_text(elem, "initialValue", "")
                    variables.append({"name": name, "type": var_type, "initialValue": initial_value})

        return variables

    def _parse_decompositions(self, spec_elem: ET.Element) -> list[dict[str, Any]]:
        """Parse all decompositions from specification.

        Parameters
        ----------
        spec_elem : ET.Element
            Specification element

        Returns
        -------
        list[dict[str, Any]]
            List of decomposition definitions
        """
        decompositions = []

        for elem in spec_elem.iter():
            if elem.tag.endswith("decomposition") or elem.tag == "decomposition":
                decomp_id = elem.get("id", "")
                if decomp_id:
                    # Parse input/output params
                    input_params = []
                    output_params = []

                    for param in elem:
                        if param.tag.endswith("inputParam") or param.tag == "inputParam":
                            input_params.append(
                                {"name": param.get("name", ""), "type": self._get_text(param, "type", "xs:string")}
                            )
                        elif param.tag.endswith("outputParam") or param.tag == "outputParam":
                            output_params.append(
                                {"name": param.get("name", ""), "type": self._get_text(param, "type", "xs:string")}
                            )

                    decompositions.append(
                        {
                            "id": decomp_id,
                            "type": elem.get(
                                "{http://www.w3.org/2001/XMLSchema-instance}type", "WebServiceGatewayFactsType"
                            ),
                            "inputParams": input_params,
                            "outputParams": output_params,
                        }
                    )

        return decompositions

    def _find_element(self, parent: ET.Element, tag: str) -> ET.Element | None:
        """Find child element by tag (namespace-aware).

        Parameters
        ----------
        parent : ET.Element
            Parent element
        tag : str
            Tag to find

        Returns
        -------
        ET.Element | None
            Found element or None
        """
        # Try with namespace
        child = parent.find(f"{{{self._legacy_namespace}}}{tag}")
        if child is not None:
            return child
        # Try without namespace
        child = parent.find(tag)
        if child is not None:
            return child
        # Search all children
        for elem in parent:
            if elem.tag.endswith(tag) or elem.tag == tag:
                return elem
        return None

    def _get_text(self, parent: ET.Element, tag: str, default: str) -> str:
        """Get text content of child element.

        Parameters
        ----------
        parent : ET.Element
            Parent element
        tag : str
            Child tag
        default : str
            Default value

        Returns
        -------
        str
            Text content or default
        """
        elem = self._find_element(parent, tag)
        if elem is not None and elem.text:
            return elem.text.strip()
        return default

    def _get_join_split(self, task_elem: ET.Element, tag: str) -> str:
        """Get join or split type from task.

        Parameters
        ----------
        task_elem : ET.Element
            Task element
        tag : str
            'join' or 'split'

        Returns
        -------
        str
            Join/split code (and, or, xor)
        """
        elem = self._find_element(task_elem, tag)
        if elem is not None:
            return elem.get("code", "and")
        return "and"

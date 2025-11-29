"""YAWL specification generator from RDF ontologies.

Generates YAWL workflow specifications (XML) from RDF ontology patterns,
enabling workflow-driven code execution based on semantic knowledge.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rdflib import Graph, Namespace
from rdflib.namespace import RDF, RDFS

from kgcl.codegen.base.generator import BaseGenerator, Parser

# YAWL namespace
YAWL = Namespace("http://www.yawlfoundation.org/yawl/")
WF = Namespace("http://kgcl.io/workflow#")


@dataclass(frozen=True)
class WorkflowMetadata:
    """Metadata from parsed workflow ontology.

    Parameters
    ----------
    graph : Graph
        Parsed RDF graph
    workflow_uri : str
        URI of the workflow specification
    tasks : list[dict[str, Any]]
        Workflow tasks extracted from ontology
    conditions : list[dict[str, Any]]
        Workflow conditions (gateways)
    flows : list[dict[str, Any]]
        Control flow edges
    """

    graph: Graph
    workflow_uri: str
    tasks: list[dict[str, Any]]
    conditions: list[dict[str, Any]]
    flows: list[dict[str, Any]]


class WorkflowParser(Parser[WorkflowMetadata]):
    """Parser for workflow ontologies."""

    def parse(self, input_path: Path) -> WorkflowMetadata:
        """Parse workflow ontology file.

        Parameters
        ----------
        input_path : Path
            Path to RDF file with workflow definition

        Returns
        -------
        WorkflowMetadata
            Parsed workflow metadata

        Raises
        ------
        FileNotFoundError
            If input file doesn't exist
        """
        if not input_path.exists():
            msg = f"Workflow file not found: {input_path}"
            raise FileNotFoundError(msg)

        graph = Graph()
        graph.parse(str(input_path), format="turtle")

        # Extract workflow URI
        workflow_uri = "http://kgcl.io/workflow/default"
        for s in graph.subjects(RDF.type, WF.Workflow):
            workflow_uri = str(s)
            break

        # Extract tasks
        tasks = []
        for task_uri in graph.subjects(RDF.type, WF.Task):
            task_data = {
                "uri": str(task_uri),
                "name": str(graph.value(task_uri, RDFS.label) or task_uri.split("/")[-1]),
                "decomposition": str(graph.value(task_uri, WF.decomposition) or ""),
            }
            tasks.append(task_data)

        # Extract conditions
        conditions = []
        for cond_uri in graph.subjects(RDF.type, WF.Condition):
            cond_data = {
                "uri": str(cond_uri),
                "name": str(graph.value(cond_uri, RDFS.label) or cond_uri.split("/")[-1]),
            }
            conditions.append(cond_data)

        # Extract flows
        flows = []
        for flow_uri in graph.subjects(RDF.type, WF.Flow):
            flow_data = {
                "uri": str(flow_uri),
                "source": str(graph.value(flow_uri, WF.source) or ""),
                "target": str(graph.value(flow_uri, WF.target) or ""),
            }
            flows.append(flow_data)

        return WorkflowMetadata(graph=graph, workflow_uri=workflow_uri, tasks=tasks, conditions=conditions, flows=flows)


class YAWLSpecificationGenerator(BaseGenerator[WorkflowMetadata]):
    """Generator for YAWL workflow specifications from RDF.

    Creates YAWL XML specifications that can be loaded into the YAWL engine,
    enabling workflow execution based on semantic ontology patterns.

    Parameters
    ----------
    template_dir : Path
        Directory containing YAWL templates
    output_dir : Path
        Root directory for generated YAWL specs
    dry_run : bool
        If True, don't write output files (default: False)

    Examples
    --------
    >>> generator = YAWLSpecificationGenerator(template_dir=Path("templates/yawl"), output_dir=Path("specs"))
    >>> result = generator.generate(Path("workflow.ttl"))
    """

    def __init__(self, template_dir: Path, output_dir: Path, dry_run: bool = False) -> None:
        """Initialize YAWL generator."""
        super().__init__(template_dir, output_dir, dry_run)
        self._parser = WorkflowParser()

    @property
    def parser(self) -> Parser[WorkflowMetadata]:
        """Return workflow parser instance.

        Returns
        -------
        Parser[WorkflowMetadata]
            Workflow ontology parser
        """
        return self._parser

    def _transform(self, metadata: WorkflowMetadata, **kwargs: Any) -> dict[str, Any]:
        """Transform workflow metadata to template context.

        Parameters
        ----------
        metadata : WorkflowMetadata
            Parsed workflow metadata
        **kwargs : Any
            Additional options

        Returns
        -------
        dict[str, Any]
            Context for YAWL template rendering
        """
        # Generate unique IDs for tasks and conditions
        task_map = {task["uri"]: f"task_{i}" for i, task in enumerate(metadata.tasks)}
        cond_map = {cond["uri"]: f"cond_{i}" for i, cond in enumerate(metadata.conditions)}

        # Map URIs to IDs in flows
        flows_with_ids = []
        for flow in metadata.flows:
            source_id = task_map.get(flow["source"]) or cond_map.get(flow["source"], "unknown")
            target_id = task_map.get(flow["target"]) or cond_map.get(flow["target"], "unknown")
            flows_with_ids.append({"source": source_id, "target": target_id, "uri": flow["uri"]})

        # Add IDs to tasks and conditions
        tasks_with_ids = [{**task, "id": task_map[task["uri"]]} for task in metadata.tasks]
        conds_with_ids = [{**cond, "id": cond_map[cond["uri"]]} for cond in metadata.conditions]

        return {
            "workflow_uri": metadata.workflow_uri,
            "workflow_name": metadata.workflow_uri.split("/")[-1],
            "tasks": tasks_with_ids,
            "conditions": conds_with_ids,
            "flows": flows_with_ids,
            "specification_version": "4.3",
        }

    def _get_template_name(self, metadata: WorkflowMetadata, **kwargs: Any) -> str:
        """Get YAWL template name.

        Parameters
        ----------
        metadata : WorkflowMetadata
            Parsed metadata
        **kwargs : Any
            Additional options

        Returns
        -------
        str
            Template name
        """
        return "yawl_specification.xml.j2"

    def _get_output_path(self, metadata: WorkflowMetadata, **kwargs: Any) -> Path:
        """Determine output file path for YAWL spec.

        Parameters
        ----------
        metadata : WorkflowMetadata
            Parsed metadata
        **kwargs : Any
            May include 'output_path' override

        Returns
        -------
        Path
            Output file path
        """
        if "output_path" in kwargs:
            return Path(kwargs["output_path"])

        # Default: use workflow name with .yawl extension
        workflow_name = metadata.workflow_uri.split("/")[-1]
        return self.output_dir / f"{workflow_name}.yawl"

    def _validate(self, source: str, metadata: WorkflowMetadata, **kwargs: Any) -> None:
        """Validate generated YAWL XML.

        Parameters
        ----------
        source : str
            Generated YAWL XML
        metadata : WorkflowMetadata
            Original metadata
        **kwargs : Any
            Additional validation options

        Raises
        ------
        ValidationError
            If XML is malformed
        """
        import xml.etree.ElementTree as ET

        try:
            ET.fromstring(source)
        except ET.ParseError as e:
            msg = f"Invalid YAWL XML: {e}"
            raise ValidationError(msg) from e


class ValidationError(Exception):
    """Raised when validation fails."""

    pass


__all__ = ["YAWLSpecificationGenerator", "WorkflowMetadata", "WorkflowParser", "ValidationError"]

"""YAWL-to-RDF bridge for UNRDF knowledge graph integration.

Converts YAWL specifications and workflow state to RDF triples.
Compatible with vendors/unrdf N3/RDF knowledge engine.

Uses ontology from ontology/clients/yawl-clients.ttl.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from kgcl.yawl.integration.vendor_loader import VendorSpec


@dataclass
class RDFTriple:
    """RDF triple representation.

    Parameters
    ----------
    subject : str
        Subject URI or blank node
    predicate : str
        Predicate URI
    object : str
        Object URI, literal, or blank node
    object_type : str
        Type: 'uri', 'literal', 'blank'
    datatype : str | None
        XSD datatype for literals
    """

    subject: str
    predicate: str
    object: str
    object_type: str = "uri"
    datatype: str | None = None

    def to_turtle(self) -> str:
        """Convert to Turtle format.

        Returns
        -------
        str
            Triple in Turtle syntax
        """
        obj = self.object
        if self.object_type == "literal":
            obj = f'"{obj}"'
            if self.datatype:
                obj += f"^^<{self.datatype}>"
        elif self.object_type == "uri":
            obj = f"<{obj}>"
        return f"<{self.subject}> <{self.predicate}> {obj} ."

    def to_ntriples(self) -> str:
        """Convert to N-Triples format.

        Returns
        -------
        str
            Triple in N-Triples syntax
        """
        return self.to_turtle()


@dataclass
class YAWLRDFBridge:
    """Bridge between YAWL specifications and RDF knowledge graphs.

    Converts YAWL workflow definitions and execution state to RDF triples
    compatible with UNRDF knowledge engine.

    Parameters
    ----------
    base_uri : str
        Base URI for generated RDF resources

    Examples
    --------
    >>> from kgcl.yawl.integration.vendor_loader import VendorSpecLoader
    >>> loader = VendorSpecLoader()
    >>> spec = loader.load_spec("maketrip1.xml")
    >>> bridge = YAWLRDFBridge()
    >>> triples = bridge.spec_to_rdf(spec)
    >>> turtle = bridge.to_turtle(triples)
    """

    base_uri: str = "http://kgcl.dev/yawl/instance/"
    _prefixes: dict[str, str] = field(default_factory=dict, repr=False)

    # Standard ontology namespaces
    YAWL_NS = "http://kgcl.dev/ontology/yawl/core/v1#"
    YAWL_CLIENT_NS = "http://kgcl.dev/ontology/yawl/clients/v1#"
    RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    RDFS_NS = "http://www.w3.org/2000/01/rdf-schema#"
    XSD_NS = "http://www.w3.org/2001/XMLSchema#"
    DCTERMS_NS = "http://purl.org/dc/terms/"
    PROV_NS = "http://www.w3.org/ns/prov#"

    def __post_init__(self) -> None:
        """Initialize prefixes."""
        self._prefixes = {
            "yawl": self.YAWL_NS,
            "yawl-client": self.YAWL_CLIENT_NS,
            "rdf": self.RDF_NS,
            "rdfs": self.RDFS_NS,
            "xsd": self.XSD_NS,
            "dcterms": self.DCTERMS_NS,
            "prov": self.PROV_NS,
        }

    def spec_to_rdf(self, spec: VendorSpec) -> list[RDFTriple]:
        """Convert YAWL specification to RDF triples.

        Parameters
        ----------
        spec : VendorSpec
            Vendor specification

        Returns
        -------
        list[RDFTriple]
            Generated RDF triples
        """
        triples: list[RDFTriple] = []
        spec_uri = f"{self.base_uri}spec/{spec.uri}"

        # Specification type and metadata
        triples.append(RDFTriple(spec_uri, f"{self.RDF_NS}type", f"{self.YAWL_NS}YSpecification"))
        triples.append(RDFTriple(spec_uri, f"{self.DCTERMS_NS}identifier", spec.uri, object_type="literal"))
        triples.append(RDFTriple(spec_uri, f"{self.RDFS_NS}label", spec.name, object_type="literal"))
        if spec.documentation:
            triples.append(
                RDFTriple(spec_uri, f"{self.DCTERMS_NS}description", spec.documentation, object_type="literal")
            )

        # Root net
        if spec.root_net_id:
            net_uri = f"{self.base_uri}net/{spec.root_net_id}"
            triples.append(RDFTriple(spec_uri, f"{self.YAWL_NS}hasRootNet", net_uri))
            triples.append(RDFTriple(net_uri, f"{self.RDF_NS}type", f"{self.YAWL_NS}YNet"))
            triples.append(RDFTriple(net_uri, f"{self.DCTERMS_NS}identifier", spec.root_net_id, object_type="literal"))

        # Tasks
        triples.extend(self._tasks_to_rdf(spec))

        # Conditions
        triples.extend(self._conditions_to_rdf(spec))

        # Flows
        triples.extend(self._flows_to_rdf(spec))

        # Variables
        triples.extend(self._variables_to_rdf(spec))

        # Decompositions
        triples.extend(self._decompositions_to_rdf(spec))

        return triples

    def _tasks_to_rdf(self, spec: VendorSpec) -> list[RDFTriple]:
        """Convert tasks to RDF triples.

        Parameters
        ----------
        spec : VendorSpec
            Vendor specification

        Returns
        -------
        list[RDFTriple]
            Task triples
        """
        triples: list[RDFTriple] = []

        for task in spec.tasks:
            task_uri = f"{self.base_uri}task/{task['id']}"

            triples.append(RDFTriple(task_uri, f"{self.RDF_NS}type", f"{self.YAWL_NS}YTask"))
            triples.append(RDFTriple(task_uri, f"{self.DCTERMS_NS}identifier", task["id"], object_type="literal"))
            triples.append(RDFTriple(task_uri, f"{self.RDFS_NS}label", task["name"], object_type="literal"))

            # Join/Split types
            if task.get("join"):
                triples.append(RDFTriple(task_uri, f"{self.YAWL_NS}joinType", task["join"], object_type="literal"))
            if task.get("split"):
                triples.append(RDFTriple(task_uri, f"{self.YAWL_NS}splitType", task["split"], object_type="literal"))

            # Decomposition reference
            if task.get("decomposesTo"):
                decomp_uri = f"{self.base_uri}decomposition/{task['decomposesTo']}"
                triples.append(RDFTriple(task_uri, f"{self.YAWL_NS}decomposesTo", decomp_uri))

            # Link to net
            if spec.root_net_id:
                net_uri = f"{self.base_uri}net/{spec.root_net_id}"
                triples.append(RDFTriple(net_uri, f"{self.YAWL_NS}hasTask", task_uri))

        return triples

    def _conditions_to_rdf(self, spec: VendorSpec) -> list[RDFTriple]:
        """Convert conditions to RDF triples.

        Parameters
        ----------
        spec : VendorSpec
            Vendor specification

        Returns
        -------
        list[RDFTriple]
            Condition triples
        """
        triples: list[RDFTriple] = []

        for cond in spec.conditions:
            cond_uri = f"{self.base_uri}condition/{cond['id']}"

            # Type based on condition type
            cond_type = cond.get("type", "implicit")
            if cond_type == "input":
                rdf_type = f"{self.YAWL_NS}YInputCondition"
            elif cond_type == "output":
                rdf_type = f"{self.YAWL_NS}YOutputCondition"
            else:
                rdf_type = f"{self.YAWL_NS}YCondition"

            triples.append(RDFTriple(cond_uri, f"{self.RDF_NS}type", rdf_type))
            triples.append(RDFTriple(cond_uri, f"{self.DCTERMS_NS}identifier", cond["id"], object_type="literal"))
            if cond.get("name"):
                triples.append(RDFTriple(cond_uri, f"{self.RDFS_NS}label", cond["name"], object_type="literal"))

            # Link to net
            if spec.root_net_id:
                net_uri = f"{self.base_uri}net/{spec.root_net_id}"
                if cond_type == "input":
                    triples.append(RDFTriple(net_uri, f"{self.YAWL_NS}hasInputCondition", cond_uri))
                elif cond_type == "output":
                    triples.append(RDFTriple(net_uri, f"{self.YAWL_NS}hasOutputCondition", cond_uri))
                else:
                    triples.append(RDFTriple(net_uri, f"{self.YAWL_NS}hasCondition", cond_uri))

        return triples

    def _flows_to_rdf(self, spec: VendorSpec) -> list[RDFTriple]:
        """Convert flows to RDF triples.

        Parameters
        ----------
        spec : VendorSpec
            Vendor specification

        Returns
        -------
        list[RDFTriple]
            Flow triples
        """
        triples: list[RDFTriple] = []

        for flow in spec.flows:
            flow_uri = f"{self.base_uri}flow/{flow['id']}"

            triples.append(RDFTriple(flow_uri, f"{self.RDF_NS}type", f"{self.YAWL_NS}YFlow"))
            triples.append(RDFTriple(flow_uri, f"{self.DCTERMS_NS}identifier", flow["id"], object_type="literal"))

            # Source and target
            source_uri = f"{self.base_uri}element/{flow['source']}"
            target_uri = f"{self.base_uri}element/{flow['target']}"

            triples.append(RDFTriple(flow_uri, f"{self.YAWL_NS}hasSource", source_uri))
            triples.append(RDFTriple(flow_uri, f"{self.YAWL_NS}hasTarget", target_uri))

            # Predicate
            if flow.get("predicate"):
                triples.append(
                    RDFTriple(flow_uri, f"{self.YAWL_NS}predicate", flow["predicate"], object_type="literal")
                )

            # Default flow flag
            if flow.get("isDefault"):
                triples.append(
                    RDFTriple(
                        flow_uri,
                        f"{self.YAWL_NS}isDefaultFlow",
                        "true",
                        object_type="literal",
                        datatype=f"{self.XSD_NS}boolean",
                    )
                )

            # Link to net
            if spec.root_net_id:
                net_uri = f"{self.base_uri}net/{spec.root_net_id}"
                triples.append(RDFTriple(net_uri, f"{self.YAWL_NS}hasFlow", flow_uri))

        return triples

    def _variables_to_rdf(self, spec: VendorSpec) -> list[RDFTriple]:
        """Convert variables to RDF triples.

        Parameters
        ----------
        spec : VendorSpec
            Vendor specification

        Returns
        -------
        list[RDFTriple]
            Variable triples
        """
        triples: list[RDFTriple] = []

        for var in spec.variables:
            var_uri = f"{self.base_uri}variable/{var['name']}"

            triples.append(RDFTriple(var_uri, f"{self.RDF_NS}type", f"{self.YAWL_NS}YVariable"))
            triples.append(RDFTriple(var_uri, f"{self.DCTERMS_NS}identifier", var["name"], object_type="literal"))
            triples.append(RDFTriple(var_uri, f"{self.YAWL_NS}dataType", var["type"], object_type="literal"))

            if var.get("initialValue"):
                triples.append(
                    RDFTriple(var_uri, f"{self.YAWL_NS}initialValue", var["initialValue"], object_type="literal")
                )

            # Link to net
            if spec.root_net_id:
                net_uri = f"{self.base_uri}net/{spec.root_net_id}"
                triples.append(RDFTriple(net_uri, f"{self.YAWL_NS}hasVariable", var_uri))

        return triples

    def _decompositions_to_rdf(self, spec: VendorSpec) -> list[RDFTriple]:
        """Convert decompositions to RDF triples.

        Parameters
        ----------
        spec : VendorSpec
            Vendor specification

        Returns
        -------
        list[RDFTriple]
            Decomposition triples
        """
        triples: list[RDFTriple] = []

        for decomp in spec.decompositions:
            decomp_uri = f"{self.base_uri}decomposition/{decomp['id']}"

            triples.append(RDFTriple(decomp_uri, f"{self.RDF_NS}type", f"{self.YAWL_NS}YDecomposition"))
            triples.append(RDFTriple(decomp_uri, f"{self.DCTERMS_NS}identifier", decomp["id"], object_type="literal"))

            # Input/output params
            for param in decomp.get("inputParams", []):
                param_uri = f"{decomp_uri}/input/{param['name']}"
                triples.append(RDFTriple(decomp_uri, f"{self.YAWL_NS}hasInputParam", param_uri))
                triples.append(RDFTriple(param_uri, f"{self.RDF_NS}type", f"{self.YAWL_NS}YParameter"))
                triples.append(
                    RDFTriple(param_uri, f"{self.DCTERMS_NS}identifier", param["name"], object_type="literal")
                )
                triples.append(RDFTriple(param_uri, f"{self.YAWL_NS}dataType", param["type"], object_type="literal"))

            for param in decomp.get("outputParams", []):
                param_uri = f"{decomp_uri}/output/{param['name']}"
                triples.append(RDFTriple(decomp_uri, f"{self.YAWL_NS}hasOutputParam", param_uri))
                triples.append(RDFTriple(param_uri, f"{self.RDF_NS}type", f"{self.YAWL_NS}YParameter"))
                triples.append(
                    RDFTriple(param_uri, f"{self.DCTERMS_NS}identifier", param["name"], object_type="literal")
                )
                triples.append(RDFTriple(param_uri, f"{self.YAWL_NS}dataType", param["type"], object_type="literal"))

            # Link to spec
            spec_uri = f"{self.base_uri}spec/{spec.uri}"
            triples.append(RDFTriple(spec_uri, f"{self.YAWL_NS}hasDecomposition", decomp_uri))

        return triples

    def to_turtle(self, triples: list[RDFTriple]) -> str:
        """Convert triples to Turtle format.

        Parameters
        ----------
        triples : list[RDFTriple]
            RDF triples

        Returns
        -------
        str
            Turtle-formatted RDF
        """
        lines = []

        # Prefixes
        for prefix, ns in self._prefixes.items():
            lines.append(f"@prefix {prefix}: <{ns}> .")
        lines.append(f"@base <{self.base_uri}> .")
        lines.append("")

        # Triples
        for triple in triples:
            lines.append(triple.to_turtle())

        return "\n".join(lines)

    def to_ntriples(self, triples: list[RDFTriple]) -> str:
        """Convert triples to N-Triples format.

        Parameters
        ----------
        triples : list[RDFTriple]
            RDF triples

        Returns
        -------
        str
            N-Triples-formatted RDF
        """
        return "\n".join(triple.to_ntriples() for triple in triples)

"""Tests for YAWLRDFBridge - converting YAWL specs to RDF.

Chicago TDD: Tests verify YAWL specifications convert to valid RDF.
"""

import pytest

from kgcl.yawl.integration.rdf_bridge import RDFTriple, YAWLRDFBridge
from kgcl.yawl.integration.vendor_loader import VendorSpec, VendorSpecLoader


@pytest.fixture
def bridge() -> YAWLRDFBridge:
    """Create RDF bridge."""
    return YAWLRDFBridge()


@pytest.fixture
def loader() -> VendorSpecLoader:
    """Create vendor spec loader."""
    return VendorSpecLoader()


@pytest.fixture
def sample_spec() -> VendorSpec:
    """Create sample specification."""
    return VendorSpec(
        uri="test-spec.xml",
        name="Test Specification",
        documentation="A test workflow",
        root_net_id="main",
        tasks=[
            {"id": "task1", "name": "Task One", "join": "and", "split": "xor", "decomposesTo": "decomp1"},
            {"id": "task2", "name": "Task Two", "join": "xor", "split": "and", "decomposesTo": "decomp2"},
        ],
        conditions=[{"id": "start", "type": "input", "name": "Start"}, {"id": "end", "type": "output", "name": "End"}],
        flows=[
            {"id": "flow_0", "source": "start", "target": "task1", "predicate": "", "isDefault": False},
            {"id": "flow_1", "source": "task1", "target": "task2", "predicate": "/data/x > 0", "isDefault": False},
            {"id": "flow_2", "source": "task2", "target": "end", "predicate": "", "isDefault": True},
        ],
        variables=[
            {"name": "x", "type": "xs:integer", "initialValue": "0"},
            {"name": "y", "type": "xs:string", "initialValue": "hello"},
        ],
        decompositions=[
            {
                "id": "decomp1",
                "type": "WebServiceGatewayFactsType",
                "inputParams": [{"name": "in1", "type": "xs:string"}],
                "outputParams": [{"name": "out1", "type": "xs:string"}],
            }
        ],
    )


class TestRDFTriple:
    """Tests for RDFTriple dataclass."""

    def test_to_turtle_uri_object(self) -> None:
        """URI object renders correctly."""
        triple = RDFTriple("http://example.org/s", "http://example.org/p", "http://example.org/o", object_type="uri")

        turtle = triple.to_turtle()

        assert "<http://example.org/s>" in turtle
        assert "<http://example.org/p>" in turtle
        assert "<http://example.org/o>" in turtle
        assert turtle.endswith(".")

    def test_to_turtle_literal_object(self) -> None:
        """Literal object renders with quotes."""
        triple = RDFTriple("http://example.org/s", "http://example.org/p", "hello", object_type="literal")

        turtle = triple.to_turtle()

        assert '"hello"' in turtle

    def test_to_turtle_typed_literal(self) -> None:
        """Typed literal includes datatype."""
        triple = RDFTriple(
            "http://example.org/s",
            "http://example.org/p",
            "42",
            object_type="literal",
            datatype="http://www.w3.org/2001/XMLSchema#integer",
        )

        turtle = triple.to_turtle()

        assert '"42"' in turtle
        assert "^^<http://www.w3.org/2001/XMLSchema#integer>" in turtle


class TestYAWLRDFBridgeSpecification:
    """Tests for converting specification metadata."""

    def test_spec_to_rdf_returns_triples(self, bridge: YAWLRDFBridge, sample_spec: VendorSpec) -> None:
        """spec_to_rdf returns list of triples."""
        triples = bridge.spec_to_rdf(sample_spec)

        assert isinstance(triples, list)
        assert len(triples) > 0
        assert all(isinstance(t, RDFTriple) for t in triples)

    def test_spec_has_type_triple(self, bridge: YAWLRDFBridge, sample_spec: VendorSpec) -> None:
        """Spec has rdf:type YSpecification."""
        triples = bridge.spec_to_rdf(sample_spec)

        type_triples = [t for t in triples if "rdf-syntax-ns#type" in t.predicate]
        spec_type = [t for t in type_triples if "YSpecification" in t.object]
        assert len(spec_type) >= 1

    def test_spec_has_identifier(self, bridge: YAWLRDFBridge, sample_spec: VendorSpec) -> None:
        """Spec has dcterms:identifier."""
        triples = bridge.spec_to_rdf(sample_spec)

        id_triples = [t for t in triples if "identifier" in t.predicate]
        assert any(t.object == "test-spec.xml" for t in id_triples)

    def test_spec_has_label(self, bridge: YAWLRDFBridge, sample_spec: VendorSpec) -> None:
        """Spec has rdfs:label."""
        triples = bridge.spec_to_rdf(sample_spec)

        label_triples = [t for t in triples if "label" in t.predicate]
        assert any(t.object == "Test Specification" for t in label_triples)

    def test_spec_has_description(self, bridge: YAWLRDFBridge, sample_spec: VendorSpec) -> None:
        """Spec has dcterms:description."""
        triples = bridge.spec_to_rdf(sample_spec)

        desc_triples = [t for t in triples if "description" in t.predicate]
        assert any("test workflow" in t.object.lower() for t in desc_triples)


class TestYAWLRDFBridgeTasks:
    """Tests for converting tasks to RDF."""

    def test_tasks_converted_to_triples(self, bridge: YAWLRDFBridge, sample_spec: VendorSpec) -> None:
        """Tasks are converted to RDF triples."""
        triples = bridge.spec_to_rdf(sample_spec)

        task_types = [t for t in triples if "YTask" in t.object]
        assert len(task_types) == 2

    def test_task_has_identifier(self, bridge: YAWLRDFBridge, sample_spec: VendorSpec) -> None:
        """Tasks have identifiers."""
        triples = bridge.spec_to_rdf(sample_spec)

        task_ids = [t for t in triples if "/task/" in t.subject and "identifier" in t.predicate]
        assert any(t.object == "task1" for t in task_ids)
        assert any(t.object == "task2" for t in task_ids)

    def test_task_has_join_split(self, bridge: YAWLRDFBridge, sample_spec: VendorSpec) -> None:
        """Tasks have join/split types."""
        triples = bridge.spec_to_rdf(sample_spec)

        join_triples = [t for t in triples if "joinType" in t.predicate]
        split_triples = [t for t in triples if "splitType" in t.predicate]

        assert len(join_triples) >= 2
        assert len(split_triples) >= 2

    def test_task_decomposition_link(self, bridge: YAWLRDFBridge, sample_spec: VendorSpec) -> None:
        """Tasks link to decompositions."""
        triples = bridge.spec_to_rdf(sample_spec)

        decomp_links = [t for t in triples if "decomposesTo" in t.predicate]
        assert len(decomp_links) >= 2


class TestYAWLRDFBridgeConditions:
    """Tests for converting conditions to RDF."""

    def test_conditions_converted(self, bridge: YAWLRDFBridge, sample_spec: VendorSpec) -> None:
        """Conditions are converted to RDF."""
        triples = bridge.spec_to_rdf(sample_spec)

        input_conds = [t for t in triples if "YInputCondition" in t.object]
        output_conds = [t for t in triples if "YOutputCondition" in t.object]

        assert len(input_conds) == 1
        assert len(output_conds) == 1

    def test_net_has_conditions(self, bridge: YAWLRDFBridge, sample_spec: VendorSpec) -> None:
        """Net links to conditions."""
        triples = bridge.spec_to_rdf(sample_spec)

        input_links = [t for t in triples if "hasInputCondition" in t.predicate]
        output_links = [t for t in triples if "hasOutputCondition" in t.predicate]

        assert len(input_links) == 1
        assert len(output_links) == 1


class TestYAWLRDFBridgeFlows:
    """Tests for converting flows to RDF."""

    def test_flows_converted(self, bridge: YAWLRDFBridge, sample_spec: VendorSpec) -> None:
        """Flows are converted to RDF."""
        triples = bridge.spec_to_rdf(sample_spec)

        flow_types = [t for t in triples if "YFlow" in t.object]
        assert len(flow_types) == 3

    def test_flows_have_source_target(self, bridge: YAWLRDFBridge, sample_spec: VendorSpec) -> None:
        """Flows have source and target."""
        triples = bridge.spec_to_rdf(sample_spec)

        source_links = [t for t in triples if "hasSource" in t.predicate]
        target_links = [t for t in triples if "hasTarget" in t.predicate]

        assert len(source_links) == 3
        assert len(target_links) == 3

    def test_flow_predicates(self, bridge: YAWLRDFBridge, sample_spec: VendorSpec) -> None:
        """Conditional flows have predicates."""
        triples = bridge.spec_to_rdf(sample_spec)

        pred_triples = [t for t in triples if "/flow/" in t.subject and "predicate" in t.predicate]
        assert any("/data/x > 0" in t.object for t in pred_triples)


class TestYAWLRDFBridgeVariables:
    """Tests for converting variables to RDF."""

    def test_variables_converted(self, bridge: YAWLRDFBridge, sample_spec: VendorSpec) -> None:
        """Variables are converted to RDF."""
        triples = bridge.spec_to_rdf(sample_spec)

        var_types = [t for t in triples if "YVariable" in t.object]
        assert len(var_types) == 2

    def test_variables_have_datatypes(self, bridge: YAWLRDFBridge, sample_spec: VendorSpec) -> None:
        """Variables have data types."""
        triples = bridge.spec_to_rdf(sample_spec)

        datatype_triples = [t for t in triples if "dataType" in t.predicate]
        assert any("xs:integer" in t.object for t in datatype_triples)
        assert any("xs:string" in t.object for t in datatype_triples)


class TestYAWLRDFBridgeDecompositions:
    """Tests for converting decompositions to RDF."""

    def test_decompositions_converted(self, bridge: YAWLRDFBridge, sample_spec: VendorSpec) -> None:
        """Decompositions are converted to RDF."""
        triples = bridge.spec_to_rdf(sample_spec)

        decomp_types = [t for t in triples if "YDecomposition" in t.object]
        assert len(decomp_types) >= 1

    def test_decomposition_params(self, bridge: YAWLRDFBridge, sample_spec: VendorSpec) -> None:
        """Decompositions have input/output params."""
        triples = bridge.spec_to_rdf(sample_spec)

        input_params = [t for t in triples if "hasInputParam" in t.predicate]
        output_params = [t for t in triples if "hasOutputParam" in t.predicate]

        assert len(input_params) >= 1
        assert len(output_params) >= 1


class TestYAWLRDFBridgeSerialization:
    """Tests for RDF serialization."""

    def test_to_turtle_includes_prefixes(self, bridge: YAWLRDFBridge, sample_spec: VendorSpec) -> None:
        """Turtle output includes prefixes."""
        triples = bridge.spec_to_rdf(sample_spec)
        turtle = bridge.to_turtle(triples)

        assert "@prefix" in turtle
        assert "rdf:" in turtle or "http://www.w3.org/1999/02/22-rdf-syntax-ns#" in turtle

    def test_to_turtle_includes_base(self, bridge: YAWLRDFBridge, sample_spec: VendorSpec) -> None:
        """Turtle output includes base URI."""
        triples = bridge.spec_to_rdf(sample_spec)
        turtle = bridge.to_turtle(triples)

        assert "@base" in turtle

    def test_to_ntriples_valid(self, bridge: YAWLRDFBridge, sample_spec: VendorSpec) -> None:
        """N-Triples output is valid."""
        triples = bridge.spec_to_rdf(sample_spec)
        ntriples = bridge.to_ntriples(triples)

        lines = [line for line in ntriples.split("\n") if line.strip()]
        assert len(lines) > 0
        assert all(line.endswith(".") for line in lines)


class TestYAWLRDFBridgeVendorSpecs:
    """Tests with real vendor specifications."""

    def test_maketrip_to_rdf(self, bridge: YAWLRDFBridge, loader: VendorSpecLoader) -> None:
        """Maketrip spec converts to RDF."""
        if not loader.vendor_path.exists():
            pytest.skip("Vendor directory not available")

        spec = loader.load_spec("maketrip1.xml")
        assert spec is not None

        triples = bridge.spec_to_rdf(spec)

        assert len(triples) > 0
        # Should have all tasks from maketrip
        task_types = [t for t in triples if "YTask" in t.object]
        assert len(task_types) >= 5  # register, flight, hotel, car, pay

    def test_maketrip_turtle_valid(self, bridge: YAWLRDFBridge, loader: VendorSpecLoader) -> None:
        """Maketrip Turtle output is valid."""
        if not loader.vendor_path.exists():
            pytest.skip("Vendor directory not available")

        spec = loader.load_spec("maketrip1.xml")
        assert spec is not None

        triples = bridge.spec_to_rdf(spec)
        turtle = bridge.to_turtle(triples)

        # Basic validation
        assert "@prefix" in turtle
        assert "YSpecification" in turtle
        assert "make_trip" in turtle  # root net ID

    def test_all_vendor_specs_convert(self, bridge: YAWLRDFBridge, loader: VendorSpecLoader) -> None:
        """All vendor specs convert to RDF."""
        if not loader.vendor_path.exists():
            pytest.skip("Vendor directory not available")

        specs = loader.load_all_specs()

        for spec in specs:
            triples = bridge.spec_to_rdf(spec)
            assert len(triples) > 0, f"No triples for {spec.uri}"

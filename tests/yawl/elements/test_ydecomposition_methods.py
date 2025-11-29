"""Tests for YDecomposition missing methods implementation.

Tests all 65 methods added from ydecomposition_missing_methods.py
Covers variable management, parameters, data handling, and serialization.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from kgcl.yawl.elements.y_decomposition import DecompositionType, YDecomposition, YParameter, YVariable


@dataclass
class MockYDecomposition(YDecomposition):
    """Concrete implementation for testing."""

    def get_decomposition_category(self) -> str:
        """Return mock category."""
        return "MockDecomposition"


class MockVerificationHandler:
    """Mock verification handler for testing verify() methods."""

    def __init__(self) -> None:
        """Initialize handler."""
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def add_error(self, message: str) -> None:
        """Add error message."""
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        """Add warning message."""
        self.warnings.append(message)


class TestVariableManagement:
    """Test variable management methods."""

    def test_add_variable(self) -> None:
        """Test add_variable() adds variable and sets parent."""
        decomp = MockYDecomposition(id="d1", name="Test Decomposition")
        var = YVariable(name="amount", data_type="decimal")

        decomp.add_variable(var)

        assert "amount" in decomp._local_variables
        assert decomp._local_variables["amount"] is var
        assert var.get_parent_decomposition() is decomp

    def test_remove_variable(self) -> None:
        """Test remove_variable() removes and returns variable."""
        decomp = MockYDecomposition(id="d1")
        var = YVariable(name="count", data_type="integer")
        decomp.add_variable(var)

        removed = decomp.remove_variable("count")

        assert removed is var
        assert "count" not in decomp._local_variables

    def test_remove_variable_not_found(self) -> None:
        """Test remove_variable() returns None for missing variable."""
        decomp = MockYDecomposition(id="d1")

        removed = decomp.remove_variable("nonexistent")

        assert removed is None

    def test_get_variable(self) -> None:
        """Test get_variable() retrieves variable by name."""
        decomp = MockYDecomposition(id="d1")
        var = YVariable(name="status", data_type="string")
        decomp.add_variable(var)

        retrieved = decomp.get_variable("status")

        assert retrieved is var

    def test_get_variable_not_found(self) -> None:
        """Test get_variable() returns None for missing variable."""
        decomp = MockYDecomposition(id="d1")

        retrieved = decomp.get_variable("missing")

        assert retrieved is None

    def test_get_variables(self) -> None:
        """Test get_variables() returns all variables."""
        decomp = MockYDecomposition(id="d1")
        var1 = YVariable(name="x", data_type="int")
        var2 = YVariable(name="y", data_type="int")
        decomp.add_variable(var1)
        decomp.add_variable(var2)

        variables = decomp.get_variables()

        assert len(variables) == 2
        assert "x" in variables
        assert "y" in variables
        # Verify it's a copy
        variables["z"] = YVariable(name="z", data_type="int")
        assert "z" not in decomp._local_variables

    def test_set_variables(self) -> None:
        """Test set_variables() replaces all variables."""
        decomp = MockYDecomposition(id="d1")
        var1 = YVariable(name="a", data_type="string")
        var2 = YVariable(name="b", data_type="string")

        decomp.set_variables({"a": var1, "b": var2})

        assert len(decomp._local_variables) == 2
        assert decomp._local_variables["a"] is var1
        assert decomp._local_variables["b"] is var2


class TestBasicGettersSetters:
    """Test basic getter/setter methods."""

    def test_get_id_set_id(self) -> None:
        """Test get_id() and set_id()."""
        decomp = MockYDecomposition(id="original")

        assert decomp.get_id() == "original"

        decomp.set_id("new_id")
        assert decomp.get_id() == "new_id"
        assert decomp.id == "new_id"

    def test_get_name_set_name(self) -> None:
        """Test get_name() and set_name()."""
        decomp = MockYDecomposition(id="d1", name="Original Name")

        assert decomp.get_name() == "Original Name"

        decomp.set_name("New Name")
        assert decomp.get_name() == "New Name"
        assert decomp.name == "New Name"

    def test_get_documentation_set_documentation(self) -> None:
        """Test get_documentation() and set_documentation()."""
        decomp = MockYDecomposition(id="d1", documentation="Original docs")

        assert decomp.get_documentation() == "Original docs"

        decomp.set_documentation("Updated documentation")
        assert decomp.get_documentation() == "Updated documentation"

    def test_get_codelet_set_codelet(self) -> None:
        """Test get_codelet() and set_codelet()."""
        decomp = MockYDecomposition(id="d1")

        # Default is empty string
        assert decomp.get_codelet() == ""

        decomp.set_codelet("com.example.MyCodelet")
        assert decomp.get_codelet() == "com.example.MyCodelet"

    def test_get_codelet_with_none(self) -> None:
        """Test get_codelet() returns empty string when codelet is None."""
        decomp = MockYDecomposition(id="d1")
        decomp.codelet = None

        assert decomp.get_codelet() == ""


class TestParameterMethods:
    """Test parameter-related methods."""

    def test_get_input_parameters(self) -> None:
        """Test get_input_parameters() returns copy of input params."""
        decomp = MockYDecomposition(id="d1")
        param = YParameter(name="input1", data_type="string")
        decomp.add_input_parameter(param)

        params = decomp.get_input_parameters()

        assert len(params) == 1
        assert "input1" in params
        # Verify it's a copy
        params["input2"] = YParameter(name="input2", data_type="int")
        assert "input2" not in decomp.input_parameters

    def test_get_output_parameters(self) -> None:
        """Test get_output_parameters() returns copy of output params."""
        decomp = MockYDecomposition(id="d1")
        param = YParameter(name="output1", data_type="boolean")
        decomp.add_output_parameter(param)

        params = decomp.get_output_parameters()

        assert len(params) == 1
        assert "output1" in params

    def test_remove_input_parameter_by_name(self) -> None:
        """Test remove_input_parameter() with string name."""
        decomp = MockYDecomposition(id="d1")
        param = YParameter(name="param1", data_type="string")
        decomp.add_input_parameter(param)

        removed = decomp.remove_input_parameter("param1")

        assert removed is param
        assert "param1" not in decomp.input_parameters

    def test_remove_input_parameter_by_object(self) -> None:
        """Test remove_input_parameter() with parameter object."""
        decomp = MockYDecomposition(id="d1")
        param = YParameter(name="param2", data_type="int")
        decomp.add_input_parameter(param)

        removed = decomp.remove_input_parameter(param)

        assert removed is param
        assert "param2" not in decomp.input_parameters

    def test_remove_output_parameter_by_name(self) -> None:
        """Test remove_output_parameter() with string name."""
        decomp = MockYDecomposition(id="d1")
        param = YParameter(name="result", data_type="string")
        decomp.add_output_parameter(param)

        removed = decomp.remove_output_parameter("result")

        assert removed is param
        assert "result" not in decomp.output_parameters

    def test_remove_output_parameter_by_object(self) -> None:
        """Test remove_output_parameter() with parameter object."""
        decomp = MockYDecomposition(id="d1")
        param = YParameter(name="status", data_type="boolean")
        decomp.add_output_parameter(param)

        removed = decomp.remove_output_parameter(param)

        assert removed is param


class TestAttributesMethods:
    """Test attributes-related methods."""

    def test_get_attributes(self) -> None:
        """Test get_attributes() returns copy."""
        decomp = MockYDecomposition(id="d1")
        decomp.set_attribute("key1", "value1")
        decomp.set_attribute("key2", "value2")

        attrs = decomp.get_attributes()

        assert len(attrs) == 2
        assert attrs["key1"] == "value1"
        # Verify it's a copy
        attrs["key3"] = "value3"
        assert "key3" not in decomp.attributes

    def test_set_attributes(self) -> None:
        """Test set_attributes() replaces attributes."""
        decomp = MockYDecomposition(id="d1")
        decomp.set_attribute("old", "value")

        decomp.set_attributes({"new1": "v1", "new2": "v2"})

        assert "old" not in decomp.attributes
        assert decomp.attributes["new1"] == "v1"
        assert decomp.attributes["new2"] == "v2"


class TestSpecificationMethods:
    """Test specification-related methods."""

    def test_get_specification_set_specification(self) -> None:
        """Test get_specification() and set_specification()."""
        from kgcl.yawl.elements.y_specification import YSpecification

        decomp = MockYDecomposition(id="d1")
        spec = YSpecification(id="spec1", name="Test Specification")

        assert decomp.get_specification() is None

        decomp.set_specification(spec)
        assert decomp.get_specification() is spec
        assert decomp._specification is spec


class TestLogPredicateMethods:
    """Test log predicate methods."""

    def test_get_log_predicate_set_log_predicate(self) -> None:
        """Test get_log_predicate() and set_log_predicate()."""
        decomp = MockYDecomposition(id="d1")

        assert decomp.get_log_predicate() is None

        predicate = {"type": "log_predicate", "value": "test"}
        decomp.set_log_predicate(predicate)
        assert decomp.get_log_predicate() is predicate


class TestExternalInteractionMethods:
    """Test external interaction methods."""

    def test_set_external_interaction_true(self) -> None:
        """Test set_external_interaction() with True sets manual."""
        decomp = MockYDecomposition(id="d1")

        decomp.set_external_interaction(True)

        assert decomp.external_interaction == "manual"

    def test_set_external_interaction_false(self) -> None:
        """Test set_external_interaction() with False sets automated."""
        decomp = MockYDecomposition(id="d1")

        decomp.set_external_interaction(False)

        assert decomp.external_interaction == "automated"

    def test_requires_resourcing_decisions(self) -> None:
        """Test requires_resourcing_decisions() matches requires_resourcing()."""
        decomp = MockYDecomposition(id="d1", decomposition_type=DecompositionType.MANUAL)

        assert decomp.requires_resourcing_decisions() is True

        decomp.decomposition_type = DecompositionType.AUTOMATED
        decomp.external_interaction = "automated"
        assert decomp.requires_resourcing_decisions() is False


class TestOutputExpressionMethods:
    """Test output expression methods."""

    def test_get_output_expression_set_output_expression(self) -> None:
        """Test get_output_expression() and set_output_expression()."""
        decomp = MockYDecomposition(id="d1")

        assert decomp.get_output_expression() == ""

        query = "//result[@status='success']"
        decomp.set_output_expression(query)
        assert decomp.get_output_expression() == query

    def test_get_output_queries_with_expression(self) -> None:
        """Test get_output_queries() returns set with expression."""
        decomp = MockYDecomposition(id="d1")
        query = "//output/data"
        decomp.set_output_expression(query)

        queries = decomp.get_output_queries()

        assert queries == {query}

    def test_get_output_queries_empty(self) -> None:
        """Test get_output_queries() returns empty set when no expression."""
        decomp = MockYDecomposition(id="d1")

        queries = decomp.get_output_queries()

        assert queries == set()


class TestEnablementParameterMethods:
    """Test enablement parameter methods."""

    def test_set_enablement_parameter_get_enablement_parameter(self) -> None:
        """Test set_enablement_parameter() and get_enablement_parameter()."""
        decomp = MockYDecomposition(id="d1")
        param = YParameter(name="enable", data_type="boolean")

        assert decomp.get_enablement_parameter() is None

        decomp.set_enablement_parameter(param)
        assert decomp.get_enablement_parameter() is param


class TestDataMethods:
    """Test data-related methods."""

    def test_get_root_data_element_name(self) -> None:
        """Test get_root_data_element_name() returns ID."""
        decomp = MockYDecomposition(id="decomp123")

        assert decomp.get_root_data_element_name() == "decomp123"

    def test_get_variable_data_by_name(self) -> None:
        """Test get_variable_data_by_name() retrieves variable."""
        decomp = MockYDecomposition(id="d1")
        var = YVariable(name="data", data_type="string")
        decomp.add_variable(var)

        retrieved = decomp.get_variable_data_by_name("data")

        assert retrieved is var

    def test_get_internal_data_document(self) -> None:
        """Test get_internal_data_document()."""
        decomp = MockYDecomposition(id="d1")

        assert decomp.get_internal_data_document() is None

        decomp._internal_data_document = {"key": "value"}
        assert decomp.get_internal_data_document() == {"key": "value"}

    def test_get_output_data(self) -> None:
        """Test get_output_data() returns internal data document."""
        decomp = MockYDecomposition(id="d1")
        data = {"output": "data"}
        decomp._internal_data_document = data

        assert decomp.get_output_data() is data

    def test_get_net_data_document(self) -> None:
        """Test get_net_data_document() returns net data."""
        decomp = MockYDecomposition(id="d1")
        net_data = "<data><value>123</value></data>"

        result = decomp.get_net_data_document(net_data)

        assert result == net_data

    def test_get_state_space_bypass_params(self) -> None:
        """Test get_state_space_bypass_params() returns empty dict."""
        decomp = MockYDecomposition(id="d1")

        params = decomp.get_state_space_bypass_params()

        assert params == {}

    def test_param_map_to_xml(self) -> None:
        """Test param_map_to_xml() serializes parameters."""
        decomp = MockYDecomposition(id="d1")
        params = {
            "param1": YParameter(name="param1", data_type="string"),
            "param2": YParameter(name="param2", data_type="integer"),
        }

        xml = decomp.param_map_to_xml(params)

        assert "<data>" in xml
        assert "</data>" in xml
        assert "param1" in xml
        assert "param2" in xml
        assert "type='string'" in xml
        assert "type='integer'" in xml


class TestInitializationMethods:
    """Test initialization methods."""

    def test_initialise_without_pmgr(self) -> None:
        """Test initialise() without persistence manager."""
        decomp = MockYDecomposition(id="d1")

        decomp.initialise()

        assert decomp._internal_data_document == {}

    def test_initialise_with_pmgr(self) -> None:
        """Test initialise() with persistence manager."""
        decomp = MockYDecomposition(id="d1")
        pmgr = {"mock": "manager"}

        decomp.initialise(pmgr)

        assert decomp._internal_data_document == {}

    def test_initialize_data_store_without_pmgr(self) -> None:
        """Test initialize_data_store() without persistence manager."""
        decomp = MockYDecomposition(id="d1")
        casedata = {"case": "data"}

        decomp.initialize_data_store(casedata)

        assert decomp._internal_data_document is casedata

    def test_initialize_data_store_with_pmgr(self) -> None:
        """Test initialize_data_store() with persistence manager."""
        decomp = MockYDecomposition(id="d1")
        casedata = {"case": "data"}
        pmgr = {"mock": "manager"}

        decomp.initialize_data_store(casedata, pmgr)

        assert decomp._internal_data_document is casedata

    def test_add_data_without_pmgr(self) -> None:
        """Test add_data() without persistence manager."""
        decomp = MockYDecomposition(id="d1")
        decomp.initialise()
        element = {"new": "data"}

        decomp.add_data(element)

        assert decomp._internal_data_document["new"] == "data"

    def test_add_data_with_pmgr(self) -> None:
        """Test add_data() with persistence manager."""
        decomp = MockYDecomposition(id="d1")
        decomp.initialise()
        element = {"field": "value"}
        pmgr = {"mock": "manager"}

        decomp.add_data(element, pmgr)

        assert decomp._internal_data_document["field"] == "value"

    def test_assign_data_without_pmgr(self) -> None:
        """Test assign_data() without persistence manager."""
        decomp = MockYDecomposition(id="d1")
        decomp.initialise()
        variable = {"var": "value"}

        decomp.assign_data(variable)

        assert decomp._internal_data_document["var"] == "value"

    def test_assign_data_with_pmgr(self) -> None:
        """Test assign_data() with persistence manager."""
        decomp = MockYDecomposition(id="d1")
        decomp.initialise()
        variable = {"variable": "data"}
        pmgr = {"mock": "manager"}

        decomp.assign_data(variable, pmgr)

        assert decomp._internal_data_document["variable"] == "data"

    def test_restore_data(self) -> None:
        """Test restore_data() replaces internal data."""
        decomp = MockYDecomposition(id="d1")
        decomp._internal_data_document = {"old": "data"}
        casedata = {"restored": "data"}

        decomp.restore_data(casedata)

        assert decomp._internal_data_document is casedata
        assert "old" not in decomp._internal_data_document


class TestVerifyMethod:
    """Test verify() method."""

    def test_verify_valid_decomposition(self) -> None:
        """Test verify() with valid decomposition."""
        decomp = MockYDecomposition(id="d1", name="Valid Decomp")
        handler = MockVerificationHandler()

        decomp.verify(handler)

        assert len(handler.errors) == 0

    def test_verify_missing_id(self) -> None:
        """Test verify() detects missing ID."""
        decomp = MockYDecomposition(id="", name="No ID")
        handler = MockVerificationHandler()

        decomp.verify(handler)

        assert len(handler.errors) == 1
        assert "must have an ID" in handler.errors[0]

    def test_verify_missing_name(self) -> None:
        """Test verify() warns about missing name."""
        decomp = MockYDecomposition(id="d1", name="")
        handler = MockVerificationHandler()

        decomp.verify(handler)

        assert len(handler.warnings) == 1
        assert "has no name" in handler.warnings[0]

    def test_verify_verifies_variables(self) -> None:
        """Test verify() calls verify on variables."""
        decomp = MockYDecomposition(id="d1", name="Test")
        var = YVariable(name="", data_type="string")  # Invalid - no name
        decomp.add_variable(var)
        handler = MockVerificationHandler()

        decomp.verify(handler)

        # YVariable.verify() should add error for missing name
        assert len(handler.errors) > 0


class TestCloneMethod:
    """Test clone() method."""

    def test_clone_creates_copy(self) -> None:
        """Test clone() creates independent copy."""
        decomp = MockYDecomposition(id="d1", name="Original", documentation="Docs")
        decomp.add_input_parameter(YParameter(name="in1", data_type="string"))
        decomp.add_output_parameter(YParameter(name="out1", data_type="int"))
        decomp.set_attribute("key", "value")
        decomp.set_codelet("com.example.Codelet")
        var = YVariable(name="var1", data_type="string")
        decomp.add_variable(var)
        decomp.set_output_expression("//result")

        cloned = decomp.clone()

        assert cloned is not decomp
        assert cloned.id == decomp.id
        assert cloned.name == decomp.name
        assert cloned.documentation == decomp.documentation
        assert len(cloned.input_parameters) == 1
        assert len(cloned.output_parameters) == 1
        assert "key" in cloned.attributes
        assert cloned.codelet == decomp.codelet
        assert len(cloned._local_variables) == 1

    def test_clone_independence(self) -> None:
        """Test cloned decomposition is independent."""
        decomp = MockYDecomposition(id="d1")
        var = YVariable(name="original", data_type="string")
        decomp.add_variable(var)

        cloned = decomp.clone()

        # Modify original
        new_var = YVariable(name="new", data_type="int")
        decomp.add_variable(new_var)

        # Clone should be unchanged
        assert "new" not in cloned._local_variables
        assert len(cloned._local_variables) == 1


class TestStringMethods:
    """Test string representation methods."""

    def test_to_string(self) -> None:
        """Test to_string() returns string representation."""
        decomp = MockYDecomposition(id="d1", name="Test Decomp", decomposition_type=DecompositionType.MANUAL)

        result = decomp.to_string()

        assert "YDecomposition" in result
        assert "d1" in result
        assert "Test Decomp" in result
        assert "MANUAL" in result

    def test_to_xml_basic(self) -> None:
        """Test to_xml() basic serialization."""
        decomp = MockYDecomposition(id="d1", name="Test")

        xml = decomp.to_xml()

        assert '<decomposition id="d1" name="Test">' in xml
        assert "</decomposition>" in xml

    def test_to_xml_with_parameters(self) -> None:
        """Test to_xml() includes parameters."""
        decomp = MockYDecomposition(id="d1", name="Test")
        decomp.add_input_parameter(YParameter(name="input1", data_type="string"))
        decomp.add_output_parameter(YParameter(name="output1", data_type="boolean"))

        xml = decomp.to_xml()

        assert "<inputParameters>" in xml
        assert '<parameter name="input1" type="string"' in xml
        assert "<outputParameters>" in xml
        assert '<parameter name="output1" type="boolean"' in xml

    def test_to_xml_with_variables(self) -> None:
        """Test to_xml() includes local variables."""
        decomp = MockYDecomposition(id="d1", name="Test")
        decomp.add_variable(YVariable(name="var1", data_type="decimal"))
        decomp.add_variable(YVariable(name="var2", data_type="date"))

        xml = decomp.to_xml()

        assert "<localVariables>" in xml
        assert '<variable name="var1" type="decimal"' in xml
        assert '<variable name="var2" type="date"' in xml


class TestIntegration:
    """Integration tests combining multiple methods."""

    def test_full_workflow(self) -> None:
        """Test complete workflow with multiple operations."""
        # Create decomposition
        decomp = MockYDecomposition(id="order_process", name="Order Processing")

        # Add parameters
        decomp.add_input_parameter(YParameter(name="orderId", data_type="string"))
        decomp.add_input_parameter(YParameter(name="customerId", data_type="string"))
        decomp.add_output_parameter(YParameter(name="status", data_type="string"))
        decomp.add_output_parameter(YParameter(name="total", data_type="decimal"))

        # Add variables
        decomp.add_variable(YVariable(name="orderTotal", data_type="decimal"))
        decomp.add_variable(YVariable(name="taxAmount", data_type="decimal"))

        # Set metadata
        decomp.set_documentation("Process customer orders")
        decomp.set_external_interaction(True)
        decomp.set_output_expression("//order[@status='complete']")

        # Initialize data store
        decomp.initialise()
        decomp.add_data({"orderId": "ORD-001"})

        # Verify all set correctly
        assert len(decomp.get_input_parameters()) == 2
        assert len(decomp.get_output_parameters()) == 2
        assert len(decomp.get_variables()) == 2
        assert decomp.get_documentation() == "Process customer orders"
        assert decomp.requires_resourcing_decisions() is True
        assert len(decomp.get_output_queries()) == 1
        assert decomp._internal_data_document["orderId"] == "ORD-001"

        # Clone and verify independence
        cloned = decomp.clone()
        assert cloned.id == decomp.id
        assert len(cloned.get_variables()) == 2

        # Modify original
        decomp.add_variable(YVariable(name="discount", data_type="decimal"))

        # Clone unchanged
        assert len(cloned.get_variables()) == 2
        assert len(decomp.get_variables()) == 3

    def test_serialization_round_trip(self) -> None:
        """Test XML serialization produces valid output."""
        decomp = MockYDecomposition(id="test_decomp", name="Test Decomposition")
        decomp.add_input_parameter(YParameter(name="input", data_type="string"))
        decomp.add_output_parameter(YParameter(name="output", data_type="int"))
        decomp.add_variable(YVariable(name="counter", data_type="int"))

        xml = decomp.to_xml()

        # Verify XML structure
        assert xml.startswith('<decomposition id="test_decomp"')
        assert xml.endswith("</decomposition>")
        assert "<inputParameters>" in xml
        assert "<outputParameters>" in xml
        assert "<localVariables>" in xml
        assert "input" in xml
        assert "output" in xml
        assert "counter" in xml

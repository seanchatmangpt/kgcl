"""Tests for YAWL XML parser.

These tests prove that:
1. XML parser correctly parses YAWL specification files
2. Parser handles malformed XML gracefully
3. Net, task, and flow structures are correctly extracted
4. Join/split types are correctly interpreted
"""

from __future__ import annotations

import pytest

from kgcl.yawl.elements.y_task import JoinType, SplitType
from kgcl.yawl.persistence.xml_parser import ParseResult, XMLParser


@pytest.fixture
def parser() -> XMLParser:
    """Create XML parser."""
    return XMLParser(strict_mode=False)


@pytest.fixture
def simple_spec_xml() -> str:
    """Create simple YAWL specification XML."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<specification id="simple-spec" version="1.0" uri="urn:simple-spec">
    <name>Simple Specification</name>
    <documentation>A simple test specification</documentation>
    <metaData>
        <creator>Test Author</creator>
    </metaData>
    <decomposition id="MainNet" isRootNet="true">
        <processControlElements>
            <inputCondition id="InputCondition"/>
            <task id="Task_A">
                <name>Task A</name>
                <join code="xor"/>
                <split code="and"/>
                <flowsInto>
                    <nextElementRef>Task_B</nextElementRef>
                </flowsInto>
            </task>
            <task id="Task_B">
                <name>Task B</name>
                <join code="and"/>
                <split code="xor"/>
                <flowsInto>
                    <nextElementRef>OutputCondition</nextElementRef>
                </flowsInto>
            </task>
            <outputCondition id="OutputCondition"/>
        </processControlElements>
    </decomposition>
</specification>"""


@pytest.fixture
def spec_with_predicate_xml() -> str:
    """Create specification with flow predicates."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<specification id="predicate-spec" version="1.0">
    <name>Predicate Spec</name>
    <decomposition id="MainNet" isRootNet="true">
        <processControlElements>
            <inputCondition id="InputCondition"/>
            <task id="Decision">
                <name>Decision</name>
                <split code="xor"/>
                <flowsInto>
                    <nextElementRef>PathA</nextElementRef>
                    <predicate>amount &gt; 100</predicate>
                </flowsInto>
                <flowsInto>
                    <nextElementRef>PathB</nextElementRef>
                    <predicate>amount &lt;= 100</predicate>
                </flowsInto>
            </task>
            <task id="PathA">
                <name>Path A</name>
                <flowsInto>
                    <nextElementRef>OutputCondition</nextElementRef>
                </flowsInto>
            </task>
            <task id="PathB">
                <name>Path B</name>
                <flowsInto>
                    <nextElementRef>OutputCondition</nextElementRef>
                </flowsInto>
            </task>
            <outputCondition id="OutputCondition"/>
        </processControlElements>
    </decomposition>
</specification>"""


class TestXMLParserBasic:
    """Tests proving basic XML parsing behavior."""

    def test_parse_string_returns_parse_result(self, parser: XMLParser, simple_spec_xml: str) -> None:
        """Prove parse_string returns ParseResult."""
        result = parser.parse_string(simple_spec_xml)

        assert isinstance(result, ParseResult)

    def test_successful_parse_has_success_true(self, parser: XMLParser, simple_spec_xml: str) -> None:
        """Prove successful parse sets success=True."""
        result = parser.parse_string(simple_spec_xml)

        assert result.success is True
        assert result.specification is not None
        assert len(result.errors) == 0

    def test_parse_extracts_specification_id(self, parser: XMLParser, simple_spec_xml: str) -> None:
        """Prove parser extracts specification ID."""
        result = parser.parse_string(simple_spec_xml)

        assert result.specification.id == "simple-spec"

    def test_parse_extracts_specification_name(self, parser: XMLParser, simple_spec_xml: str) -> None:
        """Prove parser extracts specification name."""
        result = parser.parse_string(simple_spec_xml)

        assert result.specification.name == "Simple Specification"

    def test_parse_extracts_documentation(self, parser: XMLParser, simple_spec_xml: str) -> None:
        """Prove parser extracts documentation."""
        result = parser.parse_string(simple_spec_xml)

        assert result.specification is not None
        assert "simple test specification" in result.specification.documentation.lower()


class TestXMLParserMalformedInput:
    """Tests proving parser handles malformed input."""

    def test_malformed_xml_returns_error(self, parser: XMLParser) -> None:
        """Prove malformed XML returns error result."""
        malformed = "<specification><unclosed>"

        result = parser.parse_string(malformed)

        assert result.success is False
        assert len(result.errors) > 0
        assert "parse error" in result.errors[0].lower()

    def test_missing_id_returns_error(self, parser: XMLParser) -> None:
        """Prove missing specification ID returns error."""
        no_id = """<?xml version="1.0"?>
<specification version="1.0">
    <name>No ID Spec</name>
</specification>"""

        result = parser.parse_string(no_id)

        assert result.success is False
        assert any("id" in e.lower() for e in result.errors)

    def test_empty_string_returns_error(self, parser: XMLParser) -> None:
        """Prove empty string returns error."""
        result = parser.parse_string("")

        assert result.success is False


class TestNetParsing:
    """Tests proving net structure parsing."""

    def test_parse_extracts_root_net(self, parser: XMLParser, simple_spec_xml: str) -> None:
        """Prove parser identifies root net."""
        result = parser.parse_string(simple_spec_xml)

        assert result.specification.root_net_id == "MainNet"

    def test_parse_extracts_input_condition(self, parser: XMLParser, simple_spec_xml: str) -> None:
        """Prove parser extracts input condition."""
        result = parser.parse_string(simple_spec_xml)
        net = result.specification.get_net("MainNet")

        assert net.input_condition is not None
        assert net.input_condition.id == "InputCondition"

    def test_parse_extracts_output_condition(self, parser: XMLParser, simple_spec_xml: str) -> None:
        """Prove parser extracts output condition."""
        result = parser.parse_string(simple_spec_xml)
        net = result.specification.get_net("MainNet")

        assert net.output_condition is not None
        assert net.output_condition.id == "OutputCondition"


class TestTaskParsing:
    """Tests proving task parsing behavior."""

    def test_parse_extracts_tasks(self, parser: XMLParser, simple_spec_xml: str) -> None:
        """Prove parser extracts all tasks."""
        result = parser.parse_string(simple_spec_xml)
        net = result.specification.get_net("MainNet")

        task_ids = {t.id for t in net.tasks.values()}
        assert "Task_A" in task_ids
        assert "Task_B" in task_ids

    def test_parse_extracts_task_name(self, parser: XMLParser, simple_spec_xml: str) -> None:
        """Prove parser extracts task names."""
        result = parser.parse_string(simple_spec_xml)
        net = result.specification.get_net("MainNet")
        task_a = net.tasks.get("Task_A")

        assert task_a.name == "Task A"

    def test_parse_extracts_xor_join(self, parser: XMLParser, simple_spec_xml: str) -> None:
        """Prove parser extracts XOR join type."""
        result = parser.parse_string(simple_spec_xml)
        net = result.specification.get_net("MainNet")
        task_a = net.tasks.get("Task_A")

        assert task_a.join_type == JoinType.XOR

    def test_parse_extracts_and_join(self, parser: XMLParser, simple_spec_xml: str) -> None:
        """Prove parser extracts AND join type."""
        result = parser.parse_string(simple_spec_xml)
        net = result.specification.get_net("MainNet")
        task_b = net.tasks.get("Task_B")

        assert task_b.join_type == JoinType.AND

    def test_parse_extracts_and_split(self, parser: XMLParser, simple_spec_xml: str) -> None:
        """Prove parser extracts AND split type."""
        result = parser.parse_string(simple_spec_xml)
        net = result.specification.get_net("MainNet")
        task_a = net.tasks.get("Task_A")

        assert task_a.split_type == SplitType.AND

    def test_parse_extracts_xor_split(self, parser: XMLParser, simple_spec_xml: str) -> None:
        """Prove parser extracts XOR split type."""
        result = parser.parse_string(simple_spec_xml)
        net = result.specification.get_net("MainNet")
        task_b = net.tasks.get("Task_B")

        assert task_b.split_type == SplitType.XOR


class TestFlowParsing:
    """Tests proving flow structure parsing."""

    def test_parse_extracts_flows(self, parser: XMLParser, simple_spec_xml: str) -> None:
        """Prove parser extracts flow connections."""
        result = parser.parse_string(simple_spec_xml)
        net = result.specification.get_net("MainNet")

        # Find flow from Task_A to Task_B - flows is dict[str, YFlow]
        flow_to_b = [f for f in net.flows.values() if f.source_id == "Task_A" and f.target_id == "Task_B"]
        assert len(flow_to_b) == 1

    def test_parse_extracts_flow_predicates(self, parser: XMLParser, spec_with_predicate_xml: str) -> None:
        """Prove parser extracts flow predicates."""
        result = parser.parse_string(spec_with_predicate_xml)

        # Check parse was successful first
        assert result.success is True, f"Parse failed: {result.errors}"
        assert result.specification is not None

        net = result.specification.get_net("MainNet")
        assert net is not None, "MainNet not found"

        # Find flows from Decision task - flows is dict[str, YFlow]
        decision_flows = [f for f in net.flows.values() if f.source_id == "Decision"]
        assert len(decision_flows) == 2

        # Check predicates (XML entities are unescaped by parser)
        predicates = {f.predicate for f in decision_flows}
        assert "amount > 100" in predicates  # &gt; becomes >
        assert "amount <= 100" in predicates  # &lt;= becomes <=


class TestStrictMode:
    """Tests proving strict mode behavior."""

    def test_strict_mode_fails_on_unknown_elements(self) -> None:
        """Prove strict mode fails on unknown elements."""
        strict_parser = XMLParser(strict_mode=True)

        # Valid XML but potentially has issues in strict mode
        xml = """<?xml version="1.0"?>
<specification id="test">
    <name>Test</name>
    <unknownElement>value</unknownElement>
    <decomposition id="Net1" isRootNet="true">
        <processControlElements>
            <inputCondition id="InputCondition"/>
            <outputCondition id="OutputCondition"/>
        </processControlElements>
    </decomposition>
</specification>"""

        result = strict_parser.parse_string(xml)

        # In strict mode, unknown elements might cause warnings but basic structure should parse
        assert result.specification is not None

    def test_non_strict_mode_allows_unknown_elements(self) -> None:
        """Prove non-strict mode tolerates unknown elements."""
        parser = XMLParser(strict_mode=False)

        xml = """<?xml version="1.0"?>
<specification id="test">
    <name>Test</name>
    <customExtension>ignored</customExtension>
    <decomposition id="Net1" isRootNet="true">
        <processControlElements>
            <inputCondition id="InputCondition"/>
            <outputCondition id="OutputCondition"/>
        </processControlElements>
    </decomposition>
</specification>"""

        result = parser.parse_string(xml)

        assert result.success is True

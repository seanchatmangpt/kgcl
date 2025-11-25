"""Tests for external capability bridge."""

from __future__ import annotations

import tempfile
from pathlib import Path

from rdflib import Graph

from kgcl.unrdf_engine.externals import CapabilityType, ExecutionReceipt, ExternalCapabilityBridge


class TestExecutionReceipt:
    """Test ExecutionReceipt class."""

    def test_creation(self) -> None:
        """Test creating execution receipt."""
        receipt = ExecutionReceipt(
            capability_id="test-cap",
            capability_type=CapabilityType.PYTHON,
            input_data={"key": "value"},
        )

        assert receipt.capability_id == "test-cap"
        assert receipt.capability_type == CapabilityType.PYTHON
        assert receipt.input_data == {"key": "value"}
        assert receipt.exit_code == 0

    def test_to_dict(self) -> None:
        """Test converting to dictionary."""
        receipt = ExecutionReceipt(
            capability_id="test-cap",
            capability_type=CapabilityType.PYTHON,
            input_data={"input": "data"},
            output_data={"output": "result"},
            exit_code=0,
        )

        result_dict = receipt.to_dict()

        assert result_dict["capability_id"] == "test-cap"
        assert result_dict["capability_type"] == "python"
        assert result_dict["input_data"] == {"input": "data"}
        assert result_dict["output_data"] == {"output": "result"}
        assert result_dict["exit_code"] == 0

    def test_to_rdf(self) -> None:
        """Test converting to RDF."""
        receipt = ExecutionReceipt(
            capability_id="test-cap",
            capability_type=CapabilityType.PYTHON,
            input_data={"key": "value"},
            output_data={"result": "success"},
        )

        graph = Graph()
        receipt_uri = receipt.to_rdf(graph)

        assert receipt_uri is not None
        assert len(graph) > 0

        # Check that key triples exist
        triples = list(graph.triples((receipt_uri, None, None)))
        assert len(triples) > 0


class TestExternalCapabilityBridge:
    """Test ExternalCapabilityBridge class."""

    def test_initialization(self) -> None:
        """Test bridge initialization."""
        bridge = ExternalCapabilityBridge()

        assert bridge.working_dir == Path.cwd()
        assert len(bridge.get_execution_history()) == 0

    def test_initialization_with_working_dir(self) -> None:
        """Test bridge initialization with custom working directory."""
        working_dir = Path("/tmp")
        bridge = ExternalCapabilityBridge(working_dir=working_dir)

        assert bridge.working_dir == working_dir

    def test_execute_python_success(self) -> None:
        """Test executing Python script successfully."""
        # Create test script
        script_content = """
import json
import sys

data = json.load(sys.stdin)
result = {"doubled": data["value"] * 2}
print(json.dumps(result))
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(script_content)
            script_path = Path(f.name)

        try:
            bridge = ExternalCapabilityBridge()
            receipt = bridge.execute_python(
                script=script_path, input_data={"value": 5}, timeout=5.0
            )

            assert receipt.exit_code == 0
            assert receipt.output_data == {"doubled": 10}
            assert receipt.error is None

        finally:
            script_path.unlink()

    def test_execute_python_error(self) -> None:
        """Test executing Python script with error."""
        script_content = """
import sys
sys.exit(1)
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(script_content)
            script_path = Path(f.name)

        try:
            bridge = ExternalCapabilityBridge()
            receipt = bridge.execute_python(script=script_path, input_data={}, timeout=5.0)

            assert receipt.exit_code == 1
            assert receipt.error is not None

        finally:
            script_path.unlink()

    def test_execute_python_invalid_json(self) -> None:
        """Test executing Python script with invalid JSON output."""
        script_content = """
print("not valid json")
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(script_content)
            script_path = Path(f.name)

        try:
            bridge = ExternalCapabilityBridge()
            receipt = bridge.execute_python(script=script_path, input_data={}, timeout=5.0)

            assert receipt.exit_code == 1
            assert "Failed to parse JSON" in receipt.error

        finally:
            script_path.unlink()

    def test_execute_python_timeout(self) -> None:
        """Test Python script timeout."""
        script_content = """
import time
time.sleep(10)
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(script_content)
            script_path = Path(f.name)

        try:
            bridge = ExternalCapabilityBridge()
            receipt = bridge.execute_python(script=script_path, input_data={}, timeout=0.5)

            assert receipt.exit_code == 124  # Timeout exit code
            assert "timed out" in receipt.error

        finally:
            script_path.unlink()

    def test_execute_shell_success(self) -> None:
        """Test executing shell command successfully."""
        bridge = ExternalCapabilityBridge()

        # Use echo with JSON
        receipt = bridge.execute_shell(
            command=["python3", "-c", "import sys, json; print(json.dumps({'result': 'ok'}))"],
            input_data={},
            timeout=5.0,
        )

        assert receipt.exit_code == 0
        assert receipt.output_data == {"result": "ok"}

    def test_execution_history(self) -> None:
        """Test execution history tracking."""
        script_content = """
import json
import sys
print(json.dumps({"result": "ok"}))
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(script_content)
            script_path = Path(f.name)

        try:
            bridge = ExternalCapabilityBridge()

            assert len(bridge.get_execution_history()) == 0

            bridge.execute_python(script=script_path, input_data={}, timeout=5.0)

            history = bridge.get_execution_history()
            assert len(history) == 1
            assert history[0].capability_type == CapabilityType.PYTHON

        finally:
            script_path.unlink()

    def test_clear_history(self) -> None:
        """Test clearing execution history."""
        script_content = """
import json
print(json.dumps({"result": "ok"}))
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(script_content)
            script_path = Path(f.name)

        try:
            bridge = ExternalCapabilityBridge()

            bridge.execute_python(script=script_path, input_data={}, timeout=5.0)
            assert len(bridge.get_execution_history()) == 1

            bridge.clear_history()
            assert len(bridge.get_execution_history()) == 0

        finally:
            script_path.unlink()

    def test_link_to_graph(self) -> None:
        """Test linking receipt to RDF graph."""
        receipt = ExecutionReceipt(
            capability_id="test-cap",
            capability_type=CapabilityType.PYTHON,
            input_data={"key": "value"},
            output_data={"result": "success"},
        )

        bridge = ExternalCapabilityBridge()
        graph = Graph()

        receipt_uri = bridge.link_to_graph(receipt, graph)

        assert receipt_uri is not None
        assert len(graph) > 0

    def test_duration_tracking(self) -> None:
        """Test that execution duration is tracked."""
        script_content = """
import json
import time
time.sleep(0.1)
print(json.dumps({"result": "ok"}))
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(script_content)
            script_path = Path(f.name)

        try:
            bridge = ExternalCapabilityBridge()
            receipt = bridge.execute_python(script=script_path, input_data={}, timeout=5.0)

            # Should have taken at least 100ms
            assert receipt.duration_ms >= 100

        finally:
            script_path.unlink()

    def test_custom_python_executable(self) -> None:
        """Test using custom Python executable."""
        script_content = """
import json
print(json.dumps({"result": "ok"}))
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(script_content)
            script_path = Path(f.name)

        try:
            bridge = ExternalCapabilityBridge()
            receipt = bridge.execute_python(
                script=script_path,
                input_data={},
                timeout=5.0,
                python_exe="python3",  # Explicit Python 3
            )

            assert receipt.exit_code == 0

        finally:
            script_path.unlink()

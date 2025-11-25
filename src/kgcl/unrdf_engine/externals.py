"""External capability bridge for the UNRDF engine.

Enables spawning subprocesses (Python, Node, shell) with JSON I/O and receipt generation.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from opentelemetry import trace
from rdflib import Graph, Literal, Namespace, URIRef

tracer = trace.get_tracer(__name__)

UNRDF = Namespace("http://unrdf.org/ontology/")
PROV = Namespace("http://www.w3.org/ns/prov#")


class CapabilityType(Enum):
    """Types of external capabilities."""

    PYTHON = "python"
    NODE = "node"
    SHELL = "shell"


@dataclass
class ExecutionReceipt:
    """Receipt for external capability execution.

    Parameters
    ----------
    capability_id : str
        Unique identifier for the capability
    capability_type : CapabilityType
        Type of capability executed
    input_data : dict[str, Any]
        Input provided to capability
    output_data : dict[str, Any]
        Output from capability execution
    exit_code : int
        Process exit code
    timestamp : datetime
        Execution timestamp
    duration_ms : float
        Execution duration in milliseconds
    error : str, optional
        Error message if execution failed

    """

    capability_id: str
    capability_type: CapabilityType
    input_data: dict[str, Any]
    output_data: dict[str, Any] = field(default_factory=dict)
    exit_code: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: float = 0.0
    error: str | None = None
    stdout: str = ""
    stderr: str = ""

    def to_rdf(self, graph: Graph) -> URIRef:
        """Convert receipt to RDF triples.

        Parameters
        ----------
        graph : Graph
            RDF graph to add triples to

        Returns
        -------
        URIRef
            Receipt URI

        """
        receipt_uri = URIRef(f"urn:unrdf:receipt:{self.capability_id}:{self.timestamp.isoformat()}")

        # Receipt metadata
        graph.add((receipt_uri, UNRDF.capabilityId, Literal(self.capability_id)))
        graph.add((receipt_uri, UNRDF.capabilityType, Literal(self.capability_type.value)))
        graph.add((receipt_uri, PROV.endedAtTime, Literal(self.timestamp)))
        graph.add((receipt_uri, UNRDF.durationMs, Literal(self.duration_ms)))
        graph.add((receipt_uri, UNRDF.exitCode, Literal(self.exit_code)))

        # Input/output as JSON literals
        graph.add((receipt_uri, UNRDF.input, Literal(json.dumps(self.input_data))))
        graph.add((receipt_uri, UNRDF.output, Literal(json.dumps(self.output_data))))

        if self.error:
            graph.add((receipt_uri, UNRDF.error, Literal(self.error)))

        return receipt_uri

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns
        -------
        dict[str, Any]
            Receipt as dictionary

        """
        return {
            "capability_id": self.capability_id,
            "capability_type": self.capability_type.value,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "exit_code": self.exit_code,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms,
            "error": self.error,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


class ExternalCapabilityBridge:
    """Bridge for executing external capabilities with JSON I/O.

    Supports Python scripts, Node.js scripts, and shell commands with
    timeout handling, error capture, and receipt generation.

    Examples
    --------
    >>> bridge = ExternalCapabilityBridge()
    >>> receipt = bridge.execute_python(
    ...     script=Path("process_data.py"),
    ...     input_data={"features": [...]},
    ...     timeout=30.0
    ... )
    >>> if receipt.exit_code == 0:
    ...     result = receipt.output_data

    """

    def __init__(self, working_dir: Path | None = None) -> None:
        """Initialize external capability bridge.

        Parameters
        ----------
        working_dir : Path, optional
            Working directory for subprocess execution

        """
        self.working_dir = working_dir or Path.cwd()
        self._execution_history: list[ExecutionReceipt] = []

    @tracer.start_as_current_span("externals.execute_python")
    def execute_python(
        self,
        script: Path,
        input_data: dict[str, Any],
        timeout: float = 30.0,
        python_exe: str = "python3",
    ) -> ExecutionReceipt:
        """Execute a Python script with JSON input/output.

        The script receives JSON via stdin and writes JSON to stdout.

        Parameters
        ----------
        script : Path
            Path to Python script
        input_data : dict[str, Any]
            Input data (serialized to JSON)
        timeout : float, default=30.0
            Timeout in seconds
        python_exe : str, default="python3"
            Python executable to use

        Returns
        -------
        ExecutionReceipt
            Execution receipt with results

        """
        span = trace.get_current_span()
        span.set_attribute("script.path", str(script))
        span.set_attribute("timeout", timeout)

        return self._execute(
            capability_type=CapabilityType.PYTHON,
            command=[python_exe, str(script)],
            input_data=input_data,
            timeout=timeout,
            capability_id=f"python:{script.name}",
        )

    @tracer.start_as_current_span("externals.execute_node")
    def execute_node(
        self,
        script: Path,
        input_data: dict[str, Any],
        timeout: float = 30.0,
        node_exe: str = "node",
    ) -> ExecutionReceipt:
        """Execute a Node.js script with JSON input/output.

        The script receives JSON via stdin and writes JSON to stdout.

        Parameters
        ----------
        script : Path
            Path to Node.js script
        input_data : dict[str, Any]
            Input data (serialized to JSON)
        timeout : float, default=30.0
            Timeout in seconds
        node_exe : str, default="node"
            Node executable to use

        Returns
        -------
        ExecutionReceipt
            Execution receipt with results

        """
        span = trace.get_current_span()
        span.set_attribute("script.path", str(script))
        span.set_attribute("timeout", timeout)

        return self._execute(
            capability_type=CapabilityType.NODE,
            command=[node_exe, str(script)],
            input_data=input_data,
            timeout=timeout,
            capability_id=f"node:{script.name}",
        )

    @tracer.start_as_current_span("externals.execute_shell")
    def execute_shell(
        self,
        command: list[str],
        input_data: dict[str, Any],
        timeout: float = 30.0,
    ) -> ExecutionReceipt:
        """Execute a shell command with JSON input/output.

        The command receives JSON via stdin and writes JSON to stdout.

        Parameters
        ----------
        command : list[str]
            Shell command and arguments
        input_data : dict[str, Any]
            Input data (serialized to JSON)
        timeout : float, default=30.0
            Timeout in seconds

        Returns
        -------
        ExecutionReceipt
            Execution receipt with results

        """
        span = trace.get_current_span()
        span.set_attribute("command", " ".join(command))
        span.set_attribute("timeout", timeout)

        return self._execute(
            capability_type=CapabilityType.SHELL,
            command=command,
            input_data=input_data,
            timeout=timeout,
            capability_id=f"shell:{command[0]}",
        )

    def _execute(
        self,
        capability_type: CapabilityType,
        command: list[str],
        input_data: dict[str, Any],
        timeout: float,
        capability_id: str,
    ) -> ExecutionReceipt:
        """Execute external capability.

        Parameters
        ----------
        capability_type : CapabilityType
            Type of capability
        command : list[str]
            Command and arguments
        input_data : dict[str, Any]
            Input data
        timeout : float
            Timeout in seconds
        capability_id : str
            Capability identifier

        Returns
        -------
        ExecutionReceipt
            Execution receipt

        """
        import time

        start_time = time.time()
        receipt = ExecutionReceipt(
            capability_id=capability_id,
            capability_type=capability_type,
            input_data=input_data,
        )

        try:
            # Serialize input to JSON
            input_json = json.dumps(input_data)

            # Execute subprocess
            result = subprocess.run(
                command,
                input=input_json,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.working_dir,
                check=False,
            )

            receipt.exit_code = result.returncode
            receipt.stdout = result.stdout
            receipt.stderr = result.stderr

            # Parse output JSON if successful
            if result.returncode == 0:
                try:
                    receipt.output_data = json.loads(result.stdout)
                except json.JSONDecodeError as e:
                    receipt.error = f"Failed to parse JSON output: {e}"
                    receipt.exit_code = 1
            else:
                receipt.error = f"Process exited with code {result.returncode}"

        except subprocess.TimeoutExpired:
            receipt.error = f"Process timed out after {timeout}s"
            receipt.exit_code = 124  # Standard timeout exit code

        except Exception as e:
            receipt.error = f"Execution failed: {e}"
            receipt.exit_code = 1

        finally:
            receipt.duration_ms = (time.time() - start_time) * 1000

        self._execution_history.append(receipt)

        # Add telemetry
        span = trace.get_current_span()
        span.set_attribute("receipt.exit_code", receipt.exit_code)
        span.set_attribute("receipt.duration_ms", receipt.duration_ms)
        if receipt.error:
            span.set_attribute("receipt.error", receipt.error)

        return receipt

    def get_execution_history(self) -> list[ExecutionReceipt]:
        """Get execution history.

        Returns
        -------
        list[ExecutionReceipt]
            All execution receipts

        """
        return self._execution_history.copy()

    def clear_history(self) -> None:
        """Clear execution history."""
        self._execution_history.clear()

    @tracer.start_as_current_span("externals.link_to_graph")
    def link_to_graph(self, receipt: ExecutionReceipt, graph: Graph) -> URIRef:
        """Link execution receipt to RDF graph.

        Parameters
        ----------
        receipt : ExecutionReceipt
            Execution receipt to link
        graph : Graph
            RDF graph to add receipt to

        Returns
        -------
        URIRef
            Receipt URI in graph

        """
        return receipt.to_rdf(graph)

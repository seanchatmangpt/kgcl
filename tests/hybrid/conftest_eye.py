"""Pytest fixtures for EYE reasoner integration testing.

This module provides fixtures for testing WCP patterns using the EYE reasoner.
EYE (Euler Yet another proof Engine) is an N3 reasoning engine that can execute
physics-based rules over RDF/N3 data.

Fixtures
--------
eye_available : bool
    Checks if EYE reasoner is installed and available.
eye_temp_dir : Path
    Temporary directory for EYE input/output files.
eye_runner : Callable
    Function to execute EYE reasoner with given inputs.
eye_parser : Callable
    Function to parse N3 output from EYE.
eye_result_validator : Callable
    Function to validate EYE results against expectations.
wcp_pattern_loader : Callable
    Loads WCP pattern definitions for testing.
physics_rules_loader : Callable
    Loads physics rules for WCP pattern evaluation.

Notes
-----
Tests using these fixtures will be automatically skipped if EYE is not installed.
"""

import shutil
import subprocess
import tempfile
from collections.abc import Callable, Generator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest


@dataclass(frozen=True)
class EyeResult:
    """Result from EYE reasoner execution.

    Attributes
    ----------
    stdout : str
        Standard output from EYE (N3 format).
    stderr : str
        Standard error output.
    returncode : int
        Process exit code.
    execution_time : float
        Time taken to execute (seconds).
    output_file : Path | None
        Path to output file if written.
    """

    stdout: str
    stderr: str
    returncode: int
    execution_time: float
    output_file: Path | None = None


@dataclass(frozen=True)
class WcpPattern:
    """WCP pattern definition for testing.

    Attributes
    ----------
    pattern_id : str
        Pattern identifier (e.g., "WCP-1").
    name : str
        Human-readable pattern name.
    description : str
        Pattern description.
    n3_data : str
        N3 representation of pattern data.
    expected_result : str
        Expected reasoning result.
    """

    pattern_id: str
    name: str
    description: str
    n3_data: str
    expected_result: str


@pytest.fixture(scope="session")
def eye_available() -> bool:
    """Check if EYE reasoner is installed and available.

    Returns
    -------
    bool
        True if EYE is available, False otherwise.

    Notes
    -----
    Tests using EYE fixtures will be skipped if this returns False.
    """
    return shutil.which("eye") is not None


@pytest.fixture(scope="session")
def eye_skip_if_unavailable(eye_available: bool) -> None:
    """Skip test if EYE reasoner is not available.

    Parameters
    ----------
    eye_available : bool
        Whether EYE is available.

    Raises
    ------
    pytest.skip
        If EYE is not installed.
    """
    if not eye_available:
        pytest.skip("EYE reasoner not installed. Install from https://github.com/eyereasoner/eye")


@pytest.fixture
def eye_temp_dir() -> Generator[Path, None, None]:
    """Create temporary directory for EYE input/output files.

    Yields
    ------
    Path
        Temporary directory path.

    Notes
    -----
    Directory is automatically cleaned up after test execution.
    """
    with tempfile.TemporaryDirectory(prefix="eye_test_") as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def eye_runner(eye_skip_if_unavailable: None, eye_temp_dir: Path) -> Callable[..., EyeResult]:
    """Execute EYE reasoner with given inputs.

    Parameters
    ----------
    eye_skip_if_unavailable : None
        Ensures test is skipped if EYE unavailable.
    eye_temp_dir : Path
        Temporary directory for files.

    Returns
    -------
    Callable
        Function to run EYE with specified arguments.

    Examples
    --------
    >>> result = eye_runner(data_n3="@prefix : <#> . :s :p :o .", rules_n3="# physics rules", query_n3="# query")
    >>> assert result.returncode == 0
    """
    import time

    def run_eye(
        data_n3: str,
        rules_n3: str | None = None,
        query_n3: str | None = None,
        extra_args: list[str] | None = None,
        timeout: int = 30,
    ) -> EyeResult:
        """Execute EYE reasoner.

        Parameters
        ----------
        data_n3 : str
            N3 data to reason over.
        rules_n3 : str | None
            Physics rules in N3 format.
        query_n3 : str | None
            Query in N3 format.
        extra_args : list[str] | None
            Additional command-line arguments.
        timeout : int
            Execution timeout in seconds.

        Returns
        -------
        EyeResult
            Execution result with stdout, stderr, returncode.

        Raises
        ------
        subprocess.TimeoutExpired
            If execution exceeds timeout.
        """
        # Write input files
        data_file = eye_temp_dir / "data.n3"
        data_file.write_text(data_n3, encoding="utf-8")

        cmd = ["eye", "--nope", "--quiet", str(data_file)]

        if rules_n3:
            rules_file = eye_temp_dir / "physics.n3"
            rules_file.write_text(rules_n3, encoding="utf-8")
            cmd.append(str(rules_file))

        if query_n3:
            query_file = eye_temp_dir / "query.n3"
            query_file.write_text(query_n3, encoding="utf-8")
            cmd.extend(["--query", str(query_file)])

        if extra_args:
            cmd.extend(extra_args)

        # Execute EYE
        start_time = time.perf_counter()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        execution_time = time.perf_counter() - start_time

        return EyeResult(
            stdout=result.stdout, stderr=result.stderr, returncode=result.returncode, execution_time=execution_time
        )

    return run_eye


@pytest.fixture
def eye_parser() -> Callable[[str], list[dict[str, Any]]]:
    """Parse N3 output from EYE reasoner.

    Returns
    -------
    Callable
        Function to parse N3 output into structured data.

    Examples
    --------
    >>> triples = eye_parser(eye_result.stdout)
    >>> assert len(triples) > 0
    """

    def parse_n3(n3_output: str) -> list[dict[str, Any]]:
        """Parse N3 output into triples.

        Parameters
        ----------
        n3_output : str
            N3 formatted output from EYE.

        Returns
        -------
        list[dict[str, Any]]
            List of triples as dictionaries with 'subject', 'predicate', 'object' keys.

        Notes
        -----
        This is a basic parser. For production use, consider rdflib or N3.js.
        """
        triples: list[dict[str, Any]] = []
        lines = n3_output.strip().split("\n")

        for line in lines:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith("#") or line.startswith("@"):
                continue

            # Basic triple parsing (subject predicate object .)
            if line.endswith("."):
                parts = line[:-1].strip().split(None, 2)
                if len(parts) == 3:
                    triples.append({"subject": parts[0], "predicate": parts[1], "object": parts[2]})

        return triples

    return parse_n3


@pytest.fixture
def eye_result_validator(eye_parser: Callable[[str], list[dict[str, Any]]]) -> Callable[..., bool]:
    """Validate EYE results against expected outcomes.

    Parameters
    ----------
    eye_parser : Callable
        N3 parser fixture.

    Returns
    -------
    Callable
        Function to validate EYE results.

    Examples
    --------
    >>> is_valid = eye_result_validator(result, expected_triples=expected)
    >>> assert is_valid
    """

    def validate(
        result: EyeResult,
        expected_triples: list[dict[str, Any]] | None = None,
        expected_triple_count: int | None = None,
        expected_patterns: list[str] | None = None,
    ) -> bool:
        """Validate EYE execution result.

        Parameters
        ----------
        result : EyeResult
            EYE execution result.
        expected_triples : list[dict[str, Any]] | None
            Expected triples in result.
        expected_triple_count : int | None
            Expected number of triples.
        expected_patterns : list[str] | None
            Expected string patterns in output.

        Returns
        -------
        bool
            True if validation passes.

        Raises
        ------
        AssertionError
            If validation fails.
        """
        # Check execution succeeded
        assert result.returncode == 0, f"EYE failed: {result.stderr}"

        # Parse output
        triples = eye_parser(result.stdout)

        # Validate triple count
        if expected_triple_count is not None:
            assert len(triples) == expected_triple_count, (
                f"Expected {expected_triple_count} triples, got {len(triples)}"
            )

        # Validate expected triples present
        if expected_triples:
            for expected_triple in expected_triples:
                assert expected_triple in triples, f"Expected triple not found: {expected_triple}"

        # Validate patterns in output
        if expected_patterns:
            for pattern in expected_patterns:
                assert pattern in result.stdout, f"Expected pattern not found: {pattern}"

        return True

    return validate


@pytest.fixture
def wcp_pattern_loader(eye_temp_dir: Path) -> Callable[[str], WcpPattern]:
    """Load WCP pattern definitions for testing.

    Parameters
    ----------
    eye_temp_dir : Path
        Temporary directory for pattern files.

    Returns
    -------
    Callable
        Function to load WCP patterns by ID.

    Examples
    --------
    >>> pattern = wcp_pattern_loader("WCP-1")
    >>> assert pattern.pattern_id == "WCP-1"
    """

    def load_pattern(pattern_id: str) -> WcpPattern:
        """Load WCP pattern by ID.

        Parameters
        ----------
        pattern_id : str
            Pattern identifier (e.g., "WCP-1").

        Returns
        -------
        WcpPattern
            Pattern definition with N3 data and expected result.

        Notes
        -----
        This is a stub implementation. In production, patterns would be
        loaded from a pattern library or database.
        """
        # Stub implementation - actual patterns would come from pattern library
        pattern_definitions = {
            "WCP-1": WcpPattern(
                pattern_id="WCP-1",
                name="Sequence",
                description="Sequential execution of activities",
                n3_data="""
                    @prefix wcp: <http://example.org/wcp#> .
                    @prefix : <#> .

                    :workflow a wcp:Workflow ;
                        wcp:hasActivity :a1, :a2 ;
                        wcp:hasSequence ( :a1 :a2 ) .
                """,
                expected_result=":a1 wcp:precedes :a2",
            ),
            "WCP-2": WcpPattern(
                pattern_id="WCP-2",
                name="Parallel Split",
                description="Parallel execution of multiple activities",
                n3_data="""
                    @prefix wcp: <http://example.org/wcp#> .
                    @prefix : <#> .

                    :workflow a wcp:Workflow ;
                        wcp:hasActivity :a1, :a2, :a3 ;
                        wcp:hasParallelSplit :split1 .

                    :split1 wcp:splits ( :a2 :a3 ) .
                """,
                expected_result=":a2 wcp:parallelTo :a3",
            ),
        }

        if pattern_id not in pattern_definitions:
            raise ValueError(f"Unknown pattern ID: {pattern_id}")

        return pattern_definitions[pattern_id]

    return load_pattern


@pytest.fixture
def physics_rules_loader(eye_temp_dir: Path) -> Callable[[str], str]:
    """Load physics rules for WCP pattern evaluation.

    Parameters
    ----------
    eye_temp_dir : Path
        Temporary directory for rules files.

    Returns
    -------
    Callable
        Function to load physics rules by pattern type.

    Examples
    --------
    >>> rules = physics_rules_loader("sequence")
    >>> assert "wcp:precedes" in rules
    """

    def load_rules(rule_type: str) -> str:
        """Load physics rules by type.

        Parameters
        ----------
        rule_type : str
            Rule type (e.g., "sequence", "parallel", "choice").

        Returns
        -------
        str
            N3 physics rules for pattern evaluation.

        Notes
        -----
        This is a stub implementation. In production, rules would be
        loaded from a rules library.
        """
        # Stub implementation - actual rules would come from rules library
        rule_definitions = {
            "sequence": """
                @prefix wcp: <http://example.org/wcp#> .
                @prefix log: <http://www.w3.org/2000/10/swap/log#> .

                # Sequence rule: if activities in sequence, first precedes second
                {
                    ?workflow wcp:hasSequence ?seq .
                    ?seq log:firstRest (?first ?rest) .
                    ?rest log:firstRest (?second ?_) .
                } => {
                    ?first wcp:precedes ?second .
                } .
            """,
            "parallel": """
                @prefix wcp: <http://example.org/wcp#> .
                @prefix log: <http://www.w3.org/2000/10/swap/log#> .

                # Parallel rule: activities in parallel split are parallel to each other
                {
                    ?split wcp:splits ?activities .
                    ?activities log:firstRest (?a1 ?rest) .
                    ?rest log:firstRest (?a2 ?_) .
                } => {
                    ?a1 wcp:parallelTo ?a2 .
                } .
            """,
            "choice": """
                @prefix wcp: <http://example.org/wcp#> .
                @prefix log: <http://www.w3.org/2000/10/swap/log#> .

                # Choice rule: activities in choice are mutually exclusive
                {
                    ?choice wcp:hasOptions ?activities .
                    ?activities log:firstRest (?a1 ?rest) .
                    ?rest log:firstRest (?a2 ?_) .
                } => {
                    ?a1 wcp:mutuallyExclusiveWith ?a2 .
                } .
            """,
        }

        if rule_type not in rule_definitions:
            raise ValueError(f"Unknown rule type: {rule_type}")

        return rule_definitions[rule_type]

    return load_rules


@pytest.fixture
def eye_batch_runner(
    eye_runner: Callable[..., EyeResult], eye_parser: Callable[[str], list[dict[str, Any]]]
) -> Callable[..., list[EyeResult]]:
    """Execute multiple EYE reasoning tasks in batch.

    Parameters
    ----------
    eye_runner : Callable
        EYE execution fixture.
    eye_parser : Callable
        N3 parser fixture.

    Returns
    -------
    Callable
        Function to run multiple EYE tasks.

    Examples
    --------
    >>> results = eye_batch_runner(tasks=[{"data_n3": "...", "rules_n3": "..."}, {"data_n3": "...", "rules_n3": "..."}])
    >>> assert all(r.returncode == 0 for r in results)
    """

    def run_batch(tasks: list[dict[str, Any]]) -> list[EyeResult]:
        """Execute multiple EYE tasks.

        Parameters
        ----------
        tasks : list[dict[str, Any]]
            List of task specifications, each with 'data_n3', 'rules_n3', etc.

        Returns
        -------
        list[EyeResult]
            Results from all executions.

        Notes
        -----
        Tasks are executed sequentially. For parallel execution,
        use concurrent.futures or multiprocessing.
        """
        results: list[EyeResult] = []

        for task in tasks:
            result = eye_runner(**task)
            results.append(result)

        return results

    return run_batch


@pytest.fixture
def eye_performance_tracker() -> Callable[..., dict[str, float]]:
    """Track EYE reasoner performance metrics.

    Returns
    -------
    Callable
        Function to collect performance metrics.

    Examples
    --------
    >>> metrics = eye_performance_tracker(results)
    >>> assert metrics["avg_execution_time"] < 1.0
    """

    def track_metrics(results: list[EyeResult]) -> dict[str, float]:
        """Collect performance metrics from EYE results.

        Parameters
        ----------
        results : list[EyeResult]
            List of EYE execution results.

        Returns
        -------
        dict[str, float]
            Performance metrics (avg time, min, max, p95, p99).
        """
        if not results:
            return {}

        execution_times = [r.execution_time for r in results]
        sorted_times = sorted(execution_times)
        n = len(sorted_times)

        return {
            "count": float(n),
            "avg_execution_time": sum(execution_times) / n,
            "min_execution_time": sorted_times[0],
            "max_execution_time": sorted_times[-1],
            "p50_execution_time": sorted_times[n // 2],
            "p95_execution_time": sorted_times[int(n * 0.95)] if n > 1 else sorted_times[0],
            "p99_execution_time": sorted_times[int(n * 0.99)] if n > 1 else sorted_times[0],
            "success_rate": sum(1 for r in results if r.returncode == 0) / n,
        }

    return track_metrics

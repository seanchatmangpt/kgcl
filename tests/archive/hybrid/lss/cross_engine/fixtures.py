"""Shared fixtures and topology definitions for WCP cross-engine tests.

This module provides:
- PyTest fixtures for engine setup
- Helper functions for engine execution
- Topology definitions for WCP patterns
- Assertion utilities for test validation

Examples
--------
Create a simple sequence topology (WCP-1):

>>> topology = '''
... @prefix kgc: <https://kgc.org/ns/> .
... @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
...
... <urn:task:A> a yawl:Task ;
...     kgc:status "Completed" ;
...     yawl:flowsInto <urn:flow:a_to_b> .
...
... <urn:flow:a_to_b> yawl:nextElementRef <urn:task:B> .
... <urn:task:B> a yawl:Task .
... '''

Create and run engine test:

>>> from kgcl.hybrid.hybrid_engine import HybridEngine
>>> engine = HybridEngine()
>>> engine.load_data(topology)  # doctest: +SKIP
>>> engine.run_to_completion(max_ticks=5)  # doctest: +SKIP
>>> statuses = engine.inspect()  # doctest: +SKIP
>>> statuses.get("urn:task:B")  # doctest: +SKIP
'Active'
"""

from __future__ import annotations

import shutil

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine

# =============================================================================
# PYTEST FIXTURES
# =============================================================================


@pytest.fixture(scope="module")
def eye_available() -> bool:
    """Check if EYE reasoner is installed and available.

    Returns
    -------
    bool
        True if EYE is installed, False otherwise

    Examples
    --------
    >>> import shutil
    >>> result = shutil.which("eye") is not None
    >>> isinstance(result, bool)
    True
    """
    return shutil.which("eye") is not None


@pytest.fixture
def oxigraph_engine() -> HybridEngine:
    """Create a fresh HybridEngine for testing.

    Returns
    -------
    HybridEngine
        Clean engine instance

    Examples
    --------
    >>> engine = HybridEngine()
    >>> isinstance(engine, HybridEngine)
    True
    """
    return HybridEngine()


@pytest.fixture
def eye_engine(eye_available: bool) -> HybridEngine:
    """Create a HybridEngine configured for EYE testing.

    Parameters
    ----------
    eye_available : bool
        Whether EYE reasoner is installed

    Returns
    -------
    HybridEngine
        Engine instance for EYE testing

    Raises
    ------
    pytest.skip
        If EYE reasoner is not installed
    """
    if not eye_available:
        pytest.skip("EYE reasoner not installed")
    return HybridEngine()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def assert_task_status(
    statuses: dict[str, str | None], task_uri: str, expected_statuses: list[str], pattern_name: str
) -> None:
    """Assert that a task has one of the expected statuses.

    Parameters
    ----------
    statuses : dict[str, str | None]
        Status dictionary from engine.inspect()
    task_uri : str
        Full URI of the task to check
    expected_statuses : list[str]
        List of acceptable status values
    pattern_name : str
        Pattern name for error messages

    Raises
    ------
    AssertionError
        If task status is not in expected values

    Examples
    --------
    >>> statuses = {"urn:task:A": "Active", "urn:task:B": "Completed"}
    >>> assert_task_status(statuses, "urn:task:A", ["Active", "Pending"], "WCP-1")
    >>> assert_task_status(statuses, "urn:task:B", ["Completed"], "WCP-1")
    """
    actual = statuses.get(task_uri)
    assert actual in expected_statuses, (
        f"{pattern_name}: Expected task {task_uri} to have status in {expected_statuses}, but got {actual}"
    )


def run_engine_test(engine: HybridEngine, topology: str, max_ticks: int = 5) -> dict[str, str | None]:
    """Load topology into engine and run to completion.

    Parameters
    ----------
    engine : HybridEngine
        The engine instance to use
    topology : str
        Turtle/N3 topology to load
    max_ticks : int, default=5
        Maximum ticks to run

    Returns
    -------
    dict[str, str | None]
        Task statuses after execution

    Examples
    --------
    >>> from kgcl.hybrid.hybrid_engine import HybridEngine
    >>> engine = HybridEngine()
    >>> topology = '''
    ... @prefix kgc: <https://kgc.org/ns/> .
    ... @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
    ... <urn:task:A> a yawl:Task ; kgc:status "Completed" .
    ... '''
    >>> statuses = run_engine_test(engine, topology, max_ticks=1)  # doctest: +SKIP
    >>> isinstance(statuses, dict)  # doctest: +SKIP
    True
    """
    engine.load_data(topology)
    engine.run_to_completion(max_ticks=max_ticks)
    return engine.inspect()


# =============================================================================
# TOPOLOGY DEFINITIONS
# =============================================================================

WCP1_SEQUENCE_TOPOLOGY = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

<urn:task:A> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:a_to_b> .

<urn:flow:a_to_b> yawl:nextElementRef <urn:task:B> .
<urn:task:B> a yawl:Task .
"""

WCP2_PARALLEL_SPLIT_TOPOLOGY = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

<urn:task:Split> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:hasSplit yawl:ControlTypeAnd ;
    yawl:flowsInto <urn:flow:to_a>, <urn:flow:to_b> .

<urn:flow:to_a> yawl:nextElementRef <urn:task:A> .
<urn:flow:to_b> yawl:nextElementRef <urn:task:B> .

<urn:task:A> a yawl:Task .
<urn:task:B> a yawl:Task .
"""

WCP3_SYNCHRONIZATION_TOPOLOGY = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

<urn:task:A> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:a_to_join> .

<urn:task:B> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:b_to_join> .

<urn:flow:a_to_join> yawl:nextElementRef <urn:task:Join> .
<urn:flow:b_to_join> yawl:nextElementRef <urn:task:Join> .

<urn:task:Join> a yawl:Task ;
    yawl:hasJoin yawl:ControlTypeAnd .
"""

WCP4_EXCLUSIVE_CHOICE_TOPOLOGY = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

<urn:task:Decision> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:hasSplit yawl:ControlTypeXor ;
    yawl:flowsInto <urn:flow:to_a>, <urn:flow:to_b> .

<urn:flow:to_a> yawl:nextElementRef <urn:task:A> ;
    yawl:hasPredicate <urn:pred:a> .
<urn:pred:a> kgc:evaluatesTo true .

<urn:flow:to_b> yawl:nextElementRef <urn:task:B> ;
    yawl:isDefaultFlow true .

<urn:task:A> a yawl:Task .
<urn:task:B> a yawl:Task .
"""

WCP11_IMPLICIT_TERMINATION_TOPOLOGY = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

<urn:task:Final> a yawl:Task ;
    kgc:status "Completed" .
"""

WCP43_EXPLICIT_TERMINATION_TOPOLOGY = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

<urn:task:Final> a yawl:Task ;
    kgc:status "Completed" ;
    kgc:terminatesWorkflow true .
"""

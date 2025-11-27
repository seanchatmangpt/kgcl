"""CLI test fixtures - Chicago School TDD with real RDF data.

No mocking. Real HybridEngine, real PyOxigraph, real EYE reasoner.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def cli_runner() -> CliRunner:
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def simple_sequence_turtle() -> str:
    """Simple sequence workflow: Start → Task1 → End.

    This is the minimal workflow that exercises:
    - LAW 1: Simple Sequence (Completed → Active)
    - LAW 5/6: Auto-Complete (Active → Completed)
    - LAW 7: Archive (Completed → Archived)
    """
    return """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

<urn:task:Start> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:1> .

<urn:flow:1> yawl:nextElementRef <urn:task:Task1> .

<urn:task:Task1> a yawl:Task ;
    yawl:flowsInto <urn:flow:2> .

<urn:flow:2> yawl:nextElementRef <urn:task:End> .

<urn:task:End> a yawl:Task .
"""


@pytest.fixture
def and_split_turtle() -> str:
    """AND-split workflow: Start → {Branch1, Branch2} → Join → End.

    Tests parallel activation (WCP-2) and synchronization (WCP-3).
    """
    return """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

<urn:task:Start> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:hasSplit yawl:ControlTypeAnd ;
    yawl:flowsInto <urn:flow:1> ;
    yawl:flowsInto <urn:flow:2> .

<urn:flow:1> yawl:nextElementRef <urn:task:Branch1> .
<urn:flow:2> yawl:nextElementRef <urn:task:Branch2> .

<urn:task:Branch1> a yawl:Task ;
    yawl:flowsInto <urn:flow:3> .

<urn:task:Branch2> a yawl:Task ;
    yawl:flowsInto <urn:flow:4> .

<urn:flow:3> yawl:nextElementRef <urn:task:Join> .
<urn:flow:4> yawl:nextElementRef <urn:task:Join> .

<urn:task:Join> a yawl:Task ;
    yawl:hasJoin yawl:ControlTypeAnd ;
    yawl:flowsInto <urn:flow:5> .

<urn:flow:5> yawl:nextElementRef <urn:task:End> .

<urn:task:End> a yawl:Task .
"""


@pytest.fixture
def xor_split_turtle() -> str:
    """XOR-split workflow with predicate evaluation.

    Tests exclusive choice (WCP-4).
    """
    return """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

<urn:task:Start> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:hasSplit yawl:ControlTypeXor ;
    yawl:flowsInto <urn:flow:approved> ;
    yawl:flowsInto <urn:flow:rejected> .

<urn:flow:approved>
    yawl:nextElementRef <urn:task:Approved> ;
    yawl:hasPredicate <urn:pred:approved> .

<urn:pred:approved> kgc:evaluatesTo true .

<urn:flow:rejected>
    yawl:nextElementRef <urn:task:Rejected> ;
    yawl:isDefaultFlow true .

<urn:task:Approved> a yawl:Task .
<urn:task:Rejected> a yawl:Task .
"""


@pytest.fixture
def topology_file(simple_sequence_turtle: str) -> Generator[Path, None, None]:
    """Create a temporary topology file for CLI testing."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".ttl", delete=False
    ) as f:
        f.write(simple_sequence_turtle)
        f.flush()
        yield Path(f.name)
    # Cleanup handled by tempfile


@pytest.fixture
def and_split_file(and_split_turtle: str) -> Generator[Path, None, None]:
    """Create a temporary AND-split topology file."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".ttl", delete=False
    ) as f:
        f.write(and_split_turtle)
        f.flush()
        yield Path(f.name)


@pytest.fixture
def xor_split_file(xor_split_turtle: str) -> Generator[Path, None, None]:
    """Create a temporary XOR-split topology file."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".ttl", delete=False
    ) as f:
        f.write(xor_split_turtle)
        f.flush()
        yield Path(f.name)

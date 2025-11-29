"""Nuclear Launch Simulation - Workflow Graph Structure Tests.

This file tests the STRUCTURE of a nuclear launch workflow graph.

HONEST LIMITATION: These tests verify GRAPH STRUCTURE only.
They do NOT test workflow EXECUTION because:
1. SemanticDriver is not yet implemented
2. No RDF-driven verb dispatch exists yet
3. The engine documented in CLAUDE.md as BROKEN

What IS tested here:
- Graph construction with correct node types
- Workflow topology (AND-splits, AND-joins, XOR-splits)
- Static code analysis (no forbidden if/else patterns)

What is NOT tested (would require SemanticDriver):
- Token movement through workflow
- Verb execution (Transmute, Copy, Await, Filter, Void)
- Performance under load
- Cryptographic provenance

Chicago School TDD: Real RDF graph structure, no mocking.
"""

from __future__ import annotations

import pytest
from rdflib import Graph, Literal, Namespace, URIRef

from kgcl.engine import GENESIS_HASH, TransactionContext

# Workflow namespaces
KGC = Namespace("http://kgcl.io/ontology/kgc#")
YAWL = Namespace("http://www.yawlfoundation.org/yawlschema#")
LAUNCH = Namespace("http://example.org/nuclear-launch#")

# Test constants
GENERAL_ALPHA = "gen_alpha_auth_key_12345"
GENERAL_BRAVO = "gen_bravo_auth_key_67890"
COUNTDOWN_SECONDS = 60


@pytest.fixture
def nuclear_workflow_graph() -> Graph:
    """Create nuclear launch workflow graph structure.

    Workflow structure:
    1. InitiateLaunch (start)
    2. GeneralApproval (AND-split → parallel authorizations)
       ├─ GeneralAlphaAuth
       └─ GeneralBravoAuth
    3. DualKeyJoin (AND-join → both generals required)
    4. ValidateLaunchCodes (XOR-split → code validation)
       ├─ ValidCodesPath
       └─ InvalidCodesAbort (→ terminal)
    5. StartCountdown (Timer with abort)
    6. ExecuteLaunch (final command)
    7. BroadcastTelemetry (AND-split → multiple channels)
       ├─ MilitaryChannel
       ├─ CivilianAlert
       └─ InternationalNotification
    """
    graph = Graph()
    graph.bind("kgc", KGC)
    graph.bind("yawl", YAWL)
    graph.bind("launch", LAUNCH)

    rdf_type = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")

    # 1. Initiate Launch (start node with token)
    graph.add((LAUNCH.InitiateLaunch, rdf_type, YAWL.Task))
    graph.add((LAUNCH.InitiateLaunch, KGC.hasToken, Literal(True)))
    graph.add((LAUNCH.InitiateLaunch, YAWL.nextElementRef, LAUNCH.GeneralApproval))

    # 2. General Approval AND-split (parallel authorization)
    graph.add((LAUNCH.GeneralApproval, rdf_type, YAWL.ANDSplit))
    graph.add((LAUNCH.GeneralApproval, YAWL.nextElementRef, LAUNCH.GeneralAlphaAuth))
    graph.add((LAUNCH.GeneralApproval, YAWL.nextElementRef, LAUNCH.GeneralBravoAuth))

    # 3. Individual general authorization tasks
    graph.add((LAUNCH.GeneralAlphaAuth, rdf_type, YAWL.Task))
    graph.add((LAUNCH.GeneralAlphaAuth, YAWL.nextElementRef, LAUNCH.DualKeyJoin))
    graph.add((LAUNCH.GeneralAlphaAuth, YAWL.requiredAuthKey, Literal(GENERAL_ALPHA)))

    graph.add((LAUNCH.GeneralBravoAuth, rdf_type, YAWL.Task))
    graph.add((LAUNCH.GeneralBravoAuth, YAWL.nextElementRef, LAUNCH.DualKeyJoin))
    graph.add((LAUNCH.GeneralBravoAuth, YAWL.requiredAuthKey, Literal(GENERAL_BRAVO)))

    # 4. Dual-key join (both generals required)
    graph.add((LAUNCH.DualKeyJoin, rdf_type, YAWL.ANDJoin))
    graph.add((LAUNCH.DualKeyJoin, YAWL.nextElementRef, LAUNCH.ValidateLaunchCodes))

    # 5. Launch codes validation XOR-split (conditional routing)
    graph.add((LAUNCH.ValidateLaunchCodes, rdf_type, YAWL.XORSplit))
    graph.add((LAUNCH.ValidateLaunchCodes, YAWL.hasPredicate, Literal("launch_code == VALID_CODE")))
    graph.add((LAUNCH.ValidateLaunchCodes, YAWL.nextElementRef, LAUNCH.ValidCodesPath))
    graph.add((LAUNCH.ValidateLaunchCodes, YAWL.nextElementRef, LAUNCH.InvalidCodesAbort))

    # 6. Valid codes path → Countdown
    graph.add((LAUNCH.ValidCodesPath, rdf_type, YAWL.Task))
    graph.add((LAUNCH.ValidCodesPath, YAWL.nextElementRef, LAUNCH.StartCountdown))

    # 7. Invalid codes path → terminal (abort)
    graph.add((LAUNCH.InvalidCodesAbort, rdf_type, YAWL.Task))
    graph.add((LAUNCH.InvalidCodesAbort, KGC.terminationType, Literal("abort")))

    # 8. Countdown timer
    graph.add((LAUNCH.StartCountdown, rdf_type, YAWL.Task))
    graph.add((LAUNCH.StartCountdown, YAWL.timeoutDuration, Literal(f"PT{COUNTDOWN_SECONDS}S")))
    graph.add((LAUNCH.StartCountdown, YAWL.nextElementRef, LAUNCH.ExecuteLaunch))
    graph.add((LAUNCH.StartCountdown, YAWL.abortOnSignal, Literal(True)))

    # 9. Execute launch command
    graph.add((LAUNCH.ExecuteLaunch, rdf_type, YAWL.Task))
    graph.add((LAUNCH.ExecuteLaunch, YAWL.nextElementRef, LAUNCH.BroadcastTelemetry))
    graph.add((LAUNCH.ExecuteLaunch, YAWL.commandType, Literal("FIRE")))

    # 10. Broadcast telemetry AND-split (parallel notifications)
    graph.add((LAUNCH.BroadcastTelemetry, rdf_type, YAWL.ANDSplit))
    graph.add((LAUNCH.BroadcastTelemetry, YAWL.nextElementRef, LAUNCH.MilitaryChannel))
    graph.add((LAUNCH.BroadcastTelemetry, YAWL.nextElementRef, LAUNCH.CivilianAlert))
    graph.add((LAUNCH.BroadcastTelemetry, YAWL.nextElementRef, LAUNCH.InternationalNotification))

    # 11. Terminal notification tasks
    for channel in [LAUNCH.MilitaryChannel, LAUNCH.CivilianAlert, LAUNCH.InternationalNotification]:
        graph.add((channel, rdf_type, YAWL.Task))
        graph.add((channel, KGC.terminal, Literal(True)))

    return graph


@pytest.fixture
def transaction_context() -> TransactionContext:
    """Transaction context for tests."""
    return TransactionContext(prev_hash=GENESIS_HASH, actor="launch-control-operator")


class TestWorkflowGraphStructure:
    """Tests verifying workflow graph structure (NOT execution)."""

    def test_workflow_contains_and_splits(self, nuclear_workflow_graph: Graph) -> None:
        """Workflow has AND-split nodes for parallel paths."""
        rdf_type = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
        and_splits = list(nuclear_workflow_graph.subjects(rdf_type, YAWL.ANDSplit))

        assert len(and_splits) == 2, "Expected GeneralApproval + BroadcastTelemetry"
        assert LAUNCH.GeneralApproval in and_splits
        assert LAUNCH.BroadcastTelemetry in and_splits

    def test_workflow_contains_and_joins(self, nuclear_workflow_graph: Graph) -> None:
        """Workflow has AND-join node for dual-key synchronization."""
        rdf_type = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
        and_joins = list(nuclear_workflow_graph.subjects(rdf_type, YAWL.ANDJoin))

        assert len(and_joins) == 1, "Expected DualKeyJoin"
        assert LAUNCH.DualKeyJoin in and_joins

    def test_workflow_contains_xor_splits(self, nuclear_workflow_graph: Graph) -> None:
        """Workflow has XOR-split node for conditional routing."""
        rdf_type = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
        xor_splits = list(nuclear_workflow_graph.subjects(rdf_type, YAWL.XORSplit))

        assert len(xor_splits) == 1, "Expected ValidateLaunchCodes"
        assert LAUNCH.ValidateLaunchCodes in xor_splits

    def test_workflow_contains_terminal_nodes(self, nuclear_workflow_graph: Graph) -> None:
        """Workflow has terminal nodes for abort and notifications."""
        terminal_nodes = list(nuclear_workflow_graph.subjects(KGC.terminal, Literal(True)))
        abort_nodes = list(nuclear_workflow_graph.subjects(KGC.terminationType, Literal("abort")))

        assert len(terminal_nodes) == 3, "Expected 3 notification channels as terminals"
        assert len(abort_nodes) == 1, "Expected InvalidCodesAbort as abort terminal"

    def test_workflow_has_token_at_start(self, nuclear_workflow_graph: Graph) -> None:
        """Workflow starts with token at InitiateLaunch."""
        token_holders = list(nuclear_workflow_graph.subjects(KGC.hasToken, Literal(True)))

        assert len(token_holders) == 1, "Only start node should have token initially"
        assert LAUNCH.InitiateLaunch in token_holders

    def test_parallel_paths_converge_at_join(self, nuclear_workflow_graph: Graph) -> None:
        """Both general auth tasks lead to the same AND-join."""
        alpha_targets = list(nuclear_workflow_graph.objects(LAUNCH.GeneralAlphaAuth, YAWL.nextElementRef))
        bravo_targets = list(nuclear_workflow_graph.objects(LAUNCH.GeneralBravoAuth, YAWL.nextElementRef))

        assert LAUNCH.DualKeyJoin in alpha_targets
        assert LAUNCH.DualKeyJoin in bravo_targets

    def test_xor_split_has_two_paths(self, nuclear_workflow_graph: Graph) -> None:
        """XOR-split has exactly two outgoing paths."""
        xor_targets = list(nuclear_workflow_graph.objects(LAUNCH.ValidateLaunchCodes, YAWL.nextElementRef))

        assert len(xor_targets) == 2, "XOR-split must have exactly 2 paths"
        assert LAUNCH.ValidCodesPath in xor_targets
        assert LAUNCH.InvalidCodesAbort in xor_targets


class TestCodeQuality:
    """Tests verifying code quality constraints."""

    def test_verify_zero_conditional_dispatch_in_engine(self) -> None:
        """CRITICAL: Verify NO `if type ==` statements in engine code."""
        from pathlib import Path

        engine_file = Path(__file__).parent.parent.parent / "src" / "kgcl" / "engine" / "knowledge_engine.py"

        if not engine_file.exists():
            pytest.skip("Engine file not found - may not be implemented yet")

        source = engine_file.read_text()

        # Forbidden patterns (CRITICAL CONSTRAINT)
        forbidden_patterns = [
            "if pattern_type ==",
            "if split_type ==",
            "elif pattern ==",
            "match pattern_type:",
            "if node_type ==",
            "if task.type ==",
        ]

        violations = []
        for pattern in forbidden_patterns:
            if pattern in source:
                violations.append(pattern)

        assert not violations, (
            f"ENGINE VIOLATION: Found forbidden dispatch patterns: {violations}\n"
            "ALL dispatch must be ontology-driven: verb = resolve_verb_from_ontology(pattern_type)"
        )

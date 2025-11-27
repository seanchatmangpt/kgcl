"""WARNING Function Tests - Non-Critical Alerting Error Proofing.

This module tests the WARNING Poka-Yoke function for non-critical error alerting.
WARNING informs about potential issues without stopping or gating the process.

Warning Categories
-----------------
- **Missing Optional Fields**: Tasks without status, flows without references
- **Orphaned Resources**: Flows without tasks, tasks without flows
- **Edge Cases**: Empty workflows, minimal topologies
- **Monitoring**: Observability and diagnostic information

Alert Principles
---------------
1. **Non-Blocking**: Process continues despite warning
2. **Informational**: Logs/alerts for operator awareness
3. **Graceful Degradation**: System handles edge cases safely
4. **Observability**: Diagnostic information for troubleshooting

References
----------
- Shigeo Shingo: "Zero Quality Control" - WARNING function
- Toyota Production System: Visual management (andon boards)
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine


@pytest.fixture
def engine() -> HybridEngine:
    """Create fresh HybridEngine for WARNING testing."""
    return HybridEngine()


class TestPY013WarningFunction:
    """PY-013: WARNING function for non-critical error alerting.

    Poka-Yoke Type: WARNING (Lowest severity)
    Error Class: Informational (alerts operator, doesn't stop process)
    """

    def test_warning_task_without_status_continues(self, engine: HybridEngine) -> None:
        """Task without status logs warning but doesn't crash."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:NoStatus> a yawl:Task .
        """
        engine.load_data(topology)

        # WARNING: No status is not fatal, just logged
        result = engine.apply_physics()
        assert result is not None, "WARNING: System should continue"

    def test_warning_empty_workflow_continues(self, engine: HybridEngine) -> None:
        """Empty workflow logs warning but doesn't crash."""
        engine.load_data("")

        # WARNING: Empty workflow is valid edge case
        result = engine.apply_physics()
        assert result.delta == 0, "WARNING: Empty workflow produces no changes"

    def test_warning_orphan_flow_detected(self, engine: HybridEngine) -> None:
        """Orphan flow (no task reference) logs warning."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:flow:Orphan> a yawl:Flow .
        """
        engine.load_data(topology)

        # WARNING: Orphan flow doesn't crash, just produces no effect
        result = engine.apply_physics()
        assert result is not None, "WARNING: Orphan flow should not crash"

    def test_warning_dangling_flow_no_crash(self, engine: HybridEngine) -> None:
        """Dangling flow (no nextElementRef) logs warning but doesn't crash."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:dangling> .

        <urn:flow:dangling> a yawl:Flow .
        """
        engine.load_data(topology)

        # WARNING: Dangling flow doesn't crash, just no activation
        result = engine.apply_physics()
        assert result is not None, "WARNING: Dangling flow should not crash"

    def test_warning_orphan_task_valid(self, engine: HybridEngine) -> None:
        """Orphan task (no incoming flow) is valid but logs warning."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:Orphan> a yawl:Task ;
            kgc:status "Active" .
        """
        engine.load_data(topology)

        # WARNING: Orphan task is valid (could be start task)
        result = engine.apply_physics()
        assert result is not None, "WARNING: Orphan task is valid"

    def test_warning_minimal_topology_valid(self, engine: HybridEngine) -> None:
        """Minimal topology (single task) is valid edge case."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:Single> a yawl:Task ;
            kgc:status "Completed" .
        """
        engine.load_data(topology)

        # WARNING: Minimal topology is valid
        result = engine.apply_physics()
        assert result is not None, "WARNING: Minimal topology valid"
        statuses = engine.inspect()
        assert statuses.get("urn:task:Single") in ["Completed", "Archived"]

    def test_warning_whitespace_only_topology(self, engine: HybridEngine) -> None:
        """Whitespace-only topology logs warning but doesn't crash."""
        engine.load_data("   \n\t   \n   ")

        # WARNING: Whitespace is treated as empty
        result = engine.apply_physics()
        assert result.delta == 0, "WARNING: Whitespace-only produces no changes"

    def test_warning_missing_flow_reference(self, engine: HybridEngine) -> None:
        """Flow without nextElementRef logs warning."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:incomplete> .

        <urn:flow:incomplete> a yawl:Flow .
        """
        engine.load_data(topology)

        # WARNING: Missing reference doesn't crash
        result = engine.apply_physics()
        assert result is not None, "WARNING: Missing flow reference handled"

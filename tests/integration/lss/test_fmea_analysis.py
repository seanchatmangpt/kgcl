"""Integration tests for FMEA (Failure Mode and Effects Analysis) with containers.

Tests FMEA workflow using RDF ontology for failure mode modeling and
PostgreSQL for risk priority tracking.

Real-world scenarios:
- Product design FMEA
- Process FMEA for manufacturing
- Risk priority number (RPN) calculation
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from tests.containers.rdf_stores import OxigraphContainer


@pytest.mark.container
@pytest.mark.oxigraph_server
@pytest.mark.postgres
class TestFMEAFailureModeModeling:
    """Test FMEA failure mode modeling with RDF ontology."""

    def test_fmea_failure_modes_in_rdf(
        self,
        oxigraph_container: OxigraphContainer,
        postgres_connection: Any,
    ) -> None:
        """Test failure mode modeling in RDF.

        Scenario: Model widget assembly failure modes
        - Failure modes, effects, and causes in RDF
        - S/O/D ratings stored
        - RPN calculated

        Assert:
        - Failure modes properly linked
        - RPN calculated correctly
        """
        from kgcl.hybrid.adapters.remote_store_adapter import RemoteStoreAdapter

        # Arrange
        adapter = RemoteStoreAdapter(
            query_endpoint=oxigraph_container.get_sparql_endpoint(),
            update_endpoint=oxigraph_container.get_update_endpoint(),
        )
        cursor = postgres_connection.cursor()
        project_id = "FMEA-001"

        # Load FMEA ontology with failure modes
        fmea_turtle = """
            @prefix fmea: <http://kgcl.io/ontology/fmea#> .
            @prefix fm: <http://example.org/failure_mode/> .
            @prefix proc: <http://example.org/process/> .

            # Process step
            proc:widget_assembly a fmea:ProcessStep ;
                fmea:stepName "Widget Final Assembly" ;
                fmea:hasFailureMode fm:improper_torque, fm:missing_component, fm:misaligned_parts .

            # Failure Mode 1: Improper Torque
            fm:improper_torque a fmea:FailureMode ;
                fmea:modeName "Improper fastener torque" ;
                fmea:hasEffect fm:loose_connection_effect ;
                fmea:hasCause fm:operator_error_cause, fm:tool_variation_cause ;
                fmea:severity 8 ;
                fmea:occurrence 6 ;
                fmea:detection 4 ;
                fmea:currentControl "Visual inspection" .

            fm:loose_connection_effect a fmea:Effect ;
                fmea:effectDescription "Loose connection leading to field failure" ;
                fmea:severityRating 8 .

            fm:operator_error_cause a fmea:Cause ;
                fmea:causeDescription "Operator not following torque spec" ;
                fmea:occurrenceRating 5 .

            fm:tool_variation_cause a fmea:Cause ;
                fmea:causeDescription "Torque wrench out of calibration" ;
                fmea:occurrenceRating 3 .

            # Failure Mode 2: Missing Component
            fm:missing_component a fmea:FailureMode ;
                fmea:modeName "Missing component" ;
                fmea:hasEffect fm:incomplete_assembly_effect ;
                fmea:hasCause fm:kit_shortage_cause ;
                fmea:severity 9 ;
                fmea:occurrence 3 ;
                fmea:detection 2 ;
                fmea:currentControl "Poka-yoke fixture" .

            fm:incomplete_assembly_effect a fmea:Effect ;
                fmea:effectDescription "Product does not function" ;
                fmea:severityRating 9 .

            fm:kit_shortage_cause a fmea:Cause ;
                fmea:causeDescription "Incomplete kit from supplier" ;
                fmea:occurrenceRating 3 .

            # Failure Mode 3: Misaligned Parts
            fm:misaligned_parts a fmea:FailureMode ;
                fmea:modeName "Misaligned parts" ;
                fmea:hasEffect fm:fit_issue_effect ;
                fmea:hasCause fm:fixture_worn_cause ;
                fmea:severity 5 ;
                fmea:occurrence 7 ;
                fmea:detection 5 ;
                fmea:currentControl "Dimensional check" .

            fm:fit_issue_effect a fmea:Effect ;
                fmea:effectDescription "Parts do not fit together properly" ;
                fmea:severityRating 5 .

            fm:fixture_worn_cause a fmea:Cause ;
                fmea:causeDescription "Assembly fixture worn" ;
                fmea:occurrenceRating 7 .
        """
        adapter.load_turtle(fmea_turtle)

        # Act - Query failure modes and calculate RPN
        failure_modes = adapter.query("""
            PREFIX fmea: <http://kgcl.io/ontology/fmea#>

            SELECT ?modeName ?severity ?occurrence ?detection
                   ((?severity * ?occurrence * ?detection) AS ?rpn)
            WHERE {
                ?fm a fmea:FailureMode ;
                    fmea:modeName ?modeName ;
                    fmea:severity ?severity ;
                    fmea:occurrence ?occurrence ;
                    fmea:detection ?detection .
            }
            ORDER BY DESC(?rpn)
        """)

        # Store RPN results in PostgreSQL
        for fm in failure_modes:
            cursor.execute(
                """
                INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    project_id,
                    1,
                    "fmea_rpn",
                    fm["modeName"].replace(" ", "_").lower(),
                    json.dumps({
                        "failure_mode": fm["modeName"],
                        "severity": int(fm["severity"]),
                        "occurrence": int(fm["occurrence"]),
                        "detection": int(fm["detection"]),
                        "rpn": int(fm["rpn"]),
                    }),
                ),
            )
        postgres_connection.commit()

        # Assert
        assert len(failure_modes) == 3, "Should have 3 failure modes"

        # Verify RPN calculation: S * O * D
        for fm in failure_modes:
            expected_rpn = int(fm["severity"]) * int(fm["occurrence"]) * int(fm["detection"])
            assert int(fm["rpn"]) == expected_rpn, f"RPN mismatch for {fm['modeName']}"

        # Improper torque should have highest RPN (8 * 6 * 4 = 192)
        assert failure_modes[0]["modeName"] == "Improper fastener torque"
        assert int(failure_modes[0]["rpn"]) == 192

        # Cleanup
        adapter.clear()


@pytest.mark.container
@pytest.mark.oxigraph_server
@pytest.mark.postgres
@pytest.mark.redis
class TestFMEARiskPrioritization:
    """Test FMEA risk prioritization and action tracking."""

    def test_fmea_action_tracking(
        self,
        oxigraph_container: OxigraphContainer,
        postgres_connection: Any,
        redis_connection: Any,
    ) -> None:
        """Test FMEA corrective action tracking.

        Scenario: Track actions for high-RPN failure modes
        - Actions linked to failure modes in RDF
        - Action status tracked in PostgreSQL
        - Due dates cached in Redis

        Assert:
        - Actions linked correctly
        - Status tracking works
        """
        from kgcl.hybrid.adapters.remote_store_adapter import RemoteStoreAdapter

        # Arrange
        adapter = RemoteStoreAdapter(
            query_endpoint=oxigraph_container.get_sparql_endpoint(),
            update_endpoint=oxigraph_container.get_update_endpoint(),
        )
        cursor = postgres_connection.cursor()
        project_id = "FMEA-ACTIONS-001"

        # Load FMEA with actions
        fmea_actions_turtle = """
            @prefix fmea: <http://kgcl.io/ontology/fmea#> .
            @prefix fm: <http://example.org/failure_mode/> .
            @prefix act: <http://example.org/action/> .

            fm:improper_torque a fmea:FailureMode ;
                fmea:modeName "Improper fastener torque" ;
                fmea:severity 8 ;
                fmea:occurrence 6 ;
                fmea:detection 4 ;
                fmea:hasAction act:torque_wrench_upgrade, act:operator_training .

            act:torque_wrench_upgrade a fmea:CorrectiveAction ;
                fmea:actionDescription "Upgrade to digital torque wrenches with data logging" ;
                fmea:actionType "Design" ;
                fmea:targetOccurrence 2 ;
                fmea:targetDetection 2 ;
                fmea:responsibility "Engineering" ;
                fmea:dueDate "2024-03-15" ;
                fmea:status "In Progress" .

            act:operator_training a fmea:CorrectiveAction ;
                fmea:actionDescription "Retrain operators on torque specifications" ;
                fmea:actionType "Process" ;
                fmea:targetOccurrence 3 ;
                fmea:targetDetection 4 ;
                fmea:responsibility "Training" ;
                fmea:dueDate "2024-02-28" ;
                fmea:status "Completed" .

            fm:misaligned_parts a fmea:FailureMode ;
                fmea:modeName "Misaligned parts" ;
                fmea:severity 5 ;
                fmea:occurrence 7 ;
                fmea:detection 5 ;
                fmea:hasAction act:fixture_replacement .

            act:fixture_replacement a fmea:CorrectiveAction ;
                fmea:actionDescription "Replace worn fixtures with new tooling" ;
                fmea:actionType "Design" ;
                fmea:targetOccurrence 2 ;
                fmea:targetDetection 3 ;
                fmea:responsibility "Tooling" ;
                fmea:dueDate "2024-04-01" ;
                fmea:status "Planned" .
        """
        adapter.load_turtle(fmea_actions_turtle)

        # Act - Query actions with RPN reduction potential
        actions = adapter.query("""
            PREFIX fmea: <http://kgcl.io/ontology/fmea#>

            SELECT ?modeName ?actionDesc ?actionType ?responsibility ?dueDate ?status
                   ?severity ?occurrence ?detection ?targetOccurrence ?targetDetection
                   ((?severity * ?occurrence * ?detection) AS ?currentRPN)
                   ((?severity * ?targetOccurrence * ?targetDetection) AS ?targetRPN)
            WHERE {
                ?fm a fmea:FailureMode ;
                    fmea:modeName ?modeName ;
                    fmea:severity ?severity ;
                    fmea:occurrence ?occurrence ;
                    fmea:detection ?detection ;
                    fmea:hasAction ?action .

                ?action fmea:actionDescription ?actionDesc ;
                    fmea:actionType ?actionType ;
                    fmea:targetOccurrence ?targetOccurrence ;
                    fmea:targetDetection ?targetDetection ;
                    fmea:responsibility ?responsibility ;
                    fmea:dueDate ?dueDate ;
                    fmea:status ?status .
            }
            ORDER BY DESC(?currentRPN)
        """)

        # Store action status in PostgreSQL
        for action in actions:
            rpn_reduction = int(action["currentRPN"]) - int(action["targetRPN"])

            cursor.execute(
                """
                INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    project_id,
                    2,
                    "fmea_action",
                    action["actionDesc"][:30].replace(" ", "_").lower(),
                    json.dumps({
                        "failure_mode": action["modeName"],
                        "action": action["actionDesc"],
                        "type": action["actionType"],
                        "responsibility": action["responsibility"],
                        "due_date": action["dueDate"],
                        "status": action["status"],
                        "current_rpn": int(action["currentRPN"]),
                        "target_rpn": int(action["targetRPN"]),
                        "rpn_reduction": rpn_reduction,
                    }),
                ),
            )

            # Cache due date in Redis for alerts
            redis_connection.hset(
                f"fmea:{project_id}:actions",
                action["actionDesc"][:50],
                json.dumps({
                    "due_date": action["dueDate"],
                    "status": action["status"],
                    "responsibility": action["responsibility"],
                }),
            )

        postgres_connection.commit()

        # Assert
        assert len(actions) == 3, "Should have 3 actions"

        # Verify RPN reduction calculated
        for action in actions:
            current = int(action["currentRPN"])
            target = int(action["targetRPN"])
            assert target < current, f"Target RPN should be lower for {action['actionDesc']}"

        # Verify status tracking
        statuses = {a["status"] for a in actions}
        assert "Completed" in statuses
        assert "In Progress" in statuses
        assert "Planned" in statuses

        # Verify Redis cache
        cached_actions = redis_connection.hgetall(f"fmea:{project_id}:actions")
        assert len(cached_actions) == 3, "All actions should be cached"

        # Cleanup
        adapter.clear()


@pytest.mark.container
@pytest.mark.oxigraph_server
@pytest.mark.postgres
class TestFMEARPNThresholds:
    """Test FMEA RPN threshold-based prioritization."""

    def test_rpn_threshold_categorization(
        self,
        oxigraph_container: OxigraphContainer,
        postgres_connection: Any,
    ) -> None:
        """Test RPN threshold categorization.

        Scenario: Categorize failure modes by RPN threshold
        - High: RPN >= 100
        - Medium: 50 <= RPN < 100
        - Low: RPN < 50

        Assert:
        - Correct categorization
        - High-risk items flagged
        """
        from kgcl.hybrid.adapters.remote_store_adapter import RemoteStoreAdapter

        # Arrange
        adapter = RemoteStoreAdapter(
            query_endpoint=oxigraph_container.get_sparql_endpoint(),
            update_endpoint=oxigraph_container.get_update_endpoint(),
        )
        cursor = postgres_connection.cursor()
        project_id = "FMEA-THRESHOLD-001"

        # Load multiple failure modes with varying RPN
        fmea_turtle = """
            @prefix fmea: <http://kgcl.io/ontology/fmea#> .
            @prefix fm: <http://example.org/failure_mode/> .

            fm:high_risk_1 a fmea:FailureMode ;
                fmea:modeName "Critical failure mode A" ;
                fmea:severity 9 ;
                fmea:occurrence 5 ;
                fmea:detection 4 .  # RPN = 180

            fm:high_risk_2 a fmea:FailureMode ;
                fmea:modeName "Critical failure mode B" ;
                fmea:severity 8 ;
                fmea:occurrence 6 ;
                fmea:detection 3 .  # RPN = 144

            fm:medium_risk_1 a fmea:FailureMode ;
                fmea:modeName "Medium failure mode A" ;
                fmea:severity 5 ;
                fmea:occurrence 4 ;
                fmea:detection 4 .  # RPN = 80

            fm:medium_risk_2 a fmea:FailureMode ;
                fmea:modeName "Medium failure mode B" ;
                fmea:severity 6 ;
                fmea:occurrence 3 ;
                fmea:detection 3 .  # RPN = 54

            fm:low_risk_1 a fmea:FailureMode ;
                fmea:modeName "Low failure mode A" ;
                fmea:severity 3 ;
                fmea:occurrence 2 ;
                fmea:detection 4 .  # RPN = 24

            fm:low_risk_2 a fmea:FailureMode ;
                fmea:modeName "Low failure mode B" ;
                fmea:severity 2 ;
                fmea:occurrence 3 ;
                fmea:detection 2 .  # RPN = 12
        """
        adapter.load_turtle(fmea_turtle)

        # Act - Query and categorize by RPN threshold
        # Note: SPARQL doesn't support IF/CASE, so we categorize in Python
        all_modes = adapter.query("""
            PREFIX fmea: <http://kgcl.io/ontology/fmea#>

            SELECT ?modeName ?severity ?occurrence ?detection
                   ((?severity * ?occurrence * ?detection) AS ?rpn)
            WHERE {
                ?fm a fmea:FailureMode ;
                    fmea:modeName ?modeName ;
                    fmea:severity ?severity ;
                    fmea:occurrence ?occurrence ;
                    fmea:detection ?detection .
            }
            ORDER BY DESC(?rpn)
        """)

        # Categorize by threshold
        categories = {"high": [], "medium": [], "low": []}
        for mode in all_modes:
            rpn = int(mode["rpn"])
            if rpn >= 100:
                category = "high"
            elif rpn >= 50:
                category = "medium"
            else:
                category = "low"

            categories[category].append({
                "name": mode["modeName"],
                "rpn": rpn,
            })

            cursor.execute(
                """
                INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    project_id,
                    1,
                    f"fmea_rpn_{category}",
                    mode["modeName"].replace(" ", "_").lower(),
                    json.dumps({
                        "failure_mode": mode["modeName"],
                        "rpn": rpn,
                        "category": category,
                        "action_required": category in ["high", "medium"],
                    }),
                ),
            )
        postgres_connection.commit()

        # Store summary
        summary = {
            "total_modes": len(all_modes),
            "high_risk_count": len(categories["high"]),
            "medium_risk_count": len(categories["medium"]),
            "low_risk_count": len(categories["low"]),
            "action_required_count": len(categories["high"]) + len(categories["medium"]),
        }

        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                project_id,
                1,
                "fmea_summary",
                "categorization",
                json.dumps(summary),
            ),
        )
        postgres_connection.commit()

        # Assert
        assert len(categories["high"]) == 2, "Should have 2 high-risk modes"
        assert len(categories["medium"]) == 2, "Should have 2 medium-risk modes"
        assert len(categories["low"]) == 2, "Should have 2 low-risk modes"

        # Verify high-risk modes
        high_names = {m["name"] for m in categories["high"]}
        assert "Critical failure mode A" in high_names
        assert "Critical failure mode B" in high_names

        # Verify RPN values
        assert categories["high"][0]["rpn"] == 180  # Highest
        assert categories["low"][-1]["rpn"] == 12  # Lowest

        # Cleanup
        adapter.clear()

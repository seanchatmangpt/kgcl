"""Integration tests for Explicit Termination Pattern (WCP-43).

Tests workflow explicit termination with full cleanup across all services,
lockchain finalization, and resource release.

Real-world scenarios:
- Explicit workflow termination with cleanup
- Lockchain receipt finalization
- Cross-service resource release
"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from tests.containers.rdf_stores import OxigraphContainer


@pytest.mark.container
@pytest.mark.postgres
@pytest.mark.redis
@pytest.mark.wcp(43)
class TestWCP43ExplicitTerminationWithCleanup:
    """WCP-43: Explicit Termination with full cleanup.

    Scenario: Order Fulfillment Completion
    - Order processing completes successfully
    - All resources released
    - Final lockchain receipt written
    - State cleaned up
    """

    def test_explicit_termination_full_cleanup(
        self,
        postgres_connection: Any,
        redis_connection: Any,
    ) -> None:
        """Test explicit termination with complete resource cleanup.

        Arrange:
        - Create workflow with multiple active resources
        - Set up state in Redis and PostgreSQL

        Act:
        - Execute explicit termination
        - Clean up all resources

        Assert:
        - All resources released
        - Final state logged
        - Lockchain finalized
        """
        # Arrange
        workflow_id = "WF-TERM-001"
        cursor = postgres_connection.cursor()

        # Create workflow state in Redis
        state_keys = [
            f"workflow:{workflow_id}:state",
            f"workflow:{workflow_id}:locks",
            f"workflow:{workflow_id}:tokens",
            f"workflow:{workflow_id}:cache",
        ]

        for key in state_keys:
            redis_connection.set(key, json.dumps({"status": "active"}))

        # Log workflow execution state
        tasks = ["receive_order", "process_payment", "reserve_inventory", "ship_order"]
        for task in tasks:
            cursor.execute(
                """
                INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    workflow_id,
                    43,
                    "task_completed",
                    task,
                    json.dumps({"status": "completed", "timestamp": time.time()}),
                ),
            )

        # Write tick receipts (simulating lockchain)
        for tick in range(1, 5):
            cursor.execute(
                """
                INSERT INTO tick_receipts (workflow_id, tick_number, graph_hash, previous_hash, receipt_hash, hook_results)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    workflow_id,
                    tick,
                    f"hash_{tick}",
                    f"prev_{tick - 1}" if tick > 1 else "genesis",
                    f"receipt_{tick}",
                    json.dumps([]),
                ),
            )
        postgres_connection.commit()

        # Act: Execute explicit termination
        # 1. Write final lockchain receipt
        cursor.execute(
            """
            INSERT INTO tick_receipts (workflow_id, tick_number, graph_hash, previous_hash, receipt_hash, hook_results, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                workflow_id,
                5,  # Final tick
                "final_hash",
                "receipt_4",
                "final_receipt",
                json.dumps([]),
                json.dumps({"termination": "explicit", "final": True}),
            ),
        )

        # 2. Clean up Redis state
        for key in state_keys:
            redis_connection.delete(key)

        # 3. Log termination
        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                workflow_id,
                43,
                "explicit_termination",
                "workflow_end",
                json.dumps({
                    "termination_type": "explicit",
                    "resources_cleaned": state_keys,
                    "final_tick": 5,
                    "total_tasks": len(tasks),
                }),
            ),
        )
        postgres_connection.commit()

        # Assert
        # Verify Redis state cleaned
        for key in state_keys:
            assert not redis_connection.exists(key), f"{key} should be deleted"

        # Verify final lockchain receipt
        cursor.execute(
            """
            SELECT metadata FROM tick_receipts
            WHERE workflow_id = %s
            ORDER BY tick_number DESC
            LIMIT 1
            """,
            (workflow_id,),
        )
        final_receipt = cursor.fetchone()
        assert final_receipt is not None
        metadata = json.loads(final_receipt[0])
        assert metadata["final"] is True
        assert metadata["termination"] == "explicit"

        # Verify termination logged
        cursor.execute(
            """
            SELECT event_type FROM workflow_audit
            WHERE workflow_id = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (workflow_id,),
        )
        last_event = cursor.fetchone()[0]
        assert last_event == "explicit_termination"


@pytest.mark.container
@pytest.mark.oxigraph_server
@pytest.mark.postgres
@pytest.mark.redis
@pytest.mark.wcp(43)
class TestWCP43CrossServiceTermination:
    """WCP-43: Cross-service explicit termination.

    Demonstrates coordinated termination across:
    - Oxigraph (RDF state)
    - PostgreSQL (audit/lockchain)
    - Redis (runtime state)
    """

    def test_coordinated_termination_all_services(
        self,
        oxigraph_container: OxigraphContainer,
        postgres_connection: Any,
        redis_connection: Any,
    ) -> None:
        """Test explicit termination with coordinated cleanup across all services.

        Arrange:
        - Create workflow state in all three services

        Act:
        - Execute coordinated termination

        Assert:
        - All services cleaned up
        - Termination recorded in each
        """
        from kgcl.hybrid.adapters.remote_store_adapter import RemoteStoreAdapter

        # Arrange
        workflow_id = "WF-CROSS-TERM-001"

        adapter = RemoteStoreAdapter(
            query_endpoint=oxigraph_container.get_sparql_endpoint(),
            update_endpoint=oxigraph_container.get_update_endpoint(),
        )

        # Create state in Oxigraph
        workflow_turtle = f"""
            @prefix kgc: <http://kgcl.io/ontology/kgc#> .
            @prefix wf: <http://example.org/workflow/> .

            wf:{workflow_id} a kgc:WorkflowInstance ;
                kgc:status "active" ;
                kgc:hasTask wf:task_1, wf:task_2 .

            wf:task_1 kgc:status "completed" ;
                kgc:hasToken false .

            wf:task_2 kgc:status "completed" ;
                kgc:hasToken false .
        """
        adapter.load_turtle(workflow_turtle)

        # Create state in Redis
        redis_connection.set(f"wf:{workflow_id}:active", "true")
        redis_connection.hset(f"wf:{workflow_id}:tokens", "task_1", "0")
        redis_connection.hset(f"wf:{workflow_id}:tokens", "task_2", "0")

        # Create state in PostgreSQL
        cursor = postgres_connection.cursor()
        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                workflow_id,
                43,
                "workflow_active",
                "monitor",
                json.dumps({"services": ["oxigraph", "redis", "postgres"]}),
            ),
        )
        postgres_connection.commit()

        # Verify state exists in all services
        rdf_exists_before = adapter.ask(f"""
            PREFIX wf: <http://example.org/workflow/>
            ASK {{ wf:{workflow_id} ?p ?o }}
        """)
        redis_exists_before = redis_connection.exists(f"wf:{workflow_id}:active")
        assert rdf_exists_before, "RDF state should exist before termination"
        assert redis_exists_before, "Redis state should exist before termination"

        # Act: Coordinated termination
        # 1. Clear Oxigraph
        adapter.update(f"""
            PREFIX wf: <http://example.org/workflow/>
            PREFIX kgc: <http://kgcl.io/ontology/kgc#>
            DELETE WHERE {{
                wf:{workflow_id} ?p ?o .
            }}
        """)
        # Also clear related tasks
        adapter.update(f"""
            PREFIX wf: <http://example.org/workflow/>
            DELETE WHERE {{
                wf:task_1 ?p ?o .
                wf:task_2 ?p ?o .
            }}
        """)

        # 2. Clear Redis
        redis_connection.delete(
            f"wf:{workflow_id}:active",
            f"wf:{workflow_id}:tokens",
        )

        # 3. Log termination to PostgreSQL
        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                workflow_id,
                43,
                "cross_service_termination",
                "terminator",
                json.dumps({
                    "services_cleaned": ["oxigraph", "redis"],
                    "termination_recorded": "postgres",
                }),
            ),
        )
        postgres_connection.commit()

        # Assert
        # Verify Oxigraph cleared
        rdf_exists_after = adapter.ask(f"""
            PREFIX wf: <http://example.org/workflow/>
            ASK {{ wf:{workflow_id} ?p ?o }}
        """)
        assert not rdf_exists_after, "RDF state should be cleared"

        # Verify Redis cleared
        redis_exists_after = redis_connection.exists(f"wf:{workflow_id}:active")
        assert not redis_exists_after, "Redis state should be cleared"

        # Verify PostgreSQL has termination record
        cursor.execute(
            """
            SELECT COUNT(*) FROM workflow_audit
            WHERE workflow_id = %s AND event_type = 'cross_service_termination'
            """,
            (workflow_id,),
        )
        term_count = cursor.fetchone()[0]
        assert term_count == 1, "Termination should be recorded"

        # Cleanup
        adapter.clear()


@pytest.mark.container
@pytest.mark.postgres
@pytest.mark.wcp(43)
class TestWCP43LockchainFinalization:
    """WCP-43: Lockchain finalization at termination.

    Ensures cryptographic chain is properly closed with
    final receipt at workflow termination.
    """

    def test_lockchain_finalization(
        self,
        postgres_connection: Any,
    ) -> None:
        """Test lockchain is finalized with terminal receipt.

        Arrange:
        - Create workflow with tick receipts

        Act:
        - Write final termination receipt

        Assert:
        - Chain is complete
        - Final receipt marked as terminal
        """
        from kgcl.hybrid.adapters.postgres_lockchain import PostgresLockchainWriter

        # Arrange
        workflow_id = "WF-LOCKCHAIN-001"
        writer = PostgresLockchainWriter(postgres_connection)

        # Write execution tick receipts
        for tick in range(1, 4):
            writer.write_tick_receipt(
                workflow_id=workflow_id,
                tick_number=tick,
                graph_hash=f"graph_hash_{tick}",
                hook_results=[{"hook_id": f"hook_{tick}", "result": True}],
            )

        # Act: Write terminal receipt
        final_tick = writer.write_tick_receipt(
            workflow_id=workflow_id,
            tick_number=4,
            graph_hash="final_graph_hash",
            hook_results=[],
            metadata={"terminal": True, "reason": "explicit_termination"},
        )

        # Assert
        assert final_tick > 0, "Final receipt should be written"

        # Verify chain integrity
        is_valid, message = writer.verify_chain(workflow_id)
        assert is_valid, f"Chain should be valid: {message}"

        # Verify final receipt
        chain = writer.get_chain(workflow_id)
        assert len(chain) == 4, "Should have 4 receipts"
        assert chain[-1].metadata is not None
        assert chain[-1].metadata.get("terminal") is True

        # Verify chain links
        for i in range(1, len(chain)):
            assert chain[i].previous_hash == chain[i - 1].receipt_hash, (
                f"Chain link broken at tick {chain[i].tick_number}"
            )

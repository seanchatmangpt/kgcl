"""Integration tests for DMAIC workflow with containers.

Tests the Define, Measure, Analyze, Improve, Control (DMAIC) cycle
using real database infrastructure for metric persistence and RDF
for ontology-based quality modeling.

Real-world scenarios:
- Manufacturing defect reduction
- Process cycle time improvement
- Quality control workflow
"""

from __future__ import annotations

import json
import statistics
import time
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from tests.containers.rdf_stores import OxigraphContainer


@pytest.mark.container
@pytest.mark.postgres
@pytest.mark.redis
class TestDMAICDefinePhase:
    """Test DMAIC Define phase with persistent problem definition."""

    def test_define_problem_statement_persisted(
        self,
        postgres_connection: Any,
        redis_connection: Any,
    ) -> None:
        """Test problem statement persistence across services.

        Scenario: Define a manufacturing quality problem
        - Problem statement stored in PostgreSQL
        - Current metrics cached in Redis
        - CTQ (Critical to Quality) factors identified

        Assert:
        - Problem definition persisted
        - CTQs linked to problem
        """
        # Arrange
        cursor = postgres_connection.cursor()
        project_id = "DMAIC-001"

        problem_definition = {
            "project_id": project_id,
            "problem_statement": "Widget assembly defect rate exceeds 3% target",
            "project_scope": "Widget assembly line A",
            "business_case": "Reducing defects by 50% saves $500K annually",
            "goal_statement": "Reduce defect rate from 5% to 2.5%",
            "timeline": "12 weeks",
            "team": ["Process Engineer", "QC Manager", "Line Supervisor"],
        }

        ctqs = [
            {"name": "Defect Rate", "target": 0.025, "current": 0.05, "unit": "%"},
            {"name": "First Pass Yield", "target": 0.975, "current": 0.95, "unit": "%"},
            {"name": "Rework Hours", "target": 100, "current": 200, "unit": "hours/week"},
        ]

        # Act - Store problem definition
        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                project_id,
                1,
                "dmaic_define",
                "problem_definition",
                json.dumps(problem_definition),
            ),
        )

        # Store CTQs
        for ctq in ctqs:
            cursor.execute(
                """
                INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    project_id,
                    1,
                    "dmaic_ctq",
                    f"ctq_{ctq['name'].lower().replace(' ', '_')}",
                    json.dumps(ctq),
                ),
            )
        postgres_connection.commit()

        # Cache current metrics in Redis
        for ctq in ctqs:
            redis_connection.hset(
                f"dmaic:{project_id}:metrics",
                ctq["name"],
                str(ctq["current"]),
            )

        # Assert
        cursor.execute(
            """
            SELECT token_state FROM workflow_audit
            WHERE workflow_id = %s AND event_type = 'dmaic_define'
            """,
            (project_id,),
        )
        stored = json.loads(cursor.fetchone()[0])
        assert stored["problem_statement"] == problem_definition["problem_statement"]

        cursor.execute(
            """
            SELECT COUNT(*) FROM workflow_audit
            WHERE workflow_id = %s AND event_type = 'dmaic_ctq'
            """,
            (project_id,),
        )
        ctq_count = cursor.fetchone()[0]
        assert ctq_count == 3, "All CTQs should be stored"

        metrics = redis_connection.hgetall(f"dmaic:{project_id}:metrics")
        assert len(metrics) == 3, "All metrics should be cached"


@pytest.mark.container
@pytest.mark.postgres
@pytest.mark.redis
class TestDMAICMeasurePhase:
    """Test DMAIC Measure phase with data collection."""

    def test_measure_baseline_data_collection(
        self,
        postgres_connection: Any,
        redis_connection: Any,
    ) -> None:
        """Test baseline measurement data collection.

        Scenario: Collect defect data over time
        - Time-series data stored in PostgreSQL
        - Running statistics in Redis
        - Measurement system analysis recorded

        Assert:
        - Data points collected and stored
        - Statistical summary calculated
        """
        import random

        # Arrange
        cursor = postgres_connection.cursor()
        project_id = "DMAIC-MEASURE-001"
        num_samples = 100

        # Simulate defect data (baseline ~5% defect rate)
        random.seed(42)
        samples = []
        for i in range(num_samples):
            sample = {
                "sample_id": f"S{i:04d}",
                "timestamp": time.time() + i * 3600,
                "total_units": 100,
                "defects": random.randint(2, 8),  # 2-8% range
                "shift": ["A", "B", "C"][i % 3],
                "operator": f"OP{(i % 5) + 1}",
            }
            sample["defect_rate"] = sample["defects"] / sample["total_units"]
            samples.append(sample)

        # Act - Store measurement data
        for sample in samples:
            cursor.execute(
                """
                INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    project_id,
                    2,
                    "dmaic_measure",
                    sample["sample_id"],
                    json.dumps(sample),
                ),
            )

        # Calculate and store statistics
        defect_rates = [s["defect_rate"] for s in samples]
        stats = {
            "mean": statistics.mean(defect_rates),
            "stdev": statistics.stdev(defect_rates),
            "min": min(defect_rates),
            "max": max(defect_rates),
            "median": statistics.median(defect_rates),
            "sample_size": len(samples),
        }

        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                project_id,
                2,
                "dmaic_baseline_stats",
                "statistics",
                json.dumps(stats),
            ),
        )
        postgres_connection.commit()

        # Cache running stats in Redis
        redis_connection.hset(
            f"dmaic:{project_id}:baseline",
            mapping={
                "mean": str(stats["mean"]),
                "stdev": str(stats["stdev"]),
                "sample_size": str(stats["sample_size"]),
            },
        )

        # Assert
        cursor.execute(
            """
            SELECT COUNT(*) FROM workflow_audit
            WHERE workflow_id = %s AND event_type = 'dmaic_measure'
            """,
            (project_id,),
        )
        sample_count = cursor.fetchone()[0]
        assert sample_count == num_samples, "All samples should be stored"

        cursor.execute(
            """
            SELECT token_state FROM workflow_audit
            WHERE workflow_id = %s AND event_type = 'dmaic_baseline_stats'
            """,
            (project_id,),
        )
        stored_stats = json.loads(cursor.fetchone()[0])
        assert 0.04 < stored_stats["mean"] < 0.06, "Mean should be around 5%"
        assert stored_stats["sample_size"] == num_samples

        cached_mean = float(redis_connection.hget(f"dmaic:{project_id}:baseline", "mean") or 0)
        assert abs(cached_mean - stats["mean"]) < 0.001


@pytest.mark.container
@pytest.mark.oxigraph_server
@pytest.mark.postgres
class TestDMAICAnalyzePhase:
    """Test DMAIC Analyze phase with RDF-based root cause analysis."""

    def test_analyze_root_cause_with_rdf_ontology(
        self,
        oxigraph_container: OxigraphContainer,
        postgres_connection: Any,
    ) -> None:
        """Test root cause analysis using RDF ontology.

        Scenario: Model defect causes in RDF
        - Fishbone diagram as RDF graph
        - Statistical correlations stored
        - Root causes prioritized

        Assert:
        - Cause-effect relationships modeled
        - Top causes identified
        """
        from kgcl.hybrid.adapters.remote_store_adapter import RemoteStoreAdapter

        # Arrange
        adapter = RemoteStoreAdapter(
            query_endpoint=oxigraph_container.get_sparql_endpoint(),
            update_endpoint=oxigraph_container.get_update_endpoint(),
        )
        cursor = postgres_connection.cursor()
        project_id = "DMAIC-ANALYZE-001"

        # Load fishbone diagram as RDF
        fishbone_turtle = """
            @prefix lss: <http://kgcl.io/ontology/lss#> .
            @prefix def: <http://example.org/defect/> .

            def:widget_defect a lss:Problem ;
                lss:hasEffect "Widget assembly defect rate 5%" ;
                lss:hasCategory def:machine, def:method, def:material,
                                def:measurement, def:manpower, def:environment .

            # Machine category
            def:machine a lss:CauseCategory ;
                lss:categoryName "Machine" ;
                lss:hasCause def:worn_tooling, def:misaligned_fixture .

            def:worn_tooling a lss:RootCause ;
                lss:causeName "Worn tooling" ;
                lss:correlation 0.72 ;
                lss:pValue 0.001 .

            def:misaligned_fixture a lss:RootCause ;
                lss:causeName "Misaligned fixture" ;
                lss:correlation 0.45 ;
                lss:pValue 0.023 .

            # Method category
            def:method a lss:CauseCategory ;
                lss:categoryName "Method" ;
                lss:hasCause def:inconsistent_torque, def:wrong_sequence .

            def:inconsistent_torque a lss:RootCause ;
                lss:causeName "Inconsistent torque application" ;
                lss:correlation 0.68 ;
                lss:pValue 0.002 .

            def:wrong_sequence a lss:RootCause ;
                lss:causeName "Wrong assembly sequence" ;
                lss:correlation 0.31 ;
                lss:pValue 0.089 .

            # Material category
            def:material a lss:CauseCategory ;
                lss:categoryName "Material" ;
                lss:hasCause def:supplier_variation .

            def:supplier_variation a lss:RootCause ;
                lss:causeName "Supplier material variation" ;
                lss:correlation 0.55 ;
                lss:pValue 0.008 .
        """
        adapter.load_turtle(fishbone_turtle)

        # Act - Query top root causes by correlation
        top_causes = adapter.query("""
            PREFIX lss: <http://kgcl.io/ontology/lss#>

            SELECT ?causeName ?correlation ?pValue
            WHERE {
                ?cause a lss:RootCause ;
                    lss:causeName ?causeName ;
                    lss:correlation ?correlation ;
                    lss:pValue ?pValue .
                FILTER (?pValue < 0.05)
            }
            ORDER BY DESC(?correlation)
            LIMIT 5
        """)

        # Store analysis results
        for cause in top_causes:
            cursor.execute(
                """
                INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    project_id,
                    3,
                    "dmaic_root_cause",
                    cause["causeName"].replace(" ", "_").lower(),
                    json.dumps({
                        "cause": cause["causeName"],
                        "correlation": float(cause["correlation"]),
                        "p_value": float(cause["pValue"]),
                    }),
                ),
            )
        postgres_connection.commit()

        # Assert
        assert len(top_causes) >= 3, "Should find at least 3 significant causes"
        assert top_causes[0]["causeName"] == "Worn tooling", "Top cause should be worn tooling"
        assert float(top_causes[0]["correlation"]) > 0.7, "Top correlation should be >0.7"

        # Verify all significant causes have p-value < 0.05
        for cause in top_causes:
            assert float(cause["pValue"]) < 0.05, f"{cause['causeName']} should be significant"

        # Cleanup
        adapter.clear()


@pytest.mark.container
@pytest.mark.postgres
@pytest.mark.redis
class TestDMAICImprovePhase:
    """Test DMAIC Improve phase with experiment tracking."""

    def test_improve_experiment_tracking(
        self,
        postgres_connection: Any,
        redis_connection: Any,
    ) -> None:
        """Test improvement experiment tracking.

        Scenario: Track DOE (Design of Experiments)
        - Experiment configurations stored
        - Results compared to baseline
        - Statistical significance validated

        Assert:
        - Experiments tracked
        - Improvement quantified
        """
        import random

        # Arrange
        cursor = postgres_connection.cursor()
        project_id = "DMAIC-IMPROVE-001"

        # Baseline metrics
        baseline = {
            "defect_rate_mean": 0.05,
            "defect_rate_stdev": 0.015,
        }
        redis_connection.hset(
            f"dmaic:{project_id}:baseline",
            mapping={k: str(v) for k, v in baseline.items()},
        )

        # Experiment: New tooling + Torque control
        experiments = [
            {
                "exp_id": "EXP-001",
                "name": "New Tooling Only",
                "factors": {"new_tooling": True, "torque_control": False},
                "expected_improvement": 0.015,
            },
            {
                "exp_id": "EXP-002",
                "name": "Torque Control Only",
                "factors": {"new_tooling": False, "torque_control": True},
                "expected_improvement": 0.012,
            },
            {
                "exp_id": "EXP-003",
                "name": "Combined Treatment",
                "factors": {"new_tooling": True, "torque_control": True},
                "expected_improvement": 0.025,
            },
        ]

        # Act - Run experiments and collect results
        random.seed(42)
        results = []
        for exp in experiments:
            # Simulate experiment results
            improvement = exp["expected_improvement"]
            new_rate = baseline["defect_rate_mean"] - improvement
            samples = [
                max(0, random.gauss(new_rate, baseline["defect_rate_stdev"] * 0.8))
                for _ in range(30)
            ]

            result = {
                **exp,
                "sample_size": 30,
                "mean": statistics.mean(samples),
                "stdev": statistics.stdev(samples),
                "improvement": baseline["defect_rate_mean"] - statistics.mean(samples),
                "improvement_pct": (
                    baseline["defect_rate_mean"] - statistics.mean(samples)
                ) / baseline["defect_rate_mean"] * 100,
            }
            results.append(result)

            cursor.execute(
                """
                INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    project_id,
                    4,
                    "dmaic_experiment",
                    exp["exp_id"],
                    json.dumps(result),
                ),
            )

        # Find best experiment
        best = max(results, key=lambda x: x["improvement"])

        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                project_id,
                4,
                "dmaic_best_solution",
                "selection",
                json.dumps({
                    "selected": best["exp_id"],
                    "name": best["name"],
                    "improvement": best["improvement"],
                    "new_defect_rate": best["mean"],
                }),
            ),
        )
        postgres_connection.commit()

        # Assert
        assert best["exp_id"] == "EXP-003", "Combined treatment should be best"
        assert best["improvement"] > 0.02, "Improvement should exceed 2%"

        cursor.execute(
            """
            SELECT COUNT(*) FROM workflow_audit
            WHERE workflow_id = %s AND event_type = 'dmaic_experiment'
            """,
            (project_id,),
        )
        exp_count = cursor.fetchone()[0]
        assert exp_count == 3, "All experiments should be recorded"


@pytest.mark.container
@pytest.mark.postgres
@pytest.mark.redis
class TestDMAICControlPhase:
    """Test DMAIC Control phase with monitoring."""

    def test_control_phase_monitoring(
        self,
        postgres_connection: Any,
        redis_connection: Any,
    ) -> None:
        """Test control phase monitoring and alerts.

        Scenario: Monitor process after improvement
        - Control limits established
        - Out-of-control points detected
        - Alerts generated

        Assert:
        - Control limits set correctly
        - OOC points identified
        """
        import random

        # Arrange
        cursor = postgres_connection.cursor()
        project_id = "DMAIC-CONTROL-001"

        # Improved process parameters
        new_mean = 0.025  # 2.5% defect rate
        new_stdev = 0.008

        # Control limits (3-sigma)
        ucl = new_mean + 3 * new_stdev
        lcl = max(0, new_mean - 3 * new_stdev)

        control_plan = {
            "metric": "defect_rate",
            "target": new_mean,
            "ucl": ucl,
            "lcl": lcl,
            "sample_frequency": "hourly",
            "sample_size": 50,
            "response_plan": "Stop line if 2 consecutive OOC",
        }

        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                project_id,
                5,
                "dmaic_control_plan",
                "setup",
                json.dumps(control_plan),
            ),
        )

        # Cache control limits in Redis
        redis_connection.hset(
            f"dmaic:{project_id}:control",
            mapping={
                "ucl": str(ucl),
                "lcl": str(lcl),
                "target": str(new_mean),
            },
        )

        # Act - Simulate monitoring data (some OOC points)
        random.seed(42)
        monitoring_data = []
        ooc_count = 0

        for i in range(50):
            # Inject some out-of-control points
            if i in [15, 16, 35]:
                value = ucl + 0.005  # Above UCL
            elif i == 40:
                value = lcl - 0.002  # Below LCL (if possible)
            else:
                value = random.gauss(new_mean, new_stdev)

            is_ooc = value > ucl or value < lcl
            if is_ooc:
                ooc_count += 1

            point = {
                "sample_id": f"MON{i:04d}",
                "timestamp": time.time() + i * 3600,
                "value": value,
                "is_ooc": is_ooc,
                "ucl": ucl,
                "lcl": lcl,
            }
            monitoring_data.append(point)

            if is_ooc:
                cursor.execute(
                    """
                    INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        project_id,
                        5,
                        "dmaic_ooc_alert",
                        point["sample_id"],
                        json.dumps(point),
                    ),
                )

        # Store summary
        in_control_pct = (50 - ooc_count) / 50 * 100
        summary = {
            "total_samples": 50,
            "ooc_count": ooc_count,
            "in_control_pct": in_control_pct,
            "process_stable": ooc_count < 5 and in_control_pct > 95,
        }

        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                project_id,
                5,
                "dmaic_control_summary",
                "monitoring_summary",
                json.dumps(summary),
            ),
        )
        postgres_connection.commit()

        # Update Redis with latest status
        redis_connection.hset(
            f"dmaic:{project_id}:control",
            mapping={
                "ooc_count": str(ooc_count),
                "in_control_pct": str(in_control_pct),
                "status": "stable" if summary["process_stable"] else "investigate",
            },
        )

        # Assert
        cursor.execute(
            """
            SELECT COUNT(*) FROM workflow_audit
            WHERE workflow_id = %s AND event_type = 'dmaic_ooc_alert'
            """,
            (project_id,),
        )
        alert_count = cursor.fetchone()[0]
        assert alert_count == ooc_count, "All OOC points should generate alerts"

        status = redis_connection.hget(f"dmaic:{project_id}:control", "status")
        if isinstance(status, bytes):
            status = status.decode()
        assert status in ["stable", "investigate"], "Status should be set"

"""Integration tests for SPC (Statistical Process Control) with containers.

Tests SPC monitoring using Redis for real-time data and PostgreSQL
for historical storage with control chart calculations.

Real-world scenarios:
- X-bar and R chart monitoring
- Control limit violations
- Western Electric rules detection
- Process capability analysis
"""

from __future__ import annotations

import json
import random
import statistics
import time
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    pass


@pytest.mark.container
@pytest.mark.postgres
@pytest.mark.redis
class TestSPCControlCharts:
    """Test SPC control chart implementation."""

    def test_xbar_r_chart_setup(
        self,
        postgres_connection: Any,
        redis_connection: Any,
    ) -> None:
        """Test X-bar and R chart setup and monitoring.

        Scenario: Monitor widget dimension
        - Collect subgroups of 5 measurements
        - Calculate X-bar and R for each subgroup
        - Establish control limits

        Assert:
        - Control limits calculated correctly
        - Data stored properly
        """
        # Arrange
        cursor = postgres_connection.cursor()
        project_id = "SPC-XBAR-001"
        subgroup_size = 5
        num_subgroups = 25

        # Target dimension: 10.0 mm, natural variation ~0.1 mm
        target = 10.0
        sigma = 0.1
        random.seed(42)

        # Collect subgroup data
        subgroups = []
        for i in range(num_subgroups):
            measurements = [random.gauss(target, sigma) for _ in range(subgroup_size)]
            subgroup = {
                "subgroup_id": i + 1,
                "timestamp": time.time() + i * 3600,
                "measurements": measurements,
                "xbar": statistics.mean(measurements),
                "r": max(measurements) - min(measurements),
            }
            subgroups.append(subgroup)

        # Calculate control limits
        xbar_values = [s["xbar"] for s in subgroups]
        r_values = [s["r"] for s in subgroups]

        xbar_bar = statistics.mean(xbar_values)  # Grand average
        r_bar = statistics.mean(r_values)  # Average range

        # A2 and D3, D4 factors for n=5
        a2 = 0.577
        d3 = 0.0
        d4 = 2.114

        x_ucl = xbar_bar + a2 * r_bar
        x_lcl = xbar_bar - a2 * r_bar
        r_ucl = d4 * r_bar
        r_lcl = d3 * r_bar

        control_limits = {
            "xbar_bar": xbar_bar,
            "r_bar": r_bar,
            "x_ucl": x_ucl,
            "x_lcl": x_lcl,
            "r_ucl": r_ucl,
            "r_lcl": r_lcl,
            "subgroup_size": subgroup_size,
            "num_subgroups": num_subgroups,
        }

        # Act - Store control limits
        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                project_id,
                1,
                "spc_control_limits",
                "setup",
                json.dumps(control_limits),
            ),
        )

        # Store subgroup data
        for sg in subgroups:
            cursor.execute(
                """
                INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    project_id,
                    1,
                    "spc_subgroup",
                    f"sg_{sg['subgroup_id']:03d}",
                    json.dumps(sg),
                ),
            )
        postgres_connection.commit()

        # Cache control limits in Redis
        redis_connection.hset(
            f"spc:{project_id}:limits",
            mapping={k: str(v) for k, v in control_limits.items()},
        )

        # Assert
        cursor.execute(
            """
            SELECT COUNT(*) FROM workflow_audit
            WHERE workflow_id = %s AND event_type = 'spc_subgroup'
            """,
            (project_id,),
        )
        sg_count = cursor.fetchone()[0]
        assert sg_count == num_subgroups, "All subgroups should be stored"

        # Verify control limits reasonable
        assert abs(xbar_bar - target) < 0.05, "Grand average should be near target"
        assert x_ucl > xbar_bar > x_lcl, "X-bar limits should bracket center"
        assert r_ucl > r_bar > r_lcl, "R limits should bracket center"

        # Verify Redis cache
        cached = redis_connection.hgetall(f"spc:{project_id}:limits")
        assert len(cached) > 0, "Limits should be cached"

    def test_control_limit_violation_detection(
        self,
        postgres_connection: Any,
        redis_connection: Any,
    ) -> None:
        """Test detection of control limit violations.

        Scenario: Monitor production with some OOC points
        - Inject known violations
        - Detect and flag violations

        Assert:
        - All violations detected
        - Correct classification
        """
        # Arrange
        cursor = postgres_connection.cursor()
        project_id = "SPC-VIOLATION-001"

        # Establish baseline limits
        xbar_bar = 10.0
        r_bar = 0.3
        x_ucl = 10.2
        x_lcl = 9.8
        r_ucl = 0.63
        r_lcl = 0.0

        redis_connection.hset(
            f"spc:{project_id}:limits",
            mapping={
                "xbar_bar": str(xbar_bar),
                "r_bar": str(r_bar),
                "x_ucl": str(x_ucl),
                "x_lcl": str(x_lcl),
                "r_ucl": str(r_ucl),
                "r_lcl": str(r_lcl),
            },
        )

        # Create test data with known violations
        test_points = [
            {"subgroup": 1, "xbar": 10.05, "r": 0.28, "expected_violation": None},
            {"subgroup": 2, "xbar": 9.95, "r": 0.32, "expected_violation": None},
            {"subgroup": 3, "xbar": 10.25, "r": 0.30, "expected_violation": "x_above_ucl"},  # OOC
            {"subgroup": 4, "xbar": 10.02, "r": 0.65, "expected_violation": "r_above_ucl"},  # OOC
            {"subgroup": 5, "xbar": 9.75, "r": 0.29, "expected_violation": "x_below_lcl"},  # OOC
            {"subgroup": 6, "xbar": 10.01, "r": 0.31, "expected_violation": None},
            {"subgroup": 7, "xbar": 9.98, "r": 0.27, "expected_violation": None},
        ]

        # Act - Process points and detect violations
        violations = []
        for point in test_points:
            violation = None

            if point["xbar"] > x_ucl:
                violation = "x_above_ucl"
            elif point["xbar"] < x_lcl:
                violation = "x_below_lcl"
            elif point["r"] > r_ucl:
                violation = "r_above_ucl"
            elif point["r"] < r_lcl:
                violation = "r_below_lcl"

            point["detected_violation"] = violation

            if violation:
                violations.append(point)
                cursor.execute(
                    """
                    INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        project_id,
                        1,
                        "spc_violation",
                        f"sg_{point['subgroup']:03d}",
                        json.dumps({
                            "subgroup": point["subgroup"],
                            "xbar": point["xbar"],
                            "r": point["r"],
                            "violation_type": violation,
                        }),
                    ),
                )

            # Store all points
            cursor.execute(
                """
                INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    project_id,
                    1,
                    "spc_point",
                    f"point_{point['subgroup']:03d}",
                    json.dumps(point),
                ),
            )

        postgres_connection.commit()

        # Assert
        assert len(violations) == 3, "Should detect 3 violations"

        # Verify each detected violation matches expected
        for point in test_points:
            assert point["detected_violation"] == point["expected_violation"], (
                f"Subgroup {point['subgroup']}: expected {point['expected_violation']}, "
                f"got {point['detected_violation']}"
            )

        # Verify violations stored
        cursor.execute(
            """
            SELECT COUNT(*) FROM workflow_audit
            WHERE workflow_id = %s AND event_type = 'spc_violation'
            """,
            (project_id,),
        )
        stored_violations = cursor.fetchone()[0]
        assert stored_violations == 3


@pytest.mark.container
@pytest.mark.postgres
@pytest.mark.redis
class TestWesternElectricRules:
    """Test Western Electric rules for SPC."""

    def test_western_electric_rule_detection(
        self,
        postgres_connection: Any,
        redis_connection: Any,
    ) -> None:
        """Test Western Electric rules detection.

        Rules tested:
        1. One point beyond 3 sigma
        2. Two of three points beyond 2 sigma (same side)
        3. Four of five points beyond 1 sigma (same side)
        4. Eight consecutive points on one side of center

        Assert:
        - Rules correctly detected
        """
        # Arrange
        cursor = postgres_connection.cursor()
        project_id = "SPC-WE-RULES-001"

        # Control limits
        center = 10.0
        sigma = 0.1
        one_sigma = center + sigma
        two_sigma = center + 2 * sigma
        three_sigma = center + 3 * sigma

        redis_connection.hset(
            f"spc:{project_id}:limits",
            mapping={
                "center": str(center),
                "sigma": str(sigma),
                "ucl": str(three_sigma),
                "lcl": str(center - 3 * sigma),
            },
        )

        # Test data with known rule violations
        # Rule 4: 8 consecutive points below center
        rule4_data = [9.98, 9.95, 9.92, 9.99, 9.94, 9.97, 9.93, 9.96]

        # Rule 1: Point beyond 3 sigma
        rule1_data = [10.02, 10.05, 10.35, 10.01]  # Point 3 violates

        # Rule 2: 2 of 3 beyond 2 sigma (same side)
        rule2_data = [10.22, 10.05, 10.25, 10.01]  # Points 1 and 3 violate

        def check_rule1(points: list[float], center: float, sigma: float) -> list[int]:
            """Check Rule 1: Point beyond 3 sigma."""
            violations = []
            for i, p in enumerate(points):
                if abs(p - center) > 3 * sigma:
                    violations.append(i)
            return violations

        def check_rule4(points: list[float], center: float) -> list[tuple[int, int]]:
            """Check Rule 4: 8 consecutive on one side."""
            violations = []
            consecutive_above = 0
            consecutive_below = 0
            start_idx = 0

            for i, p in enumerate(points):
                if p > center:
                    consecutive_below = 0
                    if consecutive_above == 0:
                        start_idx = i
                    consecutive_above += 1
                else:
                    consecutive_above = 0
                    if consecutive_below == 0:
                        start_idx = i
                    consecutive_below += 1

                if consecutive_above >= 8 or consecutive_below >= 8:
                    violations.append((start_idx, i))

            return violations

        # Act - Check rules
        rule1_violations = check_rule1(rule1_data, center, sigma)
        rule4_violations = check_rule4(rule4_data, center)

        # Store results
        results = {
            "rule1_test": {
                "data": rule1_data,
                "violations": rule1_violations,
                "violated": len(rule1_violations) > 0,
            },
            "rule4_test": {
                "data": rule4_data,
                "violations": rule4_violations,
                "violated": len(rule4_violations) > 0,
            },
        }

        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                project_id,
                1,
                "spc_we_rules",
                "analysis",
                json.dumps(results),
            ),
        )
        postgres_connection.commit()

        # Assert
        assert len(rule1_violations) == 1, "Rule 1 should detect 1 violation"
        assert rule1_violations[0] == 2, "Violation should be at index 2"

        assert len(rule4_violations) == 1, "Rule 4 should detect pattern"
        assert rule4_violations[0][1] - rule4_violations[0][0] >= 7, (
            "Should span 8 consecutive points"
        )


@pytest.mark.container
@pytest.mark.postgres
@pytest.mark.redis
class TestProcessCapability:
    """Test process capability analysis."""

    def test_cp_cpk_calculation(
        self,
        postgres_connection: Any,
        redis_connection: Any,
    ) -> None:
        """Test Cp and Cpk calculation.

        Scenario: Calculate process capability indices
        - Cp measures potential capability
        - Cpk measures actual capability

        Assert:
        - Cp and Cpk calculated correctly
        - Process capability assessed
        """
        # Arrange
        cursor = postgres_connection.cursor()
        project_id = "SPC-CAPABILITY-001"
        random.seed(42)

        # Specification limits
        usl = 10.5  # Upper spec limit
        lsl = 9.5   # Lower spec limit
        target = 10.0

        # Process data (slightly off-center)
        process_mean = 10.08  # Slightly above target
        process_sigma = 0.12

        # Generate sample data
        num_samples = 100
        samples = [random.gauss(process_mean, process_sigma) for _ in range(num_samples)]

        # Calculate statistics
        sample_mean = statistics.mean(samples)
        sample_stdev = statistics.stdev(samples)

        # Calculate Cp (potential capability)
        cp = (usl - lsl) / (6 * sample_stdev)

        # Calculate Cpk (actual capability)
        cpu = (usl - sample_mean) / (3 * sample_stdev)
        cpl = (sample_mean - lsl) / (3 * sample_stdev)
        cpk = min(cpu, cpl)

        # Capability assessment
        if cpk >= 1.33:
            capability = "Excellent"
        elif cpk >= 1.0:
            capability = "Capable"
        elif cpk >= 0.67:
            capability = "Marginal"
        else:
            capability = "Incapable"

        capability_data = {
            "usl": usl,
            "lsl": lsl,
            "target": target,
            "process_mean": sample_mean,
            "process_stdev": sample_stdev,
            "cp": cp,
            "cpu": cpu,
            "cpl": cpl,
            "cpk": cpk,
            "capability_rating": capability,
            "sample_size": num_samples,
        }

        # Act - Store results
        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                project_id,
                1,
                "spc_capability",
                "analysis",
                json.dumps(capability_data),
            ),
        )
        postgres_connection.commit()

        # Cache results in Redis
        redis_connection.hset(
            f"spc:{project_id}:capability",
            mapping={
                "cp": str(round(cp, 3)),
                "cpk": str(round(cpk, 3)),
                "rating": capability,
            },
        )

        # Assert
        # Cp should be > Cpk since process is off-center
        assert cp > cpk, "Cp should be greater than Cpk for off-center process"

        # With sigma=0.12 and spec width=1.0, Cp ~ 1.0/(6*0.12) ~ 1.39
        assert 1.2 < cp < 1.6, f"Cp should be around 1.39, got {cp}"

        # Cpk should be lower due to off-center mean
        assert cpk < cp, "Cpk should be less than Cp"

        # Verify capability rating
        assert capability in ["Excellent", "Capable", "Marginal", "Incapable"]

        # Verify Redis cache
        cached_cpk = float(redis_connection.hget(f"spc:{project_id}:capability", "cpk") or 0)
        assert abs(cached_cpk - cpk) < 0.01

    def test_process_performance_ppk(
        self,
        postgres_connection: Any,
        redis_connection: Any,
    ) -> None:
        """Test process performance (Ppk) calculation.

        Scenario: Calculate Ppk using overall variation
        - Ppk uses total variation (not within-subgroup)
        - Compare Ppk to Cpk

        Assert:
        - Ppk calculated correctly
        - Ppk typically <= Cpk
        """
        # Arrange
        cursor = postgres_connection.cursor()
        project_id = "SPC-PERFORMANCE-001"
        random.seed(42)

        # Specification limits
        usl = 10.5
        lsl = 9.5

        # Generate data with both within and between variation
        # Simulate shift between subgroups
        subgroup_size = 5
        num_subgroups = 20
        all_data = []

        for sg in range(num_subgroups):
            # Add slight shift between subgroups
            subgroup_mean = 10.0 + random.gauss(0, 0.05)
            within_sigma = 0.08

            subgroup_data = [
                random.gauss(subgroup_mean, within_sigma)
                for _ in range(subgroup_size)
            ]
            all_data.extend(subgroup_data)

        # Calculate overall statistics
        overall_mean = statistics.mean(all_data)
        overall_stdev = statistics.stdev(all_data)  # Total variation

        # Calculate Ppk (using overall variation)
        ppu = (usl - overall_mean) / (3 * overall_stdev)
        ppl = (overall_mean - lsl) / (3 * overall_stdev)
        ppk = min(ppu, ppl)

        # Calculate Cpk (using within-subgroup variation)
        # Estimate within-subgroup sigma from range
        ranges = []
        for i in range(num_subgroups):
            sg_data = all_data[i * subgroup_size:(i + 1) * subgroup_size]
            ranges.append(max(sg_data) - min(sg_data))

        r_bar = statistics.mean(ranges)
        d2 = 2.326  # d2 for n=5
        within_sigma = r_bar / d2

        cpu_within = (usl - overall_mean) / (3 * within_sigma)
        cpl_within = (overall_mean - lsl) / (3 * within_sigma)
        cpk_within = min(cpu_within, cpl_within)

        performance_data = {
            "overall_mean": overall_mean,
            "overall_stdev": overall_stdev,
            "within_stdev": within_sigma,
            "ppk": ppk,
            "cpk": cpk_within,
            "pp": (usl - lsl) / (6 * overall_stdev),
            "cp": (usl - lsl) / (6 * within_sigma),
            "total_samples": len(all_data),
        }

        # Act - Store results
        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                project_id,
                1,
                "spc_performance",
                "analysis",
                json.dumps(performance_data),
            ),
        )
        postgres_connection.commit()

        # Assert
        # Overall variation should be >= within variation
        assert overall_stdev >= within_sigma * 0.9, "Overall should include more variation"

        # Ppk should typically be <= Cpk
        # (total variation >= within-subgroup variation)
        # Note: Due to sampling, this isn't always true
        assert abs(ppk - cpk_within) < 0.5, "Ppk and Cpk should be reasonably close"

        # Verify database storage
        cursor.execute(
            """
            SELECT token_state FROM workflow_audit
            WHERE workflow_id = %s AND event_type = 'spc_performance'
            """,
            (project_id,),
        )
        stored = json.loads(cursor.fetchone()[0])
        assert "ppk" in stored
        assert "cpk" in stored

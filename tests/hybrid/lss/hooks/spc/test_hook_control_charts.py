"""Control Charts for Knowledge Hooks tests.

This module tests control chart implementations for analyzing Knowledge Hook
execution patterns using Statistical Process Control methodology.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from kgcl.hybrid.knowledge_hooks import HookAction, HookPhase, HookReceipt
from tests.hybrid.lss.hooks.spc.control_charts import (
    HookControlChart,
    HookIMRChart,
    HookXBarRChart,
    create_hook_imr_chart,
    create_hook_xbar_r_chart,
    detect_nelson_rules,
    detect_western_electric_rules,
)


def test_hook_control_chart_basic() -> None:
    """Create basic control chart with data points.

    Arrange:
        - Control chart with center line and limits
        - Mix of in-control and out-of-control points
    Act:
        - Check control chart properties
    Assert:
        - Center line, UCL, LCL set correctly
        - Out-of-control points identified
        - Percent in control calculated correctly
    """
    chart = HookControlChart(
        chart_type="I",
        center_line=10.0,
        ucl=13.0,
        lcl=7.0,
        data_points=[10.1, 9.8, 10.3, 15.0, 9.9, 6.5],
        out_of_control_points=[3, 5],  # 15.0 and 6.5
    )

    assert chart.chart_type == "I"
    assert chart.center_line == 10.0
    assert chart.ucl == 13.0
    assert chart.lcl == 7.0
    assert len(chart.data_points) == 6
    assert chart.has_out_of_control_points()
    assert abs(chart.percent_in_control() - 66.67) < 0.1
    assert not chart.is_stable()


def test_hook_control_chart_all_in_control() -> None:
    """Control chart with all points in control is stable.

    Arrange:
        - Control chart with no out-of-control points
    Act:
        - Check stability
    Assert:
        - 100% in control
        - No out-of-control points
        - Chart is stable
    """
    chart = HookControlChart(
        chart_type="X-bar",
        center_line=10.0,
        ucl=12.0,
        lcl=8.0,
        data_points=[10.1, 9.8, 10.3, 9.9, 10.2],
        out_of_control_points=[],
    )

    assert chart.percent_in_control() == 100.0
    assert not chart.has_out_of_control_points()
    assert chart.is_stable()


def test_create_hook_imr_chart_basic() -> None:
    """Create I-MR chart from hook receipts.

    Arrange:
        - Hook receipts with execution times
    Act:
        - Create I-MR chart
    Assert:
        - I chart and MR chart created
        - Control limits calculated correctly
        - Center lines set appropriately
    """
    receipts = [
        HookReceipt("hook1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.ASSERT, 10.0),
        HookReceipt("hook1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.ASSERT, 10.5),
        HookReceipt("hook1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.ASSERT, 9.8),
        HookReceipt("hook1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.ASSERT, 10.2),
        HookReceipt("hook1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.ASSERT, 10.1),
    ]

    chart = create_hook_imr_chart(receipts)

    # I chart
    assert chart.i_chart.chart_type == "I"
    assert 9.8 < chart.i_chart.center_line < 10.3
    assert chart.i_chart.ucl > chart.i_chart.center_line
    assert chart.i_chart.lcl < chart.i_chart.center_line
    assert len(chart.i_chart.data_points) == 5

    # MR chart
    assert chart.mr_chart.chart_type == "MR"
    assert chart.mr_chart.center_line > 0
    assert chart.mr_chart.lcl == 0.0  # Moving ranges cannot be negative
    assert len(chart.mr_chart.data_points) == 4  # n-1 moving ranges


def test_create_hook_imr_chart_detects_outliers() -> None:
    """I-MR chart detects out-of-control points in stable baseline.

    Arrange:
        - Hook receipts with stable baseline followed by outlier
        - Use more data points so outlier doesn't contaminate limits as much
    Act:
        - Create I-MR chart
    Assert:
        - Outlier detected in I chart or MR chart
        - Chart marked as unstable
    """
    # Establish stable baseline with 10 points
    receipts = [
        HookReceipt("hook1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.ASSERT, 10.0 + i * 0.1)
        for i in range(10)
    ]
    # Add outlier that creates large moving range
    receipts.append(HookReceipt("hook1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.ASSERT, 50.0))

    chart = create_hook_imr_chart(receipts)

    # Either I chart or MR chart should detect the problem
    assert chart.i_chart.has_out_of_control_points() or chart.mr_chart.has_out_of_control_points()
    assert not chart.is_stable()


def test_create_hook_imr_chart_insufficient_data() -> None:
    """I-MR chart requires at least 2 data points.

    Arrange:
        - Single receipt (insufficient data)
    Act:
        - Attempt to create I-MR chart
    Assert:
        - ValueError raised
    """
    receipts = [HookReceipt("hook1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.ASSERT, 10.0)]

    with pytest.raises(ValueError, match="at least 2 receipts"):
        create_hook_imr_chart(receipts)


def test_create_hook_xbar_r_chart_basic() -> None:
    """Create X-bar & R chart from hook receipts with subgrouping.

    Arrange:
        - Hook receipts divisible into subgroups
    Act:
        - Create X-bar & R chart
    Assert:
        - X-bar chart tracks subgroup means
        - R chart tracks subgroup ranges
        - Control limits calculated correctly
    """
    # 15 receipts = 3 subgroups of 5
    receipts = [
        HookReceipt("hook1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.ASSERT, 10.0 + i * 0.1)
        for i in range(15)
    ]

    chart = create_hook_xbar_r_chart(receipts, subgroup_size=5)

    assert chart.subgroup_size == 5
    assert len(chart.xbar_chart.data_points) == 3  # 3 subgroups
    assert len(chart.r_chart.data_points) == 3

    # X-bar chart
    assert chart.xbar_chart.chart_type == "X-bar"
    assert chart.xbar_chart.center_line > 0
    assert chart.xbar_chart.ucl > chart.xbar_chart.center_line
    assert chart.xbar_chart.lcl < chart.xbar_chart.center_line

    # R chart
    assert chart.r_chart.chart_type == "R"
    assert chart.r_chart.center_line > 0
    assert chart.r_chart.ucl > chart.r_chart.center_line
    assert chart.r_chart.lcl >= 0.0


def test_create_hook_xbar_r_chart_stable_process() -> None:
    """X-bar & R chart for stable process shows no violations.

    Arrange:
        - Hook receipts with consistent execution times
    Act:
        - Create X-bar & R chart
    Assert:
        - Both charts stable (no out-of-control points)
        - is_stable() returns True
    """
    receipts = [
        HookReceipt("hook1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.ASSERT, 10.0 + (i % 5) * 0.1)
        for i in range(20)
    ]

    chart = create_hook_xbar_r_chart(receipts, subgroup_size=4)

    assert chart.is_stable()
    assert not chart.xbar_chart.has_out_of_control_points()
    assert not chart.r_chart.has_out_of_control_points()


def test_create_hook_xbar_r_chart_insufficient_data() -> None:
    """X-bar & R chart requires sufficient data for subgrouping.

    Arrange:
        - Too few receipts for subgroup size
    Act:
        - Attempt to create chart
    Assert:
        - ValueError raised
    """
    receipts = [
        HookReceipt("hook1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.ASSERT, 10.0) for _ in range(3)
    ]

    with pytest.raises(ValueError, match="at least 5 receipts"):
        create_hook_xbar_r_chart(receipts, subgroup_size=5)


def test_create_hook_xbar_r_chart_invalid_subgroup_size() -> None:
    """X-bar & R chart requires valid subgroup size.

    Arrange:
        - Invalid subgroup size (< 2 or > 10)
    Act:
        - Attempt to create chart
    Assert:
        - ValueError raised
    """
    receipts = [
        HookReceipt("hook1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.ASSERT, 10.0) for _ in range(20)
    ]

    with pytest.raises(ValueError, match="Subgroup size must be at least 2"):
        create_hook_xbar_r_chart(receipts, subgroup_size=1)

    with pytest.raises(ValueError, match="not supported"):
        create_hook_xbar_r_chart(receipts, subgroup_size=15)


def test_detect_western_electric_rule1() -> None:
    """Western Electric Rule 1: Point beyond 3σ.

    Arrange:
        - Chart with point exceeding UCL
    Act:
        - Detect Western Electric rules
    Assert:
        - Rule 1 violation detected
    """
    chart = HookControlChart(
        chart_type="I",
        center_line=10.0,
        ucl=13.0,
        lcl=7.0,
        data_points=[10.1, 9.8, 15.0, 10.2],  # 15.0 beyond UCL
        out_of_control_points=[2],
    )

    rules = detect_western_electric_rules(chart)

    assert rules["rule1_beyond_3sigma"]


def test_detect_western_electric_rule2() -> None:
    """Western Electric Rule 2: 2 of 3 beyond 2σ on same side.

    Arrange:
        - Chart with 2 of 3 points beyond 2σ
    Act:
        - Detect Western Electric rules
    Assert:
        - Rule 2 violation detected
    """
    # Center = 10, UCL = 13, sigma = 1.0
    # 2σ upper = 12.0
    chart = HookControlChart(
        chart_type="I",
        center_line=10.0,
        ucl=13.0,
        lcl=7.0,
        data_points=[12.5, 10.1, 12.3, 9.9],  # First 3: 12.5, 10.1, 12.3 (2 beyond 12.0)
        out_of_control_points=[],
    )

    rules = detect_western_electric_rules(chart)

    assert rules["rule2_2of3_beyond_2sigma"]


def test_detect_western_electric_rule3() -> None:
    """Western Electric Rule 3: 4 of 5 beyond 1σ on same side.

    Arrange:
        - Chart with 4 of 5 points beyond 1σ
    Act:
        - Detect Western Electric rules
    Assert:
        - Rule 3 violation detected
    """
    # Center = 10, UCL = 13, sigma = 1.0
    # 1σ upper = 11.0
    chart = HookControlChart(
        chart_type="I",
        center_line=10.0,
        ucl=13.0,
        lcl=7.0,
        data_points=[11.2, 11.3, 9.9, 11.1, 11.4],  # 4 beyond 11.0
        out_of_control_points=[],
    )

    rules = detect_western_electric_rules(chart)

    assert rules["rule3_4of5_beyond_1sigma"]


def test_detect_western_electric_rule4() -> None:
    """Western Electric Rule 4: 8 consecutive on same side of center.

    Arrange:
        - Chart with 8 consecutive points above center
    Act:
        - Detect Western Electric rules
    Assert:
        - Rule 4 violation detected
    """
    chart = HookControlChart(
        chart_type="I",
        center_line=10.0,
        ucl=13.0,
        lcl=7.0,
        data_points=[10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8],  # All above 10.0
        out_of_control_points=[],
    )

    rules = detect_western_electric_rules(chart)

    assert rules["rule4_8_consecutive_same_side"]


def test_detect_western_electric_no_violations() -> None:
    """Stable chart has no Western Electric violations.

    Arrange:
        - Stable chart with random variation
    Act:
        - Detect Western Electric rules
    Assert:
        - No violations detected
    """
    chart = HookControlChart(
        chart_type="I",
        center_line=10.0,
        ucl=13.0,
        lcl=7.0,
        data_points=[10.1, 9.8, 10.3, 9.9, 10.2, 9.7, 10.4],
        out_of_control_points=[],
    )

    rules = detect_western_electric_rules(chart)

    assert not rules["rule1_beyond_3sigma"]
    assert not rules["rule2_2of3_beyond_2sigma"]
    assert not rules["rule3_4of5_beyond_1sigma"]
    assert not rules["rule4_8_consecutive_same_side"]


def test_detect_nelson_rule1() -> None:
    """Nelson Rule 1: Point beyond 3σ.

    Arrange:
        - Chart with out-of-control point
    Act:
        - Detect Nelson rules
    Assert:
        - Rule 1 violation detected
    """
    chart = HookControlChart(
        chart_type="I", center_line=10.0, ucl=13.0, lcl=7.0, data_points=[10.1, 15.0, 10.2], out_of_control_points=[1]
    )

    rules = detect_nelson_rules(chart)

    assert rules["rule1_beyond_3sigma"]


def test_detect_nelson_rule2() -> None:
    """Nelson Rule 2: Nine consecutive on same side.

    Arrange:
        - Chart with 9 consecutive points above center
    Act:
        - Detect Nelson rules
    Assert:
        - Rule 2 violation detected
    """
    chart = HookControlChart(
        chart_type="I",
        center_line=10.0,
        ucl=13.0,
        lcl=7.0,
        data_points=[10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9],
        out_of_control_points=[],
    )

    rules = detect_nelson_rules(chart)

    assert rules["rule2_nine_same_side"]


def test_detect_nelson_rule3() -> None:
    """Nelson Rule 3: Six consecutive increasing or decreasing.

    Arrange:
        - Chart with clear upward trend
    Act:
        - Detect Nelson rules
    Assert:
        - Rule 3 violation detected
    """
    chart = HookControlChart(
        chart_type="I",
        center_line=10.0,
        ucl=15.0,
        lcl=5.0,
        data_points=[8.0, 9.0, 10.0, 11.0, 12.0, 13.0],
        out_of_control_points=[],
    )

    rules = detect_nelson_rules(chart)

    assert rules["rule3_six_increasing"]


def test_detect_nelson_rule4() -> None:
    """Nelson Rule 4: Fourteen consecutive alternating.

    Arrange:
        - Chart with alternating pattern
    Act:
        - Detect Nelson rules
    Assert:
        - Rule 4 violation detected
    """
    chart = HookControlChart(
        chart_type="I",
        center_line=10.0,
        ucl=12.0,
        lcl=8.0,
        data_points=[10.0, 11.0, 9.0, 11.0, 9.0, 11.0, 9.0, 11.0, 9.0, 11.0, 9.0, 11.0, 9.0, 11.0],
        out_of_control_points=[],
    )

    rules = detect_nelson_rules(chart)

    assert rules["rule4_fourteen_alternating"]


def test_detect_nelson_rule5() -> None:
    """Nelson Rule 5: 2 of 3 beyond 2σ.

    Arrange:
        - Chart with 2 of 3 beyond 2σ
    Act:
        - Detect Nelson rules
    Assert:
        - Rule 5 violation detected
    """
    chart = HookControlChart(
        chart_type="I",
        center_line=10.0,
        ucl=13.0,
        lcl=7.0,
        data_points=[12.5, 10.1, 12.3],  # 2 beyond 2σ (12.0)
        out_of_control_points=[],
    )

    rules = detect_nelson_rules(chart)

    assert rules["rule5_2of3_beyond_2sigma"]


def test_detect_nelson_rule6() -> None:
    """Nelson Rule 6: 4 of 5 beyond 1σ.

    Arrange:
        - Chart with 4 of 5 beyond 1σ
    Act:
        - Detect Nelson rules
    Assert:
        - Rule 6 violation detected
    """
    chart = HookControlChart(
        chart_type="I",
        center_line=10.0,
        ucl=13.0,
        lcl=7.0,
        data_points=[11.2, 11.3, 9.9, 11.1, 11.4],  # 4 beyond 1σ (11.0)
        out_of_control_points=[],
    )

    rules = detect_nelson_rules(chart)

    assert rules["rule6_4of5_beyond_1sigma"]


def test_detect_nelson_rule7() -> None:
    """Nelson Rule 7: 15 consecutive within 1σ.

    Arrange:
        - Chart with suspiciously low variation
    Act:
        - Detect Nelson rules
    Assert:
        - Rule 7 violation detected (stratification)
    """
    # Center = 10, UCL = 13, sigma = 1.0
    # 1σ bounds = [9.0, 11.0]
    chart = HookControlChart(
        chart_type="I",
        center_line=10.0,
        ucl=13.0,
        lcl=7.0,
        data_points=[10.0, 10.1, 9.9, 10.2, 9.8, 10.0, 10.1, 9.9, 10.2, 9.8, 10.0, 10.1, 9.9, 10.0, 10.1],
        out_of_control_points=[],
    )

    rules = detect_nelson_rules(chart)

    assert rules["rule7_15_within_1sigma"]


def test_detect_nelson_rule8() -> None:
    """Nelson Rule 8: 8 consecutive beyond 1σ.

    Arrange:
        - Chart with excessive variation
    Act:
        - Detect Nelson rules
    Assert:
        - Rule 8 violation detected (mixture)
    """
    # Center = 10, UCL = 13, sigma = 1.0
    # 1σ bounds = [9.0, 11.0]
    chart = HookControlChart(
        chart_type="I",
        center_line=10.0,
        ucl=13.0,
        lcl=7.0,
        data_points=[11.5, 8.5, 11.3, 8.7, 11.4, 8.6, 11.2, 8.8],  # All beyond 1σ
        out_of_control_points=[],
    )

    rules = detect_nelson_rules(chart)

    assert rules["rule8_8_beyond_1sigma"]


def test_detect_nelson_no_violations() -> None:
    """Stable chart has no Nelson violations.

    Arrange:
        - Random stable data
    Act:
        - Detect Nelson rules
    Assert:
        - No violations detected
    """
    chart = HookControlChart(
        chart_type="I",
        center_line=10.0,
        ucl=13.0,
        lcl=7.0,
        data_points=[10.1, 9.8, 10.3, 9.9, 10.2, 9.7, 10.4, 10.0],
        out_of_control_points=[],
    )

    rules = detect_nelson_rules(chart)

    assert not any(rules.values())


def test_hook_xbar_r_chart_is_stable() -> None:
    """X-bar & R chart stability checks both charts.

    Arrange:
        - X-bar chart stable, R chart unstable
    Act:
        - Check is_stable()
    Assert:
        - Returns False (both must be stable)
    """
    xbar_stable = HookControlChart("X-bar", 10.0, 12.0, 8.0, [10.1, 9.9, 10.2], [])
    r_unstable = HookControlChart("R", 2.0, 5.0, 0.0, [2.1, 6.0, 2.3], [1])

    chart = HookXBarRChart(xbar_stable, r_unstable, 5)

    assert not chart.is_stable()


def test_hook_imr_chart_is_stable() -> None:
    """I-MR chart stability checks both charts.

    Arrange:
        - I chart unstable, MR chart stable
    Act:
        - Check is_stable()
    Assert:
        - Returns False (both must be stable)
    """
    i_unstable = HookControlChart("I", 10.0, 13.0, 7.0, [10.1, 15.0, 10.2], [1])
    mr_stable = HookControlChart("MR", 1.0, 3.0, 0.0, [0.5, 0.8, 0.6], [])

    chart = HookIMRChart(i_unstable, mr_stable)

    assert not chart.is_stable()


def test_control_chart_empty_data() -> None:
    """Control chart with empty data.

    Arrange:
        - Chart with no data points
    Act:
        - Check properties
    Assert:
        - 100% in control (no data to violate)
        - No out-of-control points
    """
    chart = HookControlChart("I", 10.0, 13.0, 7.0, [], [])

    assert chart.percent_in_control() == 100.0
    assert not chart.has_out_of_control_points()


def test_create_hook_xbar_r_chart_constants() -> None:
    """X-bar & R chart uses correct control limit constants.

    Arrange:
        - Receipts with known subgroup size
    Act:
        - Create chart
    Assert:
        - Control limits use correct A2, D3, D4 constants
    """
    # Subgroup size 5: A2=0.577, D3=0.0, D4=2.114
    receipts = [
        HookReceipt("hook1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.ASSERT, 10.0 + i * 0.1)
        for i in range(10)
    ]

    chart = create_hook_xbar_r_chart(receipts, subgroup_size=5)

    # Verify R chart LCL is 0 (D3=0 for subgroup size 5)
    assert chart.r_chart.lcl == 0.0

    # Verify control limits are reasonable
    assert chart.xbar_chart.ucl > chart.xbar_chart.center_line
    assert chart.r_chart.ucl > chart.r_chart.center_line


def test_create_hook_imr_chart_constants() -> None:
    """I-MR chart uses correct control limit constants.

    Arrange:
        - Receipts with individual measurements
    Act:
        - Create I-MR chart
    Assert:
        - I chart uses 2.66 constant
        - MR chart uses 3.267 constant
        - MR LCL is 0
    """
    receipts = [
        HookReceipt("hook1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.ASSERT, 10.0 + i * 0.2)
        for i in range(8)
    ]

    chart = create_hook_imr_chart(receipts)

    # MR chart LCL must be 0
    assert chart.mr_chart.lcl == 0.0

    # Verify I chart control limits based on 2.66 * MR-bar
    expected_ucl = chart.i_chart.center_line + (2.66 * chart.mr_chart.center_line)
    assert abs(chart.i_chart.ucl - expected_ucl) < 0.01

    # Verify MR chart UCL based on 3.267 * MR-bar
    expected_mr_ucl = 3.267 * chart.mr_chart.center_line
    assert abs(chart.mr_chart.ucl - expected_mr_ucl) < 0.01

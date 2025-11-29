"""Tests for Multiple Instance Workflow Control Patterns (WCP 12-15).

WCP 12: Multiple Instances without Synchronization
WCP 13: Multiple Instances with a Priori Design-Time Knowledge
WCP 14: Multiple Instances with a Priori Run-Time Knowledge
WCP 15: Multiple Instances without a Priori Run-Time Knowledge
"""

from __future__ import annotations

from kgcl.yawl.elements.y_condition import ConditionType, YCondition
from kgcl.yawl.elements.y_flow import YFlow
from kgcl.yawl.elements.y_multi_instance import MICompletionMode, MICreationMode, YMultiInstanceAttributes
from kgcl.yawl.elements.y_net import YNet
from kgcl.yawl.elements.y_task import JoinType, SplitType, YTask
from kgcl.yawl.engine.y_net_runner import YNetRunner


class TestWCP12MIWithoutSync:
    """WCP-12: Multiple Instances without Synchronization.

    Multiple instances of an activity can be created. These instances
    are independent and need not be synchronized on completion.
    """

    def test_mi_without_sync_threshold_one(self) -> None:
        """MI with threshold=1 completes on single instance."""
        mi_attrs = YMultiInstanceAttributes(
            minimum=1,
            maximum=5,
            threshold=1,  # Only need 1 to complete
            creation_mode=MICreationMode.STATIC,
            completion_mode=MICompletionMode.THRESHOLD,
        )

        # With threshold=1, satisfied after just 1 completion
        assert mi_attrs.is_completion_satisfied(1, 5)
        assert mi_attrs.uses_threshold()

    def test_mi_can_create_variable_instances(self) -> None:
        """MI can create varying number of instances."""
        mi_attrs = YMultiInstanceAttributes(minimum=2, maximum=10, threshold=2, creation_mode=MICreationMode.STATIC)

        # Verify params
        assert mi_attrs.minimum == 2
        assert mi_attrs.maximum == 10
        assert mi_attrs.threshold == 2


class TestWCP13MIDesignTime:
    """WCP-13: Multiple Instances with a Priori Design-Time Knowledge.

    The number of instances is known at design time.
    """

    def test_mi_static_creation_mode(self) -> None:
        """Static MI creates known number of instances."""
        mi_attrs = YMultiInstanceAttributes(
            minimum=5, maximum=5, threshold=5, creation_mode=MICreationMode.STATIC, completion_mode=MICompletionMode.ALL
        )

        # Static mode - count known at design time
        assert mi_attrs.creation_mode == MICreationMode.STATIC
        assert mi_attrs.is_static()
        assert mi_attrs.minimum == mi_attrs.maximum  # Fixed count

    def test_mi_requires_all_completion(self) -> None:
        """Static MI can require all instances to complete."""
        mi_attrs = YMultiInstanceAttributes(
            minimum=3, maximum=3, creation_mode=MICreationMode.STATIC, completion_mode=MICompletionMode.ALL
        )

        assert mi_attrs.requires_all_completion()
        # 2 of 3 completed - not satisfied
        assert not mi_attrs.is_completion_satisfied(2, 3)
        # 3 of 3 completed - satisfied
        assert mi_attrs.is_completion_satisfied(3, 3)


class TestWCP14MIRuntimeKnowledge:
    """WCP-14: Multiple Instances with a Priori Run-Time Knowledge.

    The number of instances is not known at design time but determined
    at run-time before the instances are created.
    """

    def test_mi_dynamic_creation_mode(self) -> None:
        """Dynamic MI determines count at runtime."""
        mi_attrs = YMultiInstanceAttributes(minimum=1, maximum=100, threshold=1, creation_mode=MICreationMode.DYNAMIC)

        assert mi_attrs.creation_mode == MICreationMode.DYNAMIC
        assert mi_attrs.is_dynamic()
        assert mi_attrs.minimum < (mi_attrs.maximum or 0)

    def test_mi_with_query_expression(self) -> None:
        """MI can use query to determine instance count."""
        mi_attrs = YMultiInstanceAttributes(
            minimum=1, maximum=100, threshold=1, creation_mode=MICreationMode.DYNAMIC, min_query="item_count"
        )

        assert mi_attrs.min_query == "item_count"

        # Effective minimum from data
        data = {"item_count": 5}
        assert mi_attrs.get_effective_minimum(data) == 5


class TestWCP15MINoRuntimeKnowledge:
    """WCP-15: Multiple Instances without a Priori Run-Time Knowledge.

    New instances can be created while other instances are running.
    """

    def test_mi_dynamic_allows_runtime_creation(self) -> None:
        """Dynamic MI allows instance creation during execution."""
        mi_attrs = YMultiInstanceAttributes(
            minimum=1,
            maximum=None,  # Unlimited
            threshold=1,
            creation_mode=MICreationMode.DYNAMIC,
        )

        # No maximum - can create as needed
        assert mi_attrs.maximum is None
        assert mi_attrs.is_dynamic()


class TestMIThresholdCompletion:
    """Tests for MI threshold-based completion (synchronization)."""

    def test_threshold_completion(self) -> None:
        """MI completes when threshold instances finish."""
        mi_attrs = YMultiInstanceAttributes(
            minimum=5,
            maximum=5,
            threshold=3,  # Only need 3 of 5 to complete
            creation_mode=MICreationMode.STATIC,
            completion_mode=MICompletionMode.THRESHOLD,
        )

        assert mi_attrs.threshold == 3
        assert mi_attrs.threshold < (mi_attrs.maximum or 0)
        assert mi_attrs.uses_threshold()

        # 2 of 5 - not satisfied
        assert not mi_attrs.is_completion_satisfied(2, 5)
        # 3 of 5 - satisfied
        assert mi_attrs.is_completion_satisfied(3, 5)
        # 4 of 5 - still satisfied
        assert mi_attrs.is_completion_satisfied(4, 5)

    def test_threshold_must_be_within_bounds(self) -> None:
        """Threshold within logical bounds."""
        mi_attrs = YMultiInstanceAttributes(minimum=2, maximum=10, threshold=5)

        assert mi_attrs.threshold >= mi_attrs.minimum
        assert mi_attrs.threshold <= (mi_attrs.maximum or 0)


class TestMIQueryEvaluation:
    """Tests for MI dynamic query evaluation."""

    def test_effective_minimum_from_query(self) -> None:
        """Get effective minimum from query data."""
        mi_attrs = YMultiInstanceAttributes(minimum=1, min_query="order_count")

        # Without data, use default
        assert mi_attrs.get_effective_minimum() == 1

        # With data, use query result
        assert mi_attrs.get_effective_minimum({"order_count": 7}) == 7

    def test_effective_maximum_from_query(self) -> None:
        """Get effective maximum from query data."""
        mi_attrs = YMultiInstanceAttributes(maximum=100, max_query="max_items")

        # Without data, use default
        assert mi_attrs.get_effective_maximum() == 100

        # With data, use query result
        assert mi_attrs.get_effective_maximum({"max_items": 25}) == 25

    def test_effective_threshold_from_query(self) -> None:
        """Get effective threshold from query data."""
        mi_attrs = YMultiInstanceAttributes(
            threshold=1, threshold_query="required_approvals", completion_mode=MICompletionMode.THRESHOLD
        )

        # Without data, use default
        assert mi_attrs.get_effective_threshold() == 1

        # With data, use query result
        assert mi_attrs.get_effective_threshold({"required_approvals": 3}) == 3


class TestMICompletionModes:
    """Tests for MI completion mode behavior."""

    def test_all_completion_mode(self) -> None:
        """ALL completion mode requires all instances."""
        mi_attrs = YMultiInstanceAttributes(minimum=5, maximum=5, completion_mode=MICompletionMode.ALL)

        assert mi_attrs.requires_all_completion()
        assert not mi_attrs.uses_threshold()

    def test_threshold_completion_mode(self) -> None:
        """THRESHOLD completion mode uses threshold."""
        mi_attrs = YMultiInstanceAttributes(
            minimum=5, maximum=5, threshold=3, completion_mode=MICompletionMode.THRESHOLD
        )

        assert not mi_attrs.requires_all_completion()
        assert mi_attrs.uses_threshold()

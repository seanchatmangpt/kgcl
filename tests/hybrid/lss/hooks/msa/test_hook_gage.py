"""Hook MSA-005: Gage R&R (Reproducibility & Repeatability) Tests.

This module tests:
- Repeatability: Same hook, same condition, multiple runs
- Reproducibility: Different hook instances, same condition, multiple runs
- Gage R&R: Overall measurement system quality

Acceptance criterion: %GRR < 30% (excellent if < 10%)
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from kgcl.hybrid.knowledge_hooks import HookAction, HookPhase, HookReceipt, HookRegistry, KnowledgeHook
from tests.hybrid.lss.hooks.msa.calculations import (
    assess_hook_measurement_capability,
    calculate_hook_accuracy,
    calculate_hook_gage_rr,
    calculate_hook_precision,
)
from tests.hybrid.lss.hooks.msa.metrics import HookMSAMetrics


@pytest.fixture
def validation_hook() -> KnowledgeHook:
    """Create test validation hook.

    Returns
    -------
    KnowledgeHook
        Hook for MSA testing
    """
    return KnowledgeHook(
        hook_id="validate-person",
        name="Validate Person",
        phase=HookPhase.ON_CHANGE,
        priority=100,
        enabled=True,
        condition_query="ASK { ?s a kgc:Person . FILTER NOT EXISTS { ?s kgc:name ?name } }",
        action=HookAction.REJECT,
        handler_data={"reason": "Person must have a name"},
    )


class TestHookMSA005GageRR:
    """Hook MSA-005: Gage R&R testing (reproducibility and repeatability)."""

    def test_repeatability_single_hook(self, validation_hook: KnowledgeHook) -> None:
        """Repeatability: Same hook should give consistent execution times."""
        receipts: list[HookReceipt] = []

        # Simulate 5 repeated executions with same hook
        for trial in range(5):
            receipt = HookReceipt(
                hook_id=validation_hook.hook_id,
                phase=HookPhase.ON_CHANGE,
                timestamp=datetime.now(UTC),
                condition_matched=True,
                action_taken=HookAction.REJECT,
                duration_ms=100.0 + (trial * 0.1),  # Very low variation
            )
            receipts.append(receipt)

        # Calculate Gage R&R
        metrics = calculate_hook_gage_rr(receipts, parts=1, appraisers=1, trials=5)

        # Should have excellent repeatability
        assert metrics.repeatability < 1.0, f"Repeatability too high: {metrics.repeatability}"
        assert metrics.is_excellent or metrics.is_acceptable, f"System not acceptable: {metrics.gage_rr}%"

    def test_reproducibility_multiple_hooks(self, validation_hook: KnowledgeHook) -> None:
        """Reproducibility: Different hook instances should give consistent results."""
        receipts: list[HookReceipt] = []

        # Simulate 3 different hook instances, each executing 3 times
        for hook_idx in range(3):
            hook_id = f"hook-instance-{hook_idx}"
            for trial in range(3):
                receipt = HookReceipt(
                    hook_id=hook_id,
                    phase=HookPhase.ON_CHANGE,
                    timestamp=datetime.now(UTC),
                    condition_matched=True,
                    action_taken=HookAction.REJECT,
                    duration_ms=100.0 + (hook_idx * 0.5),  # Small between-instance variation
                )
                receipts.append(receipt)

        # Calculate Gage R&R
        metrics = calculate_hook_gage_rr(receipts, parts=1, appraisers=3, trials=3)

        # Should have good reproducibility
        assert metrics.reproducibility < 2.0, f"Reproducibility too high: {metrics.reproducibility}"
        assert metrics.is_acceptable, f"System not acceptable: {metrics.gage_rr}%"

    def test_grr_excellent_threshold(self) -> None:
        """Overall %GRR should be excellent (<10%)."""
        receipts: list[HookReceipt] = []

        # Perfect measurements (all identical)
        for hook_idx in range(3):
            hook_id = f"hook-{hook_idx}"
            for trial in range(10):
                receipt = HookReceipt(
                    hook_id=hook_id,
                    phase=HookPhase.ON_CHANGE,
                    timestamp=datetime.now(UTC),
                    condition_matched=True,
                    action_taken=HookAction.NOTIFY,
                    duration_ms=100.0,  # Perfect repeatability
                )
                receipts.append(receipt)

        metrics = calculate_hook_gage_rr(receipts, parts=1, appraisers=3, trials=10)

        # System should be excellent (%GRR = 0 for perfect measurements)
        assert metrics.gage_rr == 0.0, f"GRR should be 0 for perfect measurements: {metrics.gage_rr}%"
        assert metrics.is_excellent, "Perfect measurements should be excellent"

    def test_grr_calculation_perfect(self) -> None:
        """Test GRR calculation with perfect repeatability and reproducibility."""
        receipts = [
            HookReceipt("hook1", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 100.0),
            HookReceipt("hook1", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 100.0),
            HookReceipt("hook2", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 100.0),
            HookReceipt("hook2", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 100.0),
        ]

        metrics = calculate_hook_gage_rr(receipts, parts=1, appraisers=2, trials=2)

        assert metrics.gage_rr == 0.0, f"Perfect measurements should have %GRR=0, got {metrics.gage_rr}"
        assert metrics.is_excellent, "Perfect measurements should be excellent"
        assert metrics.repeatability == 0.0, "Perfect repeatability expected"
        assert metrics.reproducibility == 0.0, "Perfect reproducibility expected"

    def test_grr_calculation_excellent(self) -> None:
        """Test GRR calculation with excellent measurement system."""
        receipts = [
            HookReceipt("hook1", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 100.0),
            HookReceipt("hook1", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 100.1),
            HookReceipt("hook2", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 100.0),
            HookReceipt("hook2", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 100.1),
        ]

        metrics = calculate_hook_gage_rr(receipts, parts=1, appraisers=2, trials=2)

        assert metrics.is_excellent or metrics.is_acceptable, f"Should be acceptable, got %GRR={metrics.gage_rr}"

    def test_grr_calculation_acceptable(self) -> None:
        """Test GRR calculation with acceptable measurement system."""
        receipts = [
            HookReceipt("hook1", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 100.0),
            HookReceipt("hook1", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 105.0),
            HookReceipt("hook2", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 102.0),
            HookReceipt("hook2", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 103.0),
        ]

        metrics = calculate_hook_gage_rr(receipts, parts=1, appraisers=2, trials=2)

        # Should be acceptable (< 30%)
        assert metrics.gage_rr < 30.0, f"Should be acceptable, got %GRR={metrics.gage_rr}"

    def test_assess_measurement_capability_excellent(self) -> None:
        """Test assessment of excellent measurement system."""
        metrics = HookMSAMetrics(repeatability=0.05, reproducibility=0.03, gage_rr=8.3, ndc=7, is_acceptable=True)

        assessment = assess_hook_measurement_capability(metrics)
        assert assessment == "EXCELLENT", f"Expected EXCELLENT, got {assessment}"

    def test_assess_measurement_capability_acceptable(self) -> None:
        """Test assessment of acceptable measurement system."""
        metrics = HookMSAMetrics(repeatability=0.15, reproducibility=0.10, gage_rr=25.0, ndc=5, is_acceptable=True)

        assessment = assess_hook_measurement_capability(metrics)
        assert assessment == "ACCEPTABLE", f"Expected ACCEPTABLE, got {assessment}"

    def test_assess_measurement_capability_marginal(self) -> None:
        """Test assessment of marginal measurement system (low GRR but poor discrimination)."""
        metrics = HookMSAMetrics(repeatability=0.05, reproducibility=0.03, gage_rr=8.3, ndc=3, is_acceptable=False)

        assessment = assess_hook_measurement_capability(metrics)
        assert assessment == "MARGINAL", f"Expected MARGINAL, got {assessment}"

    def test_assess_measurement_capability_unacceptable(self) -> None:
        """Test assessment of unacceptable measurement system."""
        metrics = HookMSAMetrics(repeatability=0.30, reproducibility=0.20, gage_rr=35.0, ndc=3, is_acceptable=False)

        assessment = assess_hook_measurement_capability(metrics)
        assert assessment == "UNACCEPTABLE", f"Expected UNACCEPTABLE, got {assessment}"

    def test_accuracy_unbiased(self) -> None:
        """Test accuracy calculation with unbiased measurements."""
        receipts = [
            HookReceipt("hook1", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 100.0),
            HookReceipt("hook1", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 100.1),
            HookReceipt("hook1", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 99.9),
        ]

        accuracy = calculate_hook_accuracy(receipts, expected_duration=100.0)

        assert abs(accuracy.bias) < 1.0, f"Bias too high: {accuracy.bias}"
        assert accuracy.is_unbiased(), "Should be unbiased"
        # Use appropriate threshold for test data (0.1ms variation)
        assert accuracy.is_stable(threshold=0.15), f"Should be stable: stability={accuracy.stability}"

    def test_accuracy_biased(self) -> None:
        """Test accuracy calculation with biased measurements."""
        receipts = [
            HookReceipt("hook1", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 110.0),
            HookReceipt("hook1", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 111.0),
            HookReceipt("hook1", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 109.0),
        ]

        accuracy = calculate_hook_accuracy(receipts, expected_duration=100.0)

        assert accuracy.bias > 5.0, f"Expected significant bias, got {accuracy.bias}"
        assert not accuracy.is_unbiased(), "Should be biased"

    def test_precision_high(self) -> None:
        """Test precision calculation with high precision measurements."""
        receipts = [
            HookReceipt("hook1", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 100.0),
            HookReceipt("hook1", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 100.1),
            HookReceipt("hook2", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 100.0),
            HookReceipt("hook2", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 100.1),
        ]

        precision = calculate_hook_precision(receipts)

        assert precision.is_precise(), "Should have high precision"
        assert precision.total_variation < 1.0, f"Total variation too high: {precision.total_variation}"

    def test_precision_low(self) -> None:
        """Test precision calculation with low precision measurements."""
        receipts = [
            HookReceipt("hook1", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 100.0),
            HookReceipt("hook1", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 120.0),
            HookReceipt("hook2", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 90.0),
            HookReceipt("hook2", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 110.0),
        ]

        precision = calculate_hook_precision(receipts)

        assert not precision.is_precise(), "Should have low precision"
        assert precision.total_variation > 5.0, "Total variation should be high"

    def test_ndc_adequate(self) -> None:
        """Test NDC (Number of Distinct Categories) adequacy."""
        # Adequate NDC (>= 5)
        metrics = HookMSAMetrics(repeatability=0.05, reproducibility=0.03, gage_rr=8.3, ndc=7, is_acceptable=True)
        assert metrics.is_adequate_ndc, "NDC should be adequate"

        # Inadequate NDC (< 5)
        metrics2 = HookMSAMetrics(repeatability=0.05, reproducibility=0.03, gage_rr=8.3, ndc=3, is_acceptable=False)
        assert not metrics2.is_adequate_ndc, "NDC should be inadequate"

    def test_hook_registry_msa_integration(self) -> None:
        """Test MSA integration with HookRegistry."""
        registry = HookRegistry()

        # Register test hook
        hook = KnowledgeHook(
            hook_id="test-msa-hook",
            name="MSA Test Hook",
            phase=HookPhase.ON_CHANGE,
            priority=100,
            enabled=True,
            condition_query="ASK { ?s ?p ?o }",
            action=HookAction.NOTIFY,
            handler_data={"message": "Test notification"},
        )
        registry.register(hook)

        # Generate receipts with low variation for excellent MSA
        for i in range(10):
            receipt = HookReceipt(
                hook_id=hook.hook_id,
                phase=HookPhase.ON_CHANGE,
                timestamp=datetime.now(UTC),
                condition_matched=True,
                action_taken=HookAction.NOTIFY,
                duration_ms=100.0 + (i * 0.01),  # Very low variation (0.01ms increments)
            )
            registry.add_receipt(receipt)

        # Retrieve receipts and calculate MSA
        receipts = registry.get_receipts(hook_id=hook.hook_id, limit=10)
        assert len(receipts) == 10, f"Expected 10 receipts, got {len(receipts)}"

        metrics = calculate_hook_gage_rr(receipts, parts=1, appraisers=1, trials=10)
        # With low variation, should be excellent
        assert metrics.is_excellent or metrics.is_acceptable, (
            f"Registry receipts should produce acceptable MSA: GRR={metrics.gage_rr}%"
        )

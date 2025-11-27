"""Knowledge Hooks FMEA Usage Example.

Demonstrates how to use the FMEA module to analyze failure modes
in the Knowledge Hooks system.

Run this example:
    python examples/hooks_fmea_usage.py

Or with uv:
    uv run python examples/hooks_fmea_usage.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.hybrid.lss.fmea.ratings import Detection, Occurrence, Severity
from tests.hybrid.lss.hooks.fmea import HOOK_FAILURE_MODES, HookFailureMode


def main() -> None:
    """Demonstrate FMEA module usage."""
    print("=" * 80)
    print("Knowledge Hooks FMEA Analysis")
    print("=" * 80)
    print()

    # Example 1: Access pre-defined failure modes
    print("1. Pre-defined Failure Modes")
    print("-" * 80)
    for fm_id, fm in sorted(HOOK_FAILURE_MODES.items(), key=lambda x: x[1].rpn, reverse=True):
        risk_emoji = {
            "Critical": "🔴",
            "High": "🟠",
            "Medium": "🟡",
            "Low": "🟢",
        }
        emoji = risk_emoji.get(fm.risk_level(), "⚪")
        print(f"{emoji} {fm_id}: {fm.name:40} RPN={fm.rpn:3} ({fm.risk_level()})")
    print()

    # Example 2: Get highest risk failure mode
    print("2. Highest Risk Failure Mode")
    print("-" * 80)
    highest_risk = max(HOOK_FAILURE_MODES.values(), key=lambda fm: fm.rpn)
    print(f"ID: {highest_risk.id}")
    print(f"Name: {highest_risk.name}")
    print(f"RPN: {highest_risk.rpn}")
    print(f"Risk Level: {highest_risk.risk_level()}")
    print(f"Severity: {highest_risk.severity}/10")
    print(f"Occurrence: {highest_risk.occurrence}/10")
    print(f"Detection: {highest_risk.detection}/10")
    print(f"Effect: {highest_risk.effect}")
    print(f"Mitigation: {highest_risk.mitigation}")
    print()

    # Example 3: Filter by risk level
    print("3. Critical Risk Failure Modes")
    print("-" * 80)
    critical_modes = [fm for fm in HOOK_FAILURE_MODES.values() if fm.risk_level() == "Critical"]
    print(f"Found {len(critical_modes)} critical risk modes:")
    for fm in sorted(critical_modes, key=lambda x: x.rpn, reverse=True):
        print(f"  - {fm.id}: {fm.name} (RPN={fm.rpn})")
    print()

    # Example 4: Create custom failure mode
    print("4. Custom Failure Mode")
    print("-" * 80)
    custom_fm = HookFailureMode(
        id="FM-HOOK-CUSTOM-001",
        name="Custom Hook Validation Failure",
        description="Custom validation hook fails to execute due to missing dependencies",
        effect="Validation bypassed, potentially allowing invalid data",
        severity=Severity.MODERATE,
        occurrence=Occurrence.LOW,
        detection=Detection.HIGH,
        mitigation="Add dependency checks at hook registration time",
    )
    print(f"Custom FM: {custom_fm.name}")
    print(f"RPN: {custom_fm.rpn} ({custom_fm.risk_level()})")
    print(f"Calculated from: S={custom_fm.severity} × O={custom_fm.occurrence} × D={custom_fm.detection}")
    print()

    # Example 5: Risk distribution analysis
    print("5. Risk Distribution")
    print("-" * 80)
    risk_counts: dict[str, int] = {}
    for fm in HOOK_FAILURE_MODES.values():
        risk_level = fm.risk_level()
        risk_counts[risk_level] = risk_counts.get(risk_level, 0) + 1

    total = len(HOOK_FAILURE_MODES)
    for risk_level in ["Critical", "High", "Medium", "Low"]:
        count = risk_counts.get(risk_level, 0)
        percentage = (count / total * 100) if total > 0 else 0
        bar_length = int(percentage / 2)  # Scale to 50 chars max
        bar = "█" * bar_length
        print(f"{risk_level:10} {bar:50} {count:2} ({percentage:5.1f}%)")
    print()

    # Example 6: Mitigation coverage
    print("6. Mitigation Coverage")
    print("-" * 80)
    with_mitigation = [fm for fm in HOOK_FAILURE_MODES.values() if fm.mitigation is not None]
    print(f"Failure modes with mitigation: {len(with_mitigation)}/{len(HOOK_FAILURE_MODES)}")
    print(f"Coverage: {len(with_mitigation) / len(HOOK_FAILURE_MODES) * 100:.1f}%")
    print()

    # Example 7: Severity distribution
    print("7. Severity Analysis")
    print("-" * 80)
    severity_counts: dict[int, list[str]] = {}
    for fm in HOOK_FAILURE_MODES.values():
        severity_counts.setdefault(fm.severity, []).append(fm.id)

    for severity in sorted(severity_counts.keys(), reverse=True):
        fm_ids = severity_counts[severity]
        severity_name = {
            10: "HAZARDOUS",
            9: "CRITICAL",
            7: "HIGH",
            5: "MODERATE",
            3: "MINOR",
            1: "NONE",
        }.get(severity, f"S={severity}")
        print(f"{severity_name:12} (S={severity:2}): {len(fm_ids)} modes - {', '.join(fm_ids)}")
    print()

    # Example 8: Detection difficulty analysis
    print("8. Detection Difficulty")
    print("-" * 80)
    hard_to_detect = [fm for fm in HOOK_FAILURE_MODES.values() if fm.detection >= 7]
    print(f"Hard to detect (D>=7): {len(hard_to_detect)} modes")
    for fm in sorted(hard_to_detect, key=lambda x: x.detection, reverse=True):
        print(f"  - {fm.id}: {fm.name} (D={fm.detection})")
    print()

    # Example 9: Occurrence frequency analysis
    print("9. Occurrence Frequency")
    print("-" * 80)
    frequent = [fm for fm in HOOK_FAILURE_MODES.values() if fm.occurrence >= 5]
    print(f"Frequently occurring (O>=5): {len(frequent)} modes")
    for fm in sorted(frequent, key=lambda x: x.occurrence, reverse=True):
        occurrence_desc = {
            9: "VERY HIGH (1 in 8)",
            7: "HIGH (1 in 80)",
            5: "MODERATE (1 in 400)",
            3: "LOW (1 in 20K)",
            1: "REMOTE (<1 in 1M)",
        }.get(fm.occurrence, f"O={fm.occurrence}")
        print(f"  - {fm.id}: {fm.name} ({occurrence_desc})")
    print()

    # Example 10: Action recommendations
    print("10. Recommended Actions (by RPN Priority)")
    print("-" * 80)
    action_modes = [fm for fm in HOOK_FAILURE_MODES.values() if fm.rpn > 100]
    print(f"Immediate action required for {len(action_modes)} modes (RPN > 100):")
    for i, fm in enumerate(sorted(action_modes, key=lambda x: x.rpn, reverse=True), 1):
        print(f"\n{i}. {fm.id}: {fm.name} (RPN={fm.rpn})")
        if fm.mitigation:
            # Extract first sentence of mitigation
            first_sentence = fm.mitigation.split(".")[0] + "."
            print(f"   Action: {first_sentence}")
    print()

    print("=" * 80)
    print("FMEA Analysis Complete")
    print("=" * 80)


if __name__ == "__main__":
    main()

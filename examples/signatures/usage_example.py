"""Example usage of KGCL signatures.

Demonstrates how to use all signature modules for reasoning tasks
with both LLM-powered and fallback modes.
"""

from datetime import datetime

from kgcl.signatures import (
    # Context Classifier
    ContextClassifierInput,
    ContextClassifierModule,
    # Daily Brief
    DailyBriefInput,
    DailyBriefModule,
    # Feature Analyzer
    FeatureAnalyzerInput,
    FeatureAnalyzerModule,
    # Pattern Detector
    PatternDetectorInput,
    PatternDetectorModule,
    # Configuration
    SignatureConfig,
    # Weekly Retro
    WeeklyRetroInput,
    WeeklyRetroModule,
    # Wellbeing
    WellbeingInput,
    WellbeingModule,
    create_all_modules,
    health_check,
)


def example_daily_brief():
    """Example: Generate daily activity brief."""
    print("\n=== Daily Brief Example ===")

    # Create input data
    input_data = DailyBriefInput(
        time_in_app=6.5,
        domain_visits=28,
        calendar_busy_hours=4.5,
        context_switches=14,
        focus_time=2.1,
        screen_time=8.5,
        top_apps={"VSCode": 2.5, "Safari": 1.8, "Slack": 0.9},
        top_domains={"github.com": 12, "stackoverflow.com": 8},
        meeting_count=6,
        break_intervals=3,
    )

    # Generate brief (using fallback mode - no LLM required)
    module = DailyBriefModule(use_llm=False)
    output = module.generate(input_data)

    print(f"Summary: {output.summary}")
    print(f"Productivity Score: {output.productivity_score}/100")
    print(f"Highlights: {output.highlights[:3]}")
    print(f"Top Recommendation: {output.recommendations[0] if output.recommendations else 'None'}")


def example_weekly_retro():
    """Example: Generate weekly retrospective."""
    print("\n=== Weekly Retrospective Example ===")

    input_data = WeeklyRetroInput(
        week_start=datetime(2024, 11, 18),
        week_end=datetime(2024, 11, 22),
        total_screen_time=42.5,
        total_focus_time=15.5,
        total_meeting_hours=18.0,
        avg_context_switches=16.2,
        daily_summaries=[
            "Monday: Heavy coding day with 3.2h focus time",
            "Tuesday: Meeting-heavy with 5 calls",
            "Wednesday: Balanced work with good focus",
            "Thursday: Code reviews and documentation",
            "Friday: Sprint planning",
        ],
        daily_productivity_scores=[75, 65, 80, 70, 68],
        top_apps_weekly={"VSCode": 12.5, "Safari": 8.2},
        top_domains_weekly={"github.com": 85},
        total_breaks=15,
        goals=["Complete feature X", "Review 10 PRs"],
    )

    module = WeeklyRetroModule(use_llm=False)
    output = module.generate(input_data)

    print(f"Weekly Score: {output.weekly_productivity_score}/100")
    print(f"Narrative: {output.narrative[:200]}...")
    print(f"Key Pattern: {output.patterns[0] if output.patterns else 'None'}")
    print(f"Goals Progress: {len(output.progress_on_goals)} goals tracked")


def example_feature_analyzer():
    """Example: Analyze feature time series."""
    print("\n=== Feature Analyzer Example ===")

    input_data = FeatureAnalyzerInput(
        feature_name="focus_time",
        feature_values=[2.2, 2.5, 2.3, 2.4, 2.1, 2.6, 2.3],
        window="daily",
        context="Daily deep focus time in hours",
    )

    module = FeatureAnalyzerModule(use_llm=False)
    output = module.analyze(input_data)

    print(f"Trend: {output.trend}")
    print(f"Mean: {output.summary_stats['mean']:.2f}h")
    print(f"Interpretation: {output.interpretation[:150]}...")
    print(f"Outliers Detected: {len(output.outliers)}")


def example_pattern_detector():
    """Example: Detect patterns across multiple features."""
    print("\n=== Pattern Detector Example ===")

    input_data = PatternDetectorInput(
        multiple_features={
            "focus_time": [2.5, 1.8, 3.2, 2.1, 1.5],
            "meeting_hours": [1.5, 4.2, 1.0, 2.5, 3.8],
            "context_switches": [12, 18, 10, 14, 20],
        },
        time_window="daily",
        context="Weekly work pattern analysis",
    )

    module = PatternDetectorModule(use_llm=False)
    output = module.detect(input_data)

    print(f"Patterns Detected: {len(output.detected_patterns)}")
    if output.detected_patterns:
        pattern = output.detected_patterns[0]
        print(f"Top Pattern: {pattern.pattern_name}")
        print(f"Confidence: {pattern.confidence}%")
    print(f"Correlations: {list(output.correlations.items())[:2]}")


def example_context_classifier():
    """Example: Classify activity context."""
    print("\n=== Context Classifier Example ===")

    activities = [
        ContextClassifierInput(
            app_name="com.microsoft.VSCode",
            domain_names=[],
            calendar_event="",
            time_of_day=10,
            window_title="main.py - kgcl",
            duration_seconds=1800,
        ),
        ContextClassifierInput(
            app_name="com.apple.Safari",
            domain_names=["github.com", "stackoverflow.com"],
            calendar_event="",
            time_of_day=14,
            window_title="Python Documentation",
            duration_seconds=600,
        ),
        ContextClassifierInput(
            app_name="us.zoom.xos",
            domain_names=[],
            calendar_event="Team Standup",
            time_of_day=9,
            window_title="Zoom Meeting",
            duration_seconds=1800,
        ),
    ]

    module = ContextClassifierModule(use_llm=False)

    for activity in activities:
        output = module.classify(activity)
        print(
            f"App: {activity.app_name.split('.')[-1]:15} -> Context: {output.context_label:15} (confidence: {output.confidence}%)"
        )


def example_wellbeing():
    """Example: Analyze wellbeing indicators."""
    print("\n=== Wellbeing Analysis Example ===")

    input_data = WellbeingInput(
        screen_time=8.5,
        focus_time=2.1,
        meeting_time=4.5,
        break_intervals=3,
        context_switches=14,
        work_hours=9.2,
        after_hours_time=1.5,
        weekend_work_time=0,
        physical_activity=0.5,
    )

    module = WellbeingModule(use_llm=False)
    output = module.analyze(input_data)

    print(f"Wellbeing Score: {output.wellbeing_score}/100")
    print(f"Work-Life Balance: {output.work_life_balance['assessment']}")
    print(f"Focus Quality: {output.focus_quality['rating']}")
    print(f"Break Frequency: {output.break_patterns['frequency']}")
    print(f"Risk Factors: {len(output.risk_factors)}")
    print(f"Top Recommendation: {output.recommendations[0] if output.recommendations else 'None'}")


def example_configuration():
    """Example: Configure signatures globally."""
    print("\n=== Configuration Example ===")

    # Check system health
    status = health_check()
    print(f"System Status: {status['status']}")
    print(f"DSPy Available: {status['dspy_available']}")
    print(f"Modules Available: {len(status['modules_available'])}")

    # Create configuration
    config = SignatureConfig(
        use_llm=False,  # Fallback mode (no Ollama required)
        temperature=0.7,
        fallback_on_error=True,
    )
    print(f"Config: {config.to_dict()}")

    # Create all modules at once
    modules = create_all_modules(config)
    print(f"Modules Created: {list(modules.keys())}")


def example_complete_workflow():
    """Example: Complete daily workflow."""
    print("\n=== Complete Daily Workflow Example ===")

    # Configure globally
    config = SignatureConfig(use_llm=False)
    modules = create_all_modules(config)

    # Simulate a day's activities
    activities = [
        ContextClassifierInput(
            app_name="com.microsoft.VSCode",
            domain_names=[],
            calendar_event="",
            time_of_day=9,
            window_title="coding",
        ),
        ContextClassifierInput(
            app_name="us.zoom.xos",
            domain_names=[],
            calendar_event="Standup",
            time_of_day=10,
            window_title="meeting",
        ),
        ContextClassifierInput(
            app_name="com.apple.Safari",
            domain_names=["github.com"],
            calendar_event="",
            time_of_day=11,
            window_title="research",
        ),
    ]

    # Classify activities
    contexts = []
    for activity in activities:
        result = modules["context_classifier"].classify(activity)
        contexts.append(result.context_label)
    print(f"Activity Contexts: {contexts}")

    # Generate daily brief
    brief_input = DailyBriefInput(
        time_in_app=7.0,
        domain_visits=25,
        calendar_busy_hours=3.0,
        context_switches=12,
        focus_time=2.5,
        screen_time=8.0,
        meeting_count=4,
        break_intervals=4,
    )
    brief = modules["daily_brief"].generate(brief_input)
    print(f"Daily Brief Score: {brief.productivity_score}/100")

    # Analyze wellbeing
    wellbeing_input = WellbeingInput(
        screen_time=8.0,
        focus_time=2.5,
        meeting_time=3.0,
        break_intervals=4,
        context_switches=12,
        work_hours=8.5,
        after_hours_time=0.5,
    )
    wellbeing = modules["wellbeing"].analyze(wellbeing_input)
    print(f"Wellbeing Score: {wellbeing.wellbeing_score}/100")
    print(f"Work-Life Balance: {wellbeing.work_life_balance['assessment']}")

    # Analyze a feature
    feature_input = FeatureAnalyzerInput(
        feature_name="daily_focus", feature_values=[2.5, 2.8, 2.3, 2.7, 2.6], window="daily"
    )
    feature_analysis = modules["feature_analyzer"].analyze(feature_input)
    print(f"Focus Time Trend: {feature_analysis.trend}")


if __name__ == "__main__":
    print("=" * 60)
    print("KGCL Signatures - Usage Examples")
    print("=" * 60)

    example_configuration()
    example_daily_brief()
    example_weekly_retro()
    example_feature_analyzer()
    example_pattern_detector()
    example_context_classifier()
    example_wellbeing()
    example_complete_workflow()

    print("\n" + "=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)

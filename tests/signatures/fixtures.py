"""Test fixtures for signature modules.

Provides realistic test data for all signature modules to ensure
consistent and reproducible testing.
"""

from datetime import datetime
import pytest

from kgcl.signatures import (
    DailyBriefInput,
    WeeklyRetroInput,
    FeatureAnalyzerInput,
    PatternDetectorInput,
    ContextClassifierInput,
    WellbeingInput,
)


# Daily Brief Fixtures
@pytest.fixture
def daily_brief_input_standard():
    """Standard daily brief input with typical work day metrics."""
    return DailyBriefInput(
        time_in_app=6.5,
        domain_visits=28,
        calendar_busy_hours=4.5,
        context_switches=14,
        focus_time=2.1,
        screen_time=8.5,
        top_apps={"VSCode": 2.5, "Safari": 1.8, "Slack": 0.9},
        top_domains={"github.com": 12, "stackoverflow.com": 8},
        meeting_count=6,
        break_intervals=3
    )


@pytest.fixture
def daily_brief_input_high_focus():
    """Daily brief input with excellent focus metrics."""
    return DailyBriefInput(
        time_in_app=8.0,
        domain_visits=15,
        calendar_busy_hours=2.0,
        context_switches=8,
        focus_time=4.5,
        screen_time=8.0,
        top_apps={"VSCode": 5.0, "Terminal": 1.5, "Safari": 1.0},
        top_domains={"github.com": 8, "docs.python.org": 4},
        meeting_count=2,
        break_intervals=5
    )


@pytest.fixture
def daily_brief_input_meeting_heavy():
    """Daily brief input with heavy meeting load."""
    return DailyBriefInput(
        time_in_app=4.0,
        domain_visits=35,
        calendar_busy_hours=6.5,
        context_switches=22,
        focus_time=1.2,
        screen_time=9.0,
        top_apps={"Zoom": 3.5, "Slack": 2.0, "Safari": 1.5},
        top_domains={"zoom.us": 15, "notion.so": 10},
        meeting_count=10,
        break_intervals=2
    )


# Weekly Retro Fixtures
@pytest.fixture
def weekly_retro_input_standard():
    """Standard weekly retro input with 5 days of data."""
    return WeeklyRetroInput(
        week_start=datetime(2024, 11, 18),
        week_end=datetime(2024, 11, 22),
        total_screen_time=42.5,
        total_focus_time=15.5,
        total_meeting_hours=18.0,
        avg_context_switches=16.2,
        daily_summaries=[
            "Monday: Heavy coding day with 3.2h focus time",
            "Tuesday: Meeting-heavy with 5 calls (4.2h)",
            "Wednesday: Balanced work with good focus (2.8h)",
            "Thursday: Code reviews and documentation",
            "Friday: Sprint planning and retrospective (3.5h meetings)"
        ],
        daily_productivity_scores=[75, 65, 80, 70, 68],
        top_apps_weekly={"VSCode": 12.5, "Safari": 8.2, "Slack": 6.5},
        top_domains_weekly={"github.com": 85, "stackoverflow.com": 42},
        total_breaks=15,
        goals=["Complete feature X", "Review 10 PRs", "Reduce meeting time"]
    )


@pytest.fixture
def weekly_retro_input_excellent():
    """Weekly retro input with excellent productivity."""
    return WeeklyRetroInput(
        week_start=datetime(2024, 11, 18),
        week_end=datetime(2024, 11, 22),
        total_screen_time=38.0,
        total_focus_time=22.5,
        total_meeting_hours=10.0,
        avg_context_switches=10.5,
        daily_summaries=[
            "Monday: Excellent focus - 4.5h deep work",
            "Tuesday: Continued strong focus (4.2h)",
            "Wednesday: Maintained momentum (4.8h focus)",
            "Thursday: Productive code completion (4.5h)",
            "Friday: Wrapped up sprint with reviews (4.5h)"
        ],
        daily_productivity_scores=[85, 88, 90, 87, 85],
        top_apps_weekly={"VSCode": 18.0, "Terminal": 4.5, "Safari": 6.0},
        top_domains_weekly={"github.com": 120, "docs.python.org": 35},
        total_breaks=20,
        goals=["Complete feature X", "Review 10 PRs"]
    )


# Feature Analyzer Fixtures
@pytest.fixture
def feature_analyzer_input_stable():
    """Feature analyzer input with stable pattern."""
    return FeatureAnalyzerInput(
        feature_name="focus_time",
        feature_values=[2.2, 2.5, 2.3, 2.4, 2.1, 2.6, 2.3],
        window="daily",
        context="Daily deep focus time in hours"
    )


@pytest.fixture
def feature_analyzer_input_trending():
    """Feature analyzer input with increasing trend."""
    return FeatureAnalyzerInput(
        feature_name="meeting_hours",
        feature_values=[2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0],
        window="daily",
        context="Daily meeting time trending upward"
    )


@pytest.fixture
def feature_analyzer_input_outliers():
    """Feature analyzer input with outliers."""
    return FeatureAnalyzerInput(
        feature_name="context_switches",
        feature_values=[12, 14, 13, 35, 15, 14, 13],
        window="daily",
        context="Context switches with one unusual spike"
    )


# Pattern Detector Fixtures
@pytest.fixture
def pattern_detector_input_standard():
    """Standard pattern detector input with multiple features."""
    return PatternDetectorInput(
        multiple_features={
            "focus_time": [2.5, 1.8, 3.2, 2.1, 1.5],
            "meeting_hours": [1.5, 4.2, 1.0, 2.5, 3.8],
            "context_switches": [12, 18, 10, 14, 20],
            "safari_usage": [1.2, 2.5, 0.8, 1.5, 2.2]
        },
        time_window="daily",
        context="Weekly work pattern analysis"
    )


@pytest.fixture
def pattern_detector_input_correlated():
    """Pattern detector input with strong correlations."""
    return PatternDetectorInput(
        multiple_features={
            "coding_time": [4.0, 3.5, 4.5, 3.8, 4.2],
            "github_visits": [25, 22, 28, 24, 26],  # Highly correlated with coding
            "slack_usage": [0.5, 0.8, 0.4, 0.6, 0.5],  # Low and stable
        },
        time_window="daily",
        context="Focused development week"
    )


# Context Classifier Fixtures
@pytest.fixture
def context_classifier_input_coding():
    """Context classifier input for coding activity."""
    return ContextClassifierInput(
        app_name="com.microsoft.VSCode",
        domain_names=[],
        calendar_event="",
        time_of_day=10,
        window_title="main.py - kgcl - Visual Studio Code",
        duration_seconds=1800
    )


@pytest.fixture
def context_classifier_input_research():
    """Context classifier input for research activity."""
    return ContextClassifierInput(
        app_name="com.apple.Safari",
        domain_names=["github.com", "stackoverflow.com", "docs.python.org"],
        calendar_event="",
        time_of_day=14,
        window_title="Python Documentation - Built-in Functions",
        duration_seconds=600
    )


@pytest.fixture
def context_classifier_input_meeting():
    """Context classifier input for meeting activity."""
    return ContextClassifierInput(
        app_name="us.zoom.xos",
        domain_names=[],
        calendar_event="Team Standup",
        time_of_day=9,
        window_title="Zoom Meeting - Team Standup",
        duration_seconds=1800
    )


@pytest.fixture
def context_classifier_input_communication():
    """Context classifier input for communication activity."""
    return ContextClassifierInput(
        app_name="com.tinyspeck.slackmacgap",
        domain_names=[],
        calendar_event="",
        time_of_day=15,
        window_title="Slack - engineering channel",
        duration_seconds=300
    )


# Wellbeing Fixtures
@pytest.fixture
def wellbeing_input_healthy():
    """Wellbeing input with healthy work patterns."""
    return WellbeingInput(
        screen_time=7.5,
        focus_time=3.5,
        meeting_time=2.5,
        break_intervals=5,
        context_switches=10,
        work_hours=8.0,
        after_hours_time=0,
        weekend_work_time=0,
        physical_activity=1.0
    )


@pytest.fixture
def wellbeing_input_at_risk():
    """Wellbeing input with burnout risk factors."""
    return WellbeingInput(
        screen_time=11.0,
        focus_time=1.5,
        meeting_time=6.0,
        break_intervals=2,
        context_switches=25,
        work_hours=10.5,
        after_hours_time=2.5,
        weekend_work_time=3.0,
        physical_activity=0
    )


@pytest.fixture
def wellbeing_input_moderate():
    """Wellbeing input with moderate work patterns."""
    return WellbeingInput(
        screen_time=8.5,
        focus_time=2.1,
        meeting_time=4.5,
        break_intervals=3,
        context_switches=14,
        work_hours=9.2,
        after_hours_time=1.5,
        weekend_work_time=0,
        physical_activity=0.5
    )


# Combined fixtures for integration tests
@pytest.fixture
def complete_daily_data():
    """Complete daily data for integration testing."""
    return {
        "brief_input": DailyBriefInput(
            time_in_app=6.5,
            domain_visits=28,
            calendar_busy_hours=4.5,
            context_switches=14,
            focus_time=2.1,
            screen_time=8.5,
            top_apps={"VSCode": 2.5, "Safari": 1.8, "Slack": 0.9},
            top_domains={"github.com": 12, "stackoverflow.com": 8},
            meeting_count=6,
            break_intervals=3
        ),
        "wellbeing_input": WellbeingInput(
            screen_time=8.5,
            focus_time=2.1,
            meeting_time=4.5,
            break_intervals=3,
            context_switches=14,
            work_hours=9.2,
            after_hours_time=1.5,
            weekend_work_time=0,
            physical_activity=0.5
        ),
        "activities": [
            ContextClassifierInput(
                app_name="com.microsoft.VSCode",
                domain_names=[],
                calendar_event="",
                time_of_day=10,
                window_title="main.py",
                duration_seconds=1800
            ),
            ContextClassifierInput(
                app_name="us.zoom.xos",
                domain_names=[],
                calendar_event="Team Standup",
                time_of_day=9,
                window_title="Zoom Meeting",
                duration_seconds=1800
            ),
        ]
    }


# Edge case fixtures
@pytest.fixture
def edge_case_minimal_data():
    """Edge case with minimal data."""
    return DailyBriefInput(
        time_in_app=0.5,
        domain_visits=2,
        calendar_busy_hours=0,
        context_switches=1,
        focus_time=0.3,
        screen_time=0.5,
        top_apps={},
        top_domains={},
        meeting_count=0,
        break_intervals=0
    )


@pytest.fixture
def edge_case_maximum_load():
    """Edge case with maximum work load."""
    return DailyBriefInput(
        time_in_app=14.0,
        domain_visits=150,
        calendar_busy_hours=8.0,
        context_switches=50,
        focus_time=0.5,
        screen_time=14.0,
        top_apps={"Zoom": 4.0, "Slack": 3.5, "Email": 3.0, "Safari": 2.5},
        top_domains={"zoom.us": 50, "slack.com": 40, "gmail.com": 30},
        meeting_count=15,
        break_intervals=1
    )

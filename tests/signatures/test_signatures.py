"""Comprehensive tests for signature modules.

Tests all signature modules in fallback mode (no LLM required) to ensure
rule-based logic works correctly and produces expected outputs.
"""

from typing import Any

import pytest
from pytest import MonkeyPatch

from kgcl.signatures import (
    ContextClassifierInput,
    ContextClassifierModule,
    DailyBriefInput,
    DailyBriefModule,
    FeatureAnalyzerInput,
    FeatureAnalyzerModule,
    PatternDetectorInput,
    PatternDetectorModule,
    SignatureConfig,
    WeeklyRetroInput,
    WeeklyRetroModule,
    WellbeingInput,
    WellbeingModule,
    create_all_modules,
    health_check,
)

OUTLIER_INDEX = 3
STRONG_CORRELATION_THRESHOLD = 0.5
CompleteDailyData = dict[str, Any]


class TestDailyBriefModule:
    """Tests for DailyBriefModule."""

    def test_fallback_generation_standard(
        self, daily_brief_input_standard: DailyBriefInput
    ) -> None:
        """Test fallback generation with standard input."""
        module = DailyBriefModule(use_llm=False)
        output = module.generate(daily_brief_input_standard)

        assert output.summary
        assert len(output.summary) > 10
        assert output.productivity_score >= 0
        assert output.productivity_score <= 100
        assert isinstance(output.highlights, list)
        assert isinstance(output.patterns, list)
        assert isinstance(output.recommendations, list)
        assert isinstance(output.wellbeing_indicators, dict)

    def test_fallback_generation_high_focus(
        self, daily_brief_input_high_focus: DailyBriefInput
    ) -> None:
        """Test fallback with high focus input."""
        module = DailyBriefModule(use_llm=False)
        output = module.generate(daily_brief_input_high_focus)

        # High focus should yield high productivity score
        assert output.productivity_score >= 70
        assert any("focus" in h.lower() for h in output.highlights)

    def test_fallback_generation_meeting_heavy(
        self, daily_brief_input_meeting_heavy: DailyBriefInput
    ) -> None:
        """Test fallback with meeting-heavy input."""
        module = DailyBriefModule(use_llm=False)
        output = module.generate(daily_brief_input_meeting_heavy)

        # Meeting-heavy should have recommendations about meetings
        assert any("meeting" in r.lower() for r in output.recommendations)

    def test_productivity_score_calculation(self) -> None:
        """Test productivity score calculation logic."""
        module = DailyBriefModule(use_llm=False)

        # High focus, low context switches should score high
        from kgcl.signatures.daily_brief import DailyBriefInput

        high_score_input = DailyBriefInput(
            time_in_app=8.0,
            domain_visits=10,
            calendar_busy_hours=1.0,
            context_switches=5,
            focus_time=5.0,
            screen_time=8.0,
            meeting_count=1,
            break_intervals=6,
        )
        output = module.generate(high_score_input)
        assert output.productivity_score >= 80

    @pytest.mark.asyncio
    async def test_async_generation(
        self, daily_brief_input_standard: DailyBriefInput
    ) -> None:
        """Test async generation."""
        module = DailyBriefModule(use_llm=False)
        output = await module.generate_async(daily_brief_input_standard)

        assert output.summary
        assert output.productivity_score >= 0


class TestWeeklyRetroModule:
    """Tests for WeeklyRetroModule."""

    def test_fallback_generation_standard(
        self, weekly_retro_input_standard: WeeklyRetroInput
    ) -> None:
        """Test fallback generation with standard input."""
        module = WeeklyRetroModule(use_llm=False)
        output = module.generate(weekly_retro_input_standard)

        assert output.narrative
        assert len(output.narrative) > 50
        assert output.weekly_productivity_score >= 0
        assert output.weekly_productivity_score <= 100
        assert isinstance(output.patterns, list)
        assert isinstance(output.recommendations, list)
        assert isinstance(output.progress_on_goals, dict)
        assert isinstance(output.trends, dict)

    def test_fallback_generation_excellent(
        self, weekly_retro_input_excellent: WeeklyRetroInput
    ) -> None:
        """Test fallback with excellent week."""
        module = WeeklyRetroModule(use_llm=False)
        output = module.generate(weekly_retro_input_excellent)

        # Excellent week should have high score
        assert output.weekly_productivity_score >= 80
        assert len(output.achievements) > 0

    def test_goal_progress_tracking(
        self, weekly_retro_input_standard: WeeklyRetroInput
    ) -> None:
        """Test goal progress tracking."""
        module = WeeklyRetroModule(use_llm=False)
        output = module.generate(weekly_retro_input_standard)

        # Should track all goals
        assert len(output.progress_on_goals) == len(weekly_retro_input_standard.goals)
        for goal in weekly_retro_input_standard.goals:
            assert goal in output.progress_on_goals

    def test_trend_analysis(
        self, weekly_retro_input_standard: WeeklyRetroInput
    ) -> None:
        """Test trend analysis."""
        module = WeeklyRetroModule(use_llm=False)
        output = module.generate(weekly_retro_input_standard)

        assert "overall" in output.trends
        assert output.trends["overall"] in ["improving", "declining", "stable"]

    @pytest.mark.asyncio
    async def test_async_generation(
        self, weekly_retro_input_standard: WeeklyRetroInput
    ) -> None:
        """Test async generation."""
        module = WeeklyRetroModule(use_llm=False)
        output = await module.generate_async(weekly_retro_input_standard)

        assert output.narrative
        assert output.weekly_productivity_score >= 0


class TestFeatureAnalyzerModule:
    """Tests for FeatureAnalyzerModule."""

    def test_fallback_analysis_stable(
        self, feature_analyzer_input_stable: FeatureAnalyzerInput
    ) -> None:
        """Test fallback analysis with stable pattern."""
        module = FeatureAnalyzerModule(use_llm=False)
        output = module.analyze(feature_analyzer_input_stable)

        assert output.trend == "stable"
        assert "summary_stats" in dir(output)
        assert output.summary_stats["mean"] > 0
        assert output.interpretation

    def test_fallback_analysis_trending(
        self, feature_analyzer_input_trending: FeatureAnalyzerInput
    ) -> None:
        """Test fallback analysis with trending pattern."""
        module = FeatureAnalyzerModule(use_llm=False)
        output = module.analyze(feature_analyzer_input_trending)

        assert output.trend == "increasing"
        assert len(output.recommendations) > 0

    def test_outlier_detection(
        self, feature_analyzer_input_outliers: FeatureAnalyzerInput
    ) -> None:
        """Test outlier detection."""
        module = FeatureAnalyzerModule(use_llm=False)
        output = module.analyze(feature_analyzer_input_outliers)

        # Should detect the outlier at index 3
        assert len(output.outliers) > 0
        outlier_indices = [o["index"] for o in output.outliers]
        assert OUTLIER_INDEX in outlier_indices

    def test_statistical_calculations(
        self, feature_analyzer_input_stable: FeatureAnalyzerInput
    ) -> None:
        """Test statistical calculations."""
        module = FeatureAnalyzerModule(use_llm=False)
        output = module.analyze(feature_analyzer_input_stable)

        stats = output.summary_stats
        assert "mean" in stats
        assert "median" in stats
        assert "std" in stats
        assert "min" in stats
        assert "max" in stats
        assert stats["min"] <= stats["mean"] <= stats["max"]

    @pytest.mark.asyncio
    async def test_async_analysis(
        self, feature_analyzer_input_stable: FeatureAnalyzerInput
    ) -> None:
        """Test async analysis."""
        module = FeatureAnalyzerModule(use_llm=False)
        output = await module.analyze_async(feature_analyzer_input_stable)

        assert output.trend in ["increasing", "decreasing", "stable", "volatile"]


class TestPatternDetectorModule:
    """Tests for PatternDetectorModule."""

    def test_fallback_detection_standard(
        self, pattern_detector_input_standard: PatternDetectorInput
    ) -> None:
        """Test fallback detection with standard input."""
        module = PatternDetectorModule(use_llm=False)
        output = module.detect(pattern_detector_input_standard)

        assert isinstance(output.detected_patterns, list)
        assert isinstance(output.correlations, dict)
        assert isinstance(output.insights, list)
        assert isinstance(output.behavioral_clusters, dict)

    def test_correlation_detection(
        self, pattern_detector_input_correlated: PatternDetectorInput
    ) -> None:
        """Test correlation detection."""
        module = PatternDetectorModule(use_llm=False)
        output = module.detect(pattern_detector_input_correlated)

        # Should detect correlation between coding_time and github_visits
        assert len(output.correlations) > 0
        corr_values = list(output.correlations.values())
        assert any(abs(c) > STRONG_CORRELATION_THRESHOLD for c in corr_values)

    def test_pattern_confidence(
        self, pattern_detector_input_standard: PatternDetectorInput
    ) -> None:
        """Test pattern confidence scores."""
        module = PatternDetectorModule(use_llm=False)
        output = module.detect(pattern_detector_input_standard)

        for pattern in output.detected_patterns:
            assert pattern.confidence >= 0
            assert pattern.confidence <= 100
            assert pattern.pattern_name
            assert pattern.evidence

    def test_behavioral_clustering(
        self, pattern_detector_input_standard: PatternDetectorInput
    ) -> None:
        """Test behavioral clustering."""
        module = PatternDetectorModule(use_llm=False)
        output = module.detect(pattern_detector_input_standard)

        # Should identify at least one cluster
        assert len(output.behavioral_clusters) > 0

    @pytest.mark.asyncio
    async def test_async_detection(
        self, pattern_detector_input_standard: PatternDetectorInput
    ) -> None:
        """Test async detection."""
        module = PatternDetectorModule(use_llm=False)
        output = await module.detect_async(pattern_detector_input_standard)

        assert isinstance(output.detected_patterns, list)


class TestContextClassifierModule:
    """Tests for ContextClassifierModule."""

    def test_fallback_classify_coding(
        self, context_classifier_input_coding: ContextClassifierInput
    ) -> None:
        """Test fallback classification for coding activity."""
        module = ContextClassifierModule(use_llm=False)
        output = module.classify(context_classifier_input_coding)

        assert output.context_label == "work_focus"
        assert output.confidence > 0
        assert output.reasoning

    def test_fallback_classify_research(
        self, context_classifier_input_research: ContextClassifierInput
    ) -> None:
        """Test fallback classification for research activity."""
        module = ContextClassifierModule(use_llm=False)
        output = module.classify(context_classifier_input_research)

        assert output.context_label == "research"
        assert (
            "github" in output.reasoning.lower()
            or "documentation" in output.reasoning.lower()
        )

    def test_fallback_classify_meeting(
        self, context_classifier_input_meeting: ContextClassifierInput
    ) -> None:
        """Test fallback classification for meeting activity."""
        module = ContextClassifierModule(use_llm=False)
        output = module.classify(context_classifier_input_meeting)

        assert output.context_label == "meetings"
        assert output.confidence >= 85

    def test_fallback_classify_communication(
        self, context_classifier_input_communication: ContextClassifierInput
    ) -> None:
        """Test fallback classification for communication activity."""
        module = ContextClassifierModule(use_llm=False)
        output = module.classify(context_classifier_input_communication)

        assert output.context_label == "communication"

    def test_suggested_tags(
        self, context_classifier_input_coding: ContextClassifierInput
    ) -> None:
        """Test suggested tags generation."""
        module = ContextClassifierModule(use_llm=False)
        output = module.classify(context_classifier_input_coding)

        assert isinstance(output.suggested_tags, list)
        assert len(output.suggested_tags) > 0

    @pytest.mark.asyncio
    async def test_async_classification(
        self, context_classifier_input_coding: ContextClassifierInput
    ) -> None:
        """Test async classification."""
        module = ContextClassifierModule(use_llm=False)
        output = await module.classify_async(context_classifier_input_coding)

        assert output.context_label
        assert output.confidence >= 0


class TestWellbeingModule:
    """Tests for WellbeingModule."""

    def test_fallback_analysis_healthy(
        self, wellbeing_input_healthy: WellbeingInput
    ) -> None:
        """Test fallback analysis with healthy patterns."""
        module = WellbeingModule(use_llm=False)
        output = module.analyze(wellbeing_input_healthy)

        assert output.wellbeing_score >= 70  # Healthy should score well
        assert output.work_life_balance["assessment"] in ["good", "excellent"]
        assert len(output.positive_factors) > 0

    def test_fallback_analysis_at_risk(
        self, wellbeing_input_at_risk: WellbeingInput
    ) -> None:
        """Test fallback analysis with at-risk patterns."""
        module = WellbeingModule(use_llm=False)
        output = module.analyze(wellbeing_input_at_risk)

        assert output.wellbeing_score < 60  # At-risk should score low
        assert len(output.risk_factors) > 0
        assert len(output.recommendations) > 0

    def test_work_life_balance_assessment(
        self, wellbeing_input_moderate: WellbeingInput
    ) -> None:
        """Test work-life balance assessment."""
        module = WellbeingModule(use_llm=False)
        output = module.analyze(wellbeing_input_moderate)

        assert "assessment" in output.work_life_balance
        assert output.work_life_balance["assessment"] in [
            "excellent",
            "good",
            "needs_attention",
            "poor",
        ]

    def test_focus_quality_assessment(
        self, wellbeing_input_healthy: WellbeingInput
    ) -> None:
        """Test focus quality assessment."""
        module = WellbeingModule(use_llm=False)
        output = module.analyze(wellbeing_input_healthy)

        assert "rating" in output.focus_quality
        assert "focus_ratio" in output.focus_quality

    def test_break_pattern_assessment(
        self, wellbeing_input_at_risk: WellbeingInput
    ) -> None:
        """Test break pattern assessment."""
        module = WellbeingModule(use_llm=False)
        output = module.analyze(wellbeing_input_at_risk)

        assert "frequency" in output.break_patterns
        # At-risk has only 2 breaks, should be flagged
        assert output.break_patterns["frequency"] in ["low", "moderate"]

    def test_recommendations_generated(
        self, wellbeing_input_moderate: WellbeingInput
    ) -> None:
        """Test recommendations generation."""
        module = WellbeingModule(use_llm=False)
        output = module.analyze(wellbeing_input_moderate)

        assert len(output.recommendations) > 0
        assert all(isinstance(r, str) for r in output.recommendations)

    @pytest.mark.asyncio
    async def test_async_analysis(
        self, wellbeing_input_healthy: WellbeingInput
    ) -> None:
        """Test async analysis."""
        module = WellbeingModule(use_llm=False)
        output = await module.analyze_async(wellbeing_input_healthy)

        assert output.wellbeing_score >= 0
        assert output.wellbeing_score <= 100


class TestSignatureConfig:
    """Tests for SignatureConfig."""

    def test_default_config(self) -> None:
        """Test default configuration."""
        config = SignatureConfig()
        assert isinstance(config.use_llm, bool)
        assert 0.0 <= config.temperature <= 1.0
        assert config.model
        assert config.base_url

    def test_from_env(self, monkeypatch: MonkeyPatch) -> None:
        """Test configuration from environment."""
        monkeypatch.setenv("KGCL_USE_LLM", "false")
        monkeypatch.setenv("KGCL_TEMPERATURE", "0.5")

        config = SignatureConfig.from_env()
        assert config.use_llm is False
        assert config.temperature == 0.5

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        config = SignatureConfig(use_llm=False, temperature=0.7)
        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert "use_llm" in config_dict
        assert "temperature" in config_dict
        assert "dspy_available" in config_dict


class TestModuleCreation:
    """Tests for module creation utilities."""

    def test_create_all_modules(self) -> None:
        """Test creating all modules."""
        config = SignatureConfig(use_llm=False)
        modules = create_all_modules(config)

        assert len(modules) == 6
        assert "daily_brief" in modules
        assert "weekly_retro" in modules
        assert "feature_analyzer" in modules
        assert "pattern_detector" in modules
        assert "context_classifier" in modules
        assert "wellbeing" in modules

    def test_health_check(self) -> None:
        """Test health check."""
        status = health_check()

        assert isinstance(status, dict)
        assert "status" in status
        assert status["status"] in ["healthy", "degraded", "error", "unknown"]
        assert "modules_available" in status
        assert len(status["modules_available"]) == 6


class TestIntegration:
    """Integration tests using complete daily data."""

    def test_complete_workflow(self, complete_daily_data: CompleteDailyData) -> None:
        """Test complete workflow with all modules."""
        config = SignatureConfig(use_llm=False)
        modules = create_all_modules(config)

        # Generate daily brief
        brief_output = modules["daily_brief"].generate(
            complete_daily_data["brief_input"]
        )
        assert brief_output.summary
        assert brief_output.productivity_score >= 0

        # Analyze wellbeing
        wellbeing_output = modules["wellbeing"].analyze(
            complete_daily_data["wellbeing_input"]
        )
        assert wellbeing_output.wellbeing_score >= 0

        # Classify activities
        for activity in complete_daily_data["activities"]:
            classification = modules["context_classifier"].classify(activity)
            assert classification.context_label
            assert classification.confidence > 0

    def test_edge_case_minimal(self, edge_case_minimal_data: DailyBriefInput) -> None:
        """Test edge case with minimal data."""
        module = DailyBriefModule(use_llm=False)
        output = module.generate(edge_case_minimal_data)

        # Should handle minimal data gracefully
        assert output.summary
        assert output.productivity_score >= 0

    def test_edge_case_maximum_load(
        self, edge_case_maximum_load: DailyBriefInput
    ) -> None:
        """Test edge case with maximum load."""
        module = DailyBriefModule(use_llm=False)
        output = module.generate(edge_case_maximum_load)

        # Should identify overload
        assert output.productivity_score < 70
        assert len(output.recommendations) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

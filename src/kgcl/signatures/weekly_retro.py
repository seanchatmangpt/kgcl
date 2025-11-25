"""Weekly Retrospective Signature for KGCL.

Aggregates daily summaries and metrics into comprehensive weekly retrospectives
with narrative insights, trend analysis, and goal progress tracking.
"""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field
import asyncio
import logging

try:
    import dspy
    DSPY_AVAILABLE = True
except ImportError:
    DSPY_AVAILABLE = False

from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class WeeklyRetroInput(BaseModel):
    """Input data for weekly retrospective generation.

    Attributes:
        week_start: Start date of the week
        week_end: End date of the week
        total_screen_time: Total screen time for the week (hours)
        total_focus_time: Total deep focus time (hours)
        total_meeting_hours: Total time in meetings (hours)
        avg_context_switches: Average context switches per day
        daily_summaries: List of daily summary texts
        daily_productivity_scores: Productivity scores for each day
        top_apps_weekly: Most used apps aggregated across the week
        top_domains_weekly: Most visited domains across the week
        total_breaks: Total breaks taken during the week
        goals: User-defined goals for the week (optional)
    """

    week_start: datetime = Field(..., description="Week start date")
    week_end: datetime = Field(..., description="Week end date")
    total_screen_time: float = Field(..., ge=0, description="Total screen hours")
    total_focus_time: float = Field(..., ge=0, description="Total focus hours")
    total_meeting_hours: float = Field(..., ge=0, description="Total meeting hours")
    avg_context_switches: float = Field(..., ge=0, description="Avg context switches/day")
    daily_summaries: list[str] = Field(
        default_factory=list,
        description="Daily summary texts"
    )
    daily_productivity_scores: list[int] = Field(
        default_factory=list,
        description="Daily productivity scores (0-100)"
    )
    top_apps_weekly: dict[str, float] = Field(
        default_factory=dict,
        description="App names to weekly usage hours"
    )
    top_domains_weekly: dict[str, int] = Field(
        default_factory=dict,
        description="Domain names to weekly visit counts"
    )
    total_breaks: int = Field(..., ge=0, description="Total breaks taken")
    goals: list[str] = Field(
        default_factory=list,
        description="User-defined weekly goals"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "week_start": "2024-11-18T00:00:00",
                "week_end": "2024-11-24T23:59:59",
                "total_screen_time": 45.2,
                "total_focus_time": 18.5,
                "total_meeting_hours": 12.3,
                "avg_context_switches": 16.2,
                "daily_summaries": [
                    "Monday: Heavy coding day with 3.2h focus time",
                    "Tuesday: Meeting-heavy day with 5 calls",
                    "Wednesday: Balanced work with good focus"
                ],
                "daily_productivity_scores": [75, 65, 80, 70, 72, 68, 55],
                "top_apps_weekly": {
                    "VSCode": 15.2,
                    "Safari": 8.5,
                    "Slack": 6.3
                },
                "top_domains_weekly": {
                    "github.com": 85,
                    "stackoverflow.com": 42,
                    "docs.python.org": 28
                },
                "total_breaks": 18,
                "goals": [
                    "Complete feature X",
                    "Review 10 PRs",
                    "Reduce meeting time"
                ]
            }
        }
    }


class WeeklyRetroOutput(BaseModel):
    """Output weekly retrospective with narrative and insights.

    Attributes:
        narrative: Comprehensive weekly narrative (3-5 paragraphs)
        metrics_summary: Key metrics aggregated from the week
        patterns: Multi-day patterns and trends observed
        progress_on_goals: Assessment of goal completion
        recommendations: Strategic recommendations for next week
        weekly_productivity_score: Overall productivity score (0-100)
        trends: Trend analysis (improving, stable, declining)
        achievements: Notable achievements and milestones
    """

    narrative: str = Field(..., description="Weekly narrative overview")
    metrics_summary: dict[str, Any] = Field(
        default_factory=dict,
        description="Aggregated metrics"
    )
    patterns: list[str] = Field(
        default_factory=list,
        description="Multi-day behavioral patterns"
    )
    progress_on_goals: dict[str, str] = Field(
        default_factory=dict,
        description="Goal completion assessments"
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Strategic recommendations"
    )
    weekly_productivity_score: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Overall weekly productivity (0-100)"
    )
    trends: dict[str, str] = Field(
        default_factory=dict,
        description="Trend analysis by category"
    )
    achievements: list[str] = Field(
        default_factory=list,
        description="Notable achievements"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "narrative": "This week showed strong coding productivity with 18.5 hours of deep focus time...",
                "metrics_summary": {
                    "total_screen_time": 45.2,
                    "avg_daily_focus": 2.64,
                    "meeting_load": "moderate",
                    "productivity_trend": "stable"
                },
                "patterns": [
                    "Monday-Wednesday: High focus periods",
                    "Thursday-Friday: Meeting clusters",
                    "Consistent morning deep work"
                ],
                "progress_on_goals": {
                    "Complete feature X": "Completed on Wednesday",
                    "Review 10 PRs": "Completed 8/10",
                    "Reduce meeting time": "No progress - meetings increased"
                },
                "recommendations": [
                    "Maintain Monday-Wednesday focus pattern",
                    "Schedule meetings in afternoon blocks",
                    "Increase break frequency (only 18 breaks total)"
                ],
                "weekly_productivity_score": 72,
                "trends": {
                    "focus_time": "stable",
                    "meeting_load": "increasing",
                    "context_switches": "stable"
                },
                "achievements": [
                    "Completed major feature ahead of schedule",
                    "Maintained consistent morning deep work",
                    "Reduced context switches by 15%"
                ]
            }
        }
    }


if DSPY_AVAILABLE:
    class WeeklyRetroSignature(dspy.Signature):
        """Generate comprehensive weekly retrospective from daily summaries and metrics.

        Synthesize a week's worth of daily activity summaries and metrics into a
        coherent narrative with insights on work patterns, focus time, goal progress,
        and opportunities for improvement.
        """

        # Input fields
        total_focus_time: float = dspy.InputField(
            desc="Total deep focus time for the week (hours)"
        )
        total_meeting_hours: float = dspy.InputField(
            desc="Total time spent in meetings (hours)"
        )
        avg_context_switches: float = dspy.InputField(
            desc="Average context switches per day"
        )
        daily_summaries: str = dspy.InputField(
            desc="Daily summary texts joined with newlines"
        )
        daily_productivity_scores: str = dspy.InputField(
            desc="Comma-separated daily productivity scores"
        )
        goals: str = dspy.InputField(
            desc="User-defined weekly goals (comma-separated)"
        )

        # Output fields
        narrative: str = dspy.OutputField(
            desc="Comprehensive 3-5 paragraph weekly narrative covering key activities, patterns, and insights"
        )
        patterns: str = dspy.OutputField(
            desc="Multi-day patterns and trends observed (bullet points)"
        )
        progress_on_goals: str = dspy.OutputField(
            desc="Assessment of each goal's completion status"
        )
        recommendations: str = dspy.OutputField(
            desc="5-7 strategic recommendations for improving next week"
        )
        weekly_productivity_score: int = dspy.OutputField(
            desc="Overall weekly productivity score (0-100)"
        )


class WeeklyRetroModule:
    """Module for generating weekly retrospectives using DSPy or fallback logic."""

    def __init__(self, use_llm: bool = True, temperature: float = 0.7):
        """Initialize weekly retrospective module.

        Args:
            use_llm: Whether to use LLM (DSPy) or fallback to rule-based
            temperature: LLM temperature for generation (0.0-1.0)
        """
        self.use_llm = use_llm and DSPY_AVAILABLE
        self.temperature = temperature

        if self.use_llm:
            self.predictor = dspy.ChainOfThought(WeeklyRetroSignature)
            logger.info("WeeklyRetroModule initialized with DSPy")
        else:
            logger.info("WeeklyRetroModule initialized with fallback (no LLM)")

    def _fallback_generate(self, input_data: WeeklyRetroInput) -> WeeklyRetroOutput:
        """Generate retrospective using rule-based logic (no LLM required).

        Args:
            input_data: Weekly aggregated metrics and summaries

        Returns:
            WeeklyRetroOutput with structured insights
        """
        # Calculate weekly productivity score
        weekly_score = self._calculate_weekly_score(input_data)

        # Generate narrative
        avg_daily_focus = input_data.total_focus_time / 7
        avg_daily_meetings = input_data.total_meeting_hours / 7

        narrative = (
            f"Week of {input_data.week_start.strftime('%B %d')} - "
            f"{input_data.week_end.strftime('%B %d, %Y')}\n\n"
            f"This week accumulated {input_data.total_screen_time:.1f} hours of screen time "
            f"with {input_data.total_focus_time:.1f} hours of deep focus work "
            f"(averaging {avg_daily_focus:.1f}h per day). "
            f"Meeting load was {input_data.total_meeting_hours:.1f} hours across the week "
            f"({avg_daily_meetings:.1f}h daily average). "
            f"Context switching averaged {input_data.avg_context_switches:.1f} switches per day.\n\n"
        )

        if input_data.top_apps_weekly:
            top_app = max(input_data.top_apps_weekly.items(), key=lambda x: x[1])
            narrative += (
                f"Primary tool usage was {top_app[0]} at {top_app[1]:.1f} hours, "
                f"indicating focused development work. "
            )

        # Detect patterns
        patterns = self._detect_weekly_patterns(input_data)

        # Assess goal progress
        progress_on_goals = {}
        for goal in input_data.goals:
            # Simple heuristic: check if keywords appear in daily summaries
            mentions = sum(1 for summary in input_data.daily_summaries if goal.lower() in summary.lower())
            if mentions >= 3:
                progress_on_goals[goal] = "Strong progress - mentioned in multiple daily summaries"
            elif mentions >= 1:
                progress_on_goals[goal] = "Some progress - mentioned in summaries"
            else:
                progress_on_goals[goal] = "Limited progress - not clearly reflected in daily activities"

        # Generate recommendations
        recommendations = self._generate_recommendations(input_data)

        # Analyze trends
        trends = self._analyze_trends(input_data)

        # Identify achievements
        achievements = []
        if input_data.total_focus_time > 15:
            achievements.append(f"Maintained strong focus time ({input_data.total_focus_time:.1f}h)")
        if avg_daily_focus > 2.5:
            achievements.append("Exceeded 2.5h daily focus time average")
        if input_data.avg_context_switches < 15:
            achievements.append("Kept context switching under control")

        # Metrics summary
        metrics_summary = {
            "total_screen_time": input_data.total_screen_time,
            "total_focus_time": input_data.total_focus_time,
            "avg_daily_focus": avg_daily_focus,
            "total_meeting_hours": input_data.total_meeting_hours,
            "avg_daily_meetings": avg_daily_meetings,
            "avg_context_switches": input_data.avg_context_switches,
            "total_breaks": input_data.total_breaks,
            "productivity_trend": trends.get("overall", "stable")
        }

        return WeeklyRetroOutput(
            narrative=narrative,
            metrics_summary=metrics_summary,
            patterns=patterns,
            progress_on_goals=progress_on_goals,
            recommendations=recommendations,
            weekly_productivity_score=weekly_score,
            trends=trends,
            achievements=achievements
        )

    def _calculate_weekly_score(self, input_data: WeeklyRetroInput) -> int:
        """Calculate overall weekly productivity score.

        Args:
            input_data: Weekly metrics

        Returns:
            Productivity score (0-100)
        """
        if not input_data.daily_productivity_scores:
            return 50

        # Average of daily scores with adjustments
        avg_score = sum(input_data.daily_productivity_scores) / len(input_data.daily_productivity_scores)

        # Bonus for consistent high performance
        consistency_bonus = 0
        if all(score >= 70 for score in input_data.daily_productivity_scores):
            consistency_bonus = 5
        elif all(score >= 60 for score in input_data.daily_productivity_scores):
            consistency_bonus = 3

        return int(min(100, avg_score + consistency_bonus))

    def _detect_weekly_patterns(self, input_data: WeeklyRetroInput) -> list[str]:
        """Detect multi-day patterns from weekly data.

        Args:
            input_data: Weekly metrics

        Returns:
            List of detected patterns
        """
        patterns = []

        # Focus time pattern
        avg_daily_focus = input_data.total_focus_time / 7
        if avg_daily_focus > 2.5:
            patterns.append("Strong daily focus time averaging >2.5h")
        elif avg_daily_focus < 1.5:
            patterns.append("Limited focus time - consider blocking dedicated work periods")

        # Meeting pattern
        avg_daily_meetings = input_data.total_meeting_hours / 7
        if avg_daily_meetings > 3:
            patterns.append("Heavy meeting load - may be impacting focus time")
        elif avg_daily_meetings < 1:
            patterns.append("Light meeting schedule - good for deep work")

        # Context switching
        if input_data.avg_context_switches > 20:
            patterns.append("High context switching throughout week")
        elif input_data.avg_context_switches < 10:
            patterns.append("Excellent focus with minimal context switching")

        # Productivity trend
        if len(input_data.daily_productivity_scores) >= 3:
            first_half = input_data.daily_productivity_scores[:3]
            second_half = input_data.daily_productivity_scores[3:]
            if sum(second_half) > sum(first_half):
                patterns.append("Productivity improved in second half of week")
            elif sum(first_half) > sum(second_half):
                patterns.append("Stronger start to week - energy declined later")

        return patterns

    def _generate_recommendations(self, input_data: WeeklyRetroInput) -> list[str]:
        """Generate strategic recommendations for next week.

        Args:
            input_data: Weekly metrics

        Returns:
            List of actionable recommendations
        """
        recommendations = []

        # Focus time recommendations
        avg_daily_focus = input_data.total_focus_time / 7
        if avg_daily_focus < 2:
            recommendations.append("Schedule 2-3 hour focus blocks daily")

        # Meeting recommendations
        avg_daily_meetings = input_data.total_meeting_hours / 7
        if avg_daily_meetings > 3:
            recommendations.append("Audit meetings - consider declining or delegating low-value calls")

        # Context switching
        if input_data.avg_context_switches > 15:
            recommendations.append("Batch similar tasks together to reduce context switches")

        # Break recommendations
        avg_breaks_per_day = input_data.total_breaks / 7
        if avg_breaks_per_day < 3:
            recommendations.append("Increase break frequency - aim for 3-4 breaks per day")

        # Goal-based recommendations
        if input_data.goals:
            recommendations.append("Review weekly goals on Monday and Friday to track progress")

        # General recommendations
        recommendations.append("Identify your peak focus hours and protect them from meetings")

        return recommendations[:7]  # Limit to top 7

    def _analyze_trends(self, input_data: WeeklyRetroInput) -> dict[str, str]:
        """Analyze trends across different categories.

        Args:
            input_data: Weekly metrics

        Returns:
            Dictionary of trend assessments
        """
        trends = {}

        # Productivity trend
        if len(input_data.daily_productivity_scores) >= 3:
            first_half = sum(input_data.daily_productivity_scores[:3]) / 3
            second_half = sum(input_data.daily_productivity_scores[3:]) / max(1, len(input_data.daily_productivity_scores[3:]))

            if second_half > first_half + 5:
                trends["overall"] = "improving"
            elif first_half > second_half + 5:
                trends["overall"] = "declining"
            else:
                trends["overall"] = "stable"

        # Focus time trend (simplified - would need historical data for real trend)
        avg_daily_focus = input_data.total_focus_time / 7
        trends["focus_time"] = "excellent" if avg_daily_focus > 3 else "good" if avg_daily_focus > 2 else "needs improvement"

        # Meeting load trend
        avg_daily_meetings = input_data.total_meeting_hours / 7
        trends["meeting_load"] = "high" if avg_daily_meetings > 3 else "moderate" if avg_daily_meetings > 1.5 else "low"

        # Context switching
        trends["context_switches"] = "high" if input_data.avg_context_switches > 20 else "moderate" if input_data.avg_context_switches > 10 else "low"

        return trends

    def generate(self, input_data: WeeklyRetroInput) -> WeeklyRetroOutput:
        """Generate weekly retrospective from aggregated data.

        Args:
            input_data: Weekly metrics and daily summaries

        Returns:
            WeeklyRetroOutput with comprehensive retrospective
        """
        with tracer.start_as_current_span("weekly_retro.generate") as span:
            span.set_attribute("use_llm", self.use_llm)
            span.set_attribute("days_included", len(input_data.daily_summaries))
            span.set_attribute("total_focus_time", input_data.total_focus_time)

            try:
                if self.use_llm:
                    return self._llm_generate(input_data)
                else:
                    return self._fallback_generate(input_data)
            except Exception as e:
                logger.warning(f"LLM generation failed, using fallback: {e}")
                span.set_attribute("fallback_used", True)
                return self._fallback_generate(input_data)

    def _llm_generate(self, input_data: WeeklyRetroInput) -> WeeklyRetroOutput:
        """Generate retrospective using DSPy LLM.

        Args:
            input_data: Weekly metrics and summaries

        Returns:
            WeeklyRetroOutput with LLM-generated insights
        """
        # Prepare inputs for DSPy
        daily_summaries_str = "\n".join(input_data.daily_summaries)
        scores_str = ",".join(map(str, input_data.daily_productivity_scores))
        goals_str = ", ".join(input_data.goals) if input_data.goals else "No specific goals set"

        # Invoke DSPy predictor
        result = self.predictor(
            total_focus_time=input_data.total_focus_time,
            total_meeting_hours=input_data.total_meeting_hours,
            avg_context_switches=input_data.avg_context_switches,
            daily_summaries=daily_summaries_str,
            daily_productivity_scores=scores_str,
            goals=goals_str
        )

        # Parse outputs
        patterns = [p.strip() for p in result.patterns.split("\n") if p.strip()]
        recommendations = [r.strip() for r in result.recommendations.split("\n") if r.strip()]

        # Parse goal progress
        progress_on_goals = {}
        for line in result.progress_on_goals.split("\n"):
            if ":" in line:
                goal, status = line.split(":", 1)
                progress_on_goals[goal.strip()] = status.strip()

        # Calculate trends and achievements using fallback logic
        trends = self._analyze_trends(input_data)
        achievements = []
        if input_data.total_focus_time > 15:
            achievements.append(f"Maintained {input_data.total_focus_time:.1f}h of focus time")

        # Metrics summary
        metrics_summary = {
            "total_screen_time": input_data.total_screen_time,
            "total_focus_time": input_data.total_focus_time,
            "avg_daily_focus": input_data.total_focus_time / 7,
            "total_meeting_hours": input_data.total_meeting_hours,
        }

        return WeeklyRetroOutput(
            narrative=result.narrative,
            metrics_summary=metrics_summary,
            patterns=patterns[:7],
            progress_on_goals=progress_on_goals,
            recommendations=recommendations[:7],
            weekly_productivity_score=int(result.weekly_productivity_score),
            trends=trends,
            achievements=achievements
        )

    async def generate_async(self, input_data: WeeklyRetroInput) -> WeeklyRetroOutput:
        """Async version of generate.

        Args:
            input_data: Weekly metrics and summaries

        Returns:
            WeeklyRetroOutput with retrospective
        """
        return await asyncio.to_thread(self.generate, input_data)


# Example usage
if __name__ == "__main__":
    from datetime import datetime

    example_input = WeeklyRetroInput(
        week_start=datetime(2024, 11, 18),
        week_end=datetime(2024, 11, 24),
        total_screen_time=45.2,
        total_focus_time=18.5,
        total_meeting_hours=12.3,
        avg_context_switches=16.2,
        daily_summaries=[
            "Monday: Heavy coding day with 3.2h focus time",
            "Tuesday: Meeting-heavy with 5 calls",
            "Wednesday: Balanced work with good focus",
            "Thursday: Code reviews and documentation",
            "Friday: Sprint planning and retrospective"
        ],
        daily_productivity_scores=[75, 65, 80, 70, 72],
        top_apps_weekly={"VSCode": 15.2, "Safari": 8.5, "Slack": 6.3},
        top_domains_weekly={"github.com": 85, "stackoverflow.com": 42},
        total_breaks=18,
        goals=["Complete feature X", "Review 10 PRs", "Reduce meeting time"]
    )

    module = WeeklyRetroModule(use_llm=False)
    output = module.generate(example_input)

    print("Weekly Retrospective:")
    print(f"Score: {output.weekly_productivity_score}")
    print(f"\nNarrative:\n{output.narrative}")
    print(f"\nPatterns: {output.patterns}")
    print(f"\nRecommendations: {output.recommendations}")

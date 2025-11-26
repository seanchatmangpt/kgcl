"""Daily Brief Signature for KGCL.

Generates concise daily summaries from activity metrics, highlighting key patterns,
insights, and recommendations for productivity and wellbeing.
"""

import asyncio
import logging
from typing import Any

from pydantic import BaseModel, Field

try:
    import dspy

    DSPY_AVAILABLE = True
except ImportError:
    DSPY_AVAILABLE = False

from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


# Input/Output Models using Pydantic V2
class DailyBriefInput(BaseModel):
    """Input features for daily brief generation.

    Attributes
    ----------
        time_in_app: Total time spent in various applications (hours)
        domain_visits: Number of unique domains visited
        calendar_busy_hours: Hours spent in calendar events/meetings
        context_switches: Number of application/context switches
        focus_time: Continuous uninterrupted work periods (hours)
        screen_time: Total screen time (hours)
        top_apps: Most used applications and their durations
        top_domains: Most visited domains
        meeting_count: Number of meetings attended
        break_intervals: Number of breaks taken
    """

    time_in_app: float = Field(..., ge=0, description="Total app usage time in hours")
    domain_visits: int = Field(..., ge=0, description="Unique domains visited")
    calendar_busy_hours: float = Field(..., ge=0, description="Hours in meetings")
    context_switches: int = Field(..., ge=0, description="Context switch count")
    focus_time: float = Field(..., ge=0, description="Deep focus time in hours")
    screen_time: float = Field(..., ge=0, description="Total screen time in hours")
    top_apps: dict[str, float] = Field(default_factory=dict, description="App names to usage hours mapping")
    top_domains: dict[str, int] = Field(default_factory=dict, description="Domain names to visit counts mapping")
    meeting_count: int = Field(..., ge=0, description="Number of meetings")
    break_intervals: int = Field(..., ge=0, description="Number of breaks")

    model_config = {
        "json_schema_extra": {
            "example": {
                "time_in_app": 3.2,
                "domain_visits": 28,
                "calendar_busy_hours": 4.5,
                "context_switches": 14,
                "focus_time": 2.1,
                "screen_time": 8.5,
                "top_apps": {"VSCode": 2.5, "Safari": 1.8, "Slack": 0.9},
                "top_domains": {"github.com": 12, "stackoverflow.com": 8, "docs.python.org": 5},
                "meeting_count": 6,
                "break_intervals": 3,
            }
        }
    }


class DailyBriefOutput(BaseModel):
    """Output summary and insights from daily brief.

    Attributes
    ----------
        summary: Concise overview of the day's activities (1-2 sentences)
        highlights: Key notable activities or achievements
        patterns: Observed behavioral patterns (e.g., peak focus times)
        recommendations: Actionable suggestions for improvement
        productivity_score: Estimated productivity score (0-100)
        wellbeing_indicators: Work-life balance and health indicators
    """

    summary: str = Field(..., description="Brief summary of the day")
    highlights: list[str] = Field(default_factory=list, description="Key achievements or notable activities")
    patterns: list[str] = Field(default_factory=list, description="Observed behavioral patterns")
    recommendations: list[str] = Field(default_factory=list, description="Actionable improvement suggestions")
    productivity_score: int = Field(default=0, ge=0, le=100, description="Productivity estimate (0-100)")
    wellbeing_indicators: dict[str, Any] = Field(default_factory=dict, description="Health and balance indicators")

    model_config = {
        "json_schema_extra": {
            "example": {
                "summary": "Focused coding day with 3.2h in editor across 14 context switches. Attended 6 meetings (4.5h total).",
                "highlights": [
                    "2.1 hours of deep focus time",
                    "Visited 28 unique domains for research",
                    "Balanced code and meetings effectively",
                ],
                "patterns": [
                    "Morning deep work (9-11am)",
                    "Afternoon meeting cluster (2-5pm)",
                    "High context switching during coding",
                ],
                "recommendations": [
                    "Schedule fewer meetings to preserve focus time",
                    "Batch similar tasks to reduce context switches",
                    "Take more frequent breaks (only 3 today)",
                ],
                "productivity_score": 75,
                "wellbeing_indicators": {"focus_quality": "good", "meeting_load": "high", "break_frequency": "low"},
            }
        }
    }


# DSPy Signature (only available if dspy-ai is installed)
if DSPY_AVAILABLE:

    class DailyBriefSignature(dspy.Signature):
        """Generate a concise daily activity brief from usage metrics.

        Given a day's worth of activity metrics (app usage, meetings, context switches,
        focus time), generate a brief summary highlighting key patterns, achievements,
        and actionable recommendations for improving productivity and wellbeing.
        """

        # Input fields
        time_in_app: float = dspy.InputField(desc="Total time spent in applications (hours)")
        domain_visits: int = dspy.InputField(desc="Number of unique domains visited")
        calendar_busy_hours: float = dspy.InputField(desc="Hours spent in calendar events/meetings")
        context_switches: int = dspy.InputField(desc="Number of application/context switches")
        focus_time: float = dspy.InputField(desc="Continuous uninterrupted work time (hours)")
        screen_time: float = dspy.InputField(desc="Total screen time (hours)")
        meeting_count: int = dspy.InputField(desc="Number of meetings attended")

        # Output fields
        summary: str = dspy.OutputField(desc="Concise 1-2 sentence overview of the day's activities")
        highlights: str = dspy.OutputField(desc="Key achievements and notable activities (bullet points)")
        patterns: str = dspy.OutputField(desc="Observed behavioral patterns (e.g., peak focus times, meeting clusters)")
        recommendations: str = dspy.OutputField(
            desc="3-5 actionable suggestions for improving productivity and wellbeing"
        )
        productivity_score: int = dspy.OutputField(
            desc="Productivity estimate from 0-100 based on focus time, context switches, and meeting load"
        )


class DailyBriefModule:
    """Module for generating daily activity briefs using DSPy or fallback logic."""

    def __init__(self, use_llm: bool = True, temperature: float = 0.7):
        """Initialize daily brief module.

        Args:
            use_llm: Whether to use LLM (DSPy) or fallback to rule-based
            temperature: LLM temperature for generation (0.0-1.0)
        """
        self.use_llm = use_llm and DSPY_AVAILABLE
        self.temperature = temperature

        if self.use_llm:
            self.predictor = dspy.ChainOfThought(DailyBriefSignature)
            logger.info("DailyBriefModule initialized with DSPy")
        else:
            logger.info("DailyBriefModule initialized with fallback (no LLM)")

    def _fallback_generate(self, input_data: DailyBriefInput) -> DailyBriefOutput:
        """Generate brief using rule-based logic (no LLM required).

        Args:
            input_data: Daily activity metrics

        Returns
        -------
            DailyBriefOutput with structured insights
        """
        # Calculate productivity score
        productivity_score = self._calculate_productivity_score(input_data)

        # Generate summary
        summary = (
            f"Spent {input_data.time_in_app:.1f}h in apps with "
            f"{input_data.context_switches} context switches. "
            f"Had {input_data.meeting_count} meetings ({input_data.calendar_busy_hours:.1f}h total). "
            f"Visited {input_data.domain_visits} unique domains."
        )

        # Extract highlights
        highlights = []
        if input_data.focus_time > 2.0:
            highlights.append(f"{input_data.focus_time:.1f} hours of quality focus time")
        if input_data.top_apps:
            top_app = max(input_data.top_apps.items(), key=lambda x: x[1])
            highlights.append(f"Primarily used {top_app[0]} ({top_app[1]:.1f}h)")
        if input_data.meeting_count > 0:
            highlights.append(f"Attended {input_data.meeting_count} meetings")

        # Detect patterns
        patterns = []
        if input_data.context_switches > 20:
            patterns.append("High context switching detected - may impact deep work")
        if input_data.calendar_busy_hours > 4:
            patterns.append("Heavy meeting load - limited focus time")
        if input_data.focus_time < 2:
            patterns.append("Limited continuous focus periods")

        # Generate recommendations
        recommendations = []
        if input_data.context_switches > 15:
            recommendations.append("Batch similar tasks to reduce context switches")
        if input_data.break_intervals < 3:
            recommendations.append("Take more frequent breaks (aim for 1 per 2 hours)")
        if input_data.calendar_busy_hours > 4:
            recommendations.append("Consider reducing meeting load to preserve focus time")
        if input_data.focus_time < 2:
            recommendations.append("Schedule dedicated focus blocks without interruptions")

        # Wellbeing indicators
        wellbeing = {
            "focus_quality": "excellent"
            if input_data.focus_time > 3
            else "good"
            if input_data.focus_time > 2
            else "needs improvement",
            "meeting_load": "high"
            if input_data.calendar_busy_hours > 4
            else "moderate"
            if input_data.calendar_busy_hours > 2
            else "low",
            "break_frequency": "good" if input_data.break_intervals >= 3 else "low",
            "context_switching": "high"
            if input_data.context_switches > 20
            else "moderate"
            if input_data.context_switches > 10
            else "low",
        }

        return DailyBriefOutput(
            summary=summary,
            highlights=highlights,
            patterns=patterns,
            recommendations=recommendations,
            productivity_score=productivity_score,
            wellbeing_indicators=wellbeing,
        )

    def _calculate_productivity_score(self, input_data: DailyBriefInput) -> int:
        """Calculate productivity score based on metrics.

        Args:
            input_data: Daily activity metrics

        Returns
        -------
            Productivity score (0-100)
        """
        score = 50  # Base score

        # Positive factors
        score += min(30, int(input_data.focus_time * 10))  # Up to +30 for focus time
        score += min(10, int(input_data.break_intervals * 3))  # Up to +10 for breaks

        # Negative factors
        score -= min(20, int(input_data.context_switches / 2))  # -1 per 2 switches, max -20
        score -= min(15, int(max(0, input_data.calendar_busy_hours - 3) * 3))  # Penalty for >3h meetings

        return max(0, min(100, score))

    def generate(self, input_data: DailyBriefInput) -> DailyBriefOutput:
        """Generate daily brief from activity metrics.

        Args:
            input_data: Daily activity metrics

        Returns
        -------
            DailyBriefOutput with summary and insights
        """
        with tracer.start_as_current_span("daily_brief.generate") as span:
            span.set_attribute("use_llm", self.use_llm)
            span.set_attribute("context_switches", input_data.context_switches)
            span.set_attribute("meeting_count", input_data.meeting_count)

            try:
                if self.use_llm:
                    return self._llm_generate(input_data)
                return self._fallback_generate(input_data)
            except Exception as e:
                logger.warning(f"LLM generation failed, using fallback: {e}")
                span.set_attribute("fallback_used", True)
                return self._fallback_generate(input_data)

    def _llm_generate(self, input_data: DailyBriefInput) -> DailyBriefOutput:
        """Generate brief using DSPy LLM.

        Args:
            input_data: Daily activity metrics

        Returns
        -------
            DailyBriefOutput with LLM-generated insights
        """
        # Invoke DSPy predictor
        result = self.predictor(
            time_in_app=input_data.time_in_app,
            domain_visits=input_data.domain_visits,
            calendar_busy_hours=input_data.calendar_busy_hours,
            context_switches=input_data.context_switches,
            focus_time=input_data.focus_time,
            screen_time=input_data.screen_time,
            meeting_count=input_data.meeting_count,
        )

        # Parse LLM output into structured format
        highlights = [h.strip() for h in result.highlights.split("\n") if h.strip()]
        patterns = [p.strip() for p in result.patterns.split("\n") if p.strip()]
        recommendations = [r.strip() for r in result.recommendations.split("\n") if r.strip()]

        # Calculate wellbeing indicators
        wellbeing = {
            "focus_quality": "excellent"
            if input_data.focus_time > 3
            else "good"
            if input_data.focus_time > 2
            else "needs improvement",
            "meeting_load": "high" if input_data.calendar_busy_hours > 4 else "moderate",
            "break_frequency": "good" if input_data.break_intervals >= 3 else "low",
        }

        return DailyBriefOutput(
            summary=result.summary,
            highlights=highlights[:5],  # Limit to top 5
            patterns=patterns[:5],
            recommendations=recommendations[:5],
            productivity_score=int(result.productivity_score),
            wellbeing_indicators=wellbeing,
        )

    async def generate_async(self, input_data: DailyBriefInput) -> DailyBriefOutput:
        """Async version of generate.

        Args:
            input_data: Daily activity metrics

        Returns
        -------
            DailyBriefOutput with summary and insights
        """
        return await asyncio.to_thread(self.generate, input_data)


# Example usage
if __name__ == "__main__":
    # Example input data
    example_input = DailyBriefInput(
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

    # Generate brief (will use fallback if DSPy not available)
    module = DailyBriefModule(use_llm=False)
    output = module.generate(example_input)

    print("Daily Brief:")
    print(f"Summary: {output.summary}")
    print(f"Productivity Score: {output.productivity_score}")
    print(f"Highlights: {output.highlights}")
    print(f"Patterns: {output.patterns}")
    print(f"Recommendations: {output.recommendations}")

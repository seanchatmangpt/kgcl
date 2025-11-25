"""Wellbeing Signature for KGCL.

Analyzes work-life balance, health indicators, and provides wellbeing
recommendations based on screen time, focus quality, and break patterns.
"""

from typing import Any, Literal
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


class WellbeingInput(BaseModel):
    """Input features for wellbeing analysis.

    Attributes:
        screen_time: Total screen time in hours
        focus_time: Deep focus time in hours
        meeting_time: Time spent in meetings (hours)
        break_intervals: Number of breaks taken
        context_switches: Number of context switches
        work_hours: Total work hours
        after_hours_time: Time spent working after hours
        weekend_work_time: Weekend work time (hours)
        physical_activity: Physical activity time (hours, optional)
    """

    screen_time: float = Field(..., ge=0, description="Total screen time (hours)")
    focus_time: float = Field(..., ge=0, description="Deep focus time (hours)")
    meeting_time: float = Field(..., ge=0, description="Meeting time (hours)")
    break_intervals: int = Field(..., ge=0, description="Number of breaks taken")
    context_switches: int = Field(..., ge=0, description="Context switch count")
    work_hours: float = Field(..., ge=0, description="Total work hours")
    after_hours_time: float = Field(
        default=0,
        ge=0,
        description="After-hours work time (hours)"
    )
    weekend_work_time: float = Field(
        default=0,
        ge=0,
        description="Weekend work time (hours)"
    )
    physical_activity: float = Field(
        default=0,
        ge=0,
        description="Physical activity time (hours, optional)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "screen_time": 8.5,
                "focus_time": 2.1,
                "meeting_time": 4.5,
                "break_intervals": 3,
                "context_switches": 14,
                "work_hours": 9.2,
                "after_hours_time": 1.5,
                "weekend_work_time": 0,
                "physical_activity": 0.5
            }
        }
    }


class WellbeingOutput(BaseModel):
    """Output wellbeing analysis and recommendations.

    Attributes:
        wellbeing_score: Overall wellbeing score (0-100)
        work_life_balance: Work-life balance assessment
        focus_quality: Focus quality indicators
        break_patterns: Break frequency and quality
        health_indicators: Physical and mental health signals
        recommendations: Wellbeing improvement recommendations
        risk_factors: Identified risk factors (burnout, overwork, etc.)
        positive_factors: Positive wellbeing indicators
    """

    wellbeing_score: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Overall wellbeing score (0-100)"
    )
    work_life_balance: dict[str, Any] = Field(
        default_factory=dict,
        description="Work-life balance metrics"
    )
    focus_quality: dict[str, Any] = Field(
        default_factory=dict,
        description="Focus and concentration quality"
    )
    break_patterns: dict[str, Any] = Field(
        default_factory=dict,
        description="Break frequency and quality"
    )
    health_indicators: dict[str, str] = Field(
        default_factory=dict,
        description="Health signal indicators"
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Wellbeing recommendations"
    )
    risk_factors: list[str] = Field(
        default_factory=list,
        description="Identified risk factors"
    )
    positive_factors: list[str] = Field(
        default_factory=list,
        description="Positive wellbeing indicators"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "wellbeing_score": 68,
                "work_life_balance": {
                    "assessment": "needs_attention",
                    "after_hours_ratio": 0.16,
                    "weekend_work": False
                },
                "focus_quality": {
                    "rating": "moderate",
                    "focus_ratio": 0.25,
                    "interruption_rate": "high"
                },
                "break_patterns": {
                    "frequency": "low",
                    "breaks_per_hour": 0.35,
                    "recommended_breaks": 6
                },
                "health_indicators": {
                    "screen_time": "high",
                    "physical_activity": "low",
                    "stress_signals": "moderate"
                },
                "recommendations": [
                    "Take more frequent breaks (aim for 1 every 90 minutes)",
                    "Reduce after-hours work to improve work-life balance",
                    "Consider implementing Pomodoro technique for better focus"
                ],
                "risk_factors": [
                    "High screen time (8.5h) without sufficient breaks",
                    "After-hours work detected (1.5h)"
                ],
                "positive_factors": [
                    "No weekend work - good boundary setting",
                    "Some physical activity tracked"
                ]
            }
        }
    }


if DSPY_AVAILABLE:
    class WellbeingSignature(dspy.Signature):
        """Analyze wellbeing indicators and provide health recommendations.

        Given work metrics (screen time, focus, meetings, breaks), assess work-life
        balance, identify health risks, and provide actionable wellbeing recommendations.
        """

        # Input fields
        screen_time: float = dspy.InputField(desc="Total screen time (hours)")
        focus_time: float = dspy.InputField(desc="Deep focus time (hours)")
        meeting_time: float = dspy.InputField(desc="Meeting time (hours)")
        break_intervals: int = dspy.InputField(desc="Number of breaks taken")
        context_switches: int = dspy.InputField(desc="Context switch count")
        work_hours: float = dspy.InputField(desc="Total work hours")
        after_hours_time: float = dspy.InputField(desc="After-hours work (hours)")

        # Output fields
        wellbeing_score: int = dspy.OutputField(
            desc="Overall wellbeing score 0-100 based on all indicators"
        )
        work_life_balance: str = dspy.OutputField(
            desc="Work-life balance assessment: excellent, good, needs_attention, or poor"
        )
        health_indicators: str = dspy.OutputField(
            desc="Key health signals and concerns (bullet points)"
        )
        recommendations: str = dspy.OutputField(
            desc="5-7 actionable wellbeing recommendations prioritized by impact"
        )
        risk_factors: str = dspy.OutputField(
            desc="Identified risk factors for burnout, stress, or health issues"
        )


class WellbeingModule:
    """Module for analyzing wellbeing and health indicators."""

    def __init__(self, use_llm: bool = True, temperature: float = 0.7):
        """Initialize wellbeing module.

        Args:
            use_llm: Whether to use LLM (DSPy) or fallback to heuristics
            temperature: LLM temperature for generation (0.0-1.0)
        """
        self.use_llm = use_llm and DSPY_AVAILABLE
        self.temperature = temperature

        if self.use_llm:
            self.predictor = dspy.ChainOfThought(WellbeingSignature)
            logger.info("WellbeingModule initialized with DSPy")
        else:
            logger.info("WellbeingModule initialized with fallback (heuristics)")

    def _calculate_wellbeing_score(self, input_data: WellbeingInput) -> int:
        """Calculate overall wellbeing score.

        Args:
            input_data: Wellbeing metrics

        Returns:
            Wellbeing score (0-100)
        """
        score = 70  # Base score (neutral)

        # Positive factors
        if input_data.break_intervals >= 4:
            score += 10
        elif input_data.break_intervals >= 3:
            score += 5

        if input_data.focus_time >= 2 and input_data.context_switches < 15:
            score += 10  # Good focus quality

        if input_data.after_hours_time == 0:
            score += 5  # Good boundaries

        if input_data.weekend_work_time == 0:
            score += 5  # Good boundaries

        if input_data.physical_activity > 0:
            score += 5  # Physical activity tracked

        # Negative factors
        if input_data.screen_time > 10:
            score -= 15  # Excessive screen time
        elif input_data.screen_time > 8:
            score -= 10

        if input_data.break_intervals < 2:
            score -= 10  # Insufficient breaks

        if input_data.after_hours_time > 2:
            score -= 10  # Significant after-hours work
        elif input_data.after_hours_time > 0:
            score -= 5

        if input_data.weekend_work_time > 0:
            score -= 10  # Weekend work

        if input_data.context_switches > 20:
            score -= 10  # High stress from switching

        if input_data.meeting_time > 5:
            score -= 5  # Meeting overload

        return max(0, min(100, score))

    def _assess_work_life_balance(self, input_data: WellbeingInput) -> dict[str, Any]:
        """Assess work-life balance.

        Args:
            input_data: Wellbeing metrics

        Returns:
            Work-life balance assessment
        """
        total_time = input_data.work_hours + input_data.after_hours_time
        after_hours_ratio = input_data.after_hours_time / max(1, total_time)

        # Determine assessment
        if input_data.weekend_work_time > 0 or after_hours_ratio > 0.2:
            assessment = "poor"
        elif after_hours_ratio > 0.1 or input_data.work_hours > 10:
            assessment = "needs_attention"
        elif after_hours_ratio < 0.05 and input_data.work_hours < 9:
            assessment = "excellent"
        else:
            assessment = "good"

        return {
            "assessment": assessment,
            "total_work_time": total_time,
            "after_hours_ratio": round(after_hours_ratio, 2),
            "weekend_work": input_data.weekend_work_time > 0,
            "work_hours_category": "long" if input_data.work_hours > 9 else "standard" if input_data.work_hours > 7 else "short"
        }

    def _assess_focus_quality(self, input_data: WellbeingInput) -> dict[str, Any]:
        """Assess focus and concentration quality.

        Args:
            input_data: Wellbeing metrics

        Returns:
            Focus quality assessment
        """
        focus_ratio = input_data.focus_time / max(1, input_data.work_hours)

        # Determine rating
        if focus_ratio > 0.4 and input_data.context_switches < 10:
            rating = "excellent"
        elif focus_ratio > 0.25 and input_data.context_switches < 15:
            rating = "good"
        elif focus_ratio > 0.15 or input_data.context_switches < 20:
            rating = "moderate"
        else:
            rating = "poor"

        # Interruption rate
        if input_data.context_switches > 20:
            interruption_rate = "very_high"
        elif input_data.context_switches > 15:
            interruption_rate = "high"
        elif input_data.context_switches > 10:
            interruption_rate = "moderate"
        else:
            interruption_rate = "low"

        return {
            "rating": rating,
            "focus_ratio": round(focus_ratio, 2),
            "focus_hours": input_data.focus_time,
            "interruption_rate": interruption_rate,
            "context_switches": input_data.context_switches
        }

    def _assess_break_patterns(self, input_data: WellbeingInput) -> dict[str, Any]:
        """Assess break frequency and quality.

        Args:
            input_data: Wellbeing metrics

        Returns:
            Break pattern assessment
        """
        breaks_per_hour = input_data.break_intervals / max(1, input_data.work_hours)
        recommended_breaks = max(3, int(input_data.work_hours / 2))  # 1 break per 2 hours

        # Frequency assessment
        if input_data.break_intervals >= recommended_breaks:
            frequency = "good"
        elif input_data.break_intervals >= recommended_breaks - 1:
            frequency = "moderate"
        else:
            frequency = "low"

        return {
            "frequency": frequency,
            "total_breaks": input_data.break_intervals,
            "breaks_per_hour": round(breaks_per_hour, 2),
            "recommended_breaks": recommended_breaks,
            "deficit": max(0, recommended_breaks - input_data.break_intervals)
        }

    def _identify_health_indicators(self, input_data: WellbeingInput) -> dict[str, str]:
        """Identify health indicators and signals.

        Args:
            input_data: Wellbeing metrics

        Returns:
            Health indicator assessments
        """
        indicators = {}

        # Screen time
        if input_data.screen_time > 10:
            indicators["screen_time"] = "very_high"
        elif input_data.screen_time > 8:
            indicators["screen_time"] = "high"
        elif input_data.screen_time > 6:
            indicators["screen_time"] = "moderate"
        else:
            indicators["screen_time"] = "healthy"

        # Physical activity
        if input_data.physical_activity >= 1:
            indicators["physical_activity"] = "good"
        elif input_data.physical_activity > 0:
            indicators["physical_activity"] = "moderate"
        else:
            indicators["physical_activity"] = "low"

        # Stress signals (based on context switches and meeting load)
        stress_score = 0
        if input_data.context_switches > 20:
            stress_score += 2
        elif input_data.context_switches > 15:
            stress_score += 1

        if input_data.meeting_time > 5:
            stress_score += 2
        elif input_data.meeting_time > 3:
            stress_score += 1

        if input_data.break_intervals < 3:
            stress_score += 1

        if stress_score >= 4:
            indicators["stress_signals"] = "high"
        elif stress_score >= 2:
            indicators["stress_signals"] = "moderate"
        else:
            indicators["stress_signals"] = "low"

        # Work-life balance
        if input_data.after_hours_time > 2 or input_data.weekend_work_time > 0:
            indicators["boundary_health"] = "poor"
        elif input_data.after_hours_time > 0:
            indicators["boundary_health"] = "needs_improvement"
        else:
            indicators["boundary_health"] = "good"

        return indicators

    def _generate_recommendations(
        self,
        input_data: WellbeingInput,
        balance: dict[str, Any],
        focus: dict[str, Any],
        breaks: dict[str, Any],
        health: dict[str, str]
    ) -> list[str]:
        """Generate wellbeing recommendations.

        Args:
            input_data: Wellbeing metrics
            balance: Work-life balance assessment
            focus: Focus quality assessment
            breaks: Break pattern assessment
            health: Health indicators

        Returns:
            List of recommendations
        """
        recommendations = []

        # Break recommendations (high priority)
        if breaks["frequency"] in ["low", "moderate"]:
            recommendations.append(
                f"Take more frequent breaks - aim for {breaks['recommended_breaks']} breaks "
                f"(currently {breaks['total_breaks']}). Try the 90-minute ultradian rhythm pattern."
            )

        # Work-life balance recommendations
        if balance["assessment"] in ["poor", "needs_attention"]:
            if input_data.after_hours_time > 0:
                recommendations.append(
                    f"Reduce after-hours work ({input_data.after_hours_time:.1f}h detected). "
                    "Set clear work end times and protect personal time."
                )
            if input_data.weekend_work_time > 0:
                recommendations.append(
                    "Avoid weekend work to maintain healthy boundaries and prevent burnout."
                )

        # Screen time recommendations
        if health.get("screen_time") in ["very_high", "high"]:
            recommendations.append(
                f"High screen time ({input_data.screen_time:.1f}h). "
                "Apply 20-20-20 rule: every 20 min, look at something 20 feet away for 20 seconds."
            )

        # Focus quality recommendations
        if focus["rating"] in ["moderate", "poor"]:
            if focus["interruption_rate"] in ["high", "very_high"]:
                recommendations.append(
                    "Reduce context switching with time-blocking. "
                    "Group similar tasks and use 'do not disturb' during focus blocks."
                )
            recommendations.append(
                "Increase deep focus time with dedicated 2-hour focus blocks. "
                "Currently at {:.1f}h, aim for 3-4h daily.".format(input_data.focus_time)
            )

        # Physical activity
        if health.get("physical_activity") == "low":
            recommendations.append(
                "Incorporate physical activity - aim for 30-60 minutes daily. "
                "Short walks between tasks can boost energy and focus."
            )

        # Meeting load
        if input_data.meeting_time > 4:
            recommendations.append(
                f"High meeting load ({input_data.meeting_time:.1f}h). "
                "Audit meetings for necessity and consider async alternatives."
            )

        return recommendations[:7]  # Top 7 recommendations

    def _identify_risk_factors(self, input_data: WellbeingInput) -> list[str]:
        """Identify risk factors for burnout and health issues.

        Args:
            input_data: Wellbeing metrics

        Returns:
            List of risk factors
        """
        risks = []

        if input_data.screen_time > 10:
            risks.append(f"Very high screen time ({input_data.screen_time:.1f}h) - eye strain and fatigue risk")

        if input_data.break_intervals < 2:
            risks.append("Insufficient breaks - increased stress and reduced cognitive performance")

        if input_data.after_hours_time > 1.5:
            risks.append(f"Significant after-hours work ({input_data.after_hours_time:.1f}h) - work-life imbalance")

        if input_data.weekend_work_time > 0:
            risks.append("Weekend work detected - burnout risk from insufficient recovery time")

        if input_data.context_switches > 20:
            risks.append("Very high context switching - mental fatigue and reduced efficiency")

        if input_data.meeting_time > 5:
            risks.append("Excessive meeting time - limited deep work capacity")

        if input_data.focus_time < 1.5:
            risks.append("Low deep focus time - difficulty completing complex tasks")

        return risks

    def _identify_positive_factors(self, input_data: WellbeingInput) -> list[str]:
        """Identify positive wellbeing indicators.

        Args:
            input_data: Wellbeing metrics

        Returns:
            List of positive factors
        """
        positives = []

        if input_data.weekend_work_time == 0:
            positives.append("No weekend work - excellent boundary setting")

        if input_data.after_hours_time == 0:
            positives.append("No after-hours work - maintaining healthy work-life balance")

        if input_data.break_intervals >= 4:
            positives.append(f"Good break frequency ({input_data.break_intervals} breaks)")

        if input_data.focus_time >= 2.5:
            positives.append(f"Strong deep focus time ({input_data.focus_time:.1f}h)")

        if input_data.context_switches < 10:
            positives.append("Low context switching - excellent concentration")

        if input_data.physical_activity > 0:
            positives.append(f"Physical activity tracked ({input_data.physical_activity:.1f}h)")

        if input_data.screen_time < 7:
            positives.append("Healthy screen time levels")

        return positives

    def _fallback_analyze(self, input_data: WellbeingInput) -> WellbeingOutput:
        """Analyze wellbeing using heuristics (no LLM required).

        Args:
            input_data: Wellbeing metrics

        Returns:
            WellbeingOutput with analysis
        """
        # Calculate components
        score = self._calculate_wellbeing_score(input_data)
        balance = self._assess_work_life_balance(input_data)
        focus = self._assess_focus_quality(input_data)
        breaks = self._assess_break_patterns(input_data)
        health = self._identify_health_indicators(input_data)

        # Generate recommendations and factors
        recommendations = self._generate_recommendations(input_data, balance, focus, breaks, health)
        risk_factors = self._identify_risk_factors(input_data)
        positive_factors = self._identify_positive_factors(input_data)

        return WellbeingOutput(
            wellbeing_score=score,
            work_life_balance=balance,
            focus_quality=focus,
            break_patterns=breaks,
            health_indicators=health,
            recommendations=recommendations,
            risk_factors=risk_factors,
            positive_factors=positive_factors
        )

    def analyze(self, input_data: WellbeingInput) -> WellbeingOutput:
        """Analyze wellbeing indicators.

        Args:
            input_data: Wellbeing metrics

        Returns:
            WellbeingOutput with analysis and recommendations
        """
        with tracer.start_as_current_span("wellbeing.analyze") as span:
            span.set_attribute("screen_time", input_data.screen_time)
            span.set_attribute("work_hours", input_data.work_hours)
            span.set_attribute("break_intervals", input_data.break_intervals)
            span.set_attribute("use_llm", self.use_llm)

            try:
                if self.use_llm:
                    return self._llm_analyze(input_data)
                else:
                    return self._fallback_analyze(input_data)
            except Exception as e:
                logger.warning(f"LLM wellbeing analysis failed, using fallback: {e}")
                span.set_attribute("fallback_used", True)
                return self._fallback_analyze(input_data)

    def _llm_analyze(self, input_data: WellbeingInput) -> WellbeingOutput:
        """Analyze wellbeing using DSPy LLM.

        Args:
            input_data: Wellbeing metrics

        Returns:
            WellbeingOutput with LLM analysis
        """
        # Invoke DSPy predictor
        result = self.predictor(
            screen_time=input_data.screen_time,
            focus_time=input_data.focus_time,
            meeting_time=input_data.meeting_time,
            break_intervals=input_data.break_intervals,
            context_switches=input_data.context_switches,
            work_hours=input_data.work_hours,
            after_hours_time=input_data.after_hours_time
        )

        # Parse outputs
        health_indicators_raw = [h.strip() for h in result.health_indicators.split("\n") if h.strip()]
        recommendations = [r.strip() for r in result.recommendations.split("\n") if r.strip()]
        risk_factors = [r.strip() for r in result.risk_factors.split("\n") if r.strip()]

        # Use fallback for detailed assessments
        balance = self._assess_work_life_balance(input_data)
        focus = self._assess_focus_quality(input_data)
        breaks = self._assess_break_patterns(input_data)
        health = self._identify_health_indicators(input_data)
        positive_factors = self._identify_positive_factors(input_data)

        return WellbeingOutput(
            wellbeing_score=int(result.wellbeing_score),
            work_life_balance=balance,
            focus_quality=focus,
            break_patterns=breaks,
            health_indicators=health,
            recommendations=recommendations[:7],
            risk_factors=risk_factors[:7],
            positive_factors=positive_factors
        )

    async def analyze_async(self, input_data: WellbeingInput) -> WellbeingOutput:
        """Async version of analyze.

        Args:
            input_data: Wellbeing metrics

        Returns:
            WellbeingOutput with analysis
        """
        return await asyncio.to_thread(self.analyze, input_data)


# Example usage
if __name__ == "__main__":
    example_input = WellbeingInput(
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

    module = WellbeingModule(use_llm=False)
    output = module.analyze(example_input)

    print("Wellbeing Analysis:")
    print(f"Score: {output.wellbeing_score}/100")
    print(f"Work-life balance: {output.work_life_balance}")
    print(f"Focus quality: {output.focus_quality}")
    print(f"Break patterns: {output.break_patterns}")
    print(f"\nRecommendations:")
    for rec in output.recommendations:
        print(f"  - {rec}")
    print(f"\nRisk factors: {output.risk_factors}")
    print(f"Positive factors: {output.positive_factors}")

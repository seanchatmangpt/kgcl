"""Feature Analyzer Signature for KGCL.

Analyzes individual feature time series to detect trends, outliers, and patterns
with statistical summaries and interpretations.
"""

import asyncio
import logging
import statistics
from typing import Any, Literal

from pydantic import BaseModel, Field

try:
    import dspy

    DSPY_AVAILABLE = True
except ImportError:
    DSPY_AVAILABLE = False

from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class FeatureAnalyzerInput(BaseModel):
    """Input for feature analysis.

    Attributes
    ----------
        feature_name: Name of the feature being analyzed
        feature_values: Time series of feature values
        window: Time window granularity (hourly, daily, weekly)
        timestamps: Optional timestamps for each value
        context: Optional context about what the feature represents
    """

    feature_name: str = Field(..., description="Name of the feature")
    feature_values: list[float] = Field(..., min_length=1, description="Time series values")
    window: Literal["hourly", "daily", "weekly"] = Field(..., description="Time window")
    timestamps: list[str] = Field(
        default_factory=list, description="ISO timestamps for each value (optional)"
    )
    context: str = Field(
        default="", description="Context about the feature (e.g., 'Safari usage in hours')"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "feature_name": "safari_usage_hours",
                "feature_values": [1.2, 2.5, 1.8, 3.2, 2.1, 1.5, 2.8],
                "window": "daily",
                "timestamps": ["2024-11-18T00:00:00", "2024-11-19T00:00:00", "2024-11-20T00:00:00"],
                "context": "Daily Safari browser usage in hours",
            }
        }
    }


class FeatureAnalyzerOutput(BaseModel):
    """Output feature analysis with statistics and insights.

    Attributes
    ----------
        trend: Overall trend (increasing, decreasing, stable, volatile)
        outliers: List of outlier indices and values
        summary_stats: Statistical summary (mean, median, std, etc.)
        interpretation: Natural language interpretation of the analysis
        correlations: Potential correlations noted (if context provided)
        recommendations: Suggestions based on the analysis
    """

    trend: Literal["increasing", "decreasing", "stable", "volatile"] = Field(
        ..., description="Overall trend direction"
    )
    outliers: list[dict[str, Any]] = Field(
        default_factory=list, description="Detected outliers with indices and values"
    )
    summary_stats: dict[str, float] = Field(
        default_factory=dict, description="Statistical summary metrics"
    )
    interpretation: str = Field(..., description="Natural language analysis")
    correlations: list[str] = Field(
        default_factory=list, description="Potential correlations or patterns"
    )
    recommendations: list[str] = Field(
        default_factory=list, description="Actionable recommendations"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "trend": "stable",
                "outliers": [{"index": 3, "value": 3.2, "z_score": 2.1}],
                "summary_stats": {
                    "mean": 2.16,
                    "median": 2.1,
                    "std": 0.62,
                    "min": 1.2,
                    "max": 3.2,
                    "range": 2.0,
                },
                "interpretation": "Safari usage shows stable pattern averaging 2.2h daily with one spike on day 4 (3.2h)",
                "correlations": [
                    "80% correlation with meeting times - mostly research and documentation"
                ],
                "recommendations": [
                    "Spike on day 4 suggests research-heavy day",
                    "Consider time-boxing browser usage to maintain focus",
                ],
            }
        }
    }


if DSPY_AVAILABLE:

    class FeatureAnalyzerSignature(dspy.Signature):
        """Analyze a feature's time series for trends, outliers, and patterns.

        Given a feature's values over time, identify trends, detect outliers,
        compute statistics, and provide insights on what the patterns mean.
        """

        # Input fields
        feature_name: str = dspy.InputField(desc="Name of the feature being analyzed")
        feature_values_str: str = dspy.InputField(desc="Comma-separated feature values over time")
        window: str = dspy.InputField(desc="Time window: hourly, daily, or weekly")
        context: str = dspy.InputField(desc="Context about what this feature represents")
        summary_stats_str: str = dspy.InputField(
            desc="Statistical summary: mean, median, std, min, max"
        )

        # Output fields
        trend: str = dspy.OutputField(
            desc="Overall trend: increasing, decreasing, stable, or volatile"
        )
        interpretation: str = dspy.OutputField(
            desc="Natural language interpretation of the feature's behavior and what it means"
        )
        correlations: str = dspy.OutputField(
            desc="Potential correlations with other behaviors or patterns (bullet points)"
        )
        recommendations: str = dspy.OutputField(
            desc="3-5 actionable recommendations based on the analysis"
        )


class FeatureAnalyzerModule:
    """Module for analyzing individual feature time series."""

    def __init__(self, use_llm: bool = True, temperature: float = 0.7):
        """Initialize feature analyzer module.

        Args:
            use_llm: Whether to use LLM (DSPy) or fallback to statistical analysis
            temperature: LLM temperature for generation (0.0-1.0)
        """
        self.use_llm = use_llm and DSPY_AVAILABLE
        self.temperature = temperature

        if self.use_llm:
            self.predictor = dspy.ChainOfThought(FeatureAnalyzerSignature)
            logger.info("FeatureAnalyzerModule initialized with DSPy")
        else:
            logger.info("FeatureAnalyzerModule initialized with fallback (statistical)")

    def _calculate_statistics(self, values: list[float]) -> dict[str, float]:
        """Calculate statistical summary of feature values.

        Args:
            values: List of feature values

        Returns
        -------
            Dictionary of statistical metrics
        """
        if not values:
            return {}

        return {
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "std": statistics.stdev(values) if len(values) > 1 else 0.0,
            "min": min(values),
            "max": max(values),
            "range": max(values) - min(values),
            "count": len(values),
        }

    def _detect_outliers(self, values: list[float], threshold: float = 2.0) -> list[dict[str, Any]]:
        """Detect outliers using z-score method.

        Args:
            values: List of feature values
            threshold: Z-score threshold for outlier detection

        Returns
        -------
            List of outlier dictionaries with index, value, and z-score
        """
        if len(values) < 3:
            return []

        mean = statistics.mean(values)
        std = statistics.stdev(values)

        if std == 0:
            return []

        outliers = []
        for idx, value in enumerate(values):
            z_score = abs((value - mean) / std)
            if z_score > threshold:
                outliers.append({"index": idx, "value": value, "z_score": round(z_score, 2)})

        return outliers

    def _detect_trend(
        self, values: list[float]
    ) -> Literal["increasing", "decreasing", "stable", "volatile"]:
        """Detect overall trend in the time series.

        Args:
            values: List of feature values

        Returns
        -------
            Trend classification
        """
        if len(values) < 3:
            return "stable"

        # Calculate simple linear regression slope
        n = len(values)
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(values) / n

        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return "stable"

        slope = numerator / denominator

        # Calculate coefficient of variation for volatility
        std = statistics.stdev(values)
        mean = statistics.mean(values)
        cv = (std / mean) if mean != 0 else 0

        # Classify trend
        if cv > 0.5:  # High variation relative to mean
            return "volatile"
        if slope > 0.1:
            return "increasing"
        if slope < -0.1:
            return "decreasing"
        return "stable"

    def _fallback_generate(self, input_data: FeatureAnalyzerInput) -> FeatureAnalyzerOutput:
        """Generate analysis using statistical methods (no LLM required).

        Args:
            input_data: Feature data to analyze

        Returns
        -------
            FeatureAnalyzerOutput with statistical analysis
        """
        values = input_data.feature_values

        # Calculate statistics
        stats = self._calculate_statistics(values)

        # Detect trend
        trend = self._detect_trend(values)

        # Detect outliers
        outliers = self._detect_outliers(values)

        # Generate interpretation
        interpretation = self._generate_interpretation(
            input_data.feature_name, trend, stats, outliers, input_data.window
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            input_data.feature_name, trend, stats, outliers
        )

        # Detect correlations (basic heuristics)
        correlations = []
        if (
            "browser" in input_data.feature_name.lower()
            or "safari" in input_data.feature_name.lower()
        ):
            correlations.append(
                "Browser usage often correlates with research and documentation tasks"
            )
        if "meeting" in input_data.feature_name.lower():
            correlations.append("Meeting time typically anti-correlates with focus time")
        if "context_switch" in input_data.feature_name.lower():
            correlations.append(
                "Context switches often correlate with communication apps (Slack, email)"
            )

        return FeatureAnalyzerOutput(
            trend=trend,
            outliers=outliers,
            summary_stats=stats,
            interpretation=interpretation,
            correlations=correlations,
            recommendations=recommendations,
        )

    def _generate_interpretation(
        self,
        feature_name: str,
        trend: str,
        stats: dict[str, float],
        outliers: list[dict[str, Any]],
        window: str,
    ) -> str:
        """Generate natural language interpretation.

        Args:
            feature_name: Name of the feature
            trend: Detected trend
            stats: Statistical summary
            outliers: Detected outliers
            window: Time window

        Returns
        -------
            Interpretation string
        """
        mean = stats.get("mean", 0)
        std = stats.get("std", 0)

        interpretation = (
            f"{feature_name.replace('_', ' ').title()} shows {trend} pattern "
            f"averaging {mean:.2f} per {window} window "
            f"with standard deviation of {std:.2f}."
        )

        if outliers:
            outlier_indices = [o["index"] for o in outliers]
            interpretation += (
                f" Detected {len(outliers)} outlier(s) at position(s) {outlier_indices}, "
                f"indicating unusual activity on those days."
            )

        return interpretation

    def _generate_recommendations(
        self, feature_name: str, trend: str, stats: dict[str, float], outliers: list[dict[str, Any]]
    ) -> list[str]:
        """Generate actionable recommendations.

        Args:
            feature_name: Name of the feature
            trend: Detected trend
            stats: Statistical summary
            outliers: Detected outliers

        Returns
        -------
            List of recommendations
        """
        recommendations = []

        if trend == "increasing":
            recommendations.append(
                f"{feature_name} is trending upward - monitor if this aligns with goals"
            )
        elif trend == "decreasing":
            recommendations.append(f"{feature_name} is declining - verify if this is intentional")
        elif trend == "volatile":
            recommendations.append(
                f"{feature_name} shows high volatility - consider establishing more consistent patterns"
            )

        if outliers:
            recommendations.append(
                f"Investigate outlier days to understand what caused unusual {feature_name} values"
            )

        # Feature-specific recommendations
        if "focus" in feature_name.lower():
            if stats.get("mean", 0) < 2:
                recommendations.append(
                    "Focus time below 2h average - consider blocking dedicated work periods"
                )
        elif "meeting" in feature_name.lower():
            if stats.get("mean", 0) > 4:
                recommendations.append(
                    "Meeting time exceeds 4h average - audit for low-value meetings"
                )
        elif "context_switch" in feature_name.lower():
            if stats.get("mean", 0) > 15:
                recommendations.append("High context switching - batch similar tasks together")

        return recommendations[:5]  # Limit to top 5

    def analyze(self, input_data: FeatureAnalyzerInput) -> FeatureAnalyzerOutput:
        """Analyze feature time series.

        Args:
            input_data: Feature data to analyze

        Returns
        -------
            FeatureAnalyzerOutput with analysis results
        """
        with tracer.start_as_current_span("feature_analyzer.analyze") as span:
            span.set_attribute("feature_name", input_data.feature_name)
            span.set_attribute("value_count", len(input_data.feature_values))
            span.set_attribute("window", input_data.window)
            span.set_attribute("use_llm", self.use_llm)

            try:
                if self.use_llm:
                    return self._llm_analyze(input_data)
                return self._fallback_generate(input_data)
            except Exception as e:
                logger.warning(f"LLM analysis failed, using fallback: {e}")
                span.set_attribute("fallback_used", True)
                return self._fallback_generate(input_data)

    def _llm_analyze(self, input_data: FeatureAnalyzerInput) -> FeatureAnalyzerOutput:
        """Analyze feature using DSPy LLM.

        Args:
            input_data: Feature data to analyze

        Returns
        -------
            FeatureAnalyzerOutput with LLM-generated analysis
        """
        # Calculate statistics for context
        stats = self._calculate_statistics(input_data.feature_values)
        outliers = self._detect_outliers(input_data.feature_values)
        trend_detected = self._detect_trend(input_data.feature_values)

        # Prepare inputs for DSPy
        values_str = ",".join(f"{v:.2f}" for v in input_data.feature_values)
        stats_str = (
            f"mean={stats['mean']:.2f}, median={stats['median']:.2f}, "
            f"std={stats['std']:.2f}, min={stats['min']:.2f}, max={stats['max']:.2f}"
        )
        context = (
            input_data.context or f"{input_data.feature_name} over {input_data.window} windows"
        )

        # Invoke DSPy predictor
        result = self.predictor(
            feature_name=input_data.feature_name,
            feature_values_str=values_str,
            window=input_data.window,
            context=context,
            summary_stats_str=stats_str,
        )

        # Parse outputs
        correlations = [c.strip() for c in result.correlations.split("\n") if c.strip()]
        recommendations = [r.strip() for r in result.recommendations.split("\n") if r.strip()]

        return FeatureAnalyzerOutput(
            trend=result.trend
            if result.trend in ["increasing", "decreasing", "stable", "volatile"]
            else trend_detected,
            outliers=outliers,
            summary_stats=stats,
            interpretation=result.interpretation,
            correlations=correlations[:5],
            recommendations=recommendations[:5],
        )

    async def analyze_async(self, input_data: FeatureAnalyzerInput) -> FeatureAnalyzerOutput:
        """Async version of analyze.

        Args:
            input_data: Feature data to analyze

        Returns
        -------
            FeatureAnalyzerOutput with analysis
        """
        return await asyncio.to_thread(self.analyze, input_data)


# Example usage
if __name__ == "__main__":
    example_input = FeatureAnalyzerInput(
        feature_name="safari_usage_hours",
        feature_values=[1.2, 2.5, 1.8, 3.2, 2.1, 1.5, 2.8],
        window="daily",
        context="Daily Safari browser usage in hours",
    )

    module = FeatureAnalyzerModule(use_llm=False)
    output = module.analyze(example_input)

    print(f"Feature Analysis: {example_input.feature_name}")
    print(f"Trend: {output.trend}")
    print(f"Stats: {output.summary_stats}")
    print(f"Interpretation: {output.interpretation}")
    print(f"Outliers: {output.outliers}")
    print(f"Recommendations: {output.recommendations}")

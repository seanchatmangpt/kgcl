"""Pattern Detector Signature for KGCL.

Identifies correlations and patterns across multiple features simultaneously,
detecting behavioral insights and multi-dimensional relationships.
"""

import asyncio
import logging
import statistics

from pydantic import BaseModel, Field

try:
    import dspy

    DSPY_AVAILABLE = True
except ImportError:
    DSPY_AVAILABLE = False

from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class PatternDetectorInput(BaseModel):
    """Input for multi-feature pattern detection.

    Attributes
    ----------
        multiple_features: Dictionary mapping feature names to value lists
        time_window: Time window for pattern analysis (hourly, daily, weekly)
        timestamps: Optional timestamps for alignment
        context: Optional context about the data
    """

    multiple_features: dict[str, list[float]] = Field(..., description="Feature names mapped to time series values")
    time_window: str = Field(default="daily", description="Time window: hourly, daily, weekly")
    timestamps: list[str] = Field(default_factory=list, description="ISO timestamps for alignment (optional)")
    context: str = Field(default="", description="Context about the feature set")

    model_config = {
        "json_schema_extra": {
            "example": {
                "multiple_features": {
                    "focus_time": [2.5, 1.8, 3.2, 2.1, 1.5],
                    "meeting_hours": [1.5, 4.2, 1.0, 2.5, 3.8],
                    "context_switches": [12, 18, 10, 14, 20],
                    "safari_usage": [1.2, 2.5, 0.8, 1.5, 2.2],
                },
                "time_window": "daily",
                "timestamps": ["2024-11-20", "2024-11-21", "2024-11-22"],
                "context": "Weekly work pattern analysis",
            }
        }
    }


class DetectedPattern(BaseModel):
    """Individual detected pattern.

    Attributes
    ----------
        pattern_name: Name/description of the pattern
        evidence: Supporting evidence for the pattern
        frequency: How often the pattern occurs
        confidence: Confidence score (0-100)
        recommendation: Actionable recommendation based on pattern
        involved_features: Features involved in this pattern
    """

    pattern_name: str = Field(..., description="Pattern name or description")
    evidence: str = Field(..., description="Evidence supporting the pattern")
    frequency: str = Field(..., description="Pattern frequency (e.g., 'daily', '3/5 days')")
    confidence: int = Field(default=0, ge=0, le=100, description="Confidence in pattern (0-100)")
    recommendation: str = Field(..., description="Actionable recommendation")
    involved_features: list[str] = Field(default_factory=list, description="Features involved in pattern")


class PatternDetectorOutput(BaseModel):
    """Output detected patterns and correlations.

    Attributes
    ----------
        detected_patterns: List of identified patterns
        correlations: Statistical correlations between features
        insights: High-level insights from pattern analysis
        behavioral_clusters: Grouped behavioral patterns
        anomalies: Detected anomalous combinations
    """

    detected_patterns: list[DetectedPattern] = Field(default_factory=list, description="Identified patterns")
    correlations: dict[str, float] = Field(default_factory=dict, description="Feature pair correlations (-1 to 1)")
    insights: list[str] = Field(default_factory=list, description="High-level insights")
    behavioral_clusters: dict[str, list[str]] = Field(default_factory=dict, description="Clustered behavioral patterns")
    anomalies: list[str] = Field(default_factory=list, description="Anomalous feature combinations")

    model_config = {
        "json_schema_extra": {
            "example": {
                "detected_patterns": [
                    {
                        "pattern_name": "Morning deep work pattern",
                        "evidence": "2-3 hour uninterrupted coding sessions before 11am",
                        "frequency": "4/5 days",
                        "confidence": 85,
                        "recommendation": "Protect morning time blocks from meetings",
                        "involved_features": ["focus_time", "context_switches"],
                    }
                ],
                "correlations": {"focus_time_vs_meeting_hours": -0.75, "meeting_hours_vs_context_switches": 0.68},
                "insights": [
                    "High meeting load consistently reduces focus time",
                    "Browser usage spikes during meeting days (research/documentation)",
                ],
                "behavioral_clusters": {
                    "deep_work_days": ["low meetings", "high focus", "low context switches"],
                    "collaborative_days": ["high meetings", "high browser usage", "high context switches"],
                },
                "anomalies": ["Day 3: High focus time despite high meeting load (unusual)"],
            }
        }
    }


if DSPY_AVAILABLE:

    class PatternDetectorSignature(dspy.Signature):
        """Detect patterns and correlations across multiple activity features.

        Analyze multiple features simultaneously to identify behavioral patterns,
        correlations, and insights that emerge from multi-dimensional analysis.
        """

        # Input fields
        features_summary: str = dspy.InputField(desc="Summary of all features with names and value ranges")
        correlation_matrix: str = dspy.InputField(desc="Key correlations between feature pairs")
        time_window: str = dspy.InputField(desc="Time window for analysis: hourly, daily, or weekly")
        context: str = dspy.InputField(desc="Context about what these features represent")

        # Output fields
        patterns: str = dspy.OutputField(
            desc="Detected behavioral patterns with evidence and frequency (numbered list)"
        )
        insights: str = dspy.OutputField(desc="High-level insights from multi-feature analysis (bullet points)")
        recommendations: str = dspy.OutputField(desc="Actionable recommendations based on detected patterns")
        behavioral_clusters: str = dspy.OutputField(
            desc="Groups of related behavioral patterns (e.g., 'deep work days', 'meeting days')"
        )


class PatternDetectorModule:
    """Module for detecting patterns across multiple features."""

    def __init__(self, use_llm: bool = True, temperature: float = 0.7):
        """Initialize pattern detector module.

        Args:
            use_llm: Whether to use LLM (DSPy) or fallback to statistical analysis
            temperature: LLM temperature for generation (0.0-1.0)
        """
        self.use_llm = use_llm and DSPY_AVAILABLE
        self.temperature = temperature

        if self.use_llm:
            self.predictor = dspy.ChainOfThought(PatternDetectorSignature)
            logger.info("PatternDetectorModule initialized with DSPy")
        else:
            logger.info("PatternDetectorModule initialized with fallback (statistical)")

    def _calculate_correlation(self, x: list[float], y: list[float]) -> float:
        """Calculate Pearson correlation coefficient.

        Args:
            x: First feature values
            y: Second feature values

        Returns
        -------
            Correlation coefficient (-1 to 1)
        """
        if len(x) != len(y) or len(x) < 2:
            return 0.0

        mean_x = statistics.mean(x)
        mean_y = statistics.mean(y)

        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(len(x)))
        sum_sq_x = sum((xi - mean_x) ** 2 for xi in x)
        sum_sq_y = sum((yi - mean_y) ** 2 for yi in y)

        denominator = (sum_sq_x * sum_sq_y) ** 0.5

        if denominator == 0:
            return 0.0

        return numerator / denominator

    def _detect_correlations(self, features: dict[str, list[float]]) -> dict[str, float]:
        """Detect correlations between all feature pairs.

        Args:
            features: Dictionary of feature names to values

        Returns
        -------
            Dictionary of feature pair correlations
        """
        correlations = {}
        feature_names = list(features.keys())

        for i in range(len(feature_names)):
            for j in range(i + 1, len(feature_names)):
                feat1 = feature_names[i]
                feat2 = feature_names[j]

                if len(features[feat1]) == len(features[feat2]):
                    corr = self._calculate_correlation(features[feat1], features[feat2])
                    correlations[f"{feat1}_vs_{feat2}"] = round(corr, 2)

        return correlations

    def _fallback_generate(self, input_data: PatternDetectorInput) -> PatternDetectorOutput:
        """Generate pattern detection using statistical methods (no LLM required).

        Args:
            input_data: Multi-feature data

        Returns
        -------
            PatternDetectorOutput with detected patterns
        """
        features = input_data.multiple_features

        # Calculate correlations
        correlations = self._detect_correlations(features)

        # Detect patterns based on correlations
        detected_patterns = []
        insights = []
        behavioral_clusters = {}
        anomalies = []

        # Strong negative correlation patterns (anti-patterns)
        for pair, corr in correlations.items():
            if corr < -0.6:  # Strong negative correlation
                feat1, feat2 = pair.replace("_vs_", "|").split("|")
                pattern = DetectedPattern(
                    pattern_name=f"Trade-off pattern: {feat1} vs {feat2}",
                    evidence=f"Strong negative correlation ({corr:.2f})",
                    frequency="Consistent across time window",
                    confidence=int(abs(corr) * 100),
                    recommendation=f"When increasing {feat1}, expect {feat2} to decrease",
                    involved_features=[feat1, feat2],
                )
                detected_patterns.append(pattern)
                insights.append(f"{feat1} and {feat2} show inverse relationship ({corr:.2f})")

        # Strong positive correlation patterns
        for pair, corr in correlations.items():
            if corr > 0.6:  # Strong positive correlation
                feat1, feat2 = pair.replace("_vs_", "|").split("|")
                pattern = DetectedPattern(
                    pattern_name=f"Co-occurrence pattern: {feat1} and {feat2}",
                    evidence=f"Strong positive correlation ({corr:.2f})",
                    frequency="Consistent across time window",
                    confidence=int(corr * 100),
                    recommendation=f"{feat1} and {feat2} often occur together",
                    involved_features=[feat1, feat2],
                )
                detected_patterns.append(pattern)
                insights.append(f"{feat1} and {feat2} tend to occur together ({corr:.2f})")

        # Identify behavioral clusters based on feature means
        feature_means = {name: statistics.mean(values) for name, values in features.items()}

        # Simple clustering: high/low for each feature
        high_features = [
            name for name, mean in feature_means.items() if mean > statistics.mean(list(feature_means.values()))
        ]
        low_features = [
            name for name, mean in feature_means.items() if mean <= statistics.mean(list(feature_means.values()))
        ]

        if high_features:
            behavioral_clusters["high_activity"] = high_features
        if low_features:
            behavioral_clusters["low_activity"] = low_features

        # Detect anomalies: days with unusual feature combinations
        if len(features) >= 2:
            feature_list = list(features.items())
            first_feat_name, first_feat_values = feature_list[0]
            second_feat_name, second_feat_values = feature_list[1]

            for i in range(min(len(first_feat_values), len(second_feat_values))):
                # Check if both features are simultaneously high
                if first_feat_values[i] > statistics.mean(first_feat_values) + statistics.stdev(
                    first_feat_values
                ) and second_feat_values[i] > statistics.mean(second_feat_values) + statistics.stdev(
                    second_feat_values
                ):
                    anomalies.append(
                        f"Day {i + 1}: Unusually high {first_feat_name} and {second_feat_name} simultaneously"
                    )

        # Add domain-specific pattern detection
        if "focus_time" in features and "meeting" in str(features.keys()).lower():
            meeting_key = next(k for k in features if "meeting" in k.lower())
            avg_focus = statistics.mean(features["focus_time"])
            avg_meetings = statistics.mean(features[meeting_key])

            if avg_focus > 2.5 and avg_meetings < 2:
                pattern = DetectedPattern(
                    pattern_name="Deep work routine",
                    evidence=f"High focus time ({avg_focus:.1f}h avg) with low meeting load ({avg_meetings:.1f}h avg)",
                    frequency="Consistent pattern",
                    confidence=80,
                    recommendation="Maintain this balance for sustained productivity",
                    involved_features=["focus_time", meeting_key],
                )
                detected_patterns.append(pattern)

        return PatternDetectorOutput(
            detected_patterns=detected_patterns,
            correlations=correlations,
            insights=insights,
            behavioral_clusters=behavioral_clusters,
            anomalies=anomalies,
        )

    def detect(self, input_data: PatternDetectorInput) -> PatternDetectorOutput:
        """Detect patterns across multiple features.

        Args:
            input_data: Multi-feature data

        Returns
        -------
            PatternDetectorOutput with detected patterns
        """
        with tracer.start_as_current_span("pattern_detector.detect") as span:
            span.set_attribute("feature_count", len(input_data.multiple_features))
            span.set_attribute("time_window", input_data.time_window)
            span.set_attribute("use_llm", self.use_llm)

            try:
                if self.use_llm:
                    return self._llm_detect(input_data)
                return self._fallback_generate(input_data)
            except Exception as e:
                logger.warning(f"LLM pattern detection failed, using fallback: {e}")
                span.set_attribute("fallback_used", True)
                return self._fallback_generate(input_data)

    def _llm_detect(self, input_data: PatternDetectorInput) -> PatternDetectorOutput:
        """Detect patterns using DSPy LLM.

        Args:
            input_data: Multi-feature data

        Returns
        -------
            PatternDetectorOutput with LLM-generated patterns
        """
        # Calculate correlations for context
        correlations = self._detect_correlations(input_data.multiple_features)

        # Prepare features summary
        features_summary_lines = []
        for name, values in input_data.multiple_features.items():
            mean = statistics.mean(values)
            features_summary_lines.append(f"{name}: mean={mean:.2f}, range=[{min(values):.2f}, {max(values):.2f}]")
        features_summary = "\n".join(features_summary_lines)

        # Prepare correlation matrix
        corr_lines = [f"{pair}: {corr:.2f}" for pair, corr in correlations.items()]
        correlation_matrix = "\n".join(corr_lines)

        context = input_data.context or "Multi-feature activity analysis"

        # Invoke DSPy predictor
        result = self.predictor(
            features_summary=features_summary,
            correlation_matrix=correlation_matrix,
            time_window=input_data.time_window,
            context=context,
        )

        # Parse patterns from LLM output
        detected_patterns = []
        pattern_lines = [p.strip() for p in result.patterns.split("\n") if p.strip()]

        for line in pattern_lines:
            # Simple parsing: extract pattern description
            if line and len(line) > 10:
                pattern = DetectedPattern(
                    pattern_name=line[:50],  # First 50 chars as name
                    evidence=line,
                    frequency="Detected in analysis",
                    confidence=75,  # Default confidence for LLM patterns
                    recommendation="Review and validate this pattern",
                    involved_features=list(input_data.multiple_features.keys()),
                )
                detected_patterns.append(pattern)

        # Parse insights
        insights = [i.strip() for i in result.insights.split("\n") if i.strip()]

        # Parse behavioral clusters
        behavioral_clusters = {}
        cluster_lines = [c.strip() for c in result.behavioral_clusters.split("\n") if c.strip()]
        for line in cluster_lines:
            if ":" in line:
                cluster_name, features = line.split(":", 1)
                behavioral_clusters[cluster_name.strip()] = [f.strip() for f in features.split(",")]

        # Use fallback for anomalies
        fallback_result = self._fallback_generate(input_data)

        return PatternDetectorOutput(
            detected_patterns=detected_patterns[:10],  # Limit to top 10
            correlations=correlations,
            insights=insights[:7],
            behavioral_clusters=behavioral_clusters,
            anomalies=fallback_result.anomalies,
        )

    async def detect_async(self, input_data: PatternDetectorInput) -> PatternDetectorOutput:
        """Async version of detect.

        Args:
            input_data: Multi-feature data

        Returns
        -------
            PatternDetectorOutput with patterns
        """
        return await asyncio.to_thread(self.detect, input_data)


# Example usage
if __name__ == "__main__":
    example_input = PatternDetectorInput(
        multiple_features={
            "focus_time": [2.5, 1.8, 3.2, 2.1, 1.5],
            "meeting_hours": [1.5, 4.2, 1.0, 2.5, 3.8],
            "context_switches": [12, 18, 10, 14, 20],
            "safari_usage": [1.2, 2.5, 0.8, 1.5, 2.2],
        },
        time_window="daily",
        context="Weekly work pattern analysis",
    )

    module = PatternDetectorModule(use_llm=False)
    output = module.detect(example_input)

    print("Pattern Detection Results:")
    print(f"Detected {len(output.detected_patterns)} patterns")
    print(f"Correlations: {output.correlations}")
    print(f"Insights: {output.insights}")
    print(f"Behavioral clusters: {output.behavioral_clusters}")
    if output.anomalies:
        print(f"Anomalies: {output.anomalies}")

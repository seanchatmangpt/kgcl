"""Context Classifier Signature for KGCL.

Classifies activities into meaningful contexts (work focus, admin, learning, etc.)
based on app names, domains, calendar events, and time of day.
"""

from typing import Literal
from pydantic import BaseModel, Field
import asyncio
import logging
from datetime import datetime

try:
    import dspy
    DSPY_AVAILABLE = True
except ImportError:
    DSPY_AVAILABLE = False

from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


# Context type enumeration
ContextLabel = Literal[
    "work_focus",           # Deep coding/writing work
    "communication",        # Email, Slack, messaging
    "meetings",            # Calendar events, calls
    "research",            # Documentation, web browsing
    "admin",               # Administrative tasks
    "learning",            # Courses, tutorials, reading
    "debugging",           # Troubleshooting, testing
    "code_review",         # PR reviews, code analysis
    "planning",            # Design, architecture, planning
    "break",               # Breaks, personal time
    "other"               # Unclassified
]


class ContextClassifierInput(BaseModel):
    """Input for context classification.

    Attributes:
        app_name: Application bundle name (e.g., com.apple.Safari)
        domain_names: List of visited domains (if applicable)
        calendar_event: Calendar event title (if in meeting)
        time_of_day: Hour of day (0-23)
        window_title: Active window title (optional)
        duration_seconds: Activity duration (optional)
    """

    app_name: str = Field(..., description="Application bundle or display name")
    domain_names: list[str] = Field(
        default_factory=list,
        description="Visited domain names"
    )
    calendar_event: str = Field(
        default="",
        description="Calendar event title if in meeting"
    )
    time_of_day: int = Field(
        ...,
        ge=0,
        le=23,
        description="Hour of day (0-23)"
    )
    window_title: str = Field(
        default="",
        description="Active window title"
    )
    duration_seconds: float = Field(
        default=0,
        ge=0,
        description="Activity duration in seconds"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "app_name": "com.apple.Safari",
                "domain_names": ["github.com", "stackoverflow.com"],
                "calendar_event": "",
                "time_of_day": 10,
                "window_title": "Python Documentation - Built-in Functions",
                "duration_seconds": 180.5
            }
        }
    }


class ContextClassifierOutput(BaseModel):
    """Output context classification result.

    Attributes:
        context_label: Primary context classification
        confidence: Confidence score (0-100)
        reasoning: Explanation for classification
        secondary_contexts: Alternative context labels with scores
        suggested_tags: Suggested activity tags
    """

    context_label: ContextLabel = Field(..., description="Primary context classification")
    confidence: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Classification confidence (0-100)"
    )
    reasoning: str = Field(..., description="Classification reasoning")
    secondary_contexts: dict[str, int] = Field(
        default_factory=dict,
        description="Alternative contexts with confidence scores"
    )
    suggested_tags: list[str] = Field(
        default_factory=list,
        description="Suggested activity tags"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "context_label": "research",
                "confidence": 85,
                "reasoning": "Safari browsing technical documentation (GitHub, StackOverflow) during work hours",
                "secondary_contexts": {
                    "learning": 60,
                    "work_focus": 40
                },
                "suggested_tags": ["programming", "documentation", "web_research"]
            }
        }
    }


if DSPY_AVAILABLE:
    class ContextClassifierSignature(dspy.Signature):
        """Classify activity into meaningful work context.

        Given app usage, domains, calendar events, and time of day,
        determine the primary work context (focus, communication, research, etc.).
        """

        # Input fields
        app_name: str = dspy.InputField(desc="Application name")
        domains: str = dspy.InputField(desc="Comma-separated domain names (if browser)")
        calendar_event: str = dspy.InputField(desc="Calendar event title (empty if none)")
        time_of_day: int = dspy.InputField(desc="Hour of day (0-23)")
        window_title: str = dspy.InputField(desc="Active window title")

        # Output fields
        context_label: str = dspy.OutputField(
            desc="Primary context: work_focus, communication, meetings, research, admin, learning, debugging, code_review, planning, break, or other"
        )
        confidence: int = dspy.OutputField(
            desc="Confidence score 0-100"
        )
        reasoning: str = dspy.OutputField(
            desc="1-2 sentence explanation for classification"
        )
        suggested_tags: str = dspy.OutputField(
            desc="Comma-separated activity tags"
        )


class ContextClassifierModule:
    """Module for classifying activities into work contexts."""

    def __init__(self, use_llm: bool = True, temperature: float = 0.3):
        """Initialize context classifier module.

        Args:
            use_llm: Whether to use LLM (DSPy) or fallback to rule-based
            temperature: LLM temperature for classification (0.0-1.0, lower for consistency)
        """
        self.use_llm = use_llm and DSPY_AVAILABLE
        self.temperature = temperature

        if self.use_llm:
            self.predictor = dspy.Predict(ContextClassifierSignature)  # Predict for classification
            logger.info("ContextClassifierModule initialized with DSPy")
        else:
            logger.info("ContextClassifierModule initialized with fallback (rule-based)")

    def _fallback_classify(self, input_data: ContextClassifierInput) -> ContextClassifierOutput:
        """Classify context using rule-based logic (no LLM required).

        Args:
            input_data: Activity data to classify

        Returns:
            ContextClassifierOutput with classification
        """
        app_lower = input_data.app_name.lower()
        domains_lower = [d.lower() for d in input_data.domain_names]
        window_lower = input_data.window_title.lower()
        calendar_lower = input_data.calendar_event.lower()

        # Priority 1: Calendar events
        if input_data.calendar_event:
            return ContextClassifierOutput(
                context_label="meetings",
                confidence=95,
                reasoning=f"Active calendar event: {input_data.calendar_event}",
                secondary_contexts={"communication": 70},
                suggested_tags=["meeting", "collaboration"]
            )

        # Priority 2: IDE and code editors (work focus)
        ide_apps = ["vscode", "intellij", "pycharm", "sublime", "vim", "emacs", "xcode", "code"]
        if any(ide in app_lower for ide in ide_apps):
            return ContextClassifierOutput(
                context_label="work_focus",
                confidence=90,
                reasoning=f"Using code editor/IDE: {input_data.app_name}",
                secondary_contexts={"debugging": 40},
                suggested_tags=["coding", "development"]
            )

        # Priority 3: Communication apps
        comm_apps = ["slack", "teams", "discord", "mail", "outlook", "messages", "zoom", "meet"]
        if any(comm in app_lower for comm in comm_apps):
            # Check if it's a call/meeting
            if "zoom" in app_lower or "meet" in app_lower or "call" in window_lower:
                return ContextClassifierOutput(
                    context_label="meetings",
                    confidence=85,
                    reasoning=f"Video call/meeting app: {input_data.app_name}",
                    secondary_contexts={"communication": 70},
                    suggested_tags=["meeting", "video_call"]
                )
            else:
                return ContextClassifierOutput(
                    context_label="communication",
                    confidence=85,
                    reasoning=f"Communication app: {input_data.app_name}",
                    secondary_contexts={"admin": 30},
                    suggested_tags=["messaging", "email"]
                )

        # Priority 4: Browser - classify by domains
        if "safari" in app_lower or "chrome" in app_lower or "firefox" in app_lower or "browser" in app_lower:
            return self._classify_browser_activity(input_data, domains_lower, window_lower)

        # Priority 5: Terminal (work focus or debugging)
        if "terminal" in app_lower or "iterm" in app_lower or "console" in app_lower:
            if "test" in window_lower or "debug" in window_lower:
                return ContextClassifierOutput(
                    context_label="debugging",
                    confidence=75,
                    reasoning="Terminal with testing/debugging activity",
                    secondary_contexts={"work_focus": 60},
                    suggested_tags=["terminal", "debugging"]
                )
            return ContextClassifierOutput(
                context_label="work_focus",
                confidence=80,
                reasoning="Terminal usage for development work",
                secondary_contexts={"admin": 40},
                suggested_tags=["terminal", "development"]
            )

        # Priority 6: Time-based heuristics
        if input_data.time_of_day < 9 or input_data.time_of_day > 18:
            if input_data.time_of_day >= 22 or input_data.time_of_day <= 6:
                return ContextClassifierOutput(
                    context_label="break",
                    confidence=60,
                    reasoning=f"Activity outside typical work hours ({input_data.time_of_day}:00)",
                    secondary_contexts={"other": 50},
                    suggested_tags=["after_hours"]
                )

        # Default: other
        return ContextClassifierOutput(
            context_label="other",
            confidence=40,
            reasoning=f"Could not confidently classify: {input_data.app_name}",
            secondary_contexts={},
            suggested_tags=[]
        )

    def _classify_browser_activity(
        self,
        input_data: ContextClassifierInput,
        domains_lower: list[str],
        window_lower: str
    ) -> ContextClassifierOutput:
        """Classify browser activity based on domains and window title.

        Args:
            input_data: Input data
            domains_lower: Lowercased domain names
            window_lower: Lowercased window title

        Returns:
            ContextClassifierOutput for browser activity
        """
        # Code-related domains (research/documentation)
        code_domains = [
            "github.com", "stackoverflow.com", "docs.python.org", "developer.mozilla.org",
            "npmjs.com", "pypi.org", "readthedocs.io", "gitlab.com"
        ]
        if any(domain in d for domain in code_domains for d in domains_lower):
            return ContextClassifierOutput(
                context_label="research",
                confidence=85,
                reasoning=f"Browsing technical documentation/code repositories: {domains_lower[:3]}",
                secondary_contexts={"learning": 60},
                suggested_tags=["documentation", "web_research", "programming"]
            )

        # Learning platforms
        learning_domains = [
            "coursera.org", "udemy.com", "pluralsight.com", "egghead.io",
            "youtube.com", "medium.com", "dev.to"
        ]
        if any(domain in d for domain in learning_domains for d in domains_lower):
            return ContextClassifierOutput(
                context_label="learning",
                confidence=80,
                reasoning=f"Accessing learning/educational content: {domains_lower[:3]}",
                secondary_contexts={"research": 60},
                suggested_tags=["learning", "education"]
            )

        # Admin/productivity domains
        admin_domains = [
            "google.com/calendar", "notion.so", "trello.com", "asana.com",
            "jira.atlassian.com", "linear.app"
        ]
        if any(domain in d for domain in admin_domains for d in domains_lower):
            return ContextClassifierOutput(
                context_label="admin",
                confidence=75,
                reasoning=f"Using productivity/admin tools: {domains_lower[:3]}",
                secondary_contexts={"planning": 60},
                suggested_tags=["productivity", "admin"]
            )

        # Code review domains
        if any("github.com/pulls" in d or "gitlab.com/merge" in d for d in domains_lower):
            return ContextClassifierOutput(
                context_label="code_review",
                confidence=85,
                reasoning="Reviewing pull requests/merge requests",
                secondary_contexts={"work_focus": 70},
                suggested_tags=["code_review", "collaboration"]
            )

        # Default browser usage
        return ContextClassifierOutput(
            context_label="research",
            confidence=50,
            reasoning=f"General web browsing: {domains_lower[:3] if domains_lower else 'unknown domains'}",
            secondary_contexts={"other": 50},
            suggested_tags=["web_browsing"]
        )

    def classify(self, input_data: ContextClassifierInput) -> ContextClassifierOutput:
        """Classify activity into work context.

        Args:
            input_data: Activity data to classify

        Returns:
            ContextClassifierOutput with classification
        """
        with tracer.start_as_current_span("context_classifier.classify") as span:
            span.set_attribute("app_name", input_data.app_name)
            span.set_attribute("time_of_day", input_data.time_of_day)
            span.set_attribute("has_calendar_event", bool(input_data.calendar_event))
            span.set_attribute("use_llm", self.use_llm)

            try:
                if self.use_llm:
                    return self._llm_classify(input_data)
                else:
                    return self._fallback_classify(input_data)
            except Exception as e:
                logger.warning(f"LLM classification failed, using fallback: {e}")
                span.set_attribute("fallback_used", True)
                return self._fallback_classify(input_data)

    def _llm_classify(self, input_data: ContextClassifierInput) -> ContextClassifierOutput:
        """Classify context using DSPy LLM.

        Args:
            input_data: Activity data

        Returns:
            ContextClassifierOutput with LLM classification
        """
        # Prepare inputs
        domains_str = ", ".join(input_data.domain_names) if input_data.domain_names else "none"
        calendar_str = input_data.calendar_event or "none"
        window_str = input_data.window_title or "unknown"

        # Invoke DSPy predictor
        result = self.predictor(
            app_name=input_data.app_name,
            domains=domains_str,
            calendar_event=calendar_str,
            time_of_day=input_data.time_of_day,
            window_title=window_str
        )

        # Validate context label
        valid_contexts: list[ContextLabel] = [
            "work_focus", "communication", "meetings", "research", "admin",
            "learning", "debugging", "code_review", "planning", "break", "other"
        ]

        context_label: ContextLabel = "other"
        if result.context_label in valid_contexts:
            context_label = result.context_label  # type: ignore

        # Parse suggested tags
        suggested_tags = [t.strip() for t in result.suggested_tags.split(",") if t.strip()]

        return ContextClassifierOutput(
            context_label=context_label,
            confidence=int(result.confidence),
            reasoning=result.reasoning,
            secondary_contexts={},  # LLM doesn't provide secondary contexts
            suggested_tags=suggested_tags[:5]
        )

    async def classify_async(self, input_data: ContextClassifierInput) -> ContextClassifierOutput:
        """Async version of classify.

        Args:
            input_data: Activity data

        Returns:
            ContextClassifierOutput with classification
        """
        return await asyncio.to_thread(self.classify, input_data)


# Example usage
if __name__ == "__main__":
    examples = [
        ContextClassifierInput(
            app_name="com.microsoft.VSCode",
            domain_names=[],
            calendar_event="",
            time_of_day=10,
            window_title="main.py - kgcl - Visual Studio Code",
            duration_seconds=1800
        ),
        ContextClassifierInput(
            app_name="com.apple.Safari",
            domain_names=["github.com", "stackoverflow.com"],
            calendar_event="",
            time_of_day=14,
            window_title="Python Documentation - Built-in Functions",
            duration_seconds=300
        ),
        ContextClassifierInput(
            app_name="us.zoom.xos",
            domain_names=[],
            calendar_event="Team Standup",
            time_of_day=9,
            window_title="Zoom Meeting",
            duration_seconds=1800
        )
    ]

    module = ContextClassifierModule(use_llm=False)

    for example in examples:
        output = module.classify(example)
        print(f"\nApp: {example.app_name}")
        print(f"Context: {output.context_label} (confidence: {output.confidence}%)")
        print(f"Reasoning: {output.reasoning}")
        print(f"Tags: {output.suggested_tags}")

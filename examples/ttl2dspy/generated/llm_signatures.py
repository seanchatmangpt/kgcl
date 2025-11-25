"""Auto-generated DSPy signatures from SHACL shapes."""

# This file is auto-generated. Do not edit manually.

import dspy


class TextSummarizationSignature(dspy.Signature):
    """Generate a concise summary of input text"""

    # Input fields
    text: list[str] = dspy.InputField(desc="Long text to summarize", prefix="text:")
    max_length: list[int] = dspy.InputField(
        desc="Maximum summary length in words", prefix="max_length:"
    )

    # Output fields
    summary: list[str] | None = dspy.OutputField(desc="Generated summary")


class QuestionAnsweringSignature(dspy.Signature):
    """Answer questions based on provided context"""

    # Input fields
    question: list[str] = dspy.InputField(desc="Question to answer", prefix="question:")
    context: list[str] = dspy.InputField(
        desc="Context for answering the question", prefix="context:"
    )

    # Output fields
    answer: list[str] | None = dspy.OutputField(desc="Generated answer")
    confidence: list[float] | None = dspy.OutputField(desc="Answer confidence score")


class SentimentAnalysisSignature(dspy.Signature):
    """Analyze sentiment of text"""

    # Input fields
    text: list[str] = dspy.InputField(desc="Text to analyze", prefix="text:")

    # Output fields
    sentiment: list[str] | None = dspy.OutputField(
        desc="Predicted sentiment (positive, negative, neutral)"
    )
    score: list[float] | None = dspy.OutputField(desc="Sentiment score (-1 to 1)")


class TextTranslationSignature(dspy.Signature):
    """Translate text between languages"""

    # Input fields
    text: list[str] = dspy.InputField(desc="Text to translate", prefix="text:")
    source_language: list[str] = dspy.InputField(
        desc="Source language code (e.g., 'en', 'es')", prefix="source_language:"
    )
    target_language: list[str] = dspy.InputField(
        desc="Target language code", prefix="target_language:"
    )

    # Output fields
    translation: list[str] | None = dspy.OutputField(desc="Translated text")


class CodeGenerationSignature(dspy.Signature):
    """Generate code from natural language description"""

    # Input fields
    description: list[str] = dspy.InputField(
        desc="Natural language description of code to generate", prefix="description:"
    )
    language: list[str] = dspy.InputField(
        desc="Programming language (e.g., 'python', 'javascript')", prefix="language:"
    )

    # Output fields
    code: list[str] | None = dspy.OutputField(desc="Generated code")
    explanation: list[str] | None = dspy.OutputField(desc="Explanation of generated code")


__all__ = [
    "CodeGenerationSignature",
    "QuestionAnsweringSignature",
    "SentimentAnalysisSignature",
    "TextSummarizationSignature",
    "TextTranslationSignature",
]

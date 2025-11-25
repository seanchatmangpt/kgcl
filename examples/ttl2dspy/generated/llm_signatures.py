"""Auto-generated DSPy signatures from SHACL shapes."""

# This file is auto-generated. Do not edit manually.

from typing import List, Optional
import dspy


class TextSummarizationSignature(dspy.Signature):
    """Generate a concise summary of input text
    """

    # Input fields
    text: List[str] = dspy.InputField(desc="Long text to summarize", prefix="text:")
    max_length: List[int] = dspy.InputField(desc="Maximum summary length in words", prefix="max_length:")

    # Output fields
    summary: Optional[List[str]] = dspy.OutputField(desc="Generated summary")


class QuestionAnsweringSignature(dspy.Signature):
    """Answer questions based on provided context
    """

    # Input fields
    question: List[str] = dspy.InputField(desc="Question to answer", prefix="question:")
    context: List[str] = dspy.InputField(desc="Context for answering the question", prefix="context:")

    # Output fields
    answer: Optional[List[str]] = dspy.OutputField(desc="Generated answer")
    confidence: Optional[List[float]] = dspy.OutputField(desc="Answer confidence score")


class SentimentAnalysisSignature(dspy.Signature):
    """Analyze sentiment of text
    """

    # Input fields
    text: List[str] = dspy.InputField(desc="Text to analyze", prefix="text:")

    # Output fields
    sentiment: Optional[List[str]] = dspy.OutputField(desc="Predicted sentiment (positive, negative, neutral)")
    score: Optional[List[float]] = dspy.OutputField(desc="Sentiment score (-1 to 1)")


class TextTranslationSignature(dspy.Signature):
    """Translate text between languages
    """

    # Input fields
    text: List[str] = dspy.InputField(desc="Text to translate", prefix="text:")
    source_language: List[str] = dspy.InputField(desc="Source language code (e.g., 'en', 'es')", prefix="source_language:")
    target_language: List[str] = dspy.InputField(desc="Target language code", prefix="target_language:")

    # Output fields
    translation: Optional[List[str]] = dspy.OutputField(desc="Translated text")


class CodeGenerationSignature(dspy.Signature):
    """Generate code from natural language description
    """

    # Input fields
    description: List[str] = dspy.InputField(desc="Natural language description of code to generate", prefix="description:")
    language: List[str] = dspy.InputField(desc="Programming language (e.g., 'python', 'javascript')", prefix="language:")

    # Output fields
    code: Optional[List[str]] = dspy.OutputField(desc="Generated code")
    explanation: Optional[List[str]] = dspy.OutputField(desc="Explanation of generated code")


__all__ = [
    "TextSummarizationSignature",
    "QuestionAnsweringSignature",
    "SentimentAnalysisSignature",
    "TextTranslationSignature",
    "CodeGenerationSignature",
]
"""Abstract base class for all code generators.

This module defines the core generator interface following the Template Method pattern.
All concrete generators must inherit from BaseGenerator and implement required methods.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


class Parser[T](Protocol):
    """Protocol for input parsers.

    Parsers are responsible for reading input files and converting them
    into structured metadata that generators can consume.

    Type Parameters
    ---------------
    T
        Type of parsed metadata
    """

    def parse(self, input_path: Path) -> T:
        """Parse input file and return structured metadata.

        Parameters
        ----------
        input_path : Path
            Path to input file

        Returns
        -------
        T
            Parsed metadata of type T

        Raises
        ------
        FileNotFoundError
            If input file doesn't exist
        ParseError
            If parsing fails
        """
        ...


@dataclass(frozen=True)
class GenerationResult:
    """Result of code generation operation.

    Parameters
    ----------
    output_path : Path
        Path to generated output file
    source : str
        Generated source code
    metadata : dict[str, Any]
        Additional metadata about the generation
    """

    output_path: Path
    source: str
    metadata: dict[str, Any]


class BaseGenerator[T](ABC):
    """Abstract base generator for all code generation.

    This class implements the Template Method pattern, providing a standard
    workflow while allowing subclasses to customize individual steps.

    The generation workflow is:
    1. Parse input file → structured metadata
    2. Transform metadata → generation context
    3. Render template with context
    4. Validate generated code
    5. Write output file

    Type Parameters
    ---------------
    T
        Type of parsed metadata (e.g., JavaClass, RDFGraph)

    Notes
    -----
    Subclasses must implement:
    - parser property: Return parser instance
    - _transform: Convert parsed metadata to template context
    - _get_template_name: Return template file name
    - _get_output_path: Determine output file path

    Subclasses may override:
    - _validate: Custom validation logic
    - _post_process: Post-generation processing
    """

    def __init__(self, template_dir: Path, output_dir: Path, dry_run: bool = False) -> None:
        """Initialize generator with configuration.

        Parameters
        ----------
        template_dir : Path
            Directory containing Jinja2 templates
        output_dir : Path
            Root directory for generated output
        dry_run : bool
            If True, don't write output files (default: False)

        Raises
        ------
        FileNotFoundError
            If template directory doesn't exist
        """
        from kgcl.codegen.base.template_engine import TemplateEngine

        self.template_dir = template_dir
        self.output_dir = output_dir
        self.dry_run = dry_run
        self.template_engine = TemplateEngine(template_dir)

        # Ensure output directory exists
        if not dry_run:
            self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    @abstractmethod
    def parser(self) -> Parser[T]:
        """Return parser instance for this generator.

        Returns
        -------
        Parser[T]
            Parser that converts input files to metadata type T
        """
        ...

    def generate(self, input_path: Path, **kwargs: Any) -> GenerationResult:
        """Generate code from input file.

        This is the main Template Method that orchestrates the generation workflow.
        Subclasses should NOT override this method - override individual steps instead.

        Parameters
        ----------
        input_path : Path
            Path to input file
        **kwargs : Any
            Additional generation options passed to subclass methods

        Returns
        -------
        GenerationResult
            Generation result with output path, source, and metadata

        Raises
        ------
        FileNotFoundError
            If input file doesn't exist
        ValidationError
            If generated code fails validation
        """
        # 1. Parse input file
        metadata = self.parser.parse(input_path)

        # 2. Transform to template context
        context = self._transform(metadata, **kwargs)

        # 3. Get template name
        template_name = self._get_template_name(metadata, **kwargs)

        # 4. Render template
        source = self.template_engine.render(template_name, context)

        # 5. Validate generated code
        self._validate(source, metadata, **kwargs)

        # 6. Post-process
        source = self._post_process(source, metadata, **kwargs)

        # 7. Get output path
        output_path = self._get_output_path(metadata, **kwargs)

        # 8. Write output file (unless dry run)
        if not self.dry_run:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(source, encoding="utf-8")

        # 9. Build result metadata
        result_metadata = self._build_metadata(metadata, **kwargs)

        return GenerationResult(output_path=output_path, source=source, metadata=result_metadata)

    @abstractmethod
    def _transform(self, metadata: T, **kwargs: Any) -> dict[str, Any]:
        """Transform parsed metadata into template context.

        Parameters
        ----------
        metadata : T
            Parsed metadata from input file
        **kwargs : Any
            Additional transformation options

        Returns
        -------
        dict[str, Any]
            Context dictionary for template rendering
        """
        ...

    @abstractmethod
    def _get_template_name(self, metadata: T, **kwargs: Any) -> str:
        """Get template file name for this metadata.

        Parameters
        ----------
        metadata : T
            Parsed metadata
        **kwargs : Any
            Additional options

        Returns
        -------
        str
            Template file name (relative to template_dir)
        """
        ...

    @abstractmethod
    def _get_output_path(self, metadata: T, **kwargs: Any) -> Path:
        """Determine output file path for generated code.

        Parameters
        ----------
        metadata : T
            Parsed metadata
        **kwargs : Any
            Additional options (may include output_path override)

        Returns
        -------
        Path
            Output file path
        """
        ...

    def _validate(self, source: str, metadata: T, **kwargs: Any) -> None:
        """Validate generated code.

        Default implementation does no validation. Subclasses can override
        to add syntax checking, linting, type checking, etc.

        Parameters
        ----------
        source : str
            Generated source code
        metadata : T
            Original metadata
        **kwargs : Any
            Additional validation options

        Raises
        ------
        ValidationError
            If validation fails

        Notes
        -----
        Default implementation performs no validation.
        Subclasses can override to add validation logic.
        """
        return  # No validation by default

    def _post_process(self, source: str, metadata: T, **kwargs: Any) -> str:
        """Post-process generated code.

        Default implementation returns source unchanged. Subclasses can override
        to add formatting, imports cleanup, etc.

        Parameters
        ----------
        source : str
            Generated source code
        metadata : T
            Original metadata
        **kwargs : Any
            Additional processing options

        Returns
        -------
        str
            Post-processed source code
        """
        return source

    def _build_metadata(self, metadata: T, **kwargs: Any) -> dict[str, Any]:
        """Build result metadata.

        Default implementation returns empty dict. Subclasses can override
        to include generation statistics, warnings, etc.

        Parameters
        ----------
        metadata : T
            Original parsed metadata
        **kwargs : Any
            Additional options

        Returns
        -------
        dict[str, Any]
            Result metadata
        """
        return {}

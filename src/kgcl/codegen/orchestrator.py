"""Unified code generation orchestrator.

Provides high-level interface for generating multiple output formats from
RDF ontologies: DSPy signatures, YAWL specifications, Python modules, etc.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from kgcl.codegen.base.generator import GenerationResult
from kgcl.codegen.dspy_config import configure_dspy, is_dspy_configured
from kgcl.codegen.generators.dspy_generator import DSPySignatureGenerator
from kgcl.codegen.generators.python_generator import PythonClassStyle, PythonModuleGenerator
from kgcl.codegen.generators.yawl_generator import YAWLSpecificationGenerator
from kgcl.codegen.registry import GeneratorRegistry


class OutputFormat(str, Enum):
    """Supported output formats for code generation."""

    DSPY = "dspy"
    YAWL = "yawl"
    PYTHON_DATACLASS = "python-dataclass"
    PYTHON_PYDANTIC = "python-pydantic"
    PYTHON_PLAIN = "python-plain"


@dataclass(frozen=True)
class GenerationConfig:
    """Configuration for code generation.

    Parameters
    ----------
    format : OutputFormat
        Output format to generate
    output_dir : Path
        Root directory for generated files
    template_dir : Path | None
        Directory containing templates (optional for some generators)
    dry_run : bool
        If True, don't write files (default: False)
    cache_size : int
        Graph cache size for DSPy (default: 100)
    max_workers : int
        Parallel workers for DSPy (default: 4)
    dspy_model : str | None
        DSPy model to configure (default: None - uses env/config)
    dspy_api_base : str | None
        DSPy API base URL (default: None - uses env/config)
    """

    format: OutputFormat
    output_dir: Path
    template_dir: Path | None = None
    dry_run: bool = False
    cache_size: int = 100
    max_workers: int = 4
    dspy_model: str | None = None
    dspy_api_base: str | None = None


class CodeGenOrchestrator:
    """Unified orchestrator for all code generation.

    Provides single interface for generating multiple output formats from RDF
    ontologies, automatically selecting and configuring the appropriate generator.

    Examples
    --------
    >>> # Generate DSPy signatures
    >>> config = GenerationConfig(format=OutputFormat.DSPY, output_dir=Path("generated/dspy"))
    >>> orchestrator = CodeGenOrchestrator()
    >>> result = orchestrator.generate(Path("ontology.ttl"), config)

    >>> # Generate YAWL specification
    >>> config = GenerationConfig(
    ...     format=OutputFormat.YAWL, output_dir=Path("generated/yawl"), template_dir=Path("templates/yawl")
    ... )
    >>> result = orchestrator.generate(Path("workflow.ttl"), config)

    >>> # Generate Python dataclasses
    >>> config = GenerationConfig(
    ...     format=OutputFormat.PYTHON_DATACLASS,
    ...     output_dir=Path("generated/python"),
    ...     template_dir=Path("templates/python"),
    ... )
    >>> result = orchestrator.generate(Path("ontology.ttl"), config)
    """

    def __init__(self, registry: GeneratorRegistry | None = None) -> None:
        """Initialize orchestrator with generator registry.

        Parameters
        ----------
        registry : GeneratorRegistry | None
            Generator registry (creates new if None)
        """
        self.registry = registry or GeneratorRegistry()
        self._register_builtin_generators()

    def _register_builtin_generators(self) -> None:
        """Register all built-in generators."""
        # DSPy generator
        self.registry.register(
            "dspy",
            lambda **kwargs: DSPySignatureGenerator(**kwargs),
            description="Generate DSPy signatures from RDF/SHACL",
            file_types=[".ttl", ".rdf", ".owl"],
            category="dspy",
        )

        # YAWL generator
        self.registry.register(
            "yawl",
            lambda **kwargs: YAWLSpecificationGenerator(**kwargs),
            description="Generate YAWL workflow specifications from RDF",
            file_types=[".ttl", ".rdf", ".owl"],
            category="workflow",
        )

        # Python generators
        def _make_python_factory(style: str) -> Callable[..., PythonModuleGenerator]:
            """Create factory for Python generator with specific style."""
            return lambda **kwargs: PythonModuleGenerator(**kwargs, class_style=style)  # type: ignore[arg-type]

        for style in ["dataclass", "pydantic", "plain"]:
            self.registry.register(
                f"python-{style}",
                _make_python_factory(style),
                description=f"Generate Python {style} classes from RDF",
                file_types=[".ttl", ".rdf", ".owl"],
                category="python",
            )

    def generate(self, input_path: Path, config: GenerationConfig, **kwargs: Any) -> GenerationResult:
        """Generate code from RDF ontology.

        Parameters
        ----------
        input_path : Path
            Path to RDF input file
        config : GenerationConfig
            Generation configuration
        **kwargs : Any
            Additional generator-specific options

        Returns
        -------
        GenerationResult
            Generation result with output path, source, and metadata

        Raises
        ------
        FileNotFoundError
            If input file doesn't exist
        ValueError
            If configuration is invalid

        Examples
        --------
        >>> config = GenerationConfig(format=OutputFormat.DSPY, output_dir=Path("out"))
        >>> result = orchestrator.generate(Path("ontology.ttl"), config)
        """
        if not input_path.exists():
            msg = f"Input file not found: {input_path}"
            raise FileNotFoundError(msg)

        # Configure DSPy if needed
        if config.format == OutputFormat.DSPY and not is_dspy_configured():
            configure_dspy(model=config.dspy_model, api_base=config.dspy_api_base)

        # Get template directory
        template_dir = config.template_dir or self._get_default_template_dir(config.format)

        # Create generator with appropriate configuration
        generator = self._create_generator(config, template_dir)

        # Generate code
        return generator.generate(input_path, **kwargs)

    def _get_default_template_dir(self, format: OutputFormat) -> Path:  # noqa: A002
        """Get default template directory for format.

        Parameters
        ----------
        format : OutputFormat
            Output format

        Returns
        -------
        Path
            Default template directory
        """
        # For DSPy, templates not needed (uses transpiler directly)
        if format == OutputFormat.DSPY:
            return Path("templates/dspy")  # Unused but required by BaseGenerator

        # For YAWL and Python, use bundled templates
        base_dir = Path(__file__).parent.parent / "templates"

        if format == OutputFormat.YAWL:
            return base_dir / "yawl"

        if format.value.startswith("python-"):
            return base_dir / "python"

        return base_dir / "default"

    def _create_generator(self, config: GenerationConfig, template_dir: Path) -> Any:
        """Create generator instance for configuration.

        Parameters
        ----------
        config : GenerationConfig
            Generation configuration
        template_dir : Path
            Template directory

        Returns
        -------
        Any
            Generator instance

        Raises
        ------
        ValueError
            If format is unsupported
        """
        common_kwargs = {"template_dir": template_dir, "output_dir": config.output_dir, "dry_run": config.dry_run}

        if config.format == OutputFormat.DSPY:
            return DSPySignatureGenerator(**common_kwargs, cache_size=config.cache_size, max_workers=config.max_workers)

        if config.format == OutputFormat.YAWL:
            return YAWLSpecificationGenerator(**common_kwargs)

        if config.format in {OutputFormat.PYTHON_DATACLASS, OutputFormat.PYTHON_PYDANTIC, OutputFormat.PYTHON_PLAIN}:
            style: PythonClassStyle = config.format.value.replace("python-", "")  # type: ignore[assignment]
            return PythonModuleGenerator(**common_kwargs, class_style=style)

        msg = f"Unsupported output format: {config.format}"
        raise ValueError(msg)

    def generate_multiple(
        self, input_paths: list[Path], config: GenerationConfig, **kwargs: Any
    ) -> list[GenerationResult]:
        """Generate code from multiple RDF files.

        Parameters
        ----------
        input_paths : list[Path]
            List of RDF input files
        config : GenerationConfig
            Generation configuration
        **kwargs : Any
            Additional generator-specific options

        Returns
        -------
        list[GenerationResult]
            Generation results for each input

        Examples
        --------
        >>> files = [Path("onto1.ttl"), Path("onto2.ttl")]
        >>> results = orchestrator.generate_multiple(files, config)
        """
        results = []
        for input_path in input_paths:
            result = self.generate(input_path, config, **kwargs)
            results.append(result)
        return results

    def list_formats(self) -> list[str]:
        """List all supported output formats.

        Returns
        -------
        list[str]
            List of format names
        """
        return [fmt.value for fmt in OutputFormat]

    def get_format_info(self, format_name: str) -> dict[str, Any]:
        """Get information about a specific format.

        Parameters
        ----------
        format_name : str
            Format name (e.g., "dspy", "yawl")

        Returns
        -------
        dict[str, Any]
            Format metadata

        Raises
        ------
        ValueError
            If format is unknown
        """
        try:
            format_enum = OutputFormat(format_name)
        except ValueError as e:
            msg = f"Unknown format: {format_name}"
            raise ValueError(msg) from e

        # Get generator metadata from registry
        generator_name = format_enum.value
        if generator_name in self.registry.list_generators():
            return self.registry.get_metadata(generator_name)

        return {"format": format_name, "description": f"{format_name} code generation"}


__all__ = ["CodeGenOrchestrator", "GenerationConfig", "OutputFormat"]

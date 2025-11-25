"""Base generator for KGC projections.

Provides abstract interface and common functionality for all projection
generators. Handles template rendering, error handling, and data transformation.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from rdflib import Graph


class ProjectionGenerator(ABC):
    """Abstract base class for all projection generators.

    Generators query RDF graph data, transform it to domain objects,
    and render artifacts using Jinja2 templates.

    Attributes:
        graph: RDF graph to query
        template_dir: Directory containing Jinja2 templates
        env: Jinja2 environment for template rendering
    """

    def __init__(
        self,
        graph: Graph,
        template_dir: Optional[Path] = None
    ) -> None:
        """Initialize generator with RDF graph and template directory.

        Args:
            graph: RDF graph containing knowledge base data
            template_dir: Directory with Jinja2 templates, defaults to
                         src/kgcl/templates/{generator_name}
        """
        self.graph = graph

        if template_dir is None:
            # Default to templates/{generator_name} relative to this file
            base_dir = Path(__file__).parent.parent / "templates"
            generator_name = self.__class__.__name__.replace("Generator", "").lower()
            template_dir = base_dir / generator_name

        self.template_dir = template_dir

        if not template_dir.exists():
            raise FileNotFoundError(
                f"Template directory not found: {template_dir}"
            )

        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True
        )

    @abstractmethod
    def gather_data(self) -> Dict[str, Any]:
        """Gather and transform data from RDF graph.

        Query the RDF graph for relevant triples, transform to domain
        objects, and return structured data for template rendering.

        Returns:
            Dictionary with data for template rendering

        Raises:
            ValueError: If required data is missing or invalid
        """
        pass

    @abstractmethod
    def generate(self, template_name: str = "default.md") -> str:
        """Generate artifact from template and gathered data.

        Args:
            template_name: Name of template file to render

        Returns:
            Rendered artifact as string

        Raises:
            TemplateNotFound: If template doesn't exist
            ValueError: If data gathering fails
        """
        pass

    def render_template(
        self,
        template_name: str,
        context: Dict[str, Any]
    ) -> str:
        """Render Jinja2 template with given context.

        Args:
            template_name: Name of template file
            context: Data dictionary for template rendering

        Returns:
            Rendered template as string

        Raises:
            TemplateNotFound: If template file doesn't exist
            Exception: If template rendering fails
        """
        try:
            template = self.env.get_template(template_name)
            return template.render(**context)
        except TemplateNotFound as e:
            raise TemplateNotFound(
                f"Template '{template_name}' not found in {self.template_dir}"
            ) from e
        except Exception as e:
            raise Exception(
                f"Failed to render template '{template_name}': {str(e)}"
            ) from e

    def validate_data(self, data: Dict[str, Any], required_keys: list[str]) -> None:
        """Validate that gathered data contains required keys.

        Args:
            data: Data dictionary to validate
            required_keys: List of required key names

        Raises:
            ValueError: If any required key is missing
        """
        missing = [key for key in required_keys if key not in data]
        if missing:
            raise ValueError(
                f"Missing required data keys: {', '.join(missing)}"
            )

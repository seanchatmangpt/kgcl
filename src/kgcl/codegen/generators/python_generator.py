"""Python module generator from RDF ontologies.

Generates Python dataclasses, Pydantic models, or plain classes from
RDF/OWL class definitions with properties and constraints.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from rdflib import Graph, Namespace
from rdflib.namespace import OWL, RDF, RDFS, XSD

from kgcl.codegen.base.generator import BaseGenerator, Parser

PythonClassStyle = Literal["dataclass", "pydantic", "plain"]


@dataclass(frozen=True)
class ClassDefinition:
    """Python class definition extracted from RDF.

    Parameters
    ----------
    uri : str
        Class URI
    name : str
        Python class name
    docstring : str
        Class documentation
    properties : list[dict[str, Any]]
        Class properties/fields
    parent_classes : list[str]
        Parent class names
    """

    uri: str
    name: str
    docstring: str
    properties: list[dict[str, Any]]
    parent_classes: list[str]


@dataclass(frozen=True)
class PythonModuleMetadata:
    """Metadata for Python module generation.

    Parameters
    ----------
    graph : Graph
        Parsed RDF graph
    classes : list[ClassDefinition]
        Class definitions extracted from ontology
    module_name : str
        Python module name
    imports : set[str]
        Required imports
    """

    graph: Graph
    classes: list[ClassDefinition]
    module_name: str
    imports: set[str]


class PythonClassParser(Parser[PythonModuleMetadata]):
    """Parser for RDF class definitions."""

    # Type mapping from XSD to Python
    TYPE_MAP: dict[str, str] = {
        str(XSD.string): "str",
        str(XSD.integer): "int",
        str(XSD.int): "int",
        str(XSD.long): "int",
        str(XSD.float): "float",
        str(XSD.double): "float",
        str(XSD.boolean): "bool",
        str(XSD.date): "date",
        str(XSD.dateTime): "datetime",
        str(XSD.time): "time",
    }

    def parse(self, input_path: Path) -> PythonModuleMetadata:
        """Parse RDF file and extract class definitions.

        Parameters
        ----------
        input_path : Path
            Path to RDF file

        Returns
        -------
        PythonModuleMetadata
            Parsed class metadata

        Raises
        ------
        FileNotFoundError
            If input file doesn't exist
        """
        if not input_path.exists():
            msg = f"RDF file not found: {input_path}"
            raise FileNotFoundError(msg)

        graph = Graph()
        graph.parse(str(input_path), format="turtle")

        # Extract all OWL classes
        classes = []
        imports: set[str] = set()

        for class_uri in graph.subjects(RDF.type, OWL.Class):
            class_def = self._extract_class(graph, class_uri, imports)
            if class_def:
                classes.append(class_def)

        module_name = input_path.stem

        return PythonModuleMetadata(graph=graph, classes=classes, module_name=module_name, imports=imports)

    def _extract_class(self, graph: Graph, class_uri: Any, imports: set[str]) -> ClassDefinition | None:
        """Extract class definition from RDF graph.

        Parameters
        ----------
        graph : Graph
            RDF graph
        class_uri : Any
            Class URI
        imports : set[str]
            Set to accumulate required imports

        Returns
        -------
        ClassDefinition | None
            Class definition or None if not extractable
        """
        # Get class name
        label = graph.value(class_uri, RDFS.label)
        name = str(label) if label else class_uri.split("/")[-1].split("#")[-1]

        # Convert to PascalCase
        name = "".join(word.capitalize() for word in name.replace("-", "_").replace(" ", "_").split("_"))

        # Get docstring
        comment = graph.value(class_uri, RDFS.comment)
        docstring = str(comment) if comment else f"Class representing {name}."

        # Get parent classes
        parent_classes = []
        for parent in graph.objects(class_uri, RDFS.subClassOf):
            if parent != OWL.Thing:
                parent_label = graph.value(parent, RDFS.label)
                parent_name = str(parent_label) if parent_label else str(parent).split("/")[-1].split("#")[-1]
                parent_classes.append(parent_name)

        # Get properties
        properties = []
        for prop in graph.subjects(RDFS.domain, class_uri):
            prop_def = self._extract_property(graph, prop, imports)
            if prop_def:
                properties.append(prop_def)

        return ClassDefinition(
            uri=str(class_uri), name=name, docstring=docstring, properties=properties, parent_classes=parent_classes
        )

    def _extract_property(self, graph: Graph, prop_uri: Any, imports: set[str]) -> dict[str, Any] | None:
        """Extract property definition.

        Parameters
        ----------
        graph : Graph
            RDF graph
        prop_uri : Any
            Property URI
        imports : set[str]
            Set to accumulate required imports

        Returns
        -------
        dict[str, Any] | None
            Property definition
        """
        # Get property name
        label = graph.value(prop_uri, RDFS.label)
        name = str(label) if label else prop_uri.split("/")[-1].split("#")[-1]

        # Convert to snake_case
        name = name.replace("-", "_").replace(" ", "_").lower()

        # Get property type
        range_val = graph.value(prop_uri, RDFS.range)
        if range_val:
            python_type = self.TYPE_MAP.get(str(range_val), "Any")
            if python_type in {"date", "datetime", "time"}:
                imports.add(f"from datetime import {python_type}")
        else:
            python_type = "Any"
            imports.add("from typing import Any")

        # Get docstring
        comment = graph.value(prop_uri, RDFS.comment)
        docstring = str(comment) if comment else f"{name} property"

        # Check if required
        # In a full implementation, check SHACL sh:minCount or OWL restrictions
        required = False

        return {
            "name": name,
            "type": python_type,
            "docstring": docstring,
            "required": required,
            "default": None if required else "None",
        }


class PythonModuleGenerator(BaseGenerator[PythonModuleMetadata]):
    """Generator for Python modules from RDF ontologies.

    Creates Python dataclasses, Pydantic models, or plain classes
    from OWL class definitions with properties.

    Parameters
    ----------
    template_dir : Path
        Directory containing Python templates
    output_dir : Path
        Root directory for generated modules
    dry_run : bool
        If True, don't write output files (default: False)
    class_style : PythonClassStyle
        Style of Python classes to generate (default: "dataclass")

    Examples
    --------
    >>> generator = PythonModuleGenerator(
    ...     template_dir=Path("templates/python"), output_dir=Path("generated"), class_style="dataclass"
    ... )
    >>> result = generator.generate(Path("ontology.ttl"))
    """

    def __init__(
        self, template_dir: Path, output_dir: Path, dry_run: bool = False, class_style: PythonClassStyle = "dataclass"
    ) -> None:
        """Initialize Python module generator."""
        super().__init__(template_dir, output_dir, dry_run)
        self.class_style = class_style
        self._parser = PythonClassParser()

    @property
    def parser(self) -> Parser[PythonModuleMetadata]:
        """Return Python class parser.

        Returns
        -------
        Parser[PythonModuleMetadata]
            Python class parser
        """
        return self._parser

    def _transform(self, metadata: PythonModuleMetadata, **kwargs: Any) -> dict[str, Any]:
        """Transform metadata to template context.

        Parameters
        ----------
        metadata : PythonModuleMetadata
            Parsed metadata
        **kwargs : Any
            Additional options

        Returns
        -------
        dict[str, Any]
            Template context
        """
        # Determine base imports based on class style
        base_imports = set(metadata.imports)

        if self.class_style == "dataclass":
            base_imports.add("from dataclasses import dataclass")
        elif self.class_style == "pydantic":
            base_imports.add("from pydantic import BaseModel")

        return {
            "module_name": metadata.module_name,
            "classes": [
                {
                    "name": cls.name,
                    "docstring": cls.docstring,
                    "properties": cls.properties,
                    "parent_classes": cls.parent_classes,
                    "uri": cls.uri,
                }
                for cls in metadata.classes
            ],
            "imports": sorted(base_imports),
            "class_style": self.class_style,
            "total_classes": len(metadata.classes),
        }

    def _get_template_name(self, metadata: PythonModuleMetadata, **kwargs: Any) -> str:
        """Get template name based on class style.

        Parameters
        ----------
        metadata : PythonModuleMetadata
            Parsed metadata
        **kwargs : Any
            Additional options

        Returns
        -------
        str
            Template name
        """
        return f"python_{self.class_style}.py.j2"

    def _get_output_path(self, metadata: PythonModuleMetadata, **kwargs: Any) -> Path:
        """Determine output file path.

        Parameters
        ----------
        metadata : PythonModuleMetadata
            Parsed metadata
        **kwargs : Any
            May include 'output_path' override

        Returns
        -------
        Path
            Output file path
        """
        if "output_path" in kwargs:
            return Path(kwargs["output_path"])

        return self.output_dir / f"{metadata.module_name}.py"

    def _post_process(self, source: str, metadata: PythonModuleMetadata, **kwargs: Any) -> str:
        """Post-process generated Python code.

        Parameters
        ----------
        source : str
            Generated source code
        metadata : PythonModuleMetadata
            Original metadata
        **kwargs : Any
            Additional options

        Returns
        -------
        str
            Post-processed source
        """
        # Remove duplicate blank lines
        lines = source.split("\n")
        result = []
        prev_blank = False

        for line in lines:
            is_blank = not line.strip()
            if is_blank and prev_blank:
                continue  # Skip consecutive blank lines
            result.append(line)
            prev_blank = is_blank

        return "\n".join(result)


__all__ = ["PythonModuleGenerator", "PythonModuleMetadata", "PythonClassParser", "ClassDefinition"]

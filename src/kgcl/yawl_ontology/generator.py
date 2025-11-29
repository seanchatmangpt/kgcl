"""RDF/Turtle ontology generator for YAWL codebase.

Generates semantic ontologies from Java source code using Jinja2 templates
and RDFLib for validation.
"""

from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Template
from rdflib import Graph

from kgcl.yawl_ontology.parser import ClassInfo, JavaParser


@dataclass
class PackageInfo:
    """Package metadata for ontology generation."""

    name: str
    classes: list[ClassInfo] = field(default_factory=list)

    @property
    def clean_name(self) -> str:
        """URI-safe package name."""
        return self.name.replace(".", "_")


TURTLE_TEMPLATE = """@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix yawl: <http://yawlfoundation.org/ontology/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .

# YAWL Ontology Schema
yawl:Package a owl:Class ;
    rdfs:label "Java Package" .

yawl:Class a owl:Class ;
    rdfs:label "Java Class" .

yawl:Method a owl:Class ;
    rdfs:label "Java Method" .

yawl:Field a owl:Class ;
    rdfs:label "Java Field" .

yawl:inPackage a owl:ObjectProperty ;
    rdfs:domain yawl:Class ;
    rdfs:range yawl:Package .

yawl:hasMethod a owl:ObjectProperty ;
    rdfs:domain yawl:Class ;
    rdfs:range yawl:Method .

yawl:hasField a owl:ObjectProperty ;
    rdfs:domain yawl:Class ;
    rdfs:range yawl:Field .

yawl:extends a owl:ObjectProperty ;
    rdfs:domain yawl:Class ;
    rdfs:range yawl:Class .

yawl:implements a owl:ObjectProperty ;
    rdfs:domain yawl:Class ;
    rdfs:range yawl:Class .

yawl:filePath a owl:DatatypeProperty ;
    rdfs:domain yawl:Class ;
    rdfs:range xsd:string .

yawl:signature a owl:DatatypeProperty ;
    rdfs:domain yawl:Method ;
    rdfs:range xsd:string .

yawl:returnType a owl:DatatypeProperty ;
    rdfs:domain yawl:Method ;
    rdfs:range xsd:string .

yawl:modifiers a owl:DatatypeProperty ;
    rdfs:range xsd:string .

{% for package in packages %}
# Package: {{ package.name }}
yawl:{{ package.clean_name }} a yawl:Package ;
    rdfs:label "{{ package.name }}" .

{% for cls in package.classes %}
# Class: {{ cls.fully_qualified_name }}
yawl:{{ cls.clean_name }} a yawl:Class ;
    rdfs:label "{{ cls.name }}" ;
    yawl:inPackage yawl:{{ package.clean_name }} ;
    yawl:filePath "{{ cls.file_path }}"^^xsd:string ;
    {%- if cls.javadoc %}
    rdfs:comment \"\"\"{{ cls.javadoc }}\"\"\" ;
    {%- endif %}
    {%- if cls.extends %}
    yawl:extends yawl:{{ cls.extends }} ;
    {%- endif %}
    {%- for iface in cls.implements %}
    yawl:implements yawl:{{ iface }} ;
    {%- endfor %}
    {%- for modifier in cls.modifiers %}
    yawl:modifiers "{{ modifier }}" ;
    {%- endfor %}
    {%- for method in cls.methods %}
    yawl:hasMethod yawl:{{ cls.clean_name }}_{{ method.clean_name }}_{{ loop.index }} ;
    {%- endfor %}
    {%- for field_name in cls.fields %}
    yawl:hasField yawl:{{ cls.clean_name }}_{{ field_name }} ;
    {%- endfor %}
    .

{% for method in cls.methods %}
# Method: {{ cls.name }}.{{ method.name }}
yawl:{{ cls.clean_name }}_{{ method.clean_name }}_{{ loop.index }} a yawl:Method ;
    rdfs:label "{{ method.name }}" ;
    yawl:returnType "{{ method.return_type }}" ;
    yawl:signature "{{ method.signature }}" ;
    {%- if method.javadoc %}
    rdfs:comment \"\"\"{{ method.javadoc }}\"\"\" ;
    {%- endif %}
    {%- for modifier in method.modifiers %}
    yawl:modifiers "{{ modifier }}" ;
    {%- endfor %}
    .
{% endfor %}

{% for field_name in cls.fields %}
yawl:{{ cls.clean_name }}_{{ field_name }} a yawl:Field ;
    rdfs:label "{{ field_name }}" .
{% endfor %}

{% endfor %}
{% endfor %}
"""


class YawlOntologyGenerator:
    """Generate RDF/Turtle ontology from YAWL Java codebase."""

    def __init__(self) -> None:
        """Initialize ontology generator."""
        self.parser = JavaParser()
        self.template = Template(TURTLE_TEMPLATE)

    def generate_from_directory(self, source_root: Path, output_file: Path) -> None:
        """Generate ontology from Java source directory.

        Parameters
        ----------
        source_root : Path
            Root directory containing Java source files
        output_file : Path
            Path to write generated Turtle ontology

        Raises
        ------
        ValueError
            If source_root does not exist or is not a directory
        """
        if not source_root.exists():
            msg = f"Source directory does not exist: {source_root}"
            raise ValueError(msg)
        if not source_root.is_dir():
            msg = f"Source path is not a directory: {source_root}"
            raise ValueError(msg)

        java_files = list(source_root.rglob("*.java"))
        print(f"Found {len(java_files)} Java files in {source_root}")

        packages: dict[str, PackageInfo] = {}
        for java_file in java_files:
            classes = self.parser.parse_file(java_file)
            for cls in classes:
                if cls.package not in packages:
                    packages[cls.package] = PackageInfo(name=cls.package)
                packages[cls.package].classes.append(cls)

        print(f"Parsed {len(packages)} packages")
        turtle_content = self.template.render(packages=list(packages.values()))

        self._validate_turtle(turtle_content)

        output_file.write_text(turtle_content, encoding="utf-8")
        print(f"Generated ontology: {output_file} ({len(turtle_content)} bytes)")

    def _validate_turtle(self, content: str) -> None:
        """Validate generated Turtle syntax using RDFLib.

        Parameters
        ----------
        content : str
            Turtle content to validate

        Raises
        ------
        ValueError
            If Turtle syntax is invalid
        """
        try:
            g = Graph()
            g.parse(data=content, format="turtle")
            print(f"Validation successful: {len(g)} triples")
        except Exception as e:
            msg = f"Invalid Turtle syntax: {e}"
            raise ValueError(msg) from e

"""FilesystemTemplateRegistry - Load templates from filesystem with frontmatter.

This registry implementation scans a directory for Jinja2 templates (.j2 files)
and parses their YAML frontmatter to construct TemplateDescriptor instances.

Examples
--------
>>> from pathlib import Path
>>> registry = FilesystemTemplateRegistry(Path("/templates"))
>>> registry.list_templates()
[]
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from kgcl.projection.domain.descriptors import (
    N3RuleDescriptor,
    OntologyConfig,
    QueryDescriptor,
    TemplateDescriptor,
    TemplateMetadata,
    create_n3_rule_from_dict,
    create_query_from_dict,
)
from kgcl.projection.domain.exceptions import ResourceLimitExceeded


class FilesystemTemplateRegistry:
    """Registry that loads templates from filesystem.

    Scans a directory for .j2 files, parses YAML frontmatter (delimited by ---),
    and constructs TemplateDescriptor instances with all metadata, queries,
    and N3 rules.

    Parameters
    ----------
    template_dir : Path
        Directory containing .j2 template files.
    query_dir : Path | None
        Optional directory for external query files (default: template_dir/queries).

    Attributes
    ----------
    template_dir : Path
        Root directory for templates.
    query_dir : Path
        Directory for external SPARQL query files.

    Examples
    --------
    >>> from pathlib import Path
    >>> from tempfile import TemporaryDirectory
    >>> with TemporaryDirectory() as tmpdir:
    ...     template_dir = Path(tmpdir)
    ...     registry = FilesystemTemplateRegistry(template_dir)
    ...     registry.list_templates()
    []
    """

    def __init__(self, template_dir: Path, query_dir: Path | None = None, max_template_size: int | None = None) -> None:
        """Initialize registry with template directory.

        Parameters
        ----------
        template_dir : Path
            Directory containing .j2 template files.
        query_dir : Path | None
            Optional directory for external query files.
        max_template_size : int | None
            Maximum template file size in bytes. If None, no limit.
        """
        self._template_dir = template_dir
        self._query_dir = query_dir if query_dir else template_dir / "queries"
        self._max_template_size = max_template_size
        self._cache: dict[str, TemplateDescriptor] = {}

    @property
    def template_dir(self) -> Path:
        """Return template directory.

        Returns
        -------
        Path
            Root directory for templates.
        """
        return self._template_dir

    @property
    def query_dir(self) -> Path:
        """Return query directory.

        Returns
        -------
        Path
            Directory for external SPARQL files.
        """
        return self._query_dir

    def get(self, name: str) -> TemplateDescriptor | None:
        """Load and return a template descriptor by name.

        Parameters
        ----------
        name : str
            Template name (with or without .j2 extension).

        Returns
        -------
        TemplateDescriptor | None
            Parsed template with frontmatter, or None if not found.

        Examples
        --------
        >>> from pathlib import Path
        >>> from tempfile import TemporaryDirectory
        >>> with TemporaryDirectory() as tmpdir:
        ...     template_dir = Path(tmpdir)
        ...     registry = FilesystemTemplateRegistry(template_dir)
        ...     registry.get("missing.j2") is None
        True
        """
        # Normalize name: ensure .j2 extension
        if not name.endswith(".j2"):
            name = f"{name}.j2"

        # Check cache
        if name in self._cache:
            return self._cache[name]

        # Resolve path
        template_path = self._template_dir / name
        if not template_path.exists():
            return None

        # Parse and cache
        descriptor = self._parse_template(template_path)
        self._cache[name] = descriptor
        return descriptor

    def list_templates(self) -> list[str]:
        """List all available template names.

        Returns
        -------
        list[str]
            Template names (relative to template_dir).

        Examples
        --------
        >>> from pathlib import Path
        >>> from tempfile import TemporaryDirectory
        >>> with TemporaryDirectory() as tmpdir:
        ...     template_dir = Path(tmpdir)
        ...     (template_dir / "test.j2").write_text("---\\nid: test\\n---\\nBody")
        ...     registry = FilesystemTemplateRegistry(template_dir)
        ...     "test.j2" in registry.list_templates()
        True
        """
        if not self._template_dir.exists():
            return []

        templates = []
        for path in self._template_dir.rglob("*.j2"):
            relative = path.relative_to(self._template_dir)
            templates.append(str(relative))

        return sorted(templates)

    def exists(self, name: str) -> bool:
        """Check if a template exists.

        Parameters
        ----------
        name : str
            Template name to check.

        Returns
        -------
        bool
            True if template exists.

        Examples
        --------
        >>> from pathlib import Path
        >>> from tempfile import TemporaryDirectory
        >>> with TemporaryDirectory() as tmpdir:
        ...     template_dir = Path(tmpdir)
        ...     registry = FilesystemTemplateRegistry(template_dir)
        ...     registry.exists("missing.j2")
        False
        """
        if not name.endswith(".j2"):
            name = f"{name}.j2"
        return (self._template_dir / name).exists()

    def _parse_template(self, path: Path) -> TemplateDescriptor:
        """Parse template file and extract frontmatter.

        Parameters
        ----------
        path : Path
            Path to template file.

        Returns
        -------
        TemplateDescriptor
            Parsed template descriptor.

        Raises
        ------
        ValueError
            If frontmatter is invalid or required fields are missing.
        ResourceLimitExceeded
            If template file exceeds max_template_size.
        """
        # Check file size limit before reading
        if self._max_template_size is not None:
            file_size = path.stat().st_size
            if file_size > self._max_template_size:
                raise ResourceLimitExceeded(f"template_size:{path.name}", self._max_template_size, file_size)

        content = path.read_text(encoding="utf-8")

        # Extract frontmatter (between --- delimiters)
        frontmatter_pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
        match = re.match(frontmatter_pattern, content, re.DOTALL)

        if not match:
            msg = f"Template {path} missing frontmatter (must start with ---)"
            raise ValueError(msg)

        frontmatter_text = match.group(1)
        raw_content = match.group(2)

        # Parse YAML frontmatter
        try:
            frontmatter = yaml.safe_load(frontmatter_text)
        except yaml.YAMLError as e:
            msg = f"Invalid YAML frontmatter in {path}: {e}"
            raise ValueError(msg) from e

        if not isinstance(frontmatter, dict):
            msg = f"Frontmatter in {path} must be a YAML object/dict"
            raise ValueError(msg)

        # Extract required fields
        template_id = frontmatter.get("id", "")
        if not template_id:
            msg = f"Template {path} missing required 'id' field"
            raise ValueError(msg)

        engine = frontmatter.get("engine", "jinja2")
        language = frontmatter.get("language", "")
        framework = frontmatter.get("framework", "")
        version = frontmatter.get("version", "1.0.0")

        # Parse ontology config
        ontology_data = frontmatter.get("ontology", {})
        if isinstance(ontology_data, str):
            # Simple string: just graph_id
            ontology = OntologyConfig(graph_id=ontology_data)
        elif isinstance(ontology_data, dict):
            ontology = OntologyConfig(
                graph_id=ontology_data.get("graph_id", "main"), base_iri=ontology_data.get("base_iri", "")
            )
        else:
            ontology = OntologyConfig(graph_id="main")

        # Parse queries
        queries_data = frontmatter.get("queries", [])
        queries: list[QueryDescriptor] = []
        for query_dict in queries_data:
            if isinstance(query_dict, dict):
                # Load external query files if needed
                if "file" in query_dict:
                    file_path = query_dict["file"]
                    full_path = self._query_dir / file_path
                    if full_path.exists():
                        query_dict = dict(query_dict)  # Copy to avoid mutation
                        query_dict["inline"] = full_path.read_text(encoding="utf-8")
                        query_dict.pop("file")
                queries.append(create_query_from_dict(query_dict))

        # Parse N3 rules
        n3_rules_data = frontmatter.get("n3_rules", [])
        n3_rules: list[N3RuleDescriptor] = []
        for rule_dict in n3_rules_data:
            if isinstance(rule_dict, dict):
                n3_rules.append(create_n3_rule_from_dict(rule_dict))

        # Parse metadata
        metadata_data = frontmatter.get("metadata", {})
        if isinstance(metadata_data, dict):
            metadata = TemplateMetadata(
                author=metadata_data.get("author", ""),
                description=metadata_data.get("description", ""),
                tags=tuple(metadata_data.get("tags", [])),
            )
        else:
            metadata = TemplateMetadata()

        return TemplateDescriptor(
            id=template_id,
            engine=engine,
            language=language,
            framework=framework,
            version=version,
            ontology=ontology,
            queries=tuple(queries),
            n3_rules=tuple(n3_rules),
            metadata=metadata,
            template_path=str(path),
            raw_content=raw_content,
        )

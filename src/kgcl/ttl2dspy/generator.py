"""DSPy code generator for SHACL shapes."""

import logging
from dataclasses import dataclass, field

from .parser import PropertyShape, SHACLShape

logger = logging.getLogger(__name__)


@dataclass
class SignatureDefinition:
    """Represents a generated DSPy Signature class."""

    class_name: str
    docstring: str | None = None
    inputs: list[PropertyShape] = field(default_factory=list)
    outputs: list[PropertyShape] = field(default_factory=list)
    base_classes: list[str] = field(default_factory=lambda: ["dspy.Signature"])

    def generate_code(self) -> str:
        """Generate Python code for this signature.

        Returns
        -------
            Python code as string
        """
        lines = []

        # Class definition
        bases = ", ".join(self.base_classes)
        lines.append(f"class {self.class_name}({bases}):")

        # Docstring
        if self.docstring:
            # Indent docstring
            doc_lines = self.docstring.split("\n")
            lines.append(f'    """{doc_lines[0]}')
            for line in doc_lines[1:]:
                lines.append(f"    {line}")
            lines.append('    """')
        else:
            lines.append(f'    """DSPy signature for {self.class_name}."""')

        # Input fields
        if self.inputs:
            lines.append("")
            lines.append("    # Input fields")
            for prop in self.inputs:
                field_def = self._generate_field(prop, is_input=True)
                lines.append(f"    {field_def}")

        # Output fields
        if self.outputs:
            lines.append("")
            lines.append("    # Output fields")
            for prop in self.outputs:
                field_def = self._generate_field(prop, is_input=False)
                lines.append(f"    {field_def}")

        # Empty body if no fields
        if not self.inputs and not self.outputs:
            lines.append("    pass")

        return "\n".join(lines)

    def _generate_field(self, prop: PropertyShape, is_input: bool) -> str:
        """Generate a field definition.

        Args:
            prop: PropertyShape to generate
            is_input: Whether this is an input field

        Returns
        -------
            Field definition string
        """
        # Get Python type
        python_type = prop.get_python_type()

        # Build InputField/OutputField
        field_class = "dspy.InputField" if is_input else "dspy.OutputField"
        field_args = []

        # Add description
        if prop.description:
            desc = prop.description.replace('"', '\\"')
            field_args.append(f'desc="{desc}"')

        # Add prefix for clarity
        if is_input:
            field_args.append(f'prefix="{prop.name}:"')

        # Build field call
        field_call = (
            f"{field_class}({', '.join(field_args)})"
            if field_args
            else f"{field_class}()"
        )

        # Add default value for optional inputs
        if is_input and not prop.is_required and prop.default_value:
            default = repr(prop.default_value)
            return f"{prop.name}: {python_type} = {field_call}  # default: {default}"

        return f"{prop.name}: {python_type} = {field_call}"

    def get_imports(self) -> list[str]:
        """Get required imports for this signature.

        Returns
        -------
            List of import statements
        """
        imports = ["import dspy"]

        # Check if we need typing imports
        needs_typing = False
        needs_list = False
        needs_optional = False

        for prop in self.inputs + self.outputs:
            python_type = prop.get_python_type()
            if "List[" in python_type:
                needs_list = True
                needs_typing = True
            if "Optional[" in python_type:
                needs_optional = True
                needs_typing = True

        if needs_typing:
            typing_imports = []
            if needs_list:
                typing_imports.append("List")
            if needs_optional:
                typing_imports.append("Optional")
            imports.append(f"from typing import {', '.join(typing_imports)}")

        return imports


class DSPyGenerator:
    """Generate DSPy signatures from SHACL shapes."""

    def __init__(self):
        """Initialize generator."""
        self._generated: dict[str, SignatureDefinition] = {}

    def generate_signature(self, shape: SHACLShape) -> SignatureDefinition:
        """Generate a DSPy signature from a SHACL shape.

        Args:
            shape: SHACLShape to convert

        Returns
        -------
            SignatureDefinition
        """
        class_name = shape.signature_name

        # Check if already generated
        if class_name in self._generated:
            logger.debug(f"Using cached signature for {class_name}")
            return self._generated[class_name]

        logger.info(f"Generating signature: {class_name}")

        # Create signature definition
        signature = SignatureDefinition(
            class_name=class_name,
            docstring=shape.description,
            inputs=shape.input_properties,
            outputs=shape.output_properties,
        )

        # Cache it
        self._generated[class_name] = signature

        return signature

    def generate_module(self, shapes: list[SHACLShape]) -> str:
        """Generate a complete Python module with all signatures.

        Args:
            shapes: List of SHACL shapes to convert

        Returns
        -------
            Complete Python module code
        """
        logger.info(f"Generating module with {len(shapes)} signatures")

        lines = []

        # Module docstring
        lines.append('"""Auto-generated DSPy signatures from SHACL shapes."""')
        lines.append("")
        lines.append("# This file is auto-generated. Do not edit manually.")
        lines.append("")

        # Collect all imports
        all_imports = set()
        signatures = []

        for shape in shapes:
            sig = self.generate_signature(shape)
            signatures.append(sig)
            for imp in sig.get_imports():
                all_imports.add(imp)

        # Add imports
        for imp in sorted(all_imports):
            lines.append(imp)
        lines.append("")
        lines.append("")

        # Add all signatures
        for sig in signatures:
            lines.append(sig.generate_code())
            lines.append("")
            lines.append("")

        # Add __all__
        class_names = [sig.class_name for sig in signatures]
        lines.append("__all__ = [")
        for name in class_names:
            lines.append(f'    "{name}",')
        lines.append("]")

        return "\n".join(lines)

    def clear_cache(self):
        """Clear generated signature cache."""
        self._generated.clear()
        logger.info("Cleared generator cache")

    def get_cache_stats(self) -> dict[str, int]:
        """Get cache statistics."""
        return {"generated_signatures": len(self._generated)}

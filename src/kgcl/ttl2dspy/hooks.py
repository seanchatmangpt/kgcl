"""UNRDF hooks integration for external capability invocation.

This module provides a callable interface for external systems to invoke
TTL2DSPy capabilities via stdin/stdout with JSON receipts.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any

from .ultra import CacheConfig, UltraOptimizer
from .writer import ModuleWriter

logger = logging.getLogger(__name__)


class TTL2DSpyHook:
    """UNRDF hook for TTL2DSPy capability."""

    def __init__(self, config: CacheConfig | None = None):
        """Initialize hook.

        Args:
            config: Cache configuration
        """
        self.config = config or CacheConfig()
        self.optimizer = UltraOptimizer(self.config)
        self.writer = ModuleWriter()

    def process_stdin(self, input_data: str) -> dict[str, Any]:
        """Process TTL input from stdin.

        Args:
            input_data: TTL/RDF content or JSON request

        Returns
        -------
            JSON receipt with results
        """
        try:
            # Try to parse as JSON request
            try:
                request = json.loads(input_data)
                return self._process_json_request(request)
            except json.JSONDecodeError:
                # Treat as raw TTL content
                return self._process_ttl_content(input_data)

        except Exception as e:
            logger.error(f"Hook processing failed: {e}", exc_info=True)
            return {"success": False, "error": str(e), "error_type": type(e).__name__}

    def _process_json_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Process JSON request.

        Expected format:
        {
            "action": "generate",  // or "parse", "validate", "list"
            "ttl_content": "...",  // optional: inline TTL
            "ttl_path": "...",     // optional: path to TTL file
            "output_dir": "...",   // required for generate
            "module_name": "...",  // optional: default "signatures"
            "format_code": true,   // optional: default true
        }

        Args:
            request: JSON request object

        Returns
        -------
            JSON receipt
        """
        action = request.get("action", "generate")

        # Get TTL source
        if "ttl_content" in request:
            # Save to temp file
            import tempfile

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".ttl", delete=False
            ) as f:
                f.write(request["ttl_content"])
                ttl_path = Path(f.name)
        elif "ttl_path" in request:
            ttl_path = Path(request["ttl_path"])
        else:
            return {
                "success": False,
                "error": "Either 'ttl_content' or 'ttl_path' required",
            }

        # Route to appropriate handler
        if action == "parse":
            return self._handle_parse(ttl_path)
        if action == "validate":
            return self._handle_validate(ttl_path)
        if action == "list":
            return self._handle_list(ttl_path)
        if action == "generate":
            output_dir = request.get("output_dir")
            if not output_dir:
                return {
                    "success": False,
                    "error": "'output_dir' required for generate action",
                }
            module_name = request.get("module_name", "signatures")
            format_code = request.get("format_code", True)
            return self._handle_generate(ttl_path, output_dir, module_name, format_code)
        return {"success": False, "error": f"Unknown action: {action}"}

    def _process_ttl_content(self, ttl_content: str) -> dict[str, Any]:
        """Process raw TTL content.

        Default action: parse and return shape info.

        Args:
            ttl_content: Raw TTL content

        Returns
        -------
            JSON receipt
        """
        import tempfile

        # Save to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ttl", delete=False) as f:
            f.write(ttl_content)
            ttl_path = Path(f.name)

        return self._handle_parse(ttl_path)

    def _handle_parse(self, ttl_path: Path) -> dict[str, Any]:
        """Handle parse action."""
        shapes = self.optimizer.parse_with_cache(ttl_path)

        return {
            "success": True,
            "action": "parse",
            "ttl_path": str(ttl_path),
            "shapes_count": len(shapes),
            "shapes": [
                {
                    "name": shape.name,
                    "uri": str(shape.uri),
                    "signature_name": shape.signature_name,
                    "description": shape.description,
                    "input_properties": len(shape.input_properties),
                    "output_properties": len(shape.output_properties),
                }
                for shape in shapes
            ],
            "stats": self.optimizer.get_detailed_stats(),
        }

    def _handle_validate(self, ttl_path: Path) -> dict[str, Any]:
        """Handle validate action."""
        shapes = self.optimizer.parse_with_cache(ttl_path)

        errors = []
        warnings = []

        for shape in shapes:
            if not shape.properties:
                errors.append(f"{shape.name}: No properties defined")

            if not shape.input_properties and not shape.output_properties:
                warnings.append(f"{shape.name}: No input/output categorization")

            for prop in shape.properties:
                if not prop.description:
                    warnings.append(f"{shape.name}.{prop.name}: Missing description")

        return {
            "success": len(errors) == 0,
            "action": "validate",
            "ttl_path": str(ttl_path),
            "shapes_count": len(shapes),
            "errors": errors,
            "warnings": warnings,
            "valid": len(errors) == 0,
        }

    def _handle_list(self, ttl_path: Path) -> dict[str, Any]:
        """Handle list action."""
        shapes = self.optimizer.parse_with_cache(ttl_path)

        return {
            "success": True,
            "action": "list",
            "ttl_path": str(ttl_path),
            "shapes_count": len(shapes),
            "shapes": [
                {
                    "name": shape.name,
                    "uri": str(shape.uri),
                    "signature_name": shape.signature_name,
                    "description": shape.description,
                    "target_class": str(shape.target_class)
                    if shape.target_class
                    else None,
                    "inputs": [
                        {
                            "name": prop.name,
                            "type": prop.get_python_type(),
                            "required": prop.is_required,
                            "description": prop.description,
                        }
                        for prop in shape.input_properties
                    ],
                    "outputs": [
                        {
                            "name": prop.name,
                            "type": prop.get_python_type(),
                            "description": prop.description,
                        }
                        for prop in shape.output_properties
                    ],
                }
                for shape in shapes
            ],
        }

    def _handle_generate(
        self, ttl_path: Path, output_dir: str, module_name: str, format_code: bool
    ) -> dict[str, Any]:
        """Handle generate action."""
        # Parse shapes
        shapes = self.optimizer.parse_with_cache(ttl_path)

        # Generate code
        code = self.optimizer.generate_with_cache(shapes)

        # Write module
        output_path = Path(output_dir) / f"{module_name}.py"
        result = self.writer.write_module(
            code=code,
            output_path=output_path,
            shapes_count=len(shapes),
            ttl_source=ttl_path,
            format_code=format_code,
        )

        # Write JSON receipt
        receipt_path = self.writer.write_receipt(result)

        return {
            "success": True,
            "action": "generate",
            "ttl_path": str(ttl_path),
            "output_path": str(result.output_path),
            "receipt_path": str(receipt_path),
            "shapes_count": result.shapes_count,
            "signatures_count": result.signatures_count,
            "lines_count": result.lines_count,
            "file_size": result.file_size,
            "write_time": result.write_time,
            "timestamp": result.timestamp,
            "stats": self.optimizer.get_detailed_stats(),
        }


def main_hook():
    """Main entry point for UNRDF hook invocation.

    Reads from stdin, processes, and writes JSON receipt to stdout.
    """
    # Configure logging to stderr
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )

    try:
        # Read stdin
        input_data = sys.stdin.read()

        # Process
        hook = TTL2DSpyHook()
        receipt = hook.process_stdin(input_data)

        # Write to stdout
        sys.stdout.write(json.dumps(receipt, indent=2))
        sys.stdout.write("\n")

        # Exit with appropriate code
        sys.exit(0 if receipt.get("success", False) else 1)

    except Exception as e:
        # Write error receipt
        receipt = {"success": False, "error": str(e), "error_type": type(e).__name__}
        sys.stdout.write(json.dumps(receipt, indent=2))
        sys.stdout.write("\n")
        sys.exit(1)


if __name__ == "__main__":
    main_hook()

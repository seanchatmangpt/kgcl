"""MCP resources for semantic code porting.

Defines MCP resources that can be exposed via MCP server.
"""

from pathlib import Path
from typing import Any

from kgcl.porting.mcp.server import PortingMCPServer


def create_mcp_resources(server: PortingMCPServer) -> dict[str, Any]:
    """Create MCP resource definitions.

    Parameters
    ----------
    server : PortingMCPServer
        Porting MCP server instance

    Returns
    -------
    dict[str, Any]
        Dictionary of MCP resource definitions
    """
    return {
        "codebase_graph": {
            "uri": "porting://codebase/graph",
            "name": "Codebase Graph",
            "description": "RDF graph of ingested codebases",
            "mimeType": "text/turtle",
            "handler": lambda: server.engine._export_state(),
        },
        "porting_rules": {
            "uri": "porting://rules/structural",
            "name": "Structural Porting Rules",
            "description": "N3 rules for structural pattern matching",
            "mimeType": "text/n3",
            "handler": lambda: _load_rules_file("structural-rules.n3"),
        },
        "semantic_rules": {
            "uri": "porting://rules/semantic",
            "name": "Semantic Porting Rules",
            "description": "N3 rules for semantic equivalence",
            "mimeType": "text/n3",
            "handler": lambda: _load_rules_file("semantic-rules.n3"),
        },
    }


def _load_rules_file(filename: str) -> str:
    """Load N3 rules file.

    Parameters
    ----------
    filename : str
        Name of rules file

    Returns
    -------
    str
        Rules content
    """
    rules_path = Path(__file__).parent.parent.parent.parent / "ontology" / "porting" / filename
    if rules_path.exists():
        return rules_path.read_text(encoding="utf-8")
    return ""


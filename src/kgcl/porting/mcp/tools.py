"""MCP tools for semantic code porting.

Defines MCP tools that can be exposed via MCP server.
"""

from pathlib import Path
from typing import Any

from kgcl.porting.mcp.server import PortingMCPServer


def create_mcp_tools(server: PortingMCPServer) -> dict[str, Any]:
    """Create MCP tool definitions.

    Parameters
    ----------
    server : PortingMCPServer
        Porting MCP server instance

    Returns
    -------
    dict[str, Any]
        Dictionary of MCP tool definitions
    """
    return {
        "detect_deltas": {
            "name": "detect_deltas",
            "description": "Detect deltas between Java and Python codebases",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "rules_path": {
                        "type": "string",
                        "description": "Path to N3 rules file (optional)",
                    },
                },
            },
            "handler": lambda args: server.detect_deltas(
                Path(args.get("rules_path")) if args.get("rules_path") else None
            ),
        },
        "suggest_port": {
            "name": "suggest_port",
            "description": "Suggest porting strategy for a class",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "class_name": {
                        "type": "string",
                        "description": "Name of class to port",
                    },
                },
                "required": ["class_name"],
            },
            "handler": lambda args: server.suggest_port(args["class_name"]),
        },
        "validate_port": {
            "name": "validate_port",
            "description": "Validate porting completeness for a class",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "class_name": {
                        "type": "string",
                        "description": "Name of class to validate",
                    },
                },
                "required": ["class_name"],
            },
            "handler": lambda args: server.validate_port(args["class_name"]),
        },
    }


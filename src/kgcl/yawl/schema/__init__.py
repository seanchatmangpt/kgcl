"""YAWL schema handling (mirrors Java org.yawlfoundation.yawl.schema).

This module provides schema version management and XML schema validation
for YAWL specifications.
"""

from kgcl.yawl.schema.schema_handler import SchemaHandler
from kgcl.yawl.schema.y_schema_version import YSchemaVersion

__all__ = [
    "YSchemaVersion",
    "SchemaHandler",
]


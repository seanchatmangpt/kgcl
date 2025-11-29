"""
Personal KGC Technician tooling.

This lightweight package hosts the generated KGCT CLI together with helper
modules (handlers, ingest pipeline, generators).  The package mirrors the
Lean/.kgc specification so that all technician workflows are driven from the
RDF context under `.kgc/`.
"""

from importlib.metadata import PackageNotFoundError, version


def get_version() -> str:
    """Return the installed version of the personal_kgcl tooling."""
    try:
        return version("kgcl")
    except PackageNotFoundError:
        return "0.0.0"


__all__ = ["get_version"]



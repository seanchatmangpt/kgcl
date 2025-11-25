"""Tests for observability health checks."""

from __future__ import annotations

from pathlib import Path

from kgcl.observability.health import check_graph_integrity


def _write_ttl(path: Path, content: str) -> None:
    path.write_text(
        """@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix ex: <http://example.org/> .

"""
        + content
    )


def test_check_graph_integrity_success(monkeypatch, tmp_path):
    """Graph integrity check should validate real TTL graphs."""
    graph_file = tmp_path / "graph.ttl"
    _write_ttl(graph_file, "ex:item rdf:type sh:NodeShape .\n")

    monkeypatch.setenv("KGCL_GRAPH_FILE", str(graph_file))

    is_healthy, message, details = check_graph_integrity()

    assert is_healthy is True
    assert "passed" in message
    assert details["triples"] == 1
    assert details["graph_file"] == str(graph_file)
    assert "sha256" in details
    assert details["unique_subjects"] == 1


def test_check_graph_integrity_missing_file(monkeypatch, tmp_path):
    """Health check should fail when graph file is missing."""
    graph_file = tmp_path / "missing.ttl"
    monkeypatch.setenv("KGCL_GRAPH_FILE", str(graph_file))

    is_healthy, message, details = check_graph_integrity()

    assert is_healthy is False
    assert message == "Configured graph file not found"
    assert details["error"] == "graph_file_not_found"
    assert details["graph_file"] == str(graph_file)


def test_check_graph_integrity_parse_error(monkeypatch, tmp_path):
    """Health check should surface parsing errors."""
    graph_file = tmp_path / "broken.ttl"
    graph_file.write_text("not a ttl document")
    monkeypatch.setenv("KGCL_GRAPH_FILE", str(graph_file))

    is_healthy, message, details = check_graph_integrity()

    assert is_healthy is False
    assert message == "Failed to parse graph file"
    assert "error" in details
    assert details["graph_file"] == str(graph_file)

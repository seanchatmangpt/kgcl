"""Chicago School TDD Tests for File Resolver.

Tests FileResolver with real file I/O, SHA256 verification, and security validation.
No mocks - real files and integrity checks.
"""

from hashlib import sha256
from pathlib import Path

import pytest

from kgcl.hooks.file_resolver import FileResolver, FileResolverError


class TestFileResolverLocalFiles:
    """Test loading local files."""

    @pytest.fixture
    def test_file(self, tmp_path):
        """Create test SPARQL file."""
        query_file = tmp_path / "test_query.sparql"
        content = "SELECT * WHERE { ?s ?p ?o }"
        query_file.write_text(content)
        return query_file

    def test_load_local_file_success(self, test_file):
        """Load local file successfully."""
        resolver = FileResolver()

        content = resolver.load_file(f"file://{test_file}")

        assert content == "SELECT * WHERE { ?s ?p ?o }"

    def test_load_local_file_with_valid_sha256(self, test_file):
        """Load local file with valid SHA256 passes verification."""
        content = "SELECT * WHERE { ?s ?p ?o }"
        expected_hash = sha256(content.encode()).hexdigest()

        resolver = FileResolver()

        loaded_content = resolver.load_file(f"file://{test_file}", expected_hash)

        assert loaded_content == content

    def test_load_local_file_with_invalid_sha256_fails(self, test_file):
        """Load local file with invalid SHA256 raises error."""
        resolver = FileResolver()
        wrong_hash = "0" * 64

        with pytest.raises(FileResolverError, match="Integrity check failed"):
            resolver.load_file(f"file://{test_file}", wrong_hash)

    def test_load_local_file_not_found(self):
        """Load non-existent local file raises error."""
        resolver = FileResolver()

        with pytest.raises(FileResolverError, match="File not found"):
            resolver.load_file("file:///nonexistent/file.sparql")

    def test_load_local_file_path_security_allowed(self, tmp_path):
        """Load file from allowed path succeeds."""
        allowed_dir = tmp_path / "allowed"
        allowed_dir.mkdir()

        query_file = allowed_dir / "query.sparql"
        query_file.write_text("ASK { ?s ?p ?o }")

        resolver = FileResolver(allowed_paths=[str(allowed_dir)])

        content = resolver.load_file(f"file://{query_file}")

        assert content == "ASK { ?s ?p ?o }"

    def test_load_local_file_path_security_blocked(self, tmp_path):
        """Load file from disallowed path raises error."""
        allowed_dir = tmp_path / "allowed"
        allowed_dir.mkdir()

        forbidden_dir = tmp_path / "forbidden"
        forbidden_dir.mkdir()

        query_file = forbidden_dir / "query.sparql"
        query_file.write_text("ASK { ?s ?p ?o }")

        resolver = FileResolver(allowed_paths=[str(allowed_dir)])

        with pytest.raises(FileResolverError, match="Path not allowed"):
            resolver.load_file(f"file://{query_file}")


class TestFileResolverRemoteFiles:
    """Test loading remote files (mocked with local server simulation)."""

    def test_load_remote_file_unsupported_scheme(self):
        """Load file with unsupported scheme raises error."""
        resolver = FileResolver()

        with pytest.raises(FileResolverError, match="Unsupported URI scheme"):
            resolver.load_file("ftp://example.com/query.sparql")

    def test_compute_sha256(self):
        """Compute SHA256 hash correctly."""
        resolver = FileResolver()
        content = "SELECT * WHERE { ?s ?p ?o }"

        computed = resolver.compute_sha256(content)
        expected = sha256(content.encode()).hexdigest()

        assert computed == expected


class TestFileResolverIntegration:
    """Integration tests with SPARQL conditions."""

    @pytest.fixture
    def sparql_file(self, tmp_path):
        """Create SPARQL ASK file."""
        query_file = tmp_path / "validation.sparql"
        content = "ASK WHERE { ?person a :Person ; :hasAge ?age . FILTER(?age >= 18) }"
        query_file.write_text(content)
        return query_file

    def test_load_sparql_from_file_with_resolver(self, sparql_file):
        """Load SPARQL query from file for condition."""
        from kgcl.hooks.conditions import SparqlAskCondition

        resolver = FileResolver()

        # Create condition with file reference
        condition = SparqlAskCondition(
            ref={"uri": f"file://{sparql_file}", "sha256": None}
        )

        # Get query using resolver
        query = condition.get_query(resolver)

        assert "ASK WHERE" in query
        assert "?person a :Person" in query

    def test_load_sparql_from_file_with_integrity_check(self, sparql_file):
        """Load SPARQL query with SHA256 integrity verification."""
        from kgcl.hooks.conditions import SparqlAskCondition

        content = sparql_file.read_text()
        expected_hash = sha256(content.encode()).hexdigest()

        resolver = FileResolver()

        # Create condition with file reference + hash
        condition = SparqlAskCondition(
            ref={"uri": f"file://{sparql_file}", "sha256": expected_hash}
        )

        # Get query using resolver
        query = condition.get_query(resolver)

        assert query == content

    def test_sparql_condition_inline_query_takes_precedence(self):
        """Inline query takes precedence over file reference."""
        from kgcl.hooks.conditions import SparqlAskCondition

        resolver = FileResolver()

        # Both inline and ref provided
        condition = SparqlAskCondition(
            query="ASK { ?s ?p ?o }",
            ref={"uri": "file:///some/file.sparql", "sha256": None},
        )

        # Inline query should be returned
        query = condition.get_query(resolver)

        assert query == "ASK { ?s ?p ?o }"

    def test_sparql_condition_missing_uri_in_ref_fails(self):
        """SPARQL condition with ref missing uri raises error."""
        from kgcl.hooks.conditions import SparqlAskCondition

        resolver = FileResolver()

        condition = SparqlAskCondition(ref={"sha256": "abc123"})

        with pytest.raises(ValueError, match="ref missing 'uri' field"):
            condition.get_query(resolver)

    def test_sparql_condition_no_query_or_ref_fails(self):
        """SPARQL condition without query or ref raises error."""
        from kgcl.hooks.conditions import SparqlAskCondition

        resolver = FileResolver()

        condition = SparqlAskCondition()

        with pytest.raises(ValueError, match="No query or ref provided"):
            condition.get_query(resolver)

"""Tests for RDF-specific Jinja filters."""

import pytest

from kgcl.projection.filters.rdf_filters import (
    literal_datatype,
    literal_lang,
    literal_value,
    uri_local_name,
    uri_namespace,
    uri_to_curie,
)


class TestURIFilters:
    """Test URI manipulation filters."""

    def test_uri_local_name_with_hash(self) -> None:
        """Extract local name from hash URI."""
        assert uri_local_name("http://example.org/schema#Person") == "Person"
        assert uri_local_name("http://example.org/ns#name") == "name"

    def test_uri_local_name_with_slash(self) -> None:
        """Extract local name from slash URI."""
        assert uri_local_name("http://example.org/schema/Person") == "Person"
        assert uri_local_name("http://example.org/ontology/Class") == "Class"

    def test_uri_local_name_trailing_slash(self) -> None:
        """Handle URI with trailing slash."""
        assert uri_local_name("http://example.org/") == "example.org"
        assert uri_local_name("http://example.org/schema/") == "schema"

    def test_uri_local_name_no_separator(self) -> None:
        """Handle URI with no clear separator."""
        assert uri_local_name("http://example.org") == "example.org"

    def test_uri_namespace_with_hash(self) -> None:
        """Extract namespace from hash URI."""
        assert uri_namespace("http://example.org/schema#Person") == "http://example.org/schema#"
        assert uri_namespace("http://example.org/ns#name") == "http://example.org/ns#"

    def test_uri_namespace_with_slash(self) -> None:
        """Extract namespace from slash URI."""
        assert uri_namespace("http://example.org/schema/Person") == "http://example.org/schema/"
        assert uri_namespace("http://example.org/ontology/Class") == "http://example.org/ontology/"

    def test_uri_namespace_root(self) -> None:
        """Handle root URI."""
        assert uri_namespace("http://example.org/") == "http://example.org/"

    def test_uri_to_curie_with_match(self) -> None:
        """Convert URI to CURIE with matching prefix."""
        prefixes = {"http://example.org/schema#": "ex", "http://example.org/ontology/": "onto"}

        assert uri_to_curie("http://example.org/schema#Person", prefixes) == "ex:Person"
        assert uri_to_curie("http://example.org/ontology/Class", prefixes) == "onto:Class"

    def test_uri_to_curie_no_match(self) -> None:
        """Return original URI when no prefix matches."""
        prefixes = {"http://example.org/schema#": "ex"}

        assert uri_to_curie("http://other.org/Thing", prefixes) == "http://other.org/Thing"

    def test_uri_to_curie_empty_prefixes(self) -> None:
        """Handle empty prefix dictionary."""
        assert uri_to_curie("http://example.org/schema#Person", {}) == "http://example.org/schema#Person"


class TestLiteralFilters:
    """Test RDF literal manipulation filters."""

    def test_literal_value_typed(self) -> None:
        """Extract value from typed literal."""
        assert literal_value('"42"^^xsd:integer') == "42"
        assert literal_value('"3.14"^^xsd:decimal') == "3.14"
        assert literal_value('"true"^^xsd:boolean') == "true"

    def test_literal_value_with_lang(self) -> None:
        """Extract value from literal with language tag."""
        assert literal_value('"hello"@en') == "hello"
        assert literal_value('"bonjour"@fr') == "bonjour"

    def test_literal_value_plain(self) -> None:
        """Extract value from plain literal."""
        assert literal_value('"plain"') == "plain"
        assert literal_value('"simple text"') == "simple text"

    def test_literal_value_unquoted(self) -> None:
        """Handle unquoted literal."""
        assert literal_value("unquoted") == "unquoted"

    def test_literal_lang_present(self) -> None:
        """Extract language tag when present."""
        assert literal_lang('"hello"@en') == "en"
        assert literal_lang('"bonjour"@fr') == "fr"

    def test_literal_lang_regional(self) -> None:
        """Extract regional language tag."""
        assert literal_lang('"color"@en-US') == "en-US"
        assert literal_lang('"couleur"@fr-CA') == "fr-CA"

    def test_literal_lang_missing(self) -> None:
        """Return None when no language tag."""
        assert literal_lang('"42"^^xsd:integer') is None
        assert literal_lang('"plain"') is None
        assert literal_lang("unquoted") is None

    def test_literal_datatype_present(self) -> None:
        """Extract datatype URI when present."""
        assert literal_datatype('"42"^^xsd:integer') == "xsd:integer"
        assert literal_datatype('"3.14"^^xsd:decimal') == "xsd:decimal"

    def test_literal_datatype_full_uri(self) -> None:
        """Extract full datatype URI."""
        assert (
            literal_datatype('"true"^^http://www.w3.org/2001/XMLSchema#boolean')
            == "http://www.w3.org/2001/XMLSchema#boolean"
        )

    def test_literal_datatype_missing(self) -> None:
        """Return None when no datatype."""
        assert literal_datatype('"hello"@en') is None
        assert literal_datatype('"plain"') is None
        assert literal_datatype("unquoted") is None


class TestComplexScenarios:
    """Test complex RDF filter scenarios."""

    def test_uri_curie_roundtrip_concept(self) -> None:
        """Verify URI/CURIE conversion preserves semantics."""
        uri = "http://example.org/schema#Person"
        prefixes = {"http://example.org/schema#": "ex"}

        curie = uri_to_curie(uri, prefixes)
        assert curie == "ex:Person"

        # Reconstruct URI from CURIE
        prefix, local = curie.split(":")
        namespace = next(ns for ns, p in prefixes.items() if p == prefix)
        reconstructed = namespace + local

        assert reconstructed == uri

    def test_literal_components_extraction(self) -> None:
        """Extract multiple components from complex literal."""
        literal = '"hello"@en'

        value = literal_value(literal)
        lang = literal_lang(literal)
        datatype = literal_datatype(literal)

        assert value == "hello"
        assert lang == "en"
        assert datatype is None

    def test_literal_typed_vs_lang(self) -> None:
        """Verify typed literals don't have lang tags."""
        typed = '"42"^^xsd:integer'
        lang_tagged = '"hello"@en'

        assert literal_datatype(typed) is not None
        assert literal_lang(typed) is None

        assert literal_lang(lang_tagged) is not None
        assert literal_datatype(lang_tagged) is None


class TestFilterExports:
    """Test RDF_FILTERS export."""

    def test_all_filters_exported(self) -> None:
        """Verify all filters are in RDF_FILTERS dict."""
        from kgcl.projection.filters.rdf_filters import RDF_FILTERS

        expected_filters = {
            "uri_local_name",
            "uri_namespace",
            "uri_to_curie",
            "literal_value",
            "literal_lang",
            "literal_datatype",
        }
        assert set(RDF_FILTERS.keys()) == expected_filters

    def test_filters_are_callable(self) -> None:
        """Verify all exported filters are callable."""
        from kgcl.projection.filters.rdf_filters import RDF_FILTERS

        for name, func in RDF_FILTERS.items():
            assert callable(func), f"Filter {name} is not callable"

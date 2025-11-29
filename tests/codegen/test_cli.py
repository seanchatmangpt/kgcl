"""Tests for kgcl.codegen.cli module.

Chicago School TDD tests verifying CLI behavior and argument parsing.
"""

import tempfile
from pathlib import Path

import pytest

from kgcl.codegen.cli import collect_input_files, main


def test_collect_input_files_with_single_file() -> None:
    """Test collecting single TTL file."""
    with tempfile.NamedTemporaryFile(suffix=".ttl", delete=False) as f:
        file = Path(f.name)

    try:
        files = collect_input_files([str(file)])

        assert len(files) == 1
        assert files[0] == file
    finally:
        file.unlink(missing_ok=True)


def test_collect_input_files_with_directory() -> None:
    """Test collecting TTL files from directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        file1 = test_dir / "test1.ttl"
        file2 = test_dir / "test2.ttl"
        file1.touch()
        file2.touch()

        files = collect_input_files([str(test_dir)])

        assert len(files) >= 2


def test_collect_input_files_with_nonexistent_path() -> None:
    """Test collecting files handles nonexistent paths."""
    files = collect_input_files(["/nonexistent/path.ttl"])

    assert files == []


def test_collect_input_files_filters_by_extension() -> None:
    """Test only TTL files are collected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        ttl_file = test_dir / "test.ttl"
        txt_file = test_dir / "test.txt"
        ttl_file.touch()
        txt_file.touch()

        files = collect_input_files([str(test_dir)])

        assert all(f.suffix in (".ttl", ".turtle", ".n3") for f in files)


def test_main_with_no_input_files() -> None:
    """Test main returns error code when no files found."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output = Path(tmpdir) / "output.py"

        exit_code = main(["/nonexistent", str(output)])

        assert exit_code == 2


def test_main_with_help_flag() -> None:
    """Test main handles --help flag."""
    with pytest.raises(SystemExit) as exc:
        main(["--help"])

    assert exc.value.code in (0, 2)


def test_main_generates_output_file() -> None:
    """Test main generates output file when successful."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = Path(tmpdir) / "test.ttl"
        input_file.write_text(
            """
@prefix ex: <http://example.org/> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

ex:PersonShape
    a sh:NodeShape ;
    sh:targetClass ex:Person ;
    sh:property ex:nameShape .

ex:nameShape
    sh:path ex:name ;
    sh:datatype xsd:string .
"""
        )

        output_file = Path(tmpdir) / "output.py"

        exit_code = main([str(input_file), str(output_file)])

        assert exit_code == 0
        assert output_file.exists()


def test_main_with_no_shacl_shapes() -> None:
    """Test main returns error when no SHACL shapes found."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = Path(tmpdir) / "empty.ttl"
        input_file.write_text("@prefix ex: <http://example.org/> .")

        output_file = Path(tmpdir) / "output.py"

        exit_code = main([str(input_file), str(output_file)])

        assert exit_code == 1


def test_main_creates_output_directory() -> None:
    """Test main creates output directory if it doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = Path(tmpdir) / "test.ttl"
        input_file.write_text(
            """
@prefix ex: <http://example.org/> .
@prefix sh: <http://www.w3.org/ns/shacl#> .

ex:TestShape sh:targetClass ex:Test .
ex:TestShape sh:property [sh:path ex:prop] .
"""
        )

        output_file = Path(tmpdir) / "nested" / "dir" / "output.py"

        exit_code = main([str(input_file), str(output_file)])

        assert output_file.parent.exists()


def test_main_with_verbose_flag() -> None:
    """Test main handles --verbose flag."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = Path(tmpdir) / "test.ttl"
        input_file.write_text(
            """
@prefix ex: <http://example.org/> .
@prefix sh: <http://www.w3.org/ns/shacl#> .

ex:TestShape sh:targetClass ex:Test .
ex:TestShape sh:property [sh:path ex:prop] .
"""
        )

        output_file = Path(tmpdir) / "output.py"

        exit_code = main([str(input_file), str(output_file), "--verbose"])

        assert exit_code == 0


def test_main_with_parallel_flag() -> None:
    """Test main handles --parallel flag."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = Path(tmpdir) / "test.ttl"
        input_file.write_text(
            """
@prefix ex: <http://example.org/> .
@prefix sh: <http://www.w3.org/ns/shacl#> .

ex:TestShape sh:targetClass ex:Test .
ex:TestShape sh:property [sh:path ex:prop] .
"""
        )

        output_file = Path(tmpdir) / "output.py"

        exit_code = main([str(input_file), str(output_file), "--parallel", "--workers", "2"])

        assert exit_code == 0


def test_main_with_ultra_cache_flag() -> None:
    """Test main handles --ultra-cache flag."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = Path(tmpdir) / "test.ttl"
        input_file.write_text(
            """
@prefix ex: <http://example.org/> .
@prefix sh: <http://www.w3.org/ns/shacl#> .

ex:TestShape sh:targetClass ex:Test .
ex:TestShape sh:property [sh:path ex:prop] .
"""
        )

        output_file = Path(tmpdir) / "output.py"

        exit_code = main([str(input_file), str(output_file), "--ultra-cache"])

        assert exit_code == 0


def test_main_with_benchmark_flag() -> None:
    """Test main handles --benchmark flag."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = Path(tmpdir) / "test.ttl"
        input_file.write_text(
            """
@prefix ex: <http://example.org/> .
@prefix sh: <http://www.w3.org/ns/shacl#> .

ex:TestShape sh:targetClass ex:Test .
ex:TestShape sh:property [sh:path ex:prop] .
"""
        )

        output_file = Path(tmpdir) / "output.py"

        exit_code = main([str(input_file), str(output_file), "--benchmark"])

        assert exit_code == 0

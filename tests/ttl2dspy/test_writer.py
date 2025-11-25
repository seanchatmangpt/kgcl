"""Tests for module writer."""

import json

from kgcl.ttl2dspy.writer import ModuleWriter, WriteResult


class TestWriteResult:
    """Tests for WriteResult class."""

    def test_to_dict(self, tmp_path):
        """Test conversion to dictionary."""
        result = WriteResult(
            output_path=tmp_path / "test.py",
            shapes_count=5,
            signatures_count=5,
            file_size=1024,
            write_time=0.5,
            lines_count=100,
            timestamp="2025-01-01T00:00:00",
            ttl_source="test.ttl",
        )

        data = result.to_dict()

        assert data["shapes_count"] == 5
        assert data["signatures_count"] == 5
        assert data["file_size"] == 1024
        assert data["write_time"] == 0.5
        assert data["lines_count"] == 100

    def test_to_json(self, tmp_path):
        """Test conversion to JSON."""
        result = WriteResult(
            output_path=tmp_path / "test.py",
            shapes_count=5,
            signatures_count=5,
            file_size=1024,
            write_time=0.5,
            lines_count=100,
            timestamp="2025-01-01T00:00:00",
        )

        json_str = result.to_json()
        data = json.loads(json_str)

        assert data["shapes_count"] == 5
        assert data["signatures_count"] == 5


class TestModuleWriter:
    """Tests for ModuleWriter class."""

    def test_write_module(self, tmp_path):
        """Test writing a module."""
        writer = ModuleWriter()

        code = '''import dspy

class TestSignature(dspy.Signature):
    """Test signature."""
    input: str = dspy.InputField()
    output: str = dspy.OutputField()
'''

        output_path = tmp_path / "test.py"
        result = writer.write_module(
            code=code, output_path=output_path, shapes_count=1, format_code=False
        )

        assert output_path.exists()
        assert result.output_path == output_path
        assert result.shapes_count == 1
        assert result.signatures_count == 1
        assert result.file_size > 0
        assert result.lines_count > 0

    def test_write_module_creates_directory(self, tmp_path):
        """Test that write_module creates output directory."""
        writer = ModuleWriter()

        code = "import dspy\n\nclass TestSignature(dspy.Signature):\n    pass\n"

        output_path = tmp_path / "subdir" / "test.py"
        result = writer.write_module(code=code, output_path=output_path, format_code=False)

        assert output_path.exists()
        assert output_path.parent.exists()

    def test_write_batch(self, tmp_path):
        """Test batch writing."""
        writer = ModuleWriter()

        modules = {
            "module1": "import dspy\n\nclass Sig1(dspy.Signature):\n    pass\n",
            "module2": "import dspy\n\nclass Sig2(dspy.Signature):\n    pass\n",
        }

        output_dir = tmp_path / "modules"
        results = writer.write_batch(modules=modules, output_dir=output_dir, format_code=False)

        assert len(results) == 2
        assert (output_dir / "module1.py").exists()
        assert (output_dir / "module2.py").exists()
        assert (output_dir / "__init__.py").exists()

    def test_write_receipt(self, tmp_path):
        """Test writing a receipt."""
        writer = ModuleWriter()

        result = WriteResult(
            output_path=tmp_path / "test.py",
            shapes_count=5,
            signatures_count=5,
            file_size=1024,
            write_time=0.5,
            lines_count=100,
            timestamp="2025-01-01T00:00:00",
        )

        receipt_path = writer.write_receipt(result)

        assert receipt_path.exists()
        assert receipt_path.suffix == ".json"

        # Verify content
        data = json.loads(receipt_path.read_text())
        assert data["shapes_count"] == 5
        assert data["signatures_count"] == 5

    def test_get_history(self, tmp_path):
        """Test getting write history."""
        writer = ModuleWriter()

        code = "import dspy\n\nclass TestSignature(dspy.Signature):\n    pass\n"

        writer.write_module(code=code, output_path=tmp_path / "test1.py", format_code=False)

        writer.write_module(code=code, output_path=tmp_path / "test2.py", format_code=False)

        history = writer.get_history()
        assert len(history) == 2

    def test_export_metrics(self, tmp_path):
        """Test exporting metrics."""
        writer = ModuleWriter()

        code = "import dspy\n\nclass TestSignature(dspy.Signature):\n    pass\n"

        writer.write_module(code=code, output_path=tmp_path / "test.py", format_code=False)

        metrics_path = tmp_path / "metrics.json"
        writer.export_metrics(metrics_path)

        assert metrics_path.exists()

        data = json.loads(metrics_path.read_text())
        assert data["total_writes"] == 1
        assert data["total_signatures"] >= 1
        assert "history" in data

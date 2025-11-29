"""Tests for VendorSpecLoader - loading YAWL v5.2 example specs.

Chicago TDD: Tests verify real vendor specs can be loaded and parsed.
"""

from pathlib import Path

import pytest

from kgcl.yawl.integration.vendor_loader import VendorSpec, VendorSpecLoader


@pytest.fixture
def loader() -> VendorSpecLoader:
    """Create vendor spec loader."""
    return VendorSpecLoader()


class TestVendorSpecLoaderDiscovery:
    """Tests for discovering available specs."""

    def test_specs_path_exists(self, loader: VendorSpecLoader) -> None:
        """Specs directory exists in vendor."""
        # Skip if vendor not available
        if not loader.vendor_path.exists():
            pytest.skip("Vendor directory not available")

        assert loader.specs_path.exists()

    def test_list_specs_returns_xml_files(self, loader: VendorSpecLoader) -> None:
        """list_specs returns available XML files."""
        if not loader.vendor_path.exists():
            pytest.skip("Vendor directory not available")

        specs = loader.list_specs()

        assert len(specs) > 0
        assert all(s.endswith(".xml") for s in specs)

    def test_list_specs_includes_maketrip(self, loader: VendorSpecLoader) -> None:
        """list_specs includes maketrip example."""
        if not loader.vendor_path.exists():
            pytest.skip("Vendor directory not available")

        specs = loader.list_specs()

        maketrip_specs = [s for s in specs if "maketrip" in s.lower() or "makeTrip" in s]
        assert len(maketrip_specs) > 0


class TestVendorSpecLoaderParsing:
    """Tests for parsing vendor specs."""

    def test_load_maketrip_returns_spec(self, loader: VendorSpecLoader) -> None:
        """load_spec returns VendorSpec for maketrip."""
        if not loader.vendor_path.exists():
            pytest.skip("Vendor directory not available")

        spec = loader.load_spec("maketrip1.xml")

        assert spec is not None
        assert isinstance(spec, VendorSpec)

    def test_maketrip_has_uri(self, loader: VendorSpecLoader) -> None:
        """Maketrip spec has URI."""
        if not loader.vendor_path.exists():
            pytest.skip("Vendor directory not available")

        spec = loader.load_spec("maketrip1.xml")

        assert spec is not None
        assert spec.uri == "Maketrip1.xml"

    def test_maketrip_has_name(self, loader: VendorSpecLoader) -> None:
        """Maketrip spec has name."""
        if not loader.vendor_path.exists():
            pytest.skip("Vendor directory not available")

        spec = loader.load_spec("maketrip1.xml")

        assert spec is not None
        assert "trip" in spec.name.lower() or "book" in spec.name.lower()

    def test_maketrip_has_documentation(self, loader: VendorSpecLoader) -> None:
        """Maketrip spec has documentation."""
        if not loader.vendor_path.exists():
            pytest.skip("Vendor directory not available")

        spec = loader.load_spec("maketrip1.xml")

        assert spec is not None
        assert len(spec.documentation) > 0

    def test_maketrip_has_root_net(self, loader: VendorSpecLoader) -> None:
        """Maketrip spec has root net."""
        if not loader.vendor_path.exists():
            pytest.skip("Vendor directory not available")

        spec = loader.load_spec("maketrip1.xml")

        assert spec is not None
        assert spec.root_net_id == "make_trip"


class TestVendorSpecLoaderTasks:
    """Tests for parsing tasks from vendor specs."""

    def test_maketrip_has_tasks(self, loader: VendorSpecLoader) -> None:
        """Maketrip spec has tasks."""
        if not loader.vendor_path.exists():
            pytest.skip("Vendor directory not available")

        spec = loader.load_spec("maketrip1.xml")

        assert spec is not None
        assert len(spec.tasks) > 0

    def test_maketrip_has_register_task(self, loader: VendorSpecLoader) -> None:
        """Maketrip has register task."""
        if not loader.vendor_path.exists():
            pytest.skip("Vendor directory not available")

        spec = loader.load_spec("maketrip1.xml")

        assert spec is not None
        task_ids = [t["id"] for t in spec.tasks]
        assert "register" in task_ids

    def test_maketrip_has_flight_task(self, loader: VendorSpecLoader) -> None:
        """Maketrip has flight task."""
        if not loader.vendor_path.exists():
            pytest.skip("Vendor directory not available")

        spec = loader.load_spec("maketrip1.xml")

        assert spec is not None
        task_ids = [t["id"] for t in spec.tasks]
        assert "flight" in task_ids

    def test_maketrip_has_hotel_task(self, loader: VendorSpecLoader) -> None:
        """Maketrip has hotel task."""
        if not loader.vendor_path.exists():
            pytest.skip("Vendor directory not available")

        spec = loader.load_spec("maketrip1.xml")

        assert spec is not None
        task_ids = [t["id"] for t in spec.tasks]
        assert "hotel" in task_ids

    def test_maketrip_has_car_task(self, loader: VendorSpecLoader) -> None:
        """Maketrip has car task."""
        if not loader.vendor_path.exists():
            pytest.skip("Vendor directory not available")

        spec = loader.load_spec("maketrip1.xml")

        assert spec is not None
        task_ids = [t["id"] for t in spec.tasks]
        assert "car" in task_ids

    def test_maketrip_has_pay_task(self, loader: VendorSpecLoader) -> None:
        """Maketrip has pay task."""
        if not loader.vendor_path.exists():
            pytest.skip("Vendor directory not available")

        spec = loader.load_spec("maketrip1.xml")

        assert spec is not None
        task_ids = [t["id"] for t in spec.tasks]
        assert "pay" in task_ids

    def test_task_has_join_split(self, loader: VendorSpecLoader) -> None:
        """Tasks have join/split types."""
        if not loader.vendor_path.exists():
            pytest.skip("Vendor directory not available")

        spec = loader.load_spec("maketrip1.xml")

        assert spec is not None
        register_task = next((t for t in spec.tasks if t["id"] == "register"), None)
        assert register_task is not None
        assert register_task["split"] == "or"  # OR-split for conditional branching


class TestVendorSpecLoaderConditions:
    """Tests for parsing conditions from vendor specs."""

    def test_maketrip_has_conditions(self, loader: VendorSpecLoader) -> None:
        """Maketrip spec has conditions."""
        if not loader.vendor_path.exists():
            pytest.skip("Vendor directory not available")

        spec = loader.load_spec("maketrip1.xml")

        assert spec is not None
        assert len(spec.conditions) >= 2  # At least input and output

    def test_maketrip_has_input_condition(self, loader: VendorSpecLoader) -> None:
        """Maketrip has input condition (start)."""
        if not loader.vendor_path.exists():
            pytest.skip("Vendor directory not available")

        spec = loader.load_spec("maketrip1.xml")

        assert spec is not None
        input_conds = [c for c in spec.conditions if c["type"] == "input"]
        assert len(input_conds) == 1

    def test_maketrip_has_output_condition(self, loader: VendorSpecLoader) -> None:
        """Maketrip has output condition (end)."""
        if not loader.vendor_path.exists():
            pytest.skip("Vendor directory not available")

        spec = loader.load_spec("maketrip1.xml")

        assert spec is not None
        output_conds = [c for c in spec.conditions if c["type"] == "output"]
        assert len(output_conds) == 1


class TestVendorSpecLoaderFlows:
    """Tests for parsing flows from vendor specs."""

    def test_maketrip_has_flows(self, loader: VendorSpecLoader) -> None:
        """Maketrip spec has flows."""
        if not loader.vendor_path.exists():
            pytest.skip("Vendor directory not available")

        spec = loader.load_spec("maketrip1.xml")

        assert spec is not None
        assert len(spec.flows) > 0

    def test_flows_have_source_target(self, loader: VendorSpecLoader) -> None:
        """Flows have source and target."""
        if not loader.vendor_path.exists():
            pytest.skip("Vendor directory not available")

        spec = loader.load_spec("maketrip1.xml")

        assert spec is not None
        for flow in spec.flows:
            assert flow["source"]
            assert flow["target"]

    def test_conditional_flows_have_predicates(self, loader: VendorSpecLoader) -> None:
        """Conditional flows have predicates."""
        if not loader.vendor_path.exists():
            pytest.skip("Vendor directory not available")

        spec = loader.load_spec("maketrip1.xml")

        assert spec is not None
        flows_with_predicates = [f for f in spec.flows if f.get("predicate")]
        # Maketrip has conditional flows for flight/hotel/car
        assert len(flows_with_predicates) >= 3


class TestVendorSpecLoaderVariables:
    """Tests for parsing variables from vendor specs."""

    def test_maketrip_has_variables(self, loader: VendorSpecLoader) -> None:
        """Maketrip spec has variables."""
        if not loader.vendor_path.exists():
            pytest.skip("Vendor directory not available")

        spec = loader.load_spec("maketrip1.xml")

        assert spec is not None
        assert len(spec.variables) > 0

    def test_maketrip_has_customer_variable(self, loader: VendorSpecLoader) -> None:
        """Maketrip has customer variable."""
        if not loader.vendor_path.exists():
            pytest.skip("Vendor directory not available")

        spec = loader.load_spec("maketrip1.xml")

        assert spec is not None
        var_names = [v["name"] for v in spec.variables]
        assert "customer" in var_names

    def test_maketrip_has_booking_flags(self, loader: VendorSpecLoader) -> None:
        """Maketrip has booking flag variables."""
        if not loader.vendor_path.exists():
            pytest.skip("Vendor directory not available")

        spec = loader.load_spec("maketrip1.xml")

        assert spec is not None
        var_names = [v["name"] for v in spec.variables]
        assert "want_flight" in var_names
        assert "want_hotel" in var_names
        assert "want_car" in var_names

    def test_variables_have_types(self, loader: VendorSpecLoader) -> None:
        """Variables have XSD types."""
        if not loader.vendor_path.exists():
            pytest.skip("Vendor directory not available")

        spec = loader.load_spec("maketrip1.xml")

        assert spec is not None
        for var in spec.variables:
            assert var["type"].startswith("xs:")


class TestVendorSpecLoaderDecompositions:
    """Tests for parsing decompositions from vendor specs."""

    def test_maketrip_has_decompositions(self, loader: VendorSpecLoader) -> None:
        """Maketrip spec has decompositions."""
        if not loader.vendor_path.exists():
            pytest.skip("Vendor directory not available")

        spec = loader.load_spec("maketrip1.xml")

        assert spec is not None
        assert len(spec.decompositions) > 0

    def test_decompositions_have_params(self, loader: VendorSpecLoader) -> None:
        """Decompositions have input/output params."""
        if not loader.vendor_path.exists():
            pytest.skip("Vendor directory not available")

        spec = loader.load_spec("maketrip1.xml")

        assert spec is not None
        register_decomp = next((d for d in spec.decompositions if d["id"] == "register"), None)
        assert register_decomp is not None
        assert len(register_decomp.get("inputParams", [])) > 0
        assert len(register_decomp.get("outputParams", [])) > 0


class TestVendorSpecLoaderBulkLoad:
    """Tests for loading all specs."""

    def test_load_all_specs_returns_list(self, loader: VendorSpecLoader) -> None:
        """load_all_specs returns list of specs."""
        if not loader.vendor_path.exists():
            pytest.skip("Vendor directory not available")

        specs = loader.load_all_specs()

        assert isinstance(specs, list)
        assert len(specs) > 0

    def test_all_specs_have_uri(self, loader: VendorSpecLoader) -> None:
        """All loaded specs have URI."""
        if not loader.vendor_path.exists():
            pytest.skip("Vendor directory not available")

        specs = loader.load_all_specs()

        for spec in specs:
            assert spec.uri


class TestVendorSpecLoaderErrorHandling:
    """Tests for error handling."""

    def test_load_nonexistent_returns_none(self, loader: VendorSpecLoader) -> None:
        """Loading nonexistent file returns None."""
        spec = loader.load_spec("nonexistent.xml")
        assert spec is None

    def test_invalid_path_returns_empty_list(self) -> None:
        """Invalid vendor path returns empty list."""
        loader = VendorSpecLoader(vendor_path=Path("/nonexistent/path"))
        specs = loader.list_specs()
        assert specs == []

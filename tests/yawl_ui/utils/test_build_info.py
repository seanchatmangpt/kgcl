"""Tests for BuildInformation and BuildProperties."""

import pytest

from kgcl.yawl_ui.utils.build_info import BuildInformation, BuildProperties


class TestBuildProperties:
    """Test suite for BuildProperties dataclass."""

    def test_creation(self) -> None:
        """Test creating BuildProperties."""
        props = BuildProperties(version="5.2.0", number="1234", date="2022-11-28")

        assert props.version == "5.2.0"
        assert props.number == "1234"
        assert props.date == "2022-11-28"

    def test_creation_with_none(self) -> None:
        """Test creating BuildProperties with None values."""
        props = BuildProperties(version=None, number=None, date=None)

        assert props.version is None
        assert props.number is None
        assert props.date is None

    def test_as_dict(self) -> None:
        """Test converting to dictionary."""
        props = BuildProperties(version="5.2.0", number="1234", date="2022-11-28")

        result = props.as_dict()

        assert result == {"BuildDate": "2022-11-28", "Version": "5.2.0", "BuildNumber": "1234"}

    def test_as_dict_with_none(self) -> None:
        """Test dictionary conversion with None values."""
        props = BuildProperties(version=None, number=None, date=None)

        result = props.as_dict()

        assert result == {"BuildDate": None, "Version": None, "BuildNumber": None}

    def test_frozen(self) -> None:
        """Test that BuildProperties is frozen (immutable)."""
        props = BuildProperties(version="5.2.0", number="1234", date="2022-11-28")

        with pytest.raises(AttributeError):
            props.version = "6.0.0"  # type: ignore[misc]


class TestBuildInformation:
    """Test suite for BuildInformation class."""

    def test_empty_initialization(self) -> None:
        """Test initializing with no properties."""
        info = BuildInformation()

        assert info.get("any.key") is None

    def test_initialization_with_properties(self) -> None:
        """Test initializing with properties dict."""
        props = {"ui.service.version": "5.2.0", "ui.service.build": "1234", "ui.service.build.date": "2022-11-28"}

        info = BuildInformation(props)

        assert info.get("ui.service.version") == "5.2.0"
        assert info.get("ui.service.build") == "1234"
        assert info.get("ui.service.build.date") == "2022-11-28"

    def test_get_ui_properties(self) -> None:
        """Test getting UI service properties."""
        props = {"ui.service.version": "5.2.0", "ui.service.build": "1234", "ui.service.build.date": "2022-11-28"}

        info = BuildInformation(props)
        ui_props = info.get_ui_properties()

        assert ui_props.version == "5.2.0"
        assert ui_props.number == "1234"
        assert ui_props.date == "2022-11-28"

    def test_get_mail_service_properties(self) -> None:
        """Test getting mail service properties."""
        props = {"mail.service.version": "2.0.0", "mail.service.build": "5678", "mail.service.build.date": "2022-10-15"}

        info = BuildInformation(props)
        mail_props = info.get_mail_service_properties()

        assert mail_props.version == "2.0.0"
        assert mail_props.number == "5678"
        assert mail_props.date == "2022-10-15"

    def test_get_invoker_service_properties(self) -> None:
        """Test getting invoker service properties."""
        props = {
            "invoker.service.version": "3.1.0",
            "invoker.service.build": "9012",
            "invoker.service.build.date": "2022-09-20",
        }

        info = BuildInformation(props)
        invoker_props = info.get_invoker_service_properties()

        assert invoker_props.version == "3.1.0"
        assert invoker_props.number == "9012"
        assert invoker_props.date == "2022-09-20"

    def test_get_docstore_properties(self) -> None:
        """Test getting document store properties."""
        props = {
            "docstore.service.version": "1.5.0",
            "docstore.service.build": "3456",
            "docstore.service.build.date": "2022-08-10",
        }

        info = BuildInformation(props)
        docstore_props = info.get_docstore_properties()

        assert docstore_props.version == "1.5.0"
        assert docstore_props.number == "3456"
        assert docstore_props.date == "2022-08-10"

    def test_missing_properties(self) -> None:
        """Test behavior when properties are missing."""
        info = BuildInformation()
        ui_props = info.get_ui_properties()

        assert ui_props.version is None
        assert ui_props.number is None
        assert ui_props.date is None

    def test_partial_properties(self) -> None:
        """Test behavior with partial property set."""
        props = {
            "ui.service.version": "5.2.0"
            # Missing build and date
        }

        info = BuildInformation(props)
        ui_props = info.get_ui_properties()

        assert ui_props.version == "5.2.0"
        assert ui_props.number is None
        assert ui_props.date is None

    def test_multiple_service_properties(self) -> None:
        """Test handling multiple service property sets."""
        props = {
            "ui.service.version": "5.2.0",
            "ui.service.build": "1234",
            "ui.service.build.date": "2022-11-28",
            "mail.service.version": "2.0.0",
            "mail.service.build": "5678",
            "mail.service.build.date": "2022-10-15",
        }

        info = BuildInformation(props)

        ui_props = info.get_ui_properties()
        assert ui_props.version == "5.2.0"

        mail_props = info.get_mail_service_properties()
        assert mail_props.version == "2.0.0"

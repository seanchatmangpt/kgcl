"""YAWL specification upload result models.

Ported from org.yawlfoundation.yawl.ui.service.UploadResult
"""

from dataclasses import dataclass, field

from kgcl.yawl_ui.models.case import SpecificationID


@dataclass(frozen=True)
class UploadResult:
    """Result of uploading a YAWL specification.

    Contains specification IDs, warnings, and errors from the upload
    and validation process.

    Parameters
    ----------
    specs : list[SpecificationID]
        Successfully uploaded specification IDs
    warnings : list[str]
        Warning messages from validation
    errors : list[str]
        Error messages from validation

    Examples
    --------
    >>> spec = SpecificationID("OrderProcess", "1.0")
    >>> result = UploadResult([spec], ["Minor issue"], [])
    >>> result.has_warnings()
    True
    >>> result.has_errors()
    False
    >>> result.has_spec_ids()
    True
    """

    specs: list[SpecificationID] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def has_warnings(self) -> bool:
        """Check if result has warnings.

        Returns
        -------
        bool
            True if warnings present
        """
        return len(self.warnings) > 0

    def has_errors(self) -> bool:
        """Check if result has errors.

        Returns
        -------
        bool
            True if errors present
        """
        return len(self.errors) > 0

    def has_messages(self) -> bool:
        """Check if result has any messages.

        Returns
        -------
        bool
            True if warnings or errors present
        """
        return self.has_warnings() or self.has_errors()

    def has_spec_ids(self) -> bool:
        """Check if result has specification IDs.

        Returns
        -------
        bool
            True if at least one specification ID present
        """
        return len(self.specs) > 0

    def get_warnings(self) -> list[str]:
        """Get warning messages.

        Returns
        -------
        list[str]
            Warning messages
        """
        return list(self.warnings)

    def get_errors(self) -> list[str]:
        """Get error messages.

        Returns
        -------
        list[str]
            Error messages
        """
        return list(self.errors)

    def get_spec_ids(self) -> list[SpecificationID]:
        """Get specification IDs.

        Returns
        -------
        list[SpecificationID]
            Successfully uploaded specification IDs
        """
        return list(self.specs)

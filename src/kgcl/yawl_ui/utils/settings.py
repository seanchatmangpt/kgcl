"""Application settings management.

Ported from org.yawlfoundation.yawl.ui.util.Settings
"""


class Settings:
    """Global application settings.

    This class manages application-wide settings, particularly for admin actions.
    Uses class-level state to maintain singleton behavior from Java original.

    Attributes
    ----------
    _admin_actions_directly_to_current_user : bool
        Whether admin actions should be assigned directly to the current user
    """

    _admin_actions_directly_to_current_user: bool = False

    @classmethod
    def set_directly_to_me(cls, value: bool) -> None:
        """Set whether admin actions should go directly to current user.

        Parameters
        ----------
        value : bool
            True to assign admin actions directly to current user
        """
        cls._admin_actions_directly_to_current_user = value

    @classmethod
    def is_directly_to_me(cls) -> bool:
        """Check if admin actions go directly to current user.

        Returns
        -------
        bool
            True if admin actions are assigned directly to current user
        """
        return cls._admin_actions_directly_to_current_user

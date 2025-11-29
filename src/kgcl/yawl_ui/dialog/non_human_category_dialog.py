""""""

from __future__ import annotations

from typing import Any

import httpx


class NonHumanCategoryDialog:
    """"""

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        """Initialize YAWL client.

        Parameters
        ----------
        base_url : str
            YAWL server base URL
        timeout : float
            HTTP request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        """Close HTTP client connection."""
        await self.client.aclose()

    async def __aenter__(self) -> NonHumanCategoryDialog:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def get_ok_button(self) -> Any:
        """

        Parameters
        ----------

        Returns
        -------
        Any

        """
        # Auto-generated implementation stub

    async def validate(self) -> bool:
        """

        Parameters
        ----------

        Returns
        -------
        bool

        """
        # Auto-generated implementation stub

    async def update_service(self) -> None:
        """

        Parameters
        ----------

        Returns
        -------
        None

        """
        # Auto-generated implementation stub

    async def create_form(self) -> Any:
        """

        Parameters
        ----------

        Returns
        -------
        Any

        """
        # Auto-generated implementation stub

    async def populate_form(self) -> None:
        """

        Parameters
        ----------

        Returns
        -------
        None

        """
        # Auto-generated implementation stub

    async def validate_name(self) -> bool:
        """

        Parameters
        ----------

        Returns
        -------
        bool

        """
        # Auto-generated implementation stub

    async def is_unique_name(self) -> bool:
        """

        Parameters
        ----------

        Returns
        -------
        bool

        """
        # Auto-generated implementation stub

    async def is_editing(self) -> bool:
        """

        Parameters
        ----------

        Returns
        -------
        bool

        """
        # Auto-generated implementation stub

    async def init_members_combo(self) -> None:
        """

        Parameters
        ----------

        Returns
        -------
        None

        """
        # Auto-generated implementation stub

    async def create_sub_category_list(self) -> Any[Any]:
        """

        Parameters
        ----------

        Returns
        -------
        Any[Any]

        """
        # Auto-generated implementation stub

    async def is_unique_sub_category(self) -> bool:
        """

        Parameters
        ----------

        Returns
        -------
        bool

        """
        # Auto-generated implementation stub

    async def sort_sub_categories(self) -> None:
        """

        Parameters
        ----------

        Returns
        -------
        None

        """
        # Auto-generated implementation stub

    async def has_updates(self) -> bool:
        """

        Parameters
        ----------

        Returns
        -------
        bool

        """
        # Auto-generated implementation stub

    async def add(self) -> None:
        """

        Parameters
        ----------

        Returns
        -------
        None

        """
        # Auto-generated implementation stub

    async def update(self) -> None:
        """

        Parameters
        ----------

        Returns
        -------
        None

        """
        # Auto-generated implementation stub

    async def update_sub_categories(self) -> None:
        """

        Parameters
        ----------

        Returns
        -------
        None

        """
        # Auto-generated implementation stub

    async def not_in_other(self) -> list[Any]:
        """

        Parameters
        ----------

        Returns
        -------
        list[Any]

        """
        # Auto-generated implementation stub

    async def add_sub_categories(self) -> None:
        """

        Parameters
        ----------

        Returns
        -------
        None

        """
        # Auto-generated implementation stub

    async def remove_sub_categories(self) -> None:
        """

        Parameters
        ----------

        Returns
        -------
        None

        """
        # Auto-generated implementation stub

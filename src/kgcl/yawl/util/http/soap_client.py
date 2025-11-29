"""SOAP client utility for web service calls.

Provides SOAP envelope creation and web service invocation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

from kgcl.yawl.util.xml.xnode import XNode
from kgcl.yawl.util.xml.xnode_parser import XNodeParser

_NS_PREFIX = "yns"  # Candidate namespace prefix


class SoapClient:
    """SOAP client for web service calls.

    Parameters
    ----------
    endpoint : str
        SOAP service endpoint URL
    """

    def __init__(self, endpoint: str) -> None:
        """Initialize SOAP client.

        Parameters
        ----------
        endpoint : str
            SOAP service endpoint URL
        """
        self._endpoint: str = endpoint

    def send(self, ns: str, action: str, arg_keys: Sequence[str] | None, arg_values: Sequence[str] | None) -> str:
        """Send a SOAP request to a web service.

        Parameters
        ----------
        ns : str
            Namespace URI
        action : str
            Action name
        arg_keys : Sequence[str] | None
            Argument names (may be None)
        arg_values : Sequence[str] | None
            Argument values

        Returns
        -------
        str
            Response value from web service

        Raises
        ------
        ValueError
            If arg_keys and arg_values have different sizes
        OSError
            If there's a problem connecting to the web service
        """
        envelope = self._create_envelope(ns, action, arg_keys, arg_values)
        response = self._call_soap_service(envelope)
        return self._get_response_value(response)

    def _create_envelope(
        self, ns: str, action: str, arg_keys: Sequence[str] | None, arg_values: Sequence[str] | None
    ) -> str:
        """Create SOAP envelope with required attributes.

        Parameters
        ----------
        ns : str
            Namespace URI
        action : str
            Action name
        arg_keys : Sequence[str] | None
            Argument names
        arg_values : Sequence[str] | None
            Argument values

        Returns
        -------
        str
            SOAP envelope XML string

        Raises
        ------
        ValueError
            If arg_keys and arg_values have different sizes
        """
        if self._get_size(arg_keys) != self._get_size(arg_values):
            raise ValueError("arg_keys has different size to arg_values")

        root = XNode("soapenv:Envelope")
        root.add_attribute("xmlns:soapenv", "http://schemas.xmlsoap.org/soap/envelope/")
        root.add_attribute(f"xmlns:{_NS_PREFIX}", ns)
        root.add_child("soapenv:Header")
        body = root.add_child("soapenv:Body")
        binding = body.add_child(f"{_NS_PREFIX}:{action}")

        if arg_keys:
            for key, value in zip(arg_keys, arg_values):
                binding.add_child(key, value)

        return root.to_string()

    def _call_soap_service(self, envelope: str) -> str:
        """Call SOAP web service.

        Parameters
        ----------
        envelope : str
            SOAP envelope XML

        Returns
        -------
        str
            SOAP response XML

        Raises
        ------
        OSError
            If call fails
        """
        try:
            # Use httpx or requests for SOAP call
            import httpx

            headers = {"Content-Type": "text/xml; charset=utf-8", "SOAPAction": ""}

            with httpx.Client(timeout=30.0) as client:
                response = client.post(self._endpoint, content=envelope, headers=headers)
                response.raise_for_status()
                return response.text

        except ImportError:
            try:
                import requests

                headers = {"Content-Type": "text/xml; charset=utf-8", "SOAPAction": ""}

                response = requests.post(self._endpoint, data=envelope, headers=headers, timeout=30.0)
                response.raise_for_status()
                return response.text

            except ImportError:
                raise OSError("No HTTP library available (httpx or requests required)")

    def _get_response_value(self, response_xml: str) -> str | None:
        """Extract return value from SOAP response.

        Parameters
        ----------
        response_xml : str
            SOAP response XML

        Returns
        -------
        str | None
            Return value, or None if not found
        """
        parser = XNodeParser()
        root = parser.parse(response_xml)
        if root is None:
            return None

        # Drill down to return node
        child = root.get_child()
        while child is not None and child.get_name() != "return":
            child = child.get_child()

        return child.to_pretty_string() if child else None

    def _get_size(self, items: Sequence[object] | None) -> int:
        """Get size of sequence, or 0 if None.

        Parameters
        ----------
        items : Sequence[object] | None
            Sequence to get size of

        Returns
        -------
        int
            Size of sequence, or 0 if None
        """
        return len(items) if items is not None else 0

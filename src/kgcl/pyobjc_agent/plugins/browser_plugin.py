"""
Browser plugin for Safari and Chrome history access.

This plugin provides capabilities for:
- Reading Safari browsing history
- Reading Chrome browsing history
- URL visit tracking
- Browser session reconstruction
"""

import logging
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .base import BaseCapabilityPlugin, CapabilityData, CapabilityDescriptor, EntitlementLevel

logger = logging.getLogger(__name__)


class BrowserPlugin(BaseCapabilityPlugin):
    """
    Browser history capability discovery plugin.

    Provides read-only access to:
    - Safari browsing history database
    - Chrome browsing history database
    - Visit timestamps and URLs
    - Session reconstruction
    """

    # Default paths for browser history databases
    SAFARI_HISTORY_PATH = "~/Library/Safari/History.db"
    CHROME_HISTORY_PATH = "~/Library/Application Support/Google/Chrome/Default/History"

    @property
    def plugin_name(self) -> str:
        return "Browser History Plugin"

    @property
    def plugin_version(self) -> str:
        return "1.0.0"

    @property
    def required_frameworks(self) -> list[str]:
        # No PyObjC frameworks required - uses SQLite directly
        return []

    def discover_capabilities(self) -> list[CapabilityDescriptor]:
        """Discover browser history capabilities."""
        capabilities = [
            CapabilityDescriptor(
                name="safari_history",
                description="Read Safari browsing history",
                framework="Safari",
                required_entitlement=EntitlementLevel.FULL_DISK_ACCESS,
                refresh_interval=300.0,  # 5 minutes
                tags={"browser", "safari", "history"},
                data_schema={
                    "type": "object",
                    "properties": {
                        "visits": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "url": {"type": "string"},
                                    "title": {"type": "string"},
                                    "visit_time": {"type": "string", "format": "date-time"},
                                    "visit_count": {"type": "integer"},
                                },
                            },
                        }
                    },
                },
            ),
            CapabilityDescriptor(
                name="chrome_history",
                description="Read Chrome browsing history",
                framework="Chrome",
                required_entitlement=EntitlementLevel.FULL_DISK_ACCESS,
                refresh_interval=300.0,
                tags={"browser", "chrome", "history"},
                data_schema={
                    "type": "object",
                    "properties": {
                        "visits": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "url": {"type": "string"},
                                    "title": {"type": "string"},
                                    "visit_time": {"type": "string", "format": "date-time"},
                                    "visit_count": {"type": "integer"},
                                },
                            },
                        }
                    },
                },
            ),
            CapabilityDescriptor(
                name="recent_browsing_activity",
                description="Get recent browsing activity from all browsers",
                framework="Mixed",
                required_entitlement=EntitlementLevel.FULL_DISK_ACCESS,
                refresh_interval=60.0,
                tags={"browser", "history", "aggregated"},
                data_schema={
                    "type": "object",
                    "properties": {
                        "time_window_hours": {"type": "integer"},
                        "total_visits": {"type": "integer"},
                        "browsers": {
                            "type": "object",
                            "properties": {
                                "safari": {"type": "integer"},
                                "chrome": {"type": "integer"},
                            },
                        },
                        "top_domains": {"type": "array"},
                    },
                },
            ),
        ]

        return capabilities

    def check_entitlements(self) -> dict[str, bool]:
        """Check if browser history databases are accessible."""
        entitlements = {
            "safari_access": self._check_safari_access(),
            "chrome_access": self._check_chrome_access(),
        }

        return entitlements

    def _check_safari_access(self) -> bool:
        """Check if Safari history database is accessible."""
        safari_path = Path(self.SAFARI_HISTORY_PATH).expanduser()
        accessible = safari_path.exists() and os.access(safari_path, os.R_OK)

        if not accessible:
            logger.warning(
                f"Safari history not accessible at {safari_path}. "
                "May require Full Disk Access permission."
            )

        return accessible

    def _check_chrome_access(self) -> bool:
        """Check if Chrome history database is accessible."""
        chrome_path = Path(self.CHROME_HISTORY_PATH).expanduser()
        accessible = chrome_path.exists() and os.access(chrome_path, os.R_OK)

        if not accessible:
            logger.debug(
                f"Chrome history not accessible at {chrome_path}. "
                "Chrome may not be installed or requires Full Disk Access."
            )

        return accessible

    def collect_capability_data(
        self, capability_name: str, parameters: dict[str, Any] | None = None
    ) -> CapabilityData:
        """Collect browser history data."""
        timestamp = datetime.utcnow()
        params = parameters or {}

        try:
            if capability_name == "safari_history":
                data = self._get_safari_history(params)
            elif capability_name == "chrome_history":
                data = self._get_chrome_history(params)
            elif capability_name == "recent_browsing_activity":
                data = self._get_recent_activity(params)
            else:
                raise ValueError(f"Unknown capability: {capability_name}")

            return CapabilityData(
                capability_name=capability_name,
                timestamp=timestamp,
                data=data,
                metadata={"plugin": self.plugin_id},
            )

        except Exception as e:
            logger.error(f"Error collecting {capability_name}: {e}")
            return CapabilityData(
                capability_name=capability_name, timestamp=timestamp, data={}, error=str(e)
            )

    def _get_safari_history(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Read Safari browsing history.

        Args:
            params: Query parameters (limit, hours_back, etc.)

        Returns
        -------
            Dictionary with Safari history data
        """
        safari_path = Path(self.SAFARI_HISTORY_PATH).expanduser()

        if not safari_path.exists():
            return {"error": "Safari history database not found", "visits": []}

        limit = params.get("limit", 100)
        hours_back = params.get("hours_back", 24)

        try:
            # Safari uses WebKit timestamp (seconds since 2001-01-01)
            webkit_epoch = datetime(2001, 1, 1)
            time_threshold = (
                datetime.utcnow() - timedelta(hours=hours_back) - webkit_epoch
            ).total_seconds()

            # Connect to Safari history database (read-only)
            conn = sqlite3.connect(f"file:{safari_path}?mode=ro", uri=True)
            cursor = conn.cursor()

            # Query history_visits and history_items tables
            query = """
                SELECT
                    hi.url,
                    hi.title,
                    hv.visit_time,
                    hi.visit_count
                FROM history_visits hv
                JOIN history_items hi ON hv.history_item = hi.id
                WHERE hv.visit_time > ?
                ORDER BY hv.visit_time DESC
                LIMIT ?
            """

            cursor.execute(query, (time_threshold, limit))
            rows = cursor.fetchall()

            visits = []
            for row in rows:
                url, title, visit_time, visit_count = row

                # Convert WebKit timestamp to datetime
                visit_datetime = webkit_epoch + timedelta(seconds=visit_time)

                visits.append(
                    {
                        "url": url,
                        "title": title or "",
                        "visit_time": visit_datetime.isoformat(),
                        "visit_count": visit_count or 1,
                    }
                )

            conn.close()

            return {
                "count": len(visits),
                "visits": visits,
                "query_params": {"limit": limit, "hours_back": hours_back},
            }

        except sqlite3.Error as e:
            logger.error(f"Safari database error: {e}")
            raise RuntimeError(f"Failed to read Safari history: {e}")

    def _get_chrome_history(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Read Chrome browsing history.

        Args:
            params: Query parameters (limit, hours_back, etc.)

        Returns
        -------
            Dictionary with Chrome history data
        """
        chrome_path = Path(self.CHROME_HISTORY_PATH).expanduser()

        if not chrome_path.exists():
            return {"error": "Chrome history database not found", "visits": []}

        limit = params.get("limit", 100)
        hours_back = params.get("hours_back", 24)

        try:
            # Chrome uses microseconds since Unix epoch
            time_threshold = int(
                (datetime.utcnow() - timedelta(hours=hours_back)).timestamp() * 1_000_000
            )

            # Connect to Chrome history database (read-only)
            conn = sqlite3.connect(f"file:{chrome_path}?mode=ro", uri=True)
            cursor = conn.cursor()

            # Query urls and visits tables
            query = """
                SELECT
                    u.url,
                    u.title,
                    v.visit_time,
                    u.visit_count
                FROM visits v
                JOIN urls u ON v.url = u.id
                WHERE v.visit_time > ?
                ORDER BY v.visit_time DESC
                LIMIT ?
            """

            cursor.execute(query, (time_threshold, limit))
            rows = cursor.fetchall()

            visits = []
            chrome_epoch = datetime(1601, 1, 1)

            for row in rows:
                url, title, visit_time, visit_count = row

                # Convert Chrome timestamp (microseconds since 1601) to datetime
                visit_datetime = chrome_epoch + timedelta(microseconds=visit_time)

                visits.append(
                    {
                        "url": url,
                        "title": title or "",
                        "visit_time": visit_datetime.isoformat(),
                        "visit_count": visit_count or 1,
                    }
                )

            conn.close()

            return {
                "count": len(visits),
                "visits": visits,
                "query_params": {"limit": limit, "hours_back": hours_back},
            }

        except sqlite3.Error as e:
            logger.error(f"Chrome database error: {e}")
            raise RuntimeError(f"Failed to read Chrome history: {e}")

    def _get_recent_activity(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Get aggregated recent browsing activity from all browsers.

        Args:
            params: Query parameters

        Returns
        -------
            Aggregated browsing statistics
        """
        hours_back = params.get("hours_back", 24)

        # Collect from both browsers
        safari_data = self._get_safari_history({"hours_back": hours_back, "limit": 1000})
        chrome_data = self._get_chrome_history({"hours_back": hours_back, "limit": 1000})

        # Aggregate statistics
        safari_visits = safari_data.get("visits", [])
        chrome_visits = chrome_data.get("visits", [])

        total_visits = len(safari_visits) + len(chrome_visits)

        # Extract domains
        domains = {}
        for visit in safari_visits + chrome_visits:
            url = visit.get("url", "")
            try:
                from urllib.parse import urlparse

                domain = urlparse(url).netloc
                if domain:
                    domains[domain] = domains.get(domain, 0) + 1
            except Exception:
                continue

        # Sort by visit count
        top_domains = sorted(
            [{"domain": d, "count": c} for d, c in domains.items()],
            key=lambda x: x["count"],
            reverse=True,
        )[:10]

        return {
            "time_window_hours": hours_back,
            "total_visits": total_visits,
            "browsers": {"safari": len(safari_visits), "chrome": len(chrome_visits)},
            "top_domains": top_domains,
            "unique_domains": len(domains),
        }

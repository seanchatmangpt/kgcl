"""
AppKit plugin for workspace and window discovery.

This plugin provides capabilities for:
- Frontmost application detection
- Window enumeration and properties
- Workspace monitoring
- Application state tracking
"""

import logging
from datetime import datetime
from typing import Any

from .base import BaseCapabilityPlugin, CapabilityData, CapabilityDescriptor, EntitlementLevel

logger = logging.getLogger(__name__)


class AppKitPlugin(BaseCapabilityPlugin):
    """
    AppKit-based capability discovery plugin.

    Provides access to:
    - NSWorkspace for application monitoring
    - NSRunningApplication for app state
    - Window and display information (requires accessibility)
    """

    @property
    def plugin_name(self) -> str:
        return "AppKit Workspace Plugin"

    @property
    def plugin_version(self) -> str:
        return "1.0.0"

    @property
    def required_frameworks(self) -> list[str]:
        return ["AppKit", "Foundation"]

    def discover_capabilities(self) -> list[CapabilityDescriptor]:
        """Discover AppKit-based capabilities."""
        capabilities = [
            CapabilityDescriptor(
                name="frontmost_application",
                description="Get the currently active (frontmost) application",
                framework="AppKit",
                required_entitlement=EntitlementLevel.NONE,
                refresh_interval=1.0,
                is_continuous=True,
                tags={"application", "workspace", "focus"},
                data_schema={
                    "type": "object",
                    "properties": {
                        "bundle_id": {"type": "string"},
                        "app_name": {"type": "string"},
                        "process_id": {"type": "integer"},
                        "is_active": {"type": "boolean"},
                        "launch_date": {"type": "string", "format": "date-time"},
                    },
                },
            ),
            CapabilityDescriptor(
                name="running_applications",
                description="List all currently running applications",
                framework="AppKit",
                required_entitlement=EntitlementLevel.NONE,
                refresh_interval=5.0,
                tags={"application", "workspace", "monitoring"},
                data_schema={
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "bundle_id": {"type": "string"},
                            "app_name": {"type": "string"},
                            "process_id": {"type": "integer"},
                            "is_hidden": {"type": "boolean"},
                            "is_active": {"type": "boolean"},
                        },
                    },
                },
            ),
            CapabilityDescriptor(
                name="workspace_notifications",
                description="Monitor workspace change notifications",
                framework="AppKit",
                required_entitlement=EntitlementLevel.NONE,
                refresh_interval=0.0,
                is_continuous=True,
                tags={"workspace", "notifications", "events"},
                data_schema={
                    "type": "object",
                    "properties": {
                        "notification_type": {"type": "string"},
                        "application": {"type": "object"},
                        "timestamp": {"type": "string", "format": "date-time"},
                    },
                },
            ),
            CapabilityDescriptor(
                name="active_display_count",
                description="Get number of active displays",
                framework="AppKit",
                required_entitlement=EntitlementLevel.NONE,
                refresh_interval=60.0,
                tags={"display", "hardware"},
                data_schema={
                    "type": "object",
                    "properties": {
                        "display_count": {"type": "integer"},
                        "main_display": {"type": "object"},
                    },
                },
            ),
            CapabilityDescriptor(
                name="window_list",
                description="Enumerate visible windows (requires accessibility)",
                framework="AppKit",
                required_entitlement=EntitlementLevel.ACCESSIBILITY,
                refresh_interval=2.0,
                tags={"windows", "accessibility"},
                data_schema={
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "window_id": {"type": "integer"},
                            "owner_name": {"type": "string"},
                            "window_name": {"type": "string"},
                            "bounds": {"type": "object"},
                        },
                    },
                },
            ),
        ]

        return capabilities

    def check_entitlements(self) -> dict[str, bool]:
        """Check for required entitlements."""
        entitlements = {
            "basic_appkit": True,  # Always available if AppKit loads
            "accessibility": self._check_accessibility_access(),
        }

        return entitlements

    def _check_accessibility_access(self) -> bool:
        """
        Check if accessibility access is granted.

        Returns
        -------
            True if accessibility access is available
        """
        try:
            import Quartz

            # Check if we have accessibility permissions
            options = {"AXTrustedCheckOptionPrompt": False}
            trusted = Quartz.AXIsProcessTrustedWithOptions(options)

            if not trusted:
                logger.warning(
                    "Accessibility access not granted. Window enumeration will be limited."
                )

            return trusted

        except Exception as e:
            logger.error(f"Error checking accessibility access: {e}")
            return False

    def collect_capability_data(
        self, capability_name: str, parameters: dict[str, Any] | None = None
    ) -> CapabilityData:
        """Collect data for a specific AppKit capability."""
        timestamp = datetime.utcnow()

        try:
            if capability_name == "frontmost_application":
                data = self._get_frontmost_application()
            elif capability_name == "running_applications":
                data = self._get_running_applications()
            elif capability_name == "active_display_count":
                data = self._get_display_info()
            elif capability_name == "window_list":
                data = self._get_window_list()
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

    def _get_frontmost_application(self) -> dict[str, Any]:
        """
        Get the frontmost (active) application.

        Returns
        -------
            Dictionary with application details
        """
        try:
            from AppKit import NSWorkspace

            workspace = NSWorkspace.sharedWorkspace()
            frontmost_app = workspace.frontmostApplication()

            if not frontmost_app:
                return {"error": "No frontmost application"}

            # Extract application details
            bundle_id = frontmost_app.bundleIdentifier()
            app_name = frontmost_app.localizedName()
            process_id = frontmost_app.processIdentifier()
            is_active = frontmost_app.isActive()

            # Get launch date
            launch_date = frontmost_app.launchDate()
            launch_date_str = None
            if launch_date:
                launch_date_str = launch_date.description()

            return {
                "bundle_id": bundle_id,
                "app_name": app_name,
                "process_id": process_id,
                "is_active": is_active,
                "launch_date": launch_date_str,
            }

        except Exception as e:
            logger.error(f"Error getting frontmost application: {e}")
            raise

    def _get_running_applications(self) -> dict[str, Any]:
        """
        Get all running applications.

        Returns
        -------
            Dictionary with list of running apps
        """
        try:
            from AppKit import NSWorkspace

            workspace = NSWorkspace.sharedWorkspace()
            running_apps = workspace.runningApplications()

            apps_list = []
            for app in running_apps:
                # Skip background agents and daemons
                if app.activationPolicy() == 1:  # NSApplicationActivationPolicyRegular
                    bundle_id = app.bundleIdentifier()
                    app_name = app.localizedName()

                    if bundle_id and app_name:
                        apps_list.append(
                            {
                                "bundle_id": bundle_id,
                                "app_name": app_name,
                                "process_id": app.processIdentifier(),
                                "is_hidden": app.isHidden(),
                                "is_active": app.isActive(),
                            }
                        )

            return {"count": len(apps_list), "applications": apps_list}

        except Exception as e:
            logger.error(f"Error getting running applications: {e}")
            raise

    def _get_display_info(self) -> dict[str, Any]:
        """
        Get display/screen information.

        Returns
        -------
            Dictionary with display details
        """
        try:
            from AppKit import NSScreen

            screens = NSScreen.screens()
            main_screen = NSScreen.mainScreen()

            display_info = {"display_count": len(screens), "displays": []}

            for idx, screen in enumerate(screens):
                frame = screen.frame()
                visible_frame = screen.visibleFrame()

                display_data = {
                    "index": idx,
                    "is_main": (screen == main_screen),
                    "frame": {
                        "x": frame.origin.x,
                        "y": frame.origin.y,
                        "width": frame.size.width,
                        "height": frame.size.height,
                    },
                    "visible_frame": {
                        "x": visible_frame.origin.x,
                        "y": visible_frame.origin.y,
                        "width": visible_frame.size.width,
                        "height": visible_frame.size.height,
                    },
                }

                # Add scale factor if available
                if hasattr(screen, "backingScaleFactor"):
                    display_data["scale_factor"] = screen.backingScaleFactor()

                display_info["displays"].append(display_data)

            return display_info

        except Exception as e:
            logger.error(f"Error getting display info: {e}")
            raise

    def _get_window_list(self) -> dict[str, Any]:
        """
        Get list of visible windows (requires accessibility).

        Returns
        -------
            Dictionary with window information
        """
        try:
            import Quartz

            # Check accessibility access
            if not self._check_accessibility_access():
                return {"error": "Accessibility access required", "windows": []}

            # Get window list
            window_list = Quartz.CGWindowListCopyWindowInfo(
                Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
                Quartz.kCGNullWindowID,
            )

            windows = []
            for window in window_list:
                # Extract window details
                window_data = {
                    "window_id": window.get("kCGWindowNumber", 0),
                    "owner_name": window.get("kCGWindowOwnerName", ""),
                    "window_name": window.get("kCGWindowName", ""),
                    "owner_pid": window.get("kCGWindowOwnerPID", 0),
                    "layer": window.get("kCGWindowLayer", 0),
                }

                # Get bounds if available
                bounds = window.get("kCGWindowBounds")
                if bounds:
                    window_data["bounds"] = {
                        "x": bounds.get("X", 0),
                        "y": bounds.get("Y", 0),
                        "width": bounds.get("Width", 0),
                        "height": bounds.get("Height", 0),
                    }

                windows.append(window_data)

            return {"count": len(windows), "windows": windows}

        except ImportError:
            logger.warning("Quartz framework not available for window enumeration")
            return {"error": "Quartz framework required", "windows": []}
        except Exception as e:
            logger.error(f"Error getting window list: {e}")
            raise

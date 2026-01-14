"""
Device detection from User-Agent strings.

Extracts device type, OS, and browser information for session tracking.
"""

import re
from typing import TypedDict


class DeviceInfo(TypedDict):
    """Device information extracted from User-Agent."""
    deviceType: str
    os: str
    browser: str
    displayName: str


class DeviceDetector:
    """
    Extracts device type and details from User-Agent header.
    """

    # OS detection patterns
    _OS_PATTERNS = [
        (r"iPhone|iPad|iPod", "iOS"),
        (r"Android", "Android"),
        (r"Windows NT", "Windows"),
        (r"Mac OS X", "macOS"),
        (r"Linux", "Linux"),
        (r"CrOS", "Chrome OS"),
    ]

    # Browser detection patterns
    _BROWSER_PATTERNS = [
        (r"Edg/", "Edge"),
        (r"OPR/|Opera", "Opera"),
        (r"Chrome/", "Chrome"),
        (r"Safari/", "Safari"),
        (r"Firefox/", "Firefox"),
    ]

    # Device type patterns
    _MOBILE_PATTERNS = [
        r"Mobile",
        r"Android.*Mobile",
        r"iPhone",
        r"iPod",
    ]

    _TABLET_PATTERNS = [
        r"iPad",
        r"Android(?!.*Mobile)",
        r"Tablet",
    ]

    def detect(self, user_agent: str) -> DeviceInfo:
        """
        Parse User-Agent and return device information.

        Args:
            user_agent: HTTP User-Agent header value

        Returns:
            dict with fields:
                - deviceType: "mobile" | "tablet" | "desktop"
                - os: "iOS" | "Android" | "Windows" | "macOS" | "Linux"
                - browser: "Chrome" | "Safari" | "Firefox" | "Edge" | etc.
                - displayName: Human-readable string, e.g., "Chrome on macOS"
        """
        if not user_agent:
            return DeviceInfo(
                deviceType="desktop",
                os="Unknown",
                browser="Unknown",
                displayName="Unknown device"
            )

        os_name = self._detect_os(user_agent)
        browser = self._detect_browser(user_agent)
        device_type = self._detect_device_type(user_agent)

        display_name = f"{browser} on {os_name}"

        return DeviceInfo(
            deviceType=device_type,
            os=os_name,
            browser=browser,
            displayName=display_name
        )

    def _detect_os(self, user_agent: str) -> str:
        """Detect operating system from User-Agent."""
        for pattern, os_name in self._OS_PATTERNS:
            if re.search(pattern, user_agent, re.IGNORECASE):
                return os_name
        return "Unknown"

    def _detect_browser(self, user_agent: str) -> str:
        """Detect browser from User-Agent."""
        for pattern, browser_name in self._BROWSER_PATTERNS:
            if re.search(pattern, user_agent, re.IGNORECASE):
                return browser_name
        return "Unknown"

    def _detect_device_type(self, user_agent: str) -> str:
        """Detect device type (mobile, tablet, desktop) from User-Agent."""
        for pattern in self._MOBILE_PATTERNS:
            if re.search(pattern, user_agent, re.IGNORECASE):
                return "mobile"

        for pattern in self._TABLET_PATTERNS:
            if re.search(pattern, user_agent, re.IGNORECASE):
                return "tablet"

        return "desktop"

"""
GeoIP lookup service for IP-to-location mapping.

Uses MaxMind GeoLite2 database for geographic information.
"""

import ipaddress
import logging
from typing import Optional, TypedDict

logger = logging.getLogger(__name__)


class LocationInfo(TypedDict):
    """Geographic location information."""
    city: Optional[str]
    country: str
    countryCode: str


class GeoIPService:
    """
    IP-to-location lookup service.
    Uses MaxMind GeoLite2 database or similar.
    """

    # Private IP ranges that should return None
    _PRIVATE_RANGES = [
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("127.0.0.0/8"),
        ipaddress.ip_network("::1/128"),
        ipaddress.ip_network("fc00::/7"),
        ipaddress.ip_network("fe80::/10"),
    ]

    def __init__(self, database_path: Optional[str] = None):
        """
        Initialize GeoIP service.

        Args:
            database_path: Path to GeoIP database file (MaxMind GeoLite2)
        """
        self._reader = None
        self._database_path = database_path

        if database_path:
            try:
                import geoip2.database
                self._reader = geoip2.database.Reader(database_path)
                logger.info(f"GeoIP database loaded from {database_path}")
            except ImportError:
                logger.warning(
                    "geoip2 package not installed. GeoIP lookups will return default values. "
                    "Install with: pip install geoip2"
                )
            except Exception as e:
                logger.warning(f"Failed to load GeoIP database: {e}")

    def lookup(self, ip_address: str) -> Optional[LocationInfo]:
        """
        Get location for an IP address.

        Args:
            ip_address: IPv4 or IPv6 address

        Returns:
            dict with fields:
                - city: str | None
                - country: str
                - countryCode: str (ISO 3166-1 alpha-2)
            Returns None for private/localhost IPs
        """
        if not ip_address:
            return None

        if self._is_private_ip(ip_address):
            return None

        if not self._reader:
            return LocationInfo(
                city=None,
                country="Unknown",
                countryCode="XX"
            )

        try:
            response = self._reader.city(ip_address)
            return LocationInfo(
                city=response.city.name,
                country=response.country.name or "Unknown",
                countryCode=response.country.iso_code or "XX"
            )
        except Exception as e:
            logger.debug(f"GeoIP lookup failed for {ip_address}: {e}")
            return LocationInfo(
                city=None,
                country="Unknown",
                countryCode="XX"
            )

    def _is_private_ip(self, ip_address: str) -> bool:
        """Check if an IP address is private/localhost."""
        try:
            ip = ipaddress.ip_address(ip_address)
            for network in self._PRIVATE_RANGES:
                if ip in network:
                    return True
            return False
        except ValueError:
            return False

    def close(self) -> None:
        """Close the GeoIP database reader."""
        if self._reader:
            self._reader.close()
            self._reader = None

    def __del__(self):
        """Cleanup on deletion."""
        self.close()

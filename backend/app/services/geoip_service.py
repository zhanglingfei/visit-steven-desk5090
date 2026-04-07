"""
GeoIP service for country-based access control.
Uses MaxMind GeoLite2 database (local) with fallback to known IPs.
"""
import logging
import sqlite3
import tarfile
import time
from pathlib import Path
from typing import Optional

import requests

from config import settings

logger = logging.getLogger(__name__)

# Country codes to allow (ISO 3166-1 alpha-2) - loaded from config
ALLOWED_COUNTRIES = set()

# Fallback IPs that are always allowed (bypass geo check) - loaded from config
FALLBACK_IPS = {"127.0.0.1", "::1"}  # Always allow localhost

# GeoLite2 database URLs and paths
GEOLITE2_DB_URL = "https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-Country&license_key={license_key}&suffix=tar.gz"
GEOLITE2_DB_PATH = Path(__file__).parent.parent.parent / "data" / "GeoLite2-Country.mmdb"
GEOLITE2_METADATA_PATH = Path(__file__).parent.parent.parent / "data" / ".geolite2_metadata"

# Update check interval (7 days)
UPDATE_INTERVAL_DAYS = 7

# MaxMind license key (from environment or settings)
# User should set MAXMIND_LICENSE_KEY in .env


def _load_config():
    """Load allowed countries and fallback IPs from config."""
    global ALLOWED_COUNTRIES, FALLBACK_IPS

    # Parse allowed countries from config
    if settings.geoip_allowed_countries:
        ALLOWED_COUNTRIES = {
            cc.strip().upper()
            for cc in settings.geoip_allowed_countries.split(",")
            if cc.strip()
        }

    # Parse additional fallback IPs from config
    if settings.geoip_fallback_ips:
        additional_ips = {
            ip.strip()
            for ip in settings.geoip_fallback_ips.split(",")
            if ip.strip()
        }
        FALLBACK_IPS.update(additional_ips)


class GeoIPService:
    """Service for IP geolocation and country-based access control."""

    def __init__(self):
        self._reader = None
        self._initialized = False
        self._init_error = None
        self._ensure_data_dir()
        _load_config()  # Load config before checking
        self._init_reader()

    def _ensure_data_dir(self):
        """Ensure data directory exists."""
        data_dir = GEOLITE2_DB_PATH.parent
        data_dir.mkdir(parents=True, exist_ok=True)

    def _init_reader(self):
        """Initialize the GeoIP reader."""
        try:
            # Try to import geoip2
            import geoip2.database
            import geoip2.errors

            if GEOLITE2_DB_PATH.exists():
                self._reader = geoip2.database.Reader(str(GEOLITE2_DB_PATH))
                self._initialized = True
                logger.info(f"GeoIP database loaded: {GEOLITE2_DB_PATH}")
            else:
                self._init_error = "GeoLite2 database not found"
                logger.warning("GeoLite2 database not found. Run download_geolite2() to fetch it.")
        except ImportError:
            self._init_error = "geoip2 library not installed"
            logger.warning("geoip2 library not installed. GeoIP checks disabled.")
        except Exception as e:
            self._init_error = str(e)
            logger.error(f"Failed to initialize GeoIP reader: {e}")

    def get_country_code(self, ip_address: str) -> Optional[str]:
        """
        Get ISO country code for an IP address.
        Returns None if lookup fails or IP is private/invalid.
        """
        if not self._initialized or not self._reader:
            return None

        # Skip private/reserved IPs
        if self._is_private_ip(ip_address):
            return None

        try:
            import geoip2.errors
            response = self._reader.country(ip_address)
            return response.country.iso_code
        except geoip2.errors.AddressNotFoundError:
            logger.debug(f"IP not found in GeoIP database: {ip_address}")
            return None
        except Exception as e:
            logger.warning(f"GeoIP lookup failed for {ip_address}: {e}")
            return None

    def _is_private_ip(self, ip_address: str) -> bool:
        """Check if IP is private/reserved."""
        import ipaddress
        try:
            ip = ipaddress.ip_address(ip_address)
            return ip.is_private or ip.is_loopback or ip.is_reserved
        except ValueError:
            return True

    def is_ip_allowed(self, ip_address: str) -> tuple[bool, str]:
        """
        Check if IP is allowed based on country.
        Returns: (allowed: bool, reason: str)
        """
        # Reload config in case it changed
        _load_config()

        # Always allow fallback IPs (bypass geo check)
        if ip_address in FALLBACK_IPS:
            return True, "fallback_ip"

        # If GeoIP is disabled, allow all (fail-open for disabled state)
        if not settings.geoip_enabled:
            return True, "geoip_disabled"

        # If GeoIP is not available, fail-closed (deny) unless it's a fallback IP
        if not self._initialized:
            logger.warning(f"GeoIP unavailable, blocking non-fallback IP: {ip_address}")
            return False, f"geoip_unavailable: {self._init_error}"

        # Get country code
        country_code = self.get_country_code(ip_address)

        if country_code is None:
            # Could not determine country - fail-closed for security
            logger.warning(f"Could not determine country for IP: {ip_address}, blocking")
            return False, "country_unknown"

        # Check if country is allowed
        if country_code in ALLOWED_COUNTRIES:
            return True, f"country_allowed:{country_code}"

        # Country not in allowlist
        logger.warning(f"IP blocked - country not allowed: {ip_address} ({country_code})")
        return False, f"country_blocked:{country_code}"

    def close(self):
        """Close the GeoIP reader."""
        if self._reader:
            self._reader.close()
            self._reader = None
            self._initialized = False


def download_geolite2_database(license_key: Optional[str] = None) -> bool:
    """
    Download and extract GeoLite2 Country database.
    Returns True if successful.
    """
    if not license_key:
        license_key = getattr(settings, 'maxmind_license_key', None) or \
                      getattr(settings, 'MAXMIND_LICENSE_KEY', None)

    if not license_key:
        logger.error("MaxMind license key not configured. Set MAXMIND_LICENSE_KEY in .env")
        return False

    try:
        import tarfile
        import io

        url = GEOLITE2_DB_URL.format(license_key=license_key)
        logger.info("Downloading GeoLite2 Country database...")

        response = requests.get(url, timeout=60, stream=True)
        response.raise_for_status()

        # Extract tar.gz
        with tarfile.open(fileobj=io.BytesIO(response.content), mode="r:gz") as tar:
            # Find the .mmdb file in the archive
            for member in tar.getmembers():
                if member.name.endswith(".mmdb"):
                    # Extract to data directory
                    member.name = Path(member.name).name  # Remove subdirectories
                    tar.extract(member, path=GEOLITE2_DB_PATH.parent)

                    # Rename to standard name
                    extracted_path = GEOLITE2_DB_PATH.parent / member.name
                    if extracted_path.exists():
                        extracted_path.rename(GEOLITE2_DB_PATH)

                    logger.info(f"GeoLite2 database downloaded: {GEOLITE2_DB_PATH}")

                    # Write metadata
                    GEOLITE2_METADATA_PATH.write_text(str(int(time.time())))
                    return True

        logger.error("Could not find .mmdb file in downloaded archive")
        return False

    except Exception as e:
        logger.error(f"Failed to download GeoLite2 database: {e}")
        return False


def should_update_database() -> bool:
    """Check if database should be updated (older than UPDATE_INTERVAL_DAYS)."""
    if not GEOLITE2_DB_PATH.exists():
        return True

    if not GEOLITE2_METADATA_PATH.exists():
        return True

    try:
        last_update = int(GEOLITE2_METADATA_PATH.read_text().strip())
        days_since_update = (time.time() - last_update) / (24 * 3600)
        return days_since_update >= UPDATE_INTERVAL_DAYS
    except (ValueError, OSError):
        return True


# Global instance
_geoip_service: Optional[GeoIPService] = None


def get_geoip_service() -> GeoIPService:
    """Get or create the GeoIP service singleton."""
    global _geoip_service
    if _geoip_service is None:
        _geoip_service = GeoIPService()
    return _geoip_service


def check_ip_country(ip_address: str) -> tuple[bool, str]:
    """
    Convenience function to check if IP is allowed.
    Returns: (allowed: bool, reason: str)
    """
    service = get_geoip_service()
    return service.is_ip_allowed(ip_address)


def init_geoip_on_startup():
    """Initialize GeoIP service and check for updates on startup."""
    service = get_geoip_service()

    if not service._initialized:
        logger.warning(f"GeoIP service not initialized: {service._init_error}")

        # Try to download if we have a license key
        license_key = getattr(settings, 'maxmind_license_key', None) or \
                      getattr(settings, 'MAXMIND_LICENSE_KEY', None)

        if license_key and should_update_database():
            if download_geolite2_database(license_key):
                # Re-initialize
                service._init_reader()

    return service._initialized

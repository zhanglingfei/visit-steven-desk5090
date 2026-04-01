"""Device registration and management service."""

import hashlib
import uuid
from datetime import datetime, timezone

from app.services.auth_service import load_users, save_users


def generate_device_fingerprint(user_agent: str, ip: str, headers: dict) -> str:
    """Generate a unique device fingerprint based on hardware/software characteristics.

    Note: IP address is NOT included in the fingerprint - the same physical device
    should be recognized regardless of network location. Browser version is also
    excluded as it changes with updates.
    """
    # Extract stable components from user agent (OS, platform, browser family)
    # Remove version numbers that change with updates
    import re

    # Parse user agent to extract stable parts only
    # Example: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    # We keep: OS info, architecture, browser family (not version)

    ua = user_agent or ""

    # Extract OS and platform info (stable)
    os_match = re.search(r'\(([^)]+)\)', ua)
    os_info = os_match.group(1) if os_match else ""

    # Extract browser family (without version)
    browser_families = []
    if 'Chrome' in ua or 'Chromium' in ua:
        browser_families.append('Chrome')
    if 'Firefox' in ua:
        browser_families.append('Firefox')
    if 'Safari' in ua and 'Chrome' not in ua:
        browser_families.append('Safari')
    if 'Edge' in ua:
        browser_families.append('Edge')

    browser_family = browser_families[0] if browser_families else "Unknown"

    # Combine stable factors only - NO IP, NO browser version
    # Normalize platform header - remove quotes as different browsers may send
    # sec-ch-ua-platform as "Windows" or Windows
    platform = headers.get("sec-ch-ua-platform", "").strip().strip('"')
    factors = [
        os_info,  # e.g., "Windows NT 10.0; Win64; x64"
        browser_family,  # e.g., "Chrome" (not "Chrome/120.0.0.0")
        platform,  # OS platform (e.g., "Windows" without quotes)
    ]
    fingerprint_data = "|".join(factors)
    return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:32]


def get_user_devices(username: str) -> list[dict]:
    """Get all active registered devices for a user."""
    users = load_users()
    user = users.get(username)
    if not user:
        return []
    devices = user.get("registered_devices", [])
    return [d for d in devices if d.get("is_active", True)]


def register_device(
    username: str,
    device_name: str,
    user_agent: str,
    ip: str,
    headers: dict
) -> tuple[bool, str, dict]:
    """
    Register a new device for user.
    Returns: (success, message, device_info)
    """
    users = load_users()
    user = users.get(username)
    if not user:
        return False, "User not found", {}

    # Initialize devices list if not exists
    if "registered_devices" not in user:
        user["registered_devices"] = []

    devices = user["registered_devices"]

    # Check max devices limit (default 5)
    max_devices = user.get("max_registered_devices", 5)
    active_devices = [d for d in devices if d.get("is_active", True)]

    if len(active_devices) >= max_devices:
        return False, f"Maximum {max_devices} devices allowed. Please unregister an old device first.", {}

    # Generate device fingerprint
    fingerprint = generate_device_fingerprint(user_agent, ip, headers)

    # Check if device already registered
    for device in devices:
        if device["fingerprint"] == fingerprint and device.get("is_active", True):
            # Update last used
            device["last_used"] = datetime.now(timezone.utc).isoformat()
            # Note: We intentionally do NOT update IP - device identity is based on
            # hardware/software characteristics, not network location
            save_users(users)
            return False, "Device already registered", device

    # Create new device
    device_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    new_device = {
        "device_id": device_id,
        "device_name": device_name,
        "user_agent": user_agent,
        "ip_address": ip,
        "fingerprint": fingerprint,
        "registered_at": now,
        "last_used": now,
        "is_active": True,
    }

    devices.append(new_device)
    save_users(users)

    return True, "Device registered successfully", new_device


def unregister_device(username: str, device_id: str) -> tuple[bool, str]:
    """Unregister a device by ID."""
    users = load_users()
    user = users.get(username)
    if not user:
        return False, "User not found"

    devices = user.get("registered_devices", [])
    for device in devices:
        if device["device_id"] == device_id:
            device["is_active"] = False
            device["unregistered_at"] = datetime.now(timezone.utc).isoformat()
            save_users(users)
            return True, "Device unregistered successfully"

    return False, "Device not found"


def is_registered_device(username: str, user_agent: str, ip: str, headers: dict) -> tuple[bool, dict]:
    """
    Check if current device is registered.
    Returns: (is_registered, device_info)
    """
    users = load_users()
    user = users.get(username)
    if not user:
        return False, {}

    # Check if device restriction is enabled
    if not user.get("require_registered_device", False):
        return True, {}  # No restriction

    fingerprint = generate_device_fingerprint(user_agent, ip, headers)
    devices = user.get("registered_devices", [])

    for device in devices:
        if device["fingerprint"] == fingerprint and device.get("is_active", True):
            # Update last used
            device["last_used"] = datetime.now(timezone.utc).isoformat()
            # Note: We intentionally do NOT update IP - device identity is based on
            # hardware/software characteristics, not network location
            save_users(users)
            return True, device

    return False, {}


def toggle_device_requirement(username: str, require: bool) -> bool:
    """Enable or disable device registration requirement."""
    users = load_users()
    user = users.get(username)
    if not user:
        return False

    user["require_registered_device"] = require
    save_users(users)
    return True


def update_device_name(username: str, device_id: str, new_name: str) -> tuple[bool, str]:
    """Update device friendly name."""
    users = load_users()
    user = users.get(username)
    if not user:
        return False, "User not found"

    devices = user.get("registered_devices", [])
    for device in devices:
        if device["device_id"] == device_id:
            device["device_name"] = new_name
            save_users(users)
            return True, "Device name updated"

    return False, "Device not found"

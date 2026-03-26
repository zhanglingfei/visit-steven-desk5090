"""Device registration and management service."""

import hashlib
import uuid
from datetime import datetime, timezone

from app.services.auth_service import load_users, save_users


def generate_device_fingerprint(user_agent: str, ip: str, headers: dict) -> str:
    """Generate a unique device fingerprint based on browser characteristics."""
    # Combine multiple factors for fingerprinting
    factors = [
        user_agent,
        ip,
        headers.get("accept-language", ""),
        headers.get("accept-encoding", ""),
        headers.get("sec-ch-ua", ""),  # Browser brand/version
        headers.get("sec-ch-ua-platform", ""),  # OS platform
    ]
    fingerprint_data = "|".join(factors)
    return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:32]


def get_user_devices(username: str) -> list[dict]:
    """Get all registered devices for a user."""
    users = load_users()
    user = users.get(username)
    if not user:
        return []
    return user.get("registered_devices", [])


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
            device["ip_address"] = ip  # Update IP
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

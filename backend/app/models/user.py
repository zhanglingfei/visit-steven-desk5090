from typing import Optional
from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str
    totp_code: Optional[str] = None  # 6-digit TOTP code for 2FA


class LoginResponse(BaseModel):
    token: str
    username: str
    requires_2fa: bool = False  # True if 2FA is required but not provided


class UserInfo(BaseModel):
    username: str
    role: str
    has_2fa: bool = False  # Whether 2FA is enabled
    password_change_required: bool = False
    password_change_reason: Optional[str] = None


class Setup2FARequest(BaseModel):
    username: str
    password: str


class Setup2FAResponse(BaseModel):
    secret: str
    qr_code: str  # Base64 encoded QR code
    backup_codes: list[str]  # Backup codes for recovery


class Verify2FARequest(BaseModel):
    username: str
    password: str
    totp_code: str


class Disable2FARequest(BaseModel):
    username: str
    password: str
    totp_code: str


class ChangePasswordRequest(BaseModel):
    username: str
    current_password: str
    new_password: str


class DeviceInfo(BaseModel):
    """Registered device information"""
    device_id: str
    device_name: str
    user_agent: str
    ip_address: str
    fingerprint: str  # Browser fingerprint hash
    registered_at: str
    last_used: str
    is_active: bool = True


class DeviceListResponse(BaseModel):
    devices: list[DeviceInfo]
    max_devices: int
    require_registered_device: bool


class RegisterDeviceRequest(BaseModel):
    device_name: str  # User-friendly name like "My Laptop", "iPhone 15"


class UnregisterDeviceRequest(BaseModel):
    device_id: str


class ToggleDeviceRequirementRequest(BaseModel):
    require_registered_device: bool  # Enable/disable device restriction

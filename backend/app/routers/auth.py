from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.middleware.auth import get_current_user
from app.models.user import (
    LoginRequest, LoginResponse, UserInfo,
    Setup2FARequest, Setup2FAResponse, Verify2FARequest, Disable2FARequest,
    ChangePasswordRequest,
    DeviceListResponse, RegisterDeviceRequest, UnregisterDeviceRequest,
    ToggleDeviceRequirementRequest
)
from app.services.auth_service import (
    authenticate_user,
    authenticate_with_2fa,
    change_password,
    check_password_change_required,
    check_rate_limit,
    check_session_anomaly,
    create_token,
    create_token_pair,
    get_user,
    record_attempt,
    setup_2fa,
    enable_2fa,
    disable_2fa,
    verify_totp,
    load_users,
    save_users,
    validate_password_strength,
)
from app.services.device_service import is_registered_device, register_device
from app.services.geoip_service import check_ip_country

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, request: Request):
    ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    # Check rate limit first
    error = check_rate_limit(ip, body.username)
    if error:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=error)

    # Check geo-restriction (country-based access control)
    geo_allowed, geo_reason = check_ip_country(ip)
    if not geo_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: {geo_reason}",
        )

    # Authenticate with optional 2FA
    user, requires_2fa = authenticate_with_2fa(body.username, body.password, body.totp_code)

    if requires_2fa:
        # 2FA is required but not provided
        record_attempt(ip, body.username, False)
        return LoginResponse(token="", username=body.username, requires_2fa=True)

    if not user:
        record_attempt(ip, body.username, False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username, password, or 2FA code",
        )

    # Check device registration (only if enabled)
    user_data = load_users().get(body.username, {})
    require_device = user_data.get("require_registered_device", False)

    if require_device:
        # Device restriction is enabled - check registration
        is_device_registered, device_info = is_registered_device(
            body.username, user_agent, ip, dict(request.headers)
        )

        if not is_device_registered:
            devices = user_data.get("registered_devices", [])
            active_devices = [d for d in devices if d.get("is_active", True)]

            if active_devices:
                # User has registered devices but this one is not registered
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Unregistered device. Please register this device from a trusted device first.",
                )
            # else: No devices registered yet, allow login and auto-register below

    # Auto-register first device (or when device restriction is off)
    devices = user_data.get("registered_devices", [])
    active_devices = [d for d in devices if d.get("is_active", True)]

    if not active_devices:
        # First login - auto-register device
        success, msg, device_info = register_device(
            body.username,
            "First Device",
            user_agent,
            ip,
            dict(request.headers)
        )
        if success:
            print(f"[AUTH] Auto-registered first device for {body.username}")

    # Check for session anomalies (new IP/device)
    allowed, anomaly_info = check_session_anomaly(body.username, ip, user_agent)
    if anomaly_info:
        # Log but don't block - expected for multi-country access
        print(f"[AUTH] Session anomaly for {body.username}: {anomaly_info}")

    record_attempt(ip, body.username, True)
    tokens = create_token_pair(user["username"])
    return LoginResponse(
        token=tokens["access_token"],
        username=user["username"],
        requires_2fa=False
    )


@router.get("/me", response_model=UserInfo)
async def me(user: dict = Depends(get_current_user)):
    # Get full user data (get_current_user only returns username and role)
    full_user = get_user(user["username"])
    if not full_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    # Check if password change is required
    change_required, reason = check_password_change_required(user["username"])

    return UserInfo(
        username=user["username"],
        role=user.get("role", "user"),
        has_2fa=full_user.get("2fa_enabled", False),
        password_change_required=change_required,
        password_change_reason=reason if change_required else None
    )


@router.post("/2fa/setup", response_model=Setup2FAResponse)
async def setup_2fa_endpoint(body: Setup2FARequest, request: Request):
    """Start 2FA setup - returns QR code and backup codes."""
    ip = request.client.host if request.client else "unknown"

    # Check geo-restriction
    geo_allowed, geo_reason = check_ip_country(ip)
    if not geo_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: {geo_reason}",
        )

    error = check_rate_limit(ip, body.username)
    if error:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=error)

    result = setup_2fa(body.username, body.password)
    if not result:
        record_attempt(ip, body.username, False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    secret, qr_code, backup_codes = result

    # Store temporary secret (not enabled until verified)
    users = load_users()
    if body.username in users:
        users[body.username]["temp_totp_secret"] = secret
        users[body.username]["temp_backup_codes"] = backup_codes
        save_users(users)

    return Setup2FAResponse(
        secret=secret,
        qr_code=qr_code,
        backup_codes=backup_codes
    )


@router.post("/2fa/verify")
async def verify_2fa_endpoint(body: Verify2FARequest, request: Request):
    """Verify 2FA setup with first TOTP code."""
    ip = request.client.host if request.client else "unknown"

    # Get user and temp secret
    user = authenticate_user(body.username, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    temp_secret = user.get("temp_totp_secret")
    if not temp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA setup not initiated",
        )

    # Verify TOTP code
    if not verify_totp(temp_secret, body.totp_code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid 2FA code",
        )

    # Enable 2FA permanently
    backup_codes = user.get("temp_backup_codes", [])
    from app.services.auth_service import hash_backup_codes
    enable_2fa(body.username, temp_secret, backup_codes)

    # Clear temp data
    users = load_users()
    users[body.username].pop("temp_totp_secret", None)
    users[body.username].pop("temp_backup_codes", None)
    save_users(users)

    return {"message": "2FA enabled successfully", "backup_codes": backup_codes}


@router.post("/2fa/disable")
async def disable_2fa_endpoint(body: Disable2FARequest, request: Request):
    """Disable 2FA for user."""
    ip = request.client.host if request.client else "unknown"

    # Authenticate user
    user = authenticate_user(body.username, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # Verify 2FA is enabled
    if not user.get("2fa_enabled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled",
        )

    # Verify TOTP code
    if not verify_totp(user.get("totp_secret"), body.totp_code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid 2FA code",
        )

    # Disable 2FA
    disable_2fa(body.username)

    return {"message": "2FA disabled successfully"}


@router.post("/change-password")
async def change_password_endpoint(body: ChangePasswordRequest, request: Request):
    """Change user password with complexity validation."""
    ip = request.client.host if request.client else "unknown"

    # Check geo-restriction
    geo_allowed, geo_reason = check_ip_country(ip)
    if not geo_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: {geo_reason}",
        )

    # Check rate limit
    error = check_rate_limit(ip, body.username)
    if error:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=error)

    # Validate new password strength
    is_valid, message = validate_password_strength(body.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    # Change password
    success, message = change_password(body.username, body.current_password, body.new_password)
    if not success:
        record_attempt(ip, body.username, False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=message
        )

    record_attempt(ip, body.username, True)
    return {"message": message}


# ==================== Device Management Endpoints ====================

from app.services.device_service import (
    get_user_devices,
    register_device,
    unregister_device,
    is_registered_device,
    toggle_device_requirement,
    update_device_name,
)


@router.get("/devices", response_model=DeviceListResponse)
async def list_devices(user: dict = Depends(get_current_user)):
    """List all registered devices for current user."""
    devices = get_user_devices(user["username"])
    # Get full user data for require_registered_device setting
    full_user = get_user(user["username"])
    return DeviceListResponse(
        devices=devices,
        max_devices=5,
        require_registered_device=full_user.get("require_registered_device", False) if full_user else False
    )


@router.post("/devices/register")
async def register_device_endpoint(
    body: RegisterDeviceRequest,
    request: Request,
    user: dict = Depends(get_current_user)
):
    """Register current device."""
    ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    success, message, device_info = register_device(
        user["username"],
        body.device_name,
        user_agent,
        ip,
        dict(request.headers)
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    return {"message": message, "device": device_info}


@router.post("/devices/unregister")
async def unregister_device_endpoint(
    body: UnregisterDeviceRequest,
    user: dict = Depends(get_current_user)
):
    """Unregister a device."""
    success, message = unregister_device(user["username"], body.device_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    return {"message": message}


@router.post("/devices/requirement")
async def toggle_device_requirement_endpoint(
    body: ToggleDeviceRequirementRequest,
    user: dict = Depends(get_current_user)
):
    """Enable or disable device registration requirement."""
    success = toggle_device_requirement(user["username"], body.require_registered_device)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update setting"
        )

    status_text = "enabled" if body.require_registered_device else "disabled"
    return {
        "message": f"Device registration requirement {status_text}",
        "require_registered_device": body.require_registered_device
    }


@router.post("/devices/{device_id}/rename")
async def rename_device_endpoint(
    device_id: str,
    body: dict,
    user: dict = Depends(get_current_user)
):
    """Rename a registered device."""
    new_name = body.get("name", "")
    if not new_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device name is required"
        )

    success, message = update_device_name(user["username"], device_id, new_name)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    return {"message": message}

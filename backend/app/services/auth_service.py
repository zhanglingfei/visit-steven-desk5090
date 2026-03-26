import json
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Tuple

import bcrypt
import pyotp
import qrcode
from jose import JWTError, jwt
from io import BytesIO
import base64

from config import settings


# Password policy requirements
MIN_PASSWORD_LENGTH = 12
REQUIRE_UPPERCASE = True
REQUIRE_LOWERCASE = True
REQUIRE_DIGITS = True
REQUIRE_SPECIAL = True
SPECIAL_CHARS = r"!@#$%^&*()_+-=[]{}|;:,.<>?"


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """Validate password meets complexity requirements."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters"

    if REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"

    if REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"

    if REQUIRE_DIGITS and not re.search(r'\d', password):
        return False, "Password must contain at least one digit"

    if REQUIRE_SPECIAL and not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password):
        return False, "Password must contain at least one special character"

    # Check for common weak patterns
    common_patterns = ['password', '123456', 'qwerty', 'admin', 'letmein']
    password_lower = password.lower()
    for pattern in common_patterns:
        if pattern in password_lower:
            return False, f"Password contains common weak pattern: '{pattern}'"

    return True, "Password meets complexity requirements"


def is_password_complex(password: str) -> bool:
    """Quick check if password is complex (for login validation)."""
    valid, _ = validate_password_strength(password)
    return valid

# Rate limiting state - adjusted for personal use
_login_attempts: dict[str, list[float]] = {}  # ip -> timestamps
_username_failures: dict[str, int] = {}  # username -> consecutive failures
_RATE_LIMIT_WINDOW = 60  # 1 minute window
_RATE_LIMIT_MAX = 30  # 30 requests per minute (was 10)
_LOCKOUT_THRESHOLD = 10  # 10 failed attempts before lockout (was 5)
_LOCKOUT_DURATION = 60  # 1 minute lockout (was 300)

# Session fingerprinting for anomaly detection
_session_fingerprints: dict[str, dict] = {}  # username -> {ip, user_agent, timestamp}

def check_session_anomaly(username: str, ip: str, user_agent: str) -> tuple[bool, str]:
    """Check for suspicious session changes (new IP, new device)."""
    fingerprint = _session_fingerprints.get(username)
    if not fingerprint:
        # First login, store fingerprint
        _session_fingerprints[username] = {
            "ip": ip,
            "user_agent": user_agent,
            "timestamp": time.time()
        }
        return True, ""

    # Check for changes
    changes = []
    if fingerprint["ip"] != ip:
        changes.append(f"IP changed from {fingerprint['ip']} to {ip}")
    if fingerprint["user_agent"] != user_agent:
        changes.append("Device/browser changed")

    if changes:
        # Allow but log warning - for multi-country this is expected
        # In production, you might email the user or require re-auth
        return True, "; ".join(changes)

    return True, ""


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_token(username: str, token_type: str = "access") -> str:
    """Create JWT token with short expiry for access, longer for refresh."""
    if token_type == "refresh":
        expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_days)
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours)

    return jwt.encode(
        {"sub": username, "exp": expire, "type": token_type},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_token_pair(username: str) -> dict:
    """Create both access and refresh tokens."""
    return {
        "access_token": create_token(username, "access"),
        "refresh_token": create_token(username, "refresh"),
        "token_type": "bearer"
    }


def decode_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        return payload.get("sub")
    except JWTError:
        return None


def load_users() -> dict:
    path = settings.users_file_path
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def save_users(users: dict) -> None:
    with open(settings.users_file_path, "w") as f:
        json.dump(users, f, indent=2)


def get_user(username: str) -> Optional[dict]:
    users = load_users()
    return users.get(username)


def authenticate_user(username: str, password: str) -> Optional[dict]:
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


def check_rate_limit(ip: str, username: str) -> Optional[str]:
    now = time.time()

    # Check username lockout
    if _username_failures.get(username, 0) >= _LOCKOUT_THRESHOLD:
        return "Account temporarily locked. Try again later."

    # Check IP rate limit
    attempts = _login_attempts.get(ip, [])
    attempts = [t for t in attempts if now - t < _RATE_LIMIT_WINDOW]
    _login_attempts[ip] = attempts

    if len(attempts) >= _RATE_LIMIT_MAX:
        return "Too many login attempts. Try again later."

    return None


def record_attempt(ip: str, username: str, success: bool) -> None:
    now = time.time()
    _login_attempts.setdefault(ip, []).append(now)

    if success:
        _username_failures.pop(username, None)
    else:
        _username_failures[username] = _username_failures.get(username, 0) + 1


# ==================== 2FA Functions ====================

def generate_2fa_secret() -> str:
    """Generate a new TOTP secret."""
    return pyotp.random_base32()


def get_totp_uri(username: str, secret: str) -> str:
    """Generate TOTP URI for QR code."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(
        name=username,
        issuer_name="Visit Steven Desk5090"
    )


def generate_qr_code(uri: str) -> str:
    """Generate base64 encoded QR code from URI."""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"


def verify_totp(secret: str, code: str) -> bool:
    """Verify a TOTP code against a secret."""
    if not secret or not code:
        return False
    totp = pyotp.TOTP(secret)
    # Allow 1 time step drift (30 seconds before/after)
    return totp.verify(code, valid_window=1)


def generate_backup_codes(count: int = 8) -> list[str]:
    """Generate backup codes for account recovery."""
    return [secrets.token_hex(4) for _ in range(count)]


def hash_backup_codes(codes: list[str]) -> list[str]:
    """Hash backup codes for storage."""
    return [bcrypt.hashpw(code.encode(), bcrypt.gensalt()).decode() for code in codes]


def verify_backup_code(stored_hashes: list[str], code: str) -> bool:
    """Verify a backup code against stored hashes."""
    for stored_hash in stored_hashes:
        if bcrypt.checkpw(code.encode(), stored_hash.encode()):
            return True
    return False


def setup_2fa(username: str, password: str) -> Optional[Tuple[str, str, list[str]]]:
    """
    Setup 2FA for a user.
    Returns: (secret, qr_code_base64, backup_codes) or None if auth fails
    """
    user = authenticate_user(username, password)
    if not user:
        return None

    # Generate new secret
    secret = generate_2fa_secret()

    # Generate QR code
    uri = get_totp_uri(username, secret)
    qr_code = generate_qr_code(uri)

    # Generate backup codes
    backup_codes = generate_backup_codes()

    return secret, qr_code, backup_codes


def enable_2fa(username: str, secret: str, backup_codes: list[str]) -> bool:
    """Enable 2FA for a user after verification."""
    users = load_users()
    if username not in users:
        return False

    users[username]["totp_secret"] = secret
    users[username]["backup_codes"] = hash_backup_codes(backup_codes)
    users[username]["2fa_enabled"] = True
    save_users(users)
    return True


def disable_2fa(username: str) -> bool:
    """Disable 2FA for a user."""
    users = load_users()
    if username not in users:
        return False

    users[username].pop("totp_secret", None)
    users[username].pop("backup_codes", None)
    users[username]["2fa_enabled"] = False
    save_users(users)
    return True


def verify_2fa_setup(username: str, password: str, totp_code: str) -> bool:
    """Verify 2FA setup by checking the first TOTP code."""
    user = authenticate_user(username, password)
    if not user:
        return False

    # Check if user has temporary secret (during setup)
    temp_secret = user.get("temp_totp_secret")
    if not temp_secret:
        return False

    if verify_totp(temp_secret, totp_code):
        # Move temp secret to permanent
        enable_2fa(username, temp_secret, user.get("temp_backup_codes", []))
        users = load_users()
        users[username].pop("temp_totp_secret", None)
        users[username].pop("temp_backup_codes", None)
        save_users(users)
        return True
    return False


def authenticate_with_2fa(username: str, password: str, totp_code: Optional[str] = None) -> Tuple[Optional[dict], bool]:
    """
    Authenticate user with optional 2FA.
    Returns: (user_dict, requires_2fa)
    - If 2FA not enabled: returns (user, False) on success
    - If 2FA enabled but no code: returns (None, True) to request 2FA
    - If 2FA enabled with code: returns (user, False) on success
    """
    user = authenticate_user(username, password)
    if not user:
        return None, False

    # Check if 2FA is enabled
    if not user.get("2fa_enabled"):
        return user, False

    # 2FA is enabled, check if code provided
    if not totp_code:
        return None, True  # Requires 2FA

    # Verify TOTP code
    secret = user.get("totp_secret")
    if verify_totp(secret, totp_code):
        return user, False

    # Check backup codes
    backup_hashes = user.get("backup_codes", [])
    if verify_backup_code(backup_hashes, totp_code):
        # Remove used backup code
        for i, stored_hash in enumerate(backup_hashes):
            if bcrypt.checkpw(totp_code.encode(), stored_hash.encode()):
                backup_hashes.pop(i)
                users = load_users()
                users[username]["backup_codes"] = backup_hashes
                save_users(users)
                break
        return user, False

    return None, False


def change_password(username: str, current_password: str, new_password: str) -> Tuple[bool, str]:
    """Change user password with complexity validation."""
    # Verify current password
    user = authenticate_user(username, current_password)
    if not user:
        return False, "Current password is incorrect"

    # Validate new password complexity
    is_valid, message = validate_password_strength(new_password)
    if not is_valid:
        return False, message

    # Check new password is different from old
    if verify_password(new_password, user["password_hash"]):
        return False, "New password must be different from current password"

    # Update password
    users = load_users()
    if username not in users:
        return False, "User not found"

    users[username]["password_hash"] = hash_password(new_password)
    users[username]["password_changed_at"] = datetime.now(timezone.utc).isoformat()
    users[username]["password_change_required"] = False
    save_users(users)

    return True, "Password changed successfully"


def check_password_change_required(username: str) -> Tuple[bool, str]:
    """Check if user must change password."""
    user = get_user(username)
    if not user:
        return False, ""

    # Check if password change is explicitly required
    if user.get("password_change_required", False):
        return True, "Password change required for security"

    # Check if password is weak (not meeting new complexity requirements)
    # We can't check the actual password, but we can flag if it was set before policy
    password_changed = user.get("password_changed_at")
    if not password_changed:
        return True, "Please update your password to meet new security requirements"

    return False, ""

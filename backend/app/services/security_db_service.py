"""
Persistent security database service for login attempts and rate limiting.
Uses SQLite to persist lockout state across restarts.
"""
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from config import settings


# Security settings
_LOCKOUT_THRESHOLD = 5  # 5 failed attempts before lockout
_LOCKOUT_DURATION = 300  # 5 minute lockout window (in seconds)
_RATE_LIMIT_WINDOW = 60  # 1 minute window for IP rate limiting
_RATE_LIMIT_MAX = 5  # 5 requests per minute per IP


def _get_db_path() -> Path:
    """Get the path to the security database."""
    return Path(__file__).parent.parent.parent / "security.db"


def init_security_db() -> None:
    """Initialize the security database with required tables."""
    db_path = _get_db_path()

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # Login attempts table - stores both IP and username attempts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS login_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT NOT NULL,
                username TEXT,
                success BOOLEAN NOT NULL DEFAULT 0,
                timestamp REAL NOT NULL,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes for efficient queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_attempts_ip ON login_attempts(ip_address, timestamp)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_attempts_username ON login_attempts(username, timestamp, success)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_attempts_timestamp ON login_attempts(timestamp)
        """)

        # Security events table for audit logging
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                ip_address TEXT,
                username TEXT,
                details TEXT,
                timestamp REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_type ON security_events(event_type, timestamp)
        """)

        conn.commit()


def record_login_attempt(
    ip_address: str,
    username: Optional[str],
    success: bool,
    user_agent: Optional[str] = None
) -> None:
    """Record a login attempt in the database."""
    db_path = _get_db_path()
    now = time.time()

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO login_attempts (ip_address, username, success, timestamp, user_agent)
            VALUES (?, ?, ?, ?, ?)
        """, (ip_address, username, success, now, user_agent))
        conn.commit()

    # Clean up old records periodically (1% chance to avoid overhead on every call)
    if hash(f"{now:.0f}") % 100 == 0:
        cleanup_old_records()


def check_username_lockout(username: str) -> Optional[str]:
    """
    Check if a username is locked out due to failed attempts.
    Returns error message if locked out, None otherwise.
    """
    if not username:
        return None

    db_path = _get_db_path()
    now = time.time()
    cutoff = now - _LOCKOUT_DURATION

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # Count failed attempts within the lockout window
        cursor.execute("""
            SELECT COUNT(*) as failed_count, MIN(timestamp) as first_failure
            FROM login_attempts
            WHERE username = ?
              AND success = 0
              AND timestamp > ?
        """, (username, cutoff))

        row = cursor.fetchone()
        if not row or row[0] == 0:
            return None

        failed_count, first_failure = row

        if failed_count >= _LOCKOUT_THRESHOLD:
            remaining = _LOCKOUT_DURATION - (now - first_failure)
            if remaining > 0:
                return f"Account temporarily locked. Try again in {int(remaining)} seconds."

    return None


def check_ip_rate_limit(ip_address: str) -> Optional[str]:
    """
    Check if an IP has exceeded rate limit.
    Returns error message if rate limited, None otherwise.
    """
    if not ip_address or ip_address == "unknown":
        return None

    db_path = _get_db_path()
    now = time.time()
    cutoff = now - _RATE_LIMIT_WINDOW

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # Count attempts from this IP within the rate limit window
        cursor.execute("""
            SELECT COUNT(*)
            FROM login_attempts
            WHERE ip_address = ?
              AND timestamp > ?
        """, (ip_address, cutoff))

        count = cursor.fetchone()[0]

        if count >= _RATE_LIMIT_MAX:
            return "Too many login attempts. Try again later."

    return None


def check_rate_limit(ip_address: str, username: str) -> Optional[str]:
    """
    Check both username lockout and IP rate limit.
    Returns error message if either check fails, None otherwise.
    """
    # Check username lockout first (more specific)
    error = check_username_lockout(username)
    if error:
        return error

    # Check IP rate limit
    error = check_ip_rate_limit(ip_address)
    if error:
        return error

    return None


def get_failed_attempts(username: str, window_seconds: int = _LOCKOUT_DURATION) -> int:
    """Get the number of recent failed attempts for a username."""
    db_path = _get_db_path()
    now = time.time()
    cutoff = now - window_seconds

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*)
            FROM login_attempts
            WHERE username = ?
              AND success = 0
              AND timestamp > ?
        """, (username, cutoff))

        return cursor.fetchone()[0]


def clear_failed_attempts(username: str) -> None:
    """Clear failed attempts for a username (e.g., after successful login)."""
    db_path = _get_db_path()

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM login_attempts
            WHERE username = ? AND success = 0
        """, (username,))
        conn.commit()


def cleanup_old_records(max_age_seconds: int = 86400) -> None:
    """
    Clean up old login attempt records to prevent database growth.
    Default: keep records for 24 hours.
    """
    db_path = _get_db_path()
    now = time.time()
    cutoff = now - max_age_seconds

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # Delete old login attempts
        cursor.execute("""
            DELETE FROM login_attempts
            WHERE timestamp < ?
        """, (cutoff,))

        # Delete old security events
        cursor.execute("""
            DELETE FROM security_events
            WHERE timestamp < ?
        """, (cutoff,))

        conn.commit()


def log_security_event(
    event_type: str,
    ip_address: Optional[str] = None,
    username: Optional[str] = None,
    details: Optional[str] = None
) -> None:
    """Log a security event for audit purposes."""
    db_path = _get_db_path()
    now = time.time()

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO security_events (event_type, ip_address, username, details, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (event_type, ip_address, username, details, now))
        conn.commit()


def get_recent_security_events(
    event_type: Optional[str] = None,
    username: Optional[str] = None,
    limit: int = 100
) -> list[dict]:
    """Get recent security events for analysis."""
    db_path = _get_db_path()

    query = "SELECT * FROM security_events WHERE 1=1"
    params = []

    if event_type:
        query += " AND event_type = ?"
        params.append(event_type)

    if username:
        query += " AND username = ?"
        params.append(username)

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)

        return [dict(row) for row in cursor.fetchall()]


# Initialize database on module import
init_security_db()

"""Terminal security service for auditing and restricting terminal access."""

import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Set

from config import settings

# Configure logging
logger = logging.getLogger("terminal")
logger.setLevel(logging.INFO)

# Create handler for terminal logs
terminal_log_path = Path(__file__).parent.parent.parent / "logs"
terminal_log_path.mkdir(exist_ok=True)
handler = logging.FileHandler(terminal_log_path / "terminal.log")
handler.setFormatter(logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s"
))
logger.addHandler(handler)


class TerminalSecurity:
    """Security controls for terminal sessions."""

    # Blocked commands (regex patterns) - expanded to prevent bypasses
    BLOCKED_PATTERNS = [
        # Destructive operations
        r"rm\s+.*-rf.*\/",
        r"rm\s+.*-fr.*\/",
        r">\s*/dev/",
        r"dd\s+if=.*of=/dev/",
        r"mkfs\.",
        r"fdisk\s+/dev/",
        r"parted\s+/dev/",
        # Remote code execution
        r"wget.*\|.*ba?sh",
        r"curl.*\|.*ba?sh",
        r"fetch.*\|.*ba?sh",
        # Backdoors / listeners
        r"nc\s+.*-l",
        r"netcat\s+.*-l",
        r"ncat\s+.*-l",
        r"socat\s+.*-l",
        r"python\s+.*http\.server",
        r"python3\s+.*http\.server",
        r"php\s+.*-S",
        # Tunneling / exfiltration (only block reverse tunnels, not normal SSH)
        r"ssh\s+.*-R\s+",
        r"ssh\s+.*-D\s+",
        r"ssh\s+.*-L\s+",
        # Shell escapes that could bypass filters
        r"sh\s+-c.*rm",
        r"bash\s+-c.*rm",
        r"eval.*rm",
        r"`.*rm",
        r"\$\(.*rm",
    ]

    # Sensitive files that shouldn't be accessed
    SENSITIVE_PATHS = [
        "/etc/shadow",
        "/etc/passwd",
        "/root/.ssh",
        "/home/*/.ssh",
        "/etc/ssh/sshd_config",
        "/var/log/auth.log",
    ]

    def __init__(self):
        self._session_logs: dict[str, list[dict]] = {}
        self._blocked_ips: Set[str] = set()
        self._ip_attempts: dict[str, list[float]] = {}
        self._load_ip_whitelist()

    def _load_ip_whitelist(self) -> None:
        """Load allowed IPs from settings."""
        self._allowed_ips: Set[str] = set()
        if settings.allowed_terminal_ips:
            self._allowed_ips = {
                ip.strip()
                for ip in settings.allowed_terminal_ips.split(",")
                if ip.strip()
            }

    def is_ip_allowed(self, ip: str) -> bool:
        """Check if IP is in whitelist (if whitelist is configured)."""
        if not self._allowed_ips:
            return True  # No whitelist = allow all
        return ip in self._allowed_ips

    def check_rate_limit(self, ip: str) -> bool:
        """Check if IP has exceeded terminal connection rate limit."""
        now = time.time()
        window = 300  # 5 minutes
        max_attempts = 10

        # Clean old attempts
        attempts = self._ip_attempts.get(ip, [])
        attempts = [t for t in attempts if now - t < window]
        self._ip_attempts[ip] = attempts

        if len(attempts) >= max_attempts:
            logger.warning(f"Rate limit exceeded for IP: {ip}")
            return False

        self._ip_attempts[ip].append(now)
        return True

    def log_session_start(self, session_id: str, username: str, ip: str) -> None:
        """Log terminal session start."""
        self._session_logs[session_id] = []
        logger.info(f"Session started: {session_id} - User: {username} - IP: {ip}")

    def log_command(self, session_id: str, username: str, command: bytes) -> None:
        """Log command input (if logging enabled)."""
        if not settings.terminal_command_logging:
            return

        try:
            cmd_str = command.decode("utf-8", errors="replace").strip()
            if cmd_str:
                log_entry = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "session_id": session_id,
                    "username": username,
                    "command": cmd_str,
                }
                self._session_logs.setdefault(session_id, []).append(log_entry)
                logger.info(f"Command: {session_id} - {cmd_str}")
        except Exception:
            pass

    def check_command(self, command: bytes) -> tuple[bool, Optional[str]]:
        """Check if command is allowed. Returns (allowed, reason)."""
        try:
            cmd_str = command.decode("utf-8", errors="replace").strip()

            # Check blocked patterns
            for pattern in self.BLOCKED_PATTERNS:
                if re.search(pattern, cmd_str, re.IGNORECASE):
                    logger.warning(f"Blocked command: {cmd_str}")
                    return False, f"Command pattern not allowed"

            # Check sensitive paths
            for path in self.SENSITIVE_PATHS:
                if path in cmd_str:
                    logger.warning(f"Sensitive path access attempted: {cmd_str}")
                    return False, f"Access to {path} not allowed"

            return True, None
        except Exception:
            return True, None  # Allow on error

    def log_session_end(self, session_id: str, username: str) -> None:
        """Log terminal session end and save session log."""
        logger.info(f"Session ended: {session_id} - User: {username}")

        # Save session log to file
        if session_id in self._session_logs:
            log_file = terminal_log_path / f"session_{session_id}_{int(time.time())}.json"
            try:
                with open(log_file, "w") as f:
                    json.dump(self._session_logs[session_id], f, indent=2)
            except Exception as e:
                logger.error(f"Failed to save session log: {e}")
            finally:
                del self._session_logs[session_id]

    def block_ip(self, ip: str) -> None:
        """Block an IP address."""
        self._blocked_ips.add(ip)
        logger.warning(f"IP blocked: {ip}")

    def is_ip_blocked(self, ip: str) -> bool:
        """Check if IP is blocked."""
        return ip in self._blocked_ips


# Global instance
terminal_security = TerminalSecurity()

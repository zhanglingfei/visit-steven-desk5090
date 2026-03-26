import asyncio
import fcntl
import os
import pty
import re
import signal
import struct
import termios
import time
from typing import Optional

from config import settings


# Dangerous command patterns
_DANGEROUS_PATTERNS = [
    pattern.strip()
    for pattern in settings.terminal_dangerous_commands.split(",")
    if pattern.strip()
]


def is_dangerous_command(command: str) -> tuple[bool, str]:
    """Check if a command is potentially dangerous."""
    cmd_lower = command.lower().strip()

    for pattern in _DANGEROUS_PATTERNS:
        try:
            if re.search(pattern, cmd_lower):
                return True, f"Command blocked: matches dangerous pattern '{pattern}'"
        except re.error:
            # Simple substring match if regex fails
            if pattern in cmd_lower:
                return True, f"Command blocked: contains '{pattern}'"

    return False, ""


class CommandRateLimiter:
    """Rate limit commands per session."""

    def __init__(self, max_per_minute: int = 30):
        self.max_per_minute = max_per_minute
        self._commands: dict[str, list[float]] = {}  # session_id -> timestamps

    def check_rate(self, session_id: str) -> tuple[bool, str]:
        now = time.time()
        timestamps = self._commands.get(session_id, [])
        # Keep only last minute
        timestamps = [t for t in timestamps if now - t < 60]
        timestamps.append(now)
        self._commands[session_id] = timestamps

        if len(timestamps) > self.max_per_minute:
            return False, f"Rate limit exceeded: {self.max_per_minute} commands/minute"
        return True, ""

    def cleanup_session(self, session_id: str):
        self._commands.pop(session_id, None)


command_limiter = CommandRateLimiter(settings.terminal_max_commands_per_minute)


class TerminalSession:
    def __init__(self, pid: int, master_fd: int, username: str, session_id: str):
        self.pid = pid
        self.master_fd = master_fd
        self.username = username
        self.session_id = session_id
        self.created_at = time.time()
        self.last_activity = time.time()
        self.command_buffer = ""  # Buffer for command detection
        self.blocked_count = 0  # Track blocked commands for anomaly detection

    def resize(self, rows: int, cols: int):
        try:
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)
            os.kill(self.pid, signal.SIGWINCH)
        except (OSError, ProcessLookupError):
            pass

    async def read(self) -> Optional[bytes]:
        loop = asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(
                None, lambda: os.read(self.master_fd, 4096)
            )
            self.last_activity = time.time()
            return data
        except OSError:
            return None

    def write(self, data: bytes) -> tuple[bool, str]:
        """Write data to terminal with command filtering."""
        try:
            # Decode for command checking
            text = data.decode('utf-8', errors='ignore')

            # Check for Enter key (command execution)
            if '\r' in text or '\n' in text:
                command = self.command_buffer.strip()
                self.command_buffer = ""

                if command:
                    # Check rate limiting
                    allowed, reason = command_limiter.check_rate(self.session_id)
                    if not allowed:
                        return False, f"[BLOCKED: {reason}]\r\n"

                    # Check for dangerous commands
                    is_dangerous, reason = is_dangerous_command(command)
                    if is_dangerous:
                        self.blocked_count += 1
                        # Log blocked command
                        if settings.terminal_command_logging:
                            print(f"[TERMINAL SECURITY] Blocked command from {self.username}: {command}")
                        return False, f"\r\n[SECURITY: {reason}]\r\n"

            else:
                # Accumulate command buffer
                self.command_buffer += text
                # Keep buffer reasonable size
                if len(self.command_buffer) > 1000:
                    self.command_buffer = self.command_buffer[-500:]

            os.write(self.master_fd, data)
            self.last_activity = time.time()
            return True, ""
        except OSError:
            return False, ""
        except Exception as e:
            return False, f"[Error: {str(e)}]\r\n"

    async def cleanup(self):
        try:
            os.close(self.master_fd)
        except OSError:
            pass
        try:
            os.kill(self.pid, signal.SIGTERM)
            # Wait briefly, then force kill
            await asyncio.sleep(2)
            try:
                os.kill(self.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        except ProcessLookupError:
            pass
        try:
            os.waitpid(self.pid, os.WNOHANG)
        except ChildProcessError:
            pass


class TerminalManager:
    def __init__(self):
        self._sessions: dict[str, TerminalSession] = {}
        self._idle_timeout = 3600  # 1 hour

    @property
    def session_count(self) -> int:
        return len(self._sessions)

    def create_session(self, session_id: str, username: str) -> Optional[TerminalSession]:
        if self.session_count >= settings.max_terminal_sessions:
            return None

        master_fd, slave_fd = pty.openpty()
        child_pid = os.fork()

        if child_pid == 0:
            # Child process
            os.close(master_fd)
            os.setsid()

            # Set up slave as controlling terminal
            fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)

            os.dup2(slave_fd, 0)
            os.dup2(slave_fd, 1)
            os.dup2(slave_fd, 2)
            if slave_fd > 2:
                os.close(slave_fd)

            env = os.environ.copy()
            env["TERM"] = "xterm-256color"
            env["COLORTERM"] = "truecolor"

            os.execvpe("/bin/bash", ["/bin/bash", "--login"], env)
        else:
            # Parent process
            os.close(slave_fd)
            session = TerminalSession(child_pid, master_fd, username, session_id)
            session.resize(24, 80)
            self._sessions[session_id] = session
            return session

    def get_session(self, session_id: str) -> Optional[TerminalSession]:
        return self._sessions.get(session_id)

    async def remove_session(self, session_id: str):
        session = self._sessions.pop(session_id, None)
        if session:
            command_limiter.cleanup_session(session_id)
            await session.cleanup()

    async def cleanup_idle(self):
        now = time.time()
        idle = [
            sid
            for sid, s in self._sessions.items()
            if now - s.last_activity > self._idle_timeout
        ]
        for sid in idle:
            await self.remove_session(sid)

    async def cleanup_all(self):
        for sid in list(self._sessions.keys()):
            await self.remove_session(sid)


terminal_manager = TerminalManager()

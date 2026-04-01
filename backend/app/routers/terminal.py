import asyncio
import json
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.middleware.auth import ws_auth
from app.services.terminal_service import terminal_manager
from app.services.terminal_security import terminal_security
from config import settings

router = APIRouter()


@router.websocket("/terminal")
async def terminal_ws(websocket: WebSocket, token: str = Query(...)):
    # Check Origin header to prevent CSWSH (Cross-Site WebSocket Hijacking)
    origin = websocket.headers.get("origin", "")
    allowed_origins = settings.allowed_origins.split(",")
    if origin and not any(
        origin.startswith(allowed.strip()) or
        (allowed.strip().endswith('.') and origin.startswith(allowed.strip().rstrip('.')))
        for allowed in allowed_origins
    ):
        await websocket.close(code=4003, reason="Origin not allowed")
        return

    # Get client IP
    client_ip = websocket.client.host if websocket.client else "unknown"

    # Check if IP is blocked
    if terminal_security.is_ip_blocked(client_ip):
        await websocket.close(code=4003, reason="IP blocked")
        return

    # Check IP whitelist (if configured)
    if not terminal_security.is_ip_allowed(client_ip):
        await websocket.close(code=4003, reason="IP not allowed")
        return

    # Check rate limit
    if not terminal_security.check_rate_limit(client_ip):
        await websocket.close(code=4008, reason="Rate limit exceeded")
        return

    # Authenticate user
    user = await ws_auth(token)
    if not user:
        terminal_security.block_ip(client_ip)
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()

    session_id = str(uuid.uuid4())

    # Log session start
    terminal_security.log_session_start(session_id, user["username"], client_ip)

    session = terminal_manager.create_session(session_id, user["username"])
    if not session:
        await websocket.send_json({"error": "Max terminal sessions reached"})
        await websocket.close(code=4002, reason="Session limit")
        return

    read_task = None
    try:
        # Task to read PTY output and send to WebSocket
        async def pty_reader():
            while True:
                data = await session.read()
                if data is None:
                    break
                await websocket.send_bytes(data)

        read_task = asyncio.create_task(pty_reader())

        # Read from WebSocket and write to PTY
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break
            if "bytes" in message:
                # Check command before writing
                allowed, reason = terminal_security.check_command(message["bytes"])
                if allowed:
                    terminal_security.log_command(session_id, user["username"], message["bytes"])
                    session.write(message["bytes"])
                else:
                    await websocket.send_bytes(f"\r\n[SECURITY] {reason}\r\n".encode())
            elif "text" in message:
                text = message["text"]
                try:
                    msg = json.loads(text)
                    if msg.get("type") == "resize":
                        session.resize(msg["rows"], msg["cols"])
                    elif msg.get("type") == "input":
                        data = msg["data"].encode()
                        allowed, reason = terminal_security.check_command(data)
                        if allowed:
                            terminal_security.log_command(session_id, user["username"], data)
                            session.write(data)
                        else:
                            await websocket.send_bytes(f"\r\n[SECURITY] {reason}\r\n".encode())
                except (json.JSONDecodeError, KeyError):
                    data = text.encode()
                    allowed, reason = terminal_security.check_command(data)
                    if allowed:
                        terminal_security.log_command(session_id, user["username"], data)
                        session.write(data)
                    else:
                        await websocket.send_bytes(f"\r\n[SECURITY] {reason}\r\n".encode())

    except WebSocketDisconnect:
        pass
    except Exception as e:
        import logging
        logging.error(f"Terminal error: {e}")
    finally:
        if read_task:
            read_task.cancel()
            try:
                await read_task
            except asyncio.CancelledError:
                pass
        await terminal_manager.remove_session(session_id)
        terminal_security.log_session_end(session_id, user["username"])

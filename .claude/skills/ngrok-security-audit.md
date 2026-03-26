# Security Audit: Ngrok Public Deployment

## Executive Summary

**Risk Level: HIGH** - This system has a web-based terminal providing shell access. Exposing it to the public internet via ngrok creates significant security risks that must be addressed before deployment.

---

## Critical Vulnerabilities

### 1. Web Terminal - CRITICAL

**Location**: `backend/app/routers/terminal.py`, `backend/app/services/terminal_service.py`

**Vulnerability**: The `/api/ws/terminal` WebSocket endpoint provides a fully functional bash shell via PTY.

**Risks**:
- Remote code execution (RCE) if authentication is bypassed
- Full system compromise
- Data exfiltration
- Lateral movement to internal network
- Cryptocurrency mining
- Botnet recruitment

**Current Protections**:
- JWT token authentication via query parameter
- Session limit (5 max)
- Idle timeout (1 hour)

**Required Hardening**:
```python
# 1. Add IP whitelist check
ALLOWED_IPS = ["your-home-ip"]  # Configure in .env

async def terminal_ws(websocket: WebSocket, token: str = Query(...)):
    client_ip = websocket.client.host
    if client_ip not in settings.allowed_ips:
        await websocket.close(code=4003, reason="IP not allowed")
        return
    # ... rest of auth

# 2. Add command logging and restrictions
# 3. Use chroot jail for terminal sessions
# 4. Disable sudo/root access
# 5. Add session recording
```

---

### 2. CORS Configuration - HIGH

**Location**: `backend/main.py:23-29`

**Vulnerability**:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # DANGEROUS: Allows any website to call your API
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Risk**: Any malicious website can make authenticated requests to your API using your credentials.

**Fix**:
```python
# Restrict to your ngrok domain only
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-ngrok-domain.ngrok.io"],  # Specific domain
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Limit methods
    allow_headers=["Authorization", "Content-Type"],  # Limit headers
)
```

---

### 3. JWT Secret Key - CRITICAL

**Location**: `backend/config.py:6`

**Vulnerability**:
```python
jwt_secret_key: str = "change-me"  # Default/weak secret
```

**Risk**: Attackers can forge JWT tokens and bypass authentication.

**Fix**:
```python
# Generate strong secret: openssl rand -hex 32
jwt_secret_key: str = "your-64-character-hex-secret-here"
```

Also update `.env`:
```bash
JWT_SECRET_KEY="your-strong-secret-here"
```

---

### 4. Rate Limiting Gaps - MEDIUM

**Current State**: Login has rate limiting, but other endpoints don't.

**Missing Protection**:
- Power history queries (can be abused for DoS)
- System info endpoint
- Metrics WebSocket (can exhaust connections)

**Fix**:
```python
# Add global rate limiting middleware
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# Apply to sensitive endpoints
@router.get("/history")
@limiter.limit("10/minute")
async def get_power_history(...):
    ...
```

---

### 5. Information Disclosure - MEDIUM

**Location**: Multiple endpoints

**Issues**:
- `GET /api/system/info` reveals system details
- Error messages may leak internal paths
- Health endpoint exposes service availability

**Fix**:
```python
# Sanitize system info
@router.get("/info")
async def system_info(user: dict = Depends(get_current_user)):
    info = MetricsCollector.get_system_info()
    # Remove sensitive fields
    return {
        "hostname": info.hostname,
        # Don't expose: internal IPs, usernames, kernel versions
    }
```

---

### 6. WebSocket Authentication - MEDIUM

**Location**: `backend/app/middleware/auth.py:25-32`

**Vulnerability**: WebSocket auth returns `None` on failure instead of raising exception, which may lead to inconsistent handling.

**Also**: Token passed via query parameter may be logged by proxies.

**Fix**:
```python
# Use subprotocol for token instead of query param
# Client: new WebSocket(url, ["token", actual_token])
# Server: Check Sec-WebSocket-Protocol header
```

---

### 7. SQL Injection Risk - LOW

**Location**: `backend/app/services/power_service.py`

**Current State**: Uses parameterized queries (safe), but direct SQL string construction in some places.

**Recommendation**: Continue using parameterized queries exclusively.

---

### 8. Path Traversal - MEDIUM

**Location**: `backend/main.py:48-53`

**Vulnerability**:
```python
@app.get("/{full_path:path}")
async def serve_frontend(request: Request, full_path: str):
    file = FRONTEND_DIR / full_path  # Potential path traversal
    if file.is_file():
        return FileResponse(file)
```

**Risk**: `full_path` could be `../../../etc/passwd`

**Fix**:
```python
from pathlib import Path

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    # Resolve and check path is within FRONTEND_DIR
    try:
        file = (FRONTEND_DIR / full_path).resolve()
        file.relative_to(FRONTEND_DIR.resolve())
    except (ValueError, RuntimeError):
        return FileResponse(FRONTEND_DIR / "index.html")

    if file.is_file():
        return FileResponse(file)
    return FileResponse(FRONTEND_DIR / "index.html")
```

---

### 9. No HTTPS Enforcement - HIGH

**Risk**: Ngrok provides HTTPS, but the backend accepts HTTP connections.

**Fix**:
```python
# Add HTTPS redirect middleware
@app.middleware("http")
async def https_redirect(request: Request, call_next):
    if request.headers.get("X-Forwarded-Proto") == "http":
        return RedirectResponse(
            url=request.url.replace(scheme="https"),
            status_code=307
        )
    return await call_next(request)
```

---

### 10. Missing Security Headers - MEDIUM

**Fix**: Add security headers middleware:
```python
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response
```

---

## Ngrok-Specific Risks

### 1. Public URL Exposure
- Ngrok URLs are publicly discoverable
- Anyone with the URL can attempt attacks

### 2. No DDoS Protection
- Ngrok free tier has no DDoS protection
- Easy target for volumetric attacks

### 3. Connection Limits
- Free tier: 40 connections/minute
- Can be exhausted by automated attacks

### 4. No IP Whitelisting
- Cannot restrict by IP at ngrok level (requires paid plan)

---

## Recommended Deployment Architecture

```
[Internet]
    |
[Nginx Reverse Proxy]  <- Add this layer
    |                  - Rate limiting
    |                  - IP whitelist
    |                  - WAF rules
    |                  - SSL termination
[Ngrok Tunnel]
    |
[FastAPI Backend]
    |
[SQLite DB]
```

---

## Pre-Deployment Checklist

### Must Fix (Critical)
- [ ] Change JWT secret key to strong random value
- [ ] Restrict CORS to specific ngrok domain
- [ ] Add IP whitelist for terminal access
- [ ] Disable terminal or use chroot jail
- [ ] Add HTTPS redirect

### Should Fix (High)
- [ ] Add global rate limiting
- [ ] Fix path traversal vulnerability
- [ ] Add security headers
- [ ] Sanitize error messages
- [ ] Add request logging

### Nice to Have (Medium)
- [ ] Add fail2ban for IP blocking
- [ ] Use Cloudflare in front of ngrok
- [ ] Add monitoring/alerting
- [ ] Regular security scans

---

## Emergency Response

If compromised:

1. **Immediately**: Stop ngrok tunnel
   ```bash
   pkill ngrok
   ```

2. **Check for**: Unauthorized processes
   ```bash
   ps aux | grep -E "(miner|botnet|nc|netcat)"
   ```

3. **Check for**: New users or SSH keys
   ```bash
   cat /etc/passwd | grep -v "nologin"
   cat ~/.ssh/authorized_keys
   ```

4. **Review logs**:
   ```bash
   tail -1000 /var/log/auth.log
   ```

5. **Rotate secrets**: JWT key, passwords, API keys

---

## Alternative: Safer Deployment Options

Instead of ngrok with terminal:

1. **Remove terminal feature** for public access
2. **Use VPN** (Tailscale, WireGuard) instead of public exposure
3. **Cloud deployment** with proper security (AWS/GCP/Azure)
4. **Read-only dashboard** without shell access

---

## Conclusion

**DO NOT deploy with current security posture.**

The web terminal is the highest risk. Consider:
1. Removing it entirely for public deployment
2. Or implementing all critical fixes above
3. Or using VPN-only access

The power monitoring itself is low-risk, but the terminal creates a critical attack vector.

# Visit Steven Desk5090

Web-based system monitoring and terminal access dashboard for homelab management.

## Features

- **System Monitoring**: Real-time GPU, power, and system metrics
- **Web Terminal**: Secure browser-based terminal access with command filtering
- **Authentication**: JWT-based auth with optional 2FA (TOTP)
- **Security**: GeoIP-based access control, rate limiting, device registration
- **Session Logging**: Complete audit trail for terminal sessions

## Quick Start

### Backend

```bash
cd backend
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install

# Default: http://localhost:8000
npm run dev

# With custom backend URL (IP changes, production)
BACKEND_URL=http://192.168.101.21:8000 npm run dev
```

## Configuration

Create a `.env` file in the project root:

```env
# JWT Security (change in production!)
JWT_SECRET_KEY=your-secure-random-key
JWT_EXPIRE_HOURS=4
JWT_REFRESH_DAYS=7

# GeoIP Access Control
GEOIP_ENABLED=true
GEOIP_ALLOWED_COUNTRIES=JP,CN
MAXMIND_LICENSE_KEY=your-maxmind-key  # Free at maxmind.com
GEOIP_FALLBACK_IPS=127.0.0.1,::1

# Terminal Security
ALLOWED_TERMINAL_IPS=                    # Comma-separated whitelist (empty = allow all)
TERMINAL_SESSION_TIMEOUT=3600           # Idle timeout in seconds
TERMINAL_COMMAND_LOGGING=true           # Log all terminal commands
TERMINAL_MAX_COMMANDS_PER_MINUTE=30

# CORS Origins (comma-separated)
ALLOWED_ORIGINS=https://your-domain.com,http://localhost:5173

# Users file location
USERS_FILE=users.json
```

## Security Features

### Authentication
- **JWT Tokens**: Short-lived access tokens (4h) with refresh tokens (7d)
- **2FA Support**: Time-based One-Time Password (TOTP) via authenticator apps
- **Password Policy**: Enforces strong passwords (8+ chars, mixed case, numbers, symbols)
- **Device Registration**: Optional device trust system for additional security

### Access Control
- **GeoIP Filtering**: Restrict access by country (default: JP, CN allowed)
- **Rate Limiting**: Persistent SQLite-based rate limiting (5 attempts/minute, 5min lockout after 5 failures)
- **IP Whitelist**: Optional terminal IP restrictions

### Terminal Security
- **Command Filtering**: Blocks dangerous commands (rm -rf, mkfs, etc.)
- **Path Protection**: Prevents access to sensitive files (/etc/shadow, SSH keys)
- **Session Logging**: Complete audit trail stored in `backend/logs/`
- **Rate Limiting**: Max 10 terminal connections per 5 minutes per IP

### Security Headers
All responses include:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Strict-Transport-Security` (HSTS)
- `Content-Security-Policy`

## API Overview

| Endpoint | Description |
|----------|-------------|
| `POST /api/auth/login` | Login with username/password, optional 2FA |
| `POST /api/auth/refresh` | Refresh JWT access token |
| `POST /api/auth/logout` | Logout and invalidate tokens |
| `POST /api/auth/2fa/setup` | Setup 2FA (returns QR code) |
| `POST /api/auth/2fa/verify` | Verify and enable 2FA |
| `POST /api/auth/password/change` | Change password |
| `GET /api/auth/devices` | List registered devices |
| `WS /api/ws/terminal` | WebSocket terminal connection |
| `GET /api/system/info` | System information |
| `GET /api/system/processes` | Running processes |
| `GET /api/power/status` | Power consumption data |
| `GET /api/health` | Health check endpoint |

## Backup and Restore

### Automated Backup

A backup script is included at `backend/backup.sh`:

```bash
# Run manually
cd backend
./backup.sh

# Or add to crontab for daily backups
0 2 * * * /home/steven-desk5090/visit-steven-desk5090/backend/backup.sh >> /var/log/visit-steven-backup.log 2>&1
```

Backups include:
- `power_logs.db` - Power monitoring data
- `security.db` - Login attempts and security events
- `users.json` - User accounts and settings
- `logs/` - Terminal session logs

Backups are stored in `backups/` with 30-day retention.

### Manual Restore

```bash
# Extract backup
cd backend
tar -xzf ../backups/backup_YYYYMMDD_HHMMSS.tar.gz
```

## Deployment Notes

### IP/Network Changes

When the machine IP changes:

1. Verify backend is running: `curl http://localhost:8000/api/health`
2. Update `BACKEND_URL` environment variable
3. Restart frontend service

### ngrok Deployment

For external access via ngrok:

1. Update `ALLOWED_ORIGINS` to include your ngrok domain:
   ```env
   ALLOWED_ORIGINS=https://your-app.ngrok.io,http://localhost:5173
   ```
2. Restart backend

### HTTPS Requirement

In production, the app automatically redirects HTTP to HTTPS when behind a reverse proxy. Ensure your proxy sets:
- `X-Forwarded-Proto: https`

### Docker Limitations

**Note: This application requires direct access to host hardware (GPU temperature, power sensors, process information). It must run on the host system - Docker is not supported.**

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKEND_URL` | `http://localhost:8000` | Frontend connection URL |
| `JWT_SECRET_KEY` | `change-me-in-production` | JWT signing key |
| `JWT_EXPIRE_HOURS` | `4` | Access token lifetime |
| `JWT_REFRESH_DAYS` | `7` | Refresh token lifetime |
| `GEOIP_ENABLED` | `true` | Enable country-based filtering |
| `GEOIP_ALLOWED_COUNTRIES` | `JP,CN` | Allowed country codes (ISO 3166-1 alpha-2) |
| `MAXMIND_LICENSE_KEY` | - | MaxMind GeoLite2 license |
| `GEOIP_FALLBACK_IPS` | `127.0.0.1,::1` | IPs exempt from GeoIP check |
| `ALLOWED_TERMINAL_IPS` | - | Terminal IP whitelist |
| `TERMINAL_SESSION_TIMEOUT` | `3600` | Terminal idle timeout (seconds) |
| `TERMINAL_COMMAND_LOGGING` | `true` | Enable command audit logging |
| `ALLOWED_ORIGINS` | - | CORS allowed origins |
| `USERS_FILE` | `users.json` | User database file |

## Troubleshooting

### GeoIP Not Working

If GeoIP filtering is not working:

1. Check if license key is set: `MAXMIND_LICENSE_KEY`
2. Database auto-downloads on startup if key is valid
3. Manual download: Set key and restart backend

### Rate Limit Locked Out

If locked out due to failed logins:
- Wait 5 minutes (lockout duration)
- Or clear security database: `rm backend/security.db` (loses audit history)

### Terminal Connection Failed

1. Check `ALLOWED_TERMINAL_IPS` whitelist
2. Verify CORS origins match your domain
3. Check `logs/terminal.log` for errors

## License

Private project - All rights reserved.

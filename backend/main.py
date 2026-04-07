import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.routers import auth, metrics, terminal, system, power, health
from app.services.geoip_service import init_geoip_on_startup

FRONTEND_DIR = Path(__file__).parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize GeoIP service on startup
    init_geoip_on_startup()
    yield
    from app.services.terminal_service import terminal_manager
    await terminal_manager.cleanup_all()


app = FastAPI(title="Visit Steven Desk5090", lifespan=lifespan)


# Security headers middleware
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    # Prevent MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"
    # XSS protection
    response.headers["X-XSS-Protection"] = "1; mode=block"
    # Enforce HTTPS
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    # Content Security Policy - allow base64 images for QR codes
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:;"
    # Referrer policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# HTTPS redirect middleware for production
@app.middleware("http")
async def https_redirect(request: Request, call_next):
    # Check if behind proxy with X-Forwarded-Proto
    proto = request.headers.get("X-Forwarded-Proto")
    if proto == "http":
        # Redirect to HTTPS
        url = request.url.replace(scheme="https")
        return RedirectResponse(url, status_code=307)
    return await call_next(request)

# CORS - Restrict to specific origins for production
# For ngrok: allow_origins=["https://your-ngrok-domain.ngrok.io"]
# For development: allow_origins=["http://localhost:5173"]
import os

# Get allowed origins from config
from config import settings
allow_origins = [origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()]

# CORS - Restrict to configured origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin"],
    expose_headers=["Content-Length"],
    max_age=600,
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(system.router, prefix="/api/system", tags=["system"])
app.include_router(power.router, prefix="/api/power", tags=["power"])
app.include_router(health.router, prefix="/api/health", tags=["health"])
app.include_router(metrics.router, prefix="/api/ws", tags=["metrics"])
app.include_router(terminal.router, prefix="/api/ws", tags=["terminal"])
app.include_router(power.router, prefix="/api/ws", tags=["power"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# Serve frontend static files with path traversal protection
if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(request: Request, full_path: str):
        # Prevent path traversal attacks
        try:
            # Resolve the requested path
            requested_path = (FRONTEND_DIR / full_path).resolve()
            # Ensure it's within FRONTEND_DIR
            requested_path.relative_to(FRONTEND_DIR.resolve())
        except (ValueError, RuntimeError):
            # Path traversal attempt or invalid path
            return FileResponse(FRONTEND_DIR / "index.html")

        if requested_path.is_file():
            return FileResponse(requested_path)
        return FileResponse(FRONTEND_DIR / "index.html")

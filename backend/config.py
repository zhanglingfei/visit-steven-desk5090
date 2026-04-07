from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24
    users_file: str = "users.json"
    max_terminal_sessions: int = 5
    metrics_interval: int = 2

    # Security settings for ngrok deployment
    allowed_terminal_ips: str = ""  # Comma-separated IP whitelist (empty = allow all)
    enable_terminal_logging: bool = True
    terminal_session_timeout: int = 3600  # 1 hour idle timeout
    terminal_command_logging: bool = True
    allowed_origins: str = "https://visit-steven-homelab50.axionintelligence.co.uk,https://visit-steven5090.ngrok.io,http://localhost:5173,http://localhost:4173,http://127.0.0.1:5173,http://127.0.0.1:4173,http://192.168.101.21:5173"

    # JWT settings
    jwt_expire_hours: int = 4  # Short-lived access tokens
    jwt_refresh_days: int = 7  # Longer-lived refresh tokens

    # Terminal security
    terminal_dangerous_commands: str = r"rm -rf,dd if=/dev/zero,mkfs,fdisk,format,>:\,curl.*|.*sh,wget.*|.*sh"
    terminal_max_commands_per_minute: int = 30

    # GeoIP settings
    maxmind_license_key: str = ""  # MaxMind GeoLite2 license key (free signup at maxmind.com)
    geoip_enabled: bool = True  # Enable country-based access control
    geoip_allowed_countries: str = "JP,CN"  # Comma-separated ISO country codes
    geoip_fallback_ips: str = ""  # Additional IPs to always allow (comma-separated)

    @property
    def users_file_path(self) -> Path:
        return Path(__file__).parent / self.users_file

    model_config = {"env_file": str(Path(__file__).parent.parent / ".env")}


settings = Settings()

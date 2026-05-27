from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic_settings import BaseSettings, SettingsConfigDict


def default_sqlite_path() -> Path:
    return Path("~/.codex-pool/codex_pool.db").expanduser()


def default_database_url() -> str:
    path = default_sqlite_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path.resolve().as_posix()}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = ""
    jwt_secret: str = "change-me-in-production"
    jwt_expire_minutes: int = 60 * 24 * 7
    admin_username: str = "admin"
    admin_password: str = "admin123"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    # Public URL users open in the browser (e.g. http://pool.example.com). Used for CORS and upstream self-test rewrite.
    public_base_url: str = ""
    # Process listen port (set by codex-pool-admin on startup; default 8790).
    admin_listen_port: int = 8790

    chatgpt_auth_dir: str = "~/.codex-pool/auth"
    chatgpt_oauth_client_id: str = "app_EMoamEEZ73f0CkXaXp7hrann"
    chatgpt_oauth_authorize_url: str = "https://auth.openai.com/oauth/authorize"
    chatgpt_oauth_token_url: str = "https://auth.openai.com/oauth/token"
    chatgpt_oauth_redirect_uri: str = "http://localhost:1455/auth/callback"
    chatgpt_oauth_callback_port: int = 1455
    chatgpt_usage_url: str = "https://chatgpt.com/backend-api/wham/usage"

    # Upstream forwarding: retries on transient disconnects (see proxy/forward.py).
    proxy_upstream_max_retries: int = 3
    proxy_upstream_retry_backoff_seconds: float = 0.5
    # Disable HTTP keep-alive to upstream when True (helps flaky relays with stale pooled connections).
    proxy_upstream_disable_keepalive: bool = False

    def resolved_database_url(self) -> str:
        url = (self.database_url or "").strip()
        return url or default_database_url()

    def resolved_cors_origins(self) -> list[str]:
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        public = (self.public_base_url or "").strip().rstrip("/")
        if public and public not in origins:
            origins.append(public)
            parsed = urlparse(public)
            if parsed.scheme == "http" and parsed.hostname:
                origins.append(f"https://{parsed.netloc}")
            elif parsed.scheme == "https" and parsed.hostname:
                origins.append(f"http://{parsed.netloc}")
        return origins

    def public_hostname(self) -> str | None:
        public = (self.public_base_url or "").strip()
        if not public:
            return None
        return urlparse(public).hostname

    @staticmethod
    def infer_public_base_url(
        *,
        host: str | None,
        forwarded_proto: str | None = None,
    ) -> str:
        """Derive http(s)://host from reverse-proxy headers when PUBLIC_BASE_URL is unset."""
        h = (host or "").strip()
        if not h or h.startswith("127.0.0.1") or h.startswith("localhost"):
            return ""
        if "," in h:
            h = h.split(",", 1)[0].strip()
        hostname = h.rsplit(":", 1)[0] if ":" in h and not h.startswith("[") else h
        proto = (forwarded_proto or "http").split(",", 1)[0].strip() or "http"
        return f"{proto}://{hostname}".rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()

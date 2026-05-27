from __future__ import annotations

from functools import lru_cache
from pathlib import Path

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

    chatgpt_auth_dir: str = "~/.codex-pool/auth"
    chatgpt_oauth_client_id: str = "app_EMoamEEZ73f0CkXaXp7hrann"
    chatgpt_oauth_authorize_url: str = "https://auth.openai.com/oauth/authorize"
    chatgpt_oauth_token_url: str = "https://auth.openai.com/oauth/token"
    chatgpt_oauth_redirect_uri: str = "http://localhost:1455/auth/callback"
    chatgpt_oauth_callback_port: int = 1455
    chatgpt_usage_url: str = "https://chatgpt.com/backend-api/wham/usage"

    def resolved_database_url(self) -> str:
        url = (self.database_url or "").strip()
        return url or default_database_url()


@lru_cache
def get_settings() -> Settings:
    return Settings()

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "mysql+pymysql://codex:codex@127.0.0.1:3307/codex_pool"
    redis_url: str = "redis://127.0.0.1:6379/0"
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


@lru_cache
def get_settings() -> Settings:
    return Settings()

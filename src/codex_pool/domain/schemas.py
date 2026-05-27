from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    username: str
    balance_usd: Decimal
    display_name: str | None = None
    email: str | None = None
    bio: str | None = None
    phone: str | None = None
    has_avatar: bool = False
    created_at: datetime | None = None


class UserUpdate(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    display_name: str | None = Field(default=None, max_length=64)
    email: str | None = Field(default=None, max_length=128)
    bio: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=32)
    current_password: str | None = None
    new_password: str | None = Field(default=None, min_length=6, max_length=128)


class ProfileUpdateOut(UserOut):
    access_token: str | None = None


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class ApiKeyOut(BaseModel):
    id: int
    name: str
    key_prefix: str
    enabled: bool
    created_at: datetime
    has_secret: bool = False


class ApiKeyCreated(ApiKeyOut):
    key: str


class ApiKeySecretOut(BaseModel):
    key: str


class ApiKeyUpdate(BaseModel):
    name: str | None = None
    enabled: bool | None = None


class UpstreamCreate(BaseModel):
    name: str
    type: str = "openai"
    base_url: str | None = None
    api_key: str | None = None
    auth_file: str | None = None
    priority: int = 100
    enabled: bool = True


class UpstreamUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    auth_file: str | None = None
    priority: int | None = None
    enabled: bool | None = None


class QuotaWindowOut(BaseModel):
    label: str
    used_percent: float
    remaining_percent: float
    limit_window_seconds: int | None = None
    reset_after_seconds: int | None = None
    reset_at: int | None = None


class ChatgptQuotaOut(BaseModel):
    plan_type: str | None = None
    email: str | None = None
    allowed: bool = True
    limit_reached: bool = False
    five_hour: QuotaWindowOut | None = None
    weekly: QuotaWindowOut | None = None


class UpstreamOut(BaseModel):
    id: int
    name: str
    type: str
    base_url: str | None
    api_key_masked: str | None
    auth_file: str | None
    priority: int
    enabled: bool
    created_at: datetime
    updated_at: datetime


class UpstreamTestOut(BaseModel):
    ok: bool
    message: str
    latency_ms: int | None = None


class DashboardStats(BaseModel):
    balance_usd: Decimal
    api_keys_total: int
    api_keys_enabled: int
    today_requests: int
    today_cost_usd: Decimal
    today_input_tokens: int
    today_output_tokens: int
    total_input_tokens: int
    total_output_tokens: int
    rpm: int
    tpm: int
    avg_latency_ms: float


class ModelUsageRow(BaseModel):
    model: str
    requests: int
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal


class PlatformUsageRow(BaseModel):
    platform: str
    requests: int
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal


class UsageTrendPoint(BaseModel):
    date: str
    requests: int
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal
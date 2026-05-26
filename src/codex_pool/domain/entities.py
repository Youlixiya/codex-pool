from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass
class User:
    id: int
    username: str
    password_hash: str
    balance_usd: Decimal
    created_at: datetime
    display_name: str | None = None
    email: str | None = None
    bio: str | None = None
    phone: str | None = None
    avatar_path: str | None = None


@dataclass
class ApiKey:
    id: int
    user_id: int
    name: str
    key_hash: str
    key_prefix: str
    key_secret: str | None
    enabled: bool
    created_at: datetime


@dataclass
class Upstream:
    id: int
    user_id: int
    name: str
    type: str
    base_url: str | None
    api_key: str | None
    auth_file: str | None
    priority: int
    enabled: bool
    created_at: datetime
    updated_at: datetime


@dataclass
class UsageLog:
    id: int
    api_key_id: int | None
    upstream_name: str
    model: str | None
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    cost_usd: Decimal
    status_code: int
    path: str
    created_at: datetime

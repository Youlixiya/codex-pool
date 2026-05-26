from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from ..infrastructure.redis_client import get_redis
from ..infrastructure.settings import get_settings
from .chatgpt_credentials import ChatgptCredentials, load_chatgpt_credentials

logger = logging.getLogger(__name__)

_QUOTA_CACHE_TTL = 30
_FIVE_HOUR_SECONDS = 18_000
_WEEK_SECONDS = 604_800


@dataclass(frozen=True)
class QuotaWindow:
    label: str
    used_percent: float
    remaining_percent: float
    limit_window_seconds: int | None
    reset_after_seconds: int | None
    reset_at: int | None


@dataclass(frozen=True)
class ChatgptQuota:
    plan_type: str | None
    email: str | None
    allowed: bool
    limit_reached: bool
    five_hour: QuotaWindow | None
    weekly: QuotaWindow | None


def _window_label(seconds: int | None) -> str:
    if seconds is None:
        return "额度窗口"
    if seconds == _FIVE_HOUR_SECONDS:
        return "5 小时额度"
    if seconds == _WEEK_SECONDS:
        return "一周额度"
    hours = max(1, round(seconds / 3600))
    return f"{hours} 小时额度"


def _parse_window(raw: dict[str, Any] | None) -> QuotaWindow | None:
    if not raw:
        return None
    used = raw.get("used_percent")
    if not isinstance(used, (int, float)):
        return None
    used_f = float(used)
    window_seconds = raw.get("limit_window_seconds")
    sec = int(window_seconds) if isinstance(window_seconds, (int, float)) else None
    reset_after = raw.get("reset_after_seconds")
    reset_at = raw.get("reset_at")
    return QuotaWindow(
        label=_window_label(sec),
        used_percent=used_f,
        remaining_percent=max(0.0, 100.0 - used_f),
        limit_window_seconds=sec,
        reset_after_seconds=int(reset_after) if isinstance(reset_after, (int, float)) else None,
        reset_at=int(reset_at) if isinstance(reset_at, (int, float)) else None,
    )


def _cache_key(auth_file: str) -> str:
    digest = hashlib.sha256(auth_file.encode()).hexdigest()[:16]
    return f"codex-pool:quota:{digest}"


def _parse_usage_payload(payload: dict[str, Any]) -> ChatgptQuota:
    rate = payload.get("rate_limit") if isinstance(payload.get("rate_limit"), dict) else {}
    primary = _parse_window(rate.get("primary_window") if isinstance(rate.get("primary_window"), dict) else None)
    secondary = _parse_window(
        rate.get("secondary_window") if isinstance(rate.get("secondary_window"), dict) else None
    )

    five_hour = primary if primary and primary.limit_window_seconds == _FIVE_HOUR_SECONDS else None
    weekly = secondary if secondary and secondary.limit_window_seconds == _WEEK_SECONDS else None

    if five_hour is None and primary and primary.limit_window_seconds != _WEEK_SECONDS:
        five_hour = primary
    if weekly is None and secondary:
        weekly = secondary
    if weekly is None and primary and primary.limit_window_seconds == _WEEK_SECONDS:
        weekly = primary

    email = payload.get("email") if isinstance(payload.get("email"), str) else None
    plan_type = payload.get("plan_type") if isinstance(payload.get("plan_type"), str) else None

    return ChatgptQuota(
        plan_type=plan_type,
        email=email,
        allowed=bool(rate.get("allowed", True)),
        limit_reached=bool(rate.get("limit_reached", False)),
        five_hour=five_hour,
        weekly=weekly,
    )


def fetch_chatgpt_quota(auth_file: str | Path, *, use_cache: bool = True) -> ChatgptQuota:
    path = str(Path(auth_file).expanduser().resolve())
    cache_key = _cache_key(path)

    if use_cache:
        cached = get_redis().get(cache_key)
        if cached:
            try:
                return _quota_from_dict(json.loads(cached))
            except (json.JSONDecodeError, TypeError, KeyError):
                pass

    creds = load_chatgpt_credentials(path)
    payload = _request_usage(creds)
    quota = _parse_usage_payload(payload)

    if use_cache:
        get_redis().setex(cache_key, _QUOTA_CACHE_TTL, json.dumps(_quota_to_dict(quota)))

    return quota


def enrich_auth_file_body(token_payload: dict[str, Any]) -> dict[str, Any]:
    """Merge plan/email/account_id into auth.json after OAuth token exchange."""
    from datetime import UTC, datetime

    from .chatgpt_credentials import _decode_jwt_payload

    access = token_payload.get("access_token")
    body: dict[str, Any] = {
        "auth_mode": "chatgpt",
        "tokens": {"access_token": access},
        "last_refresh": datetime.now(UTC).isoformat(),
    }
    for key in ("refresh_token", "id_token"):
        val = token_payload.get(key)
        if isinstance(val, str) and val:
            body["tokens"][key] = val

    id_token = body["tokens"].get("id_token")
    if isinstance(id_token, str):
        claims = _decode_jwt_payload(id_token)
        if claims:
            auth = claims.get("https://api.openai.com/auth")
            if isinstance(auth, dict):
                if auth.get("chatgpt_account_id"):
                    body["chatgpt_account_id"] = auth["chatgpt_account_id"]
                if auth.get("chatgpt_plan_type"):
                    body["plan_type"] = auth["chatgpt_plan_type"]
            if claims.get("email"):
                body["email"] = claims["email"]
    return body


def _request_usage(creds: ChatgptCredentials) -> dict[str, Any]:
    settings = get_settings()
    headers = {"Authorization": f"Bearer {creds.access_token}"}
    if creds.account_id:
        headers["chatgpt-account-id"] = creds.account_id

    with httpx.Client(timeout=30.0) as client:
        resp = client.get(settings.chatgpt_usage_url, headers=headers)

    if resp.status_code >= 400:
        raise RuntimeError(f"usage API error ({resp.status_code}): {resp.text[:300]}")

    data = resp.json()
    if not isinstance(data, dict):
        raise RuntimeError("invalid usage API response")
    return data


def _quota_to_dict(quota: ChatgptQuota) -> dict[str, Any]:
    def win(w: QuotaWindow | None) -> dict[str, Any] | None:
        if w is None:
            return None
        return {
            "label": w.label,
            "used_percent": w.used_percent,
            "remaining_percent": w.remaining_percent,
            "limit_window_seconds": w.limit_window_seconds,
            "reset_after_seconds": w.reset_after_seconds,
            "reset_at": w.reset_at,
        }

    return {
        "plan_type": quota.plan_type,
        "email": quota.email,
        "allowed": quota.allowed,
        "limit_reached": quota.limit_reached,
        "five_hour": win(quota.five_hour),
        "weekly": win(quota.weekly),
    }


def quota_to_schema(quota: ChatgptQuota):
    from ..domain.schemas import ChatgptQuotaOut, QuotaWindowOut

    def win(w: QuotaWindow | None) -> QuotaWindowOut | None:
        if w is None:
            return None
        return QuotaWindowOut(
            label=w.label,
            used_percent=w.used_percent,
            remaining_percent=w.remaining_percent,
            limit_window_seconds=w.limit_window_seconds,
            reset_after_seconds=w.reset_after_seconds,
            reset_at=w.reset_at,
        )

    return ChatgptQuotaOut(
        plan_type=quota.plan_type,
        email=quota.email,
        allowed=quota.allowed,
        limit_reached=quota.limit_reached,
        five_hour=win(quota.five_hour),
        weekly=win(quota.weekly),
    )


def _quota_from_dict(data: dict[str, Any]) -> ChatgptQuota:
    def win(key: str) -> QuotaWindow | None:
        raw = data.get(key)
        if not isinstance(raw, dict):
            return None
        return QuotaWindow(
            label=str(raw.get("label", "")),
            used_percent=float(raw["used_percent"]),
            remaining_percent=float(raw["remaining_percent"]),
            limit_window_seconds=raw.get("limit_window_seconds"),
            reset_after_seconds=raw.get("reset_after_seconds"),
            reset_at=raw.get("reset_at"),
        )

    return ChatgptQuota(
        plan_type=data.get("plan_type"),
        email=data.get("email"),
        allowed=bool(data.get("allowed", True)),
        limit_reached=bool(data.get("limit_reached", False)),
        five_hour=win("five_hour"),
        weekly=win("weekly"),
    )

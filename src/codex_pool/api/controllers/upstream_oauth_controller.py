from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ...domain.schemas import ChatgptQuotaOut
from ...services.chatgpt_oauth import (
    OAuthSession,
    OAuthStatus,
    ensure_callback_server,
    get_oauth_status,
    remote_oauth_setup_hint,
    start_oauth_session,
)
from ...services.chatgpt_usage import enrich_auth_file_body, fetch_chatgpt_quota, quota_to_schema
from ...infrastructure.settings import get_settings
from ..deps import get_current_user_id

router = APIRouter(prefix="/upstreams/oauth/chatgpt", tags=["upstreams-oauth"])


class OAuthStartRequest(BaseModel):
    upstream_name: str | None = Field(default=None, max_length=128)


class OAuthRemoteSetup(BaseModel):
    message: str
    ssh_tunnel_command: str
    redirect_uri: str


class OAuthStartResponse(BaseModel):
    session_id: str
    authorization_url: str
    remote_setup: OAuthRemoteSetup | None = None


class OAuthStatusResponse(BaseModel):
    status: str
    auth_file: str | None = None
    email: str | None = None
    error: str | None = None
    quota: ChatgptQuotaOut | None = None


class AuthJsonImportRequest(BaseModel):
    upstream_name: str = Field(min_length=1, max_length=128)
    auth_json: str = Field(min_length=2, max_length=200_000)


class AuthJsonImportResponse(BaseModel):
    auth_file: str
    email: str | None = None
    quota: ChatgptQuotaOut | None = None


@router.post("/start", response_model=OAuthStartResponse)
def oauth_start(
    request: Request,
    payload: OAuthStartRequest,
    user_id: Annotated[int, Depends(get_current_user_id)],
):
    ensure_callback_server()
    try:
        session: OAuthSession = start_oauth_session(
            user_id=user_id,
            upstream_name=payload.upstream_name,
        )
    except Exception as exc:
        raise HTTPException(503, f"无法启动 OAuth：{exc}") from exc
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    if host and "," in host:
        host = host.split(",", 1)[0].strip()
    if host and ":" in host:
        host = host.rsplit(":", 1)[0]
    hint = remote_oauth_setup_hint(request_host=host)
    remote_setup = OAuthRemoteSetup(**hint) if hint else None
    return OAuthStartResponse(
        session_id=session.session_id,
        authorization_url=session.authorization_url,
        remote_setup=remote_setup,
    )


@router.get("/status/{session_id}", response_model=OAuthStatusResponse)
def oauth_status(
    session_id: str,
    user_id: Annotated[int, Depends(get_current_user_id)],
):
    status: OAuthStatus | None = get_oauth_status(session_id, user_id=user_id)
    if status is None:
        raise HTTPException(404, "会话不存在或已过期")

    quota = None
    if status.status == "completed" and status.auth_file:
        try:
            quota = quota_to_schema(fetch_chatgpt_quota(status.auth_file))
        except Exception:
            quota = None

    return OAuthStatusResponse(
        status=status.status,
        auth_file=status.auth_file,
        email=status.email,
        error=status.error,
        quota=quota,
    )


@router.get("/quota", response_model=ChatgptQuotaOut)
def oauth_quota(
    _: Annotated[int, Depends(get_current_user_id)],
    auth_file: str = Query(..., min_length=1),
):
    try:
        return quota_to_schema(fetch_chatgpt_quota(auth_file))
    except Exception as exc:
        raise HTTPException(502, f"无法获取额度：{exc}") from exc


@router.post("/import", response_model=AuthJsonImportResponse)
def import_auth_json(
    payload: AuthJsonImportRequest,
    user_id: Annotated[int, Depends(get_current_user_id)],
):
    # Accept either:
    # - codex-pool enriched format: {"tokens":{"access_token": "..."}}
    # - raw OAuth token payload: {"access_token": "...", "refresh_token": "...", ...}
    try:
        data = json.loads(payload.auth_json)
    except Exception as exc:
        raise HTTPException(400, f"auth.json 不是合法 JSON：{exc}") from exc

    if not isinstance(data, dict):
        raise HTTPException(400, "auth.json 必须是 JSON 对象")

    access = None
    tokens = data.get("tokens")
    if isinstance(tokens, dict):
        access = tokens.get("access_token")
    if not isinstance(access, str) or not access:
        access = data.get("access_token")

    if not isinstance(access, str) or not access:
        raise HTTPException(400, "auth.json 缺少 access_token（应包含 tokens.access_token 或 access_token）")

    if isinstance(tokens, dict) and isinstance(tokens.get("access_token"), str):
        body = data
    else:
        token_payload = {"access_token": access}
        for k in ("refresh_token", "id_token"):
            v = data.get(k)
            if isinstance(v, str) and v:
                token_payload[k] = v
        body = enrich_auth_file_body(token_payload)

    settings = get_settings()
    auth_dir = Path(settings.chatgpt_auth_dir).expanduser()
    auth_dir.mkdir(parents=True, exist_ok=True)
    safe = "".join(ch if (ch.isalnum() or ch in ("-", "_")) else "-" for ch in payload.upstream_name.strip().lower())
    safe = safe.strip("-")[:64] or "upstream"
    auth_path = auth_dir / f"{safe}-u{user_id}.json"

    try:
        auth_path.write_text(json.dumps(body, indent=2), encoding="utf-8")
        auth_path.chmod(0o600)
    except Exception as exc:
        raise HTTPException(500, f"写入 auth 文件失败：{exc}") from exc

    try:
        quota = quota_to_schema(fetch_chatgpt_quota(str(auth_path), use_cache=False))
    except Exception as exc:
        raise HTTPException(400, f"auth.json 校验失败（token 无效或额度接口不可用）：{exc}") from exc

    return AuthJsonImportResponse(auth_file=str(auth_path), email=quota.email, quota=quota)

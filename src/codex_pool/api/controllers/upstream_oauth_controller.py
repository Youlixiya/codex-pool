from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ...domain.schemas import ChatgptQuotaOut
from ...services.chatgpt_oauth import (
    OAuthSession,
    OAuthStatus,
    ensure_callback_server,
    get_oauth_status,
    start_oauth_session,
)
from ...services.chatgpt_usage import fetch_chatgpt_quota, quota_to_schema
from ..deps import get_current_user_id

router = APIRouter(prefix="/upstreams/oauth/chatgpt", tags=["upstreams-oauth"])


class OAuthStartRequest(BaseModel):
    upstream_name: str | None = Field(default=None, max_length=128)


class OAuthStartResponse(BaseModel):
    session_id: str
    authorization_url: str


class OAuthStatusResponse(BaseModel):
    status: str
    auth_file: str | None = None
    email: str | None = None
    error: str | None = None
    quota: ChatgptQuotaOut | None = None


@router.post("/start", response_model=OAuthStartResponse)
def oauth_start(
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
    return OAuthStartResponse(
        session_id=session.session_id,
        authorization_url=session.authorization_url,
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

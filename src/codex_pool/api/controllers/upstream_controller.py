from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...domain.schemas import (
    ChatgptQuotaOut,
    UpstreamCreate,
    UpstreamOut,
    UpstreamTestOut,
    UpstreamUpdate,
)
from ...repositories.upstream_repository import UpstreamRepository
from ...services.chatgpt_usage import fetch_chatgpt_quota, quota_to_schema
from ...services.upstream_service import UpstreamService
from ...services.upstream_test import test_openai_upstream
from ..deps import get_current_user_id, get_session

router = APIRouter(prefix="/upstreams", tags=["upstreams"])


@router.get("", response_model=list[UpstreamOut])
def list_upstreams(
    user_id: Annotated[int, Depends(get_current_user_id)],
    session: Annotated[Session, Depends(get_session)],
):
    return UpstreamService(session).list_all(user_id)


@router.post("", response_model=UpstreamOut)
def create_upstream(
    payload: UpstreamCreate,
    user_id: Annotated[int, Depends(get_current_user_id)],
    session: Annotated[Session, Depends(get_session)],
):
    return UpstreamService(session).create(user_id, payload)


@router.patch("/{upstream_id}", response_model=UpstreamOut)
def update_upstream(
    upstream_id: int,
    payload: UpstreamUpdate,
    user_id: Annotated[int, Depends(get_current_user_id)],
    session: Annotated[Session, Depends(get_session)],
):
    try:
        return UpstreamService(session).update(user_id, upstream_id, payload)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/{upstream_id}/test", response_model=UpstreamTestOut)
def test_upstream_connection(
    upstream_id: int,
    user_id: Annotated[int, Depends(get_current_user_id)],
    session: Annotated[Session, Depends(get_session)],
):
    row = UpstreamRepository(session).get_for_user(upstream_id, user_id)
    if not row:
        raise HTTPException(404, "upstream not found")
    if row.type != "openai":
        raise HTTPException(400, "仅 openai 中转类型支持连接测试")
    if not row.base_url:
        raise HTTPException(400, "未配置 Base URL")
    if not row.api_key:
        raise HTTPException(400, "未配置 API Key")
    result = test_openai_upstream(base_url=row.base_url, api_key=row.api_key)
    return UpstreamTestOut(**result)


@router.get("/{upstream_id}/quota", response_model=ChatgptQuotaOut)
def upstream_quota(
    upstream_id: int,
    user_id: Annotated[int, Depends(get_current_user_id)],
    session: Annotated[Session, Depends(get_session)],
):
    row = UpstreamRepository(session).get_for_user(upstream_id, user_id)
    if not row:
        raise HTTPException(404, "upstream not found")
    if row.type != "chatgpt":
        raise HTTPException(400, "仅 chatgpt 类型上游支持额度查询")
    if not row.auth_file:
        raise HTTPException(400, "未配置 auth 文件")
    try:
        return quota_to_schema(fetch_chatgpt_quota(row.auth_file))
    except Exception as exc:
        raise HTTPException(502, f"无法获取额度：{exc}") from exc


@router.delete("/{upstream_id}")
def delete_upstream(
    upstream_id: int,
    user_id: Annotated[int, Depends(get_current_user_id)],
    session: Annotated[Session, Depends(get_session)],
):
    try:
        UpstreamService(session).delete(user_id, upstream_id)
        return {"ok": True}
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc

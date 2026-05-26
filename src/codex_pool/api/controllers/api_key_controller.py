from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...domain.schemas import ApiKeyCreate, ApiKeyCreated, ApiKeyOut, ApiKeySecretOut, ApiKeyUpdate
from ...services.api_key_service import ApiKeyService
from ..deps import get_current_user_id, get_session

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.get("", response_model=list[ApiKeyOut])
def list_keys(
    user_id: Annotated[int, Depends(get_current_user_id)],
    session: Annotated[Session, Depends(get_session)],
):
    return ApiKeyService(session).list_keys(user_id)


@router.post("", response_model=ApiKeyCreated)
def create_key(
    payload: ApiKeyCreate,
    user_id: Annotated[int, Depends(get_current_user_id)],
    session: Annotated[Session, Depends(get_session)],
):
    return ApiKeyService(session).create(user_id, payload)


@router.get("/{key_id}/secret", response_model=ApiKeySecretOut)
def reveal_key_secret(
    key_id: int,
    user_id: Annotated[int, Depends(get_current_user_id)],
    session: Annotated[Session, Depends(get_session)],
):
    try:
        return ApiKeyService(session).reveal_secret(user_id, key_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.patch("/{key_id}", response_model=ApiKeyOut)
def update_key(
    key_id: int,
    payload: ApiKeyUpdate,
    user_id: Annotated[int, Depends(get_current_user_id)],
    session: Annotated[Session, Depends(get_session)],
):
    try:
        return ApiKeyService(session).update(user_id, key_id, payload)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.delete("/{key_id}")
def delete_key(
    key_id: int,
    user_id: Annotated[int, Depends(get_current_user_id)],
    session: Annotated[Session, Depends(get_session)],
):
    try:
        ApiKeyService(session).delete(user_id, key_id)
        return {"ok": True}
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc

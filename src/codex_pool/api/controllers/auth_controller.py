from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ...domain.schemas import (
    LoginRequest,
    ProfileUpdateOut,
    RegisterRequest,
    TokenResponse,
    UserOut,
    UserUpdate,
)
from ...repositories.user_repository import UserRepository
from ...services.auth_service import AuthService
from ...services.avatar_service import avatar_file_path, avatar_media_type
from ..deps import get_current_user_id, get_session

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, session: Annotated[Session, Depends(get_session)]):
    service = AuthService(session)
    try:
        return service.register(payload)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: Annotated[Session, Depends(get_session)]):
    service = AuthService(session)
    try:
        return service.login(payload)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/me", response_model=UserOut)
def me(
    user_id: Annotated[int, Depends(get_current_user_id)],
    session: Annotated[Session, Depends(get_session)],
):
    user = UserRepository(session).get_by_id(user_id)
    if not user:
        raise HTTPException(404, "user not found")
    return AuthService._out(user)


@router.put("/me", response_model=ProfileUpdateOut)
def update_me(
    payload: UserUpdate,
    user_id: Annotated[int, Depends(get_current_user_id)],
    session: Annotated[Session, Depends(get_session)],
):
    try:
        return AuthService(session).update_user(user_id, payload)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/me/avatar", response_model=UserOut)
def upload_avatar(
    user_id: Annotated[int, Depends(get_current_user_id)],
    session: Annotated[Session, Depends(get_session)],
    file: Annotated[UploadFile, File(...)],
):
    try:
        return AuthService(session).upload_avatar(user_id, file)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.delete("/me/avatar", response_model=UserOut)
def delete_avatar(
    user_id: Annotated[int, Depends(get_current_user_id)],
    session: Annotated[Session, Depends(get_session)],
):
    try:
        return AuthService(session).delete_avatar(user_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/me/avatar")
def get_my_avatar(user_id: Annotated[int, Depends(get_current_user_id)]):
    path = avatar_file_path(user_id)
    if not path:
        raise HTTPException(404, "avatar not found")
    return FileResponse(path, media_type=avatar_media_type(path))

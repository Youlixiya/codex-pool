from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ..infrastructure.database import get_db
from ..infrastructure.security import decode_token
from ..repositories.user_repository import UserRepository

bearer = HTTPBearer(auto_error=False)


def get_session():
    yield from get_db()


def get_current_user_id(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    session: Annotated[Session, Depends(get_session)],
) -> int:
    if not creds:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "not authenticated")
    try:
        username = decode_token(creds.credentials)
    except Exception as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token") from exc
    user = UserRepository(session).get_by_username(username)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user not found")
    return user.id

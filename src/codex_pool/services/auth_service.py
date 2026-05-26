from __future__ import annotations

from sqlalchemy.orm import Session

from ..domain.schemas import (
    LoginRequest,
    ProfileUpdateOut,
    RegisterRequest,
    TokenResponse,
    UserOut,
    UserUpdate,
)
from ..infrastructure.security import create_access_token, hash_password, verify_password
from ..infrastructure.settings import get_settings
from ..repositories.user_repository import UserRepository
from .avatar_service import remove_avatar, save_avatar


class AuthService:
    def __init__(self, session: Session) -> None:
        self._users = UserRepository(session)

    def ensure_admin(self) -> None:
        settings = get_settings()
        if self._users.get_by_username(settings.admin_username):
            return
        self._users.create(settings.admin_username, hash_password(settings.admin_password))

    def register(self, payload: RegisterRequest) -> TokenResponse:
        username = payload.username.strip()
        if not username:
            raise ValueError("username is required")
        if self._users.get_by_username(username):
            raise ValueError("username already exists")
        user = self._users.create(username, hash_password(payload.password))
        return TokenResponse(access_token=create_access_token(user.username))

    def login(self, payload: LoginRequest) -> TokenResponse:
        user = self._users.get_by_username(payload.username)
        if not user or not verify_password(payload.password, user.password_hash):
            raise ValueError("invalid username or password")
        return TokenResponse(access_token=create_access_token(user.username))

    def get_user(self, username: str) -> UserOut:
        user = self._users.get_by_username(username)
        if not user:
            raise ValueError("user not found")
        return self._out(user)

    def update_user(self, user_id: int, payload: UserUpdate) -> ProfileUpdateOut:
        user = self._users.get_by_id(user_id)
        if not user:
            raise ValueError("user not found")

        username = payload.username.strip()
        if not username:
            raise ValueError("username is required")
        existing = self._users.get_by_username(username)
        if existing and existing.id != user_id:
            raise ValueError("username already exists")

        updates: dict[str, object] = {}
        if username != user.username:
            updates["username"] = username

        display_name = (payload.display_name or "").strip() or None
        email = (payload.email or "").strip() or None
        bio = (payload.bio or "").strip() or None
        phone = (payload.phone or "").strip() or None

        if display_name != user.display_name:
            updates["display_name"] = display_name
        if email != user.email:
            updates["email"] = email
        if bio != user.bio:
            updates["bio"] = bio
        if phone != user.phone:
            updates["phone"] = phone

        if payload.new_password:
            if not payload.current_password:
                raise ValueError("current password is required")
            if not verify_password(payload.current_password, user.password_hash):
                raise ValueError("current password is incorrect")
            updates["password_hash"] = hash_password(payload.new_password)

        if updates:
            user = self._users.update(user_id, **updates)
            if not user:
                raise ValueError("user not found")

        access_token = create_access_token(user.username) if "username" in updates else None
        return ProfileUpdateOut(
            **self._out(user).model_dump(),
            access_token=access_token,
        )

    def upload_avatar(self, user_id: int, upload) -> UserOut:
        user = self._users.get_by_id(user_id)
        if not user:
            raise ValueError("user not found")
        filename = save_avatar(user_id, upload)
        user = self._users.update(user_id, avatar_path=filename)
        if not user:
            raise ValueError("user not found")
        return self._out(user)

    def delete_avatar(self, user_id: int) -> UserOut:
        user = self._users.get_by_id(user_id)
        if not user:
            raise ValueError("user not found")
        remove_avatar(user_id)
        user = self._users.update(user_id, avatar_path=None)
        if not user:
            raise ValueError("user not found")
        return self._out(user)

    @staticmethod
    def _out(user) -> UserOut:
        return UserOut(
            id=user.id,
            username=user.username,
            balance_usd=user.balance_usd,
            display_name=user.display_name,
            email=user.email,
            bio=user.bio,
            phone=user.phone,
            has_avatar=bool(user.avatar_path),
            created_at=user.created_at,
        )

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain.entities import User
from ..infrastructure.orm_models import UserORM


class UserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_username(self, username: str) -> User | None:
        row = self._session.scalar(select(UserORM).where(UserORM.username == username))
        return self._to_entity(row) if row else None

    def get_by_id(self, user_id: int) -> User | None:
        row = self._session.get(UserORM, user_id)
        return self._to_entity(row) if row else None

    def create(self, username: str, password_hash: str) -> User:
        row = UserORM(username=username, password_hash=password_hash)
        self._session.add(row)
        self._session.flush()
        return self._to_entity(row)

    def update_balance(self, user_id: int, balance_usd) -> None:
        row = self._session.get(UserORM, user_id)
        if row:
            row.balance_usd = balance_usd

    def update(self, user_id: int, **fields) -> User | None:
        row = self._session.get(UserORM, user_id)
        if not row:
            return None
        for key, value in fields.items():
            if hasattr(row, key):
                setattr(row, key, value)
        self._session.flush()
        return self._to_entity(row)

    @staticmethod
    def _to_entity(row: UserORM) -> User:
        return User(
            id=row.id,
            username=row.username,
            password_hash=row.password_hash,
            balance_usd=row.balance_usd,
            created_at=row.created_at,
            display_name=row.display_name,
            email=row.email,
            bio=row.bio,
            phone=row.phone,
            avatar_path=row.avatar_path,
        )

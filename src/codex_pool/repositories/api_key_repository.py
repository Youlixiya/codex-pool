from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..domain.entities import ApiKey
from ..infrastructure.orm_models import ApiKeyORM


class ApiKeyRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_by_user(self, user_id: int) -> list[ApiKey]:
        rows = self._session.scalars(
            select(ApiKeyORM).where(ApiKeyORM.user_id == user_id).order_by(ApiKeyORM.id.desc())
        ).all()
        return [self._to_entity(r) for r in rows]

    def get(self, key_id: int) -> ApiKey | None:
        row = self._session.get(ApiKeyORM, key_id)
        return self._to_entity(row) if row else None

    def get_by_hash(self, key_hash: str) -> ApiKey | None:
        row = self._session.scalar(select(ApiKeyORM).where(ApiKeyORM.key_hash == key_hash))
        return self._to_entity(row) if row else None

    def get_for_user(self, key_id: int, user_id: int) -> ApiKey | None:
        row = self._session.get(ApiKeyORM, key_id)
        if not row or row.user_id != user_id:
            return None
        return self._to_entity(row)

    def create(
        self,
        user_id: int,
        name: str,
        key_hash: str,
        key_prefix: str,
        *,
        key_secret: str | None = None,
    ) -> ApiKey:
        row = ApiKeyORM(
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            key_secret=key_secret,
            enabled=True,
        )
        self._session.add(row)
        self._session.flush()
        return self._to_entity(row)

    def update(self, key_id: int, **fields) -> ApiKey | None:
        row = self._session.get(ApiKeyORM, key_id)
        if not row:
            return None
        for k, v in fields.items():
            if v is not None and hasattr(row, k):
                setattr(row, k, v)
        self._session.flush()
        return self._to_entity(row)

    def delete(self, key_id: int) -> bool:
        row = self._session.get(ApiKeyORM, key_id)
        if not row:
            return False
        self._session.delete(row)
        return True

    def count_stats(self, user_id: int) -> tuple[int, int]:
        total = self._session.scalar(
            select(func.count()).select_from(ApiKeyORM).where(ApiKeyORM.user_id == user_id)
        ) or 0
        enabled = self._session.scalar(
            select(func.count())
            .select_from(ApiKeyORM)
            .where(ApiKeyORM.user_id == user_id, ApiKeyORM.enabled.is_(True))
        ) or 0
        return int(total), int(enabled)

    @staticmethod
    def _to_entity(row: ApiKeyORM) -> ApiKey:
        return ApiKey(
            id=row.id,
            user_id=row.user_id,
            name=row.name,
            key_hash=row.key_hash,
            key_prefix=row.key_prefix,
            key_secret=row.key_secret,
            enabled=row.enabled,
            created_at=row.created_at,
        )

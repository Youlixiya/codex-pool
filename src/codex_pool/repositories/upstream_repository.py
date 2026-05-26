from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain.entities import Upstream
from ..infrastructure.orm_models import UpstreamORM


class UpstreamRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_by_user(self, user_id: int) -> list[Upstream]:
        rows = self._session.scalars(
            select(UpstreamORM)
            .where(UpstreamORM.user_id == user_id)
            .order_by(UpstreamORM.priority.asc(), UpstreamORM.id.asc())
        ).all()
        return [self._to_entity(r) for r in rows]

    def list_enabled_by_user(self, user_id: int) -> list[Upstream]:
        rows = self._session.scalars(
            select(UpstreamORM)
            .where(UpstreamORM.user_id == user_id, UpstreamORM.enabled.is_(True))
            .order_by(UpstreamORM.priority.asc())
        ).all()
        return [self._to_entity(r) for r in rows]

    def get_for_user(self, upstream_id: int, user_id: int) -> Upstream | None:
        row = self._session.get(UpstreamORM, upstream_id)
        if not row or row.user_id != user_id:
            return None
        return self._to_entity(row)

    def create(self, *, user_id: int, **fields) -> Upstream:
        row = UpstreamORM(user_id=user_id, **fields)
        self._session.add(row)
        self._session.flush()
        return self._to_entity(row)

    def update(self, upstream_id: int, user_id: int, **fields) -> Upstream | None:
        row = self._session.get(UpstreamORM, upstream_id)
        if not row or row.user_id != user_id:
            return None
        for k, v in fields.items():
            if v is not None and hasattr(row, k):
                setattr(row, k, v)
        self._session.flush()
        return self._to_entity(row)

    def delete(self, upstream_id: int, user_id: int) -> bool:
        row = self._session.get(UpstreamORM, upstream_id)
        if not row or row.user_id != user_id:
            return False
        self._session.delete(row)
        return True

    @staticmethod
    def _to_entity(row: UpstreamORM) -> Upstream:
        return Upstream(
            id=row.id,
            user_id=row.user_id,
            name=row.name,
            type=row.type,
            base_url=row.base_url,
            api_key=row.api_key,
            auth_file=row.auth_file,
            priority=row.priority,
            enabled=row.enabled,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

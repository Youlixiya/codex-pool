from __future__ import annotations

from sqlalchemy.orm import Session

from ..domain.schemas import UpstreamCreate, UpstreamOut, UpstreamUpdate
from ..infrastructure.config_reload import publish_config_reload
from ..repositories.upstream_repository import UpstreamRepository


def _mask_key(key: str | None) -> str | None:
    if not key:
        return None
    if len(key) <= 8:
        return "****"
    return key[:4] + "****" + key[-4:]


class UpstreamService:
    def __init__(self, session: Session) -> None:
        self._repo = UpstreamRepository(session)

    def list_all(self, user_id: int) -> list[UpstreamOut]:
        return [self._out(u) for u in self._repo.list_by_user(user_id)]

    def create(self, user_id: int, payload: UpstreamCreate) -> UpstreamOut:
        entity = self._repo.create(
            user_id=user_id,
            name=payload.name,
            type=payload.type,
            base_url=payload.base_url,
            api_key=payload.api_key,
            auth_file=payload.auth_file,
            priority=payload.priority,
            enabled=payload.enabled,
        )
        publish_config_reload()
        return self._out(entity)

    def update(self, user_id: int, upstream_id: int, payload: UpstreamUpdate) -> UpstreamOut:
        entity = self._repo.update(
            upstream_id,
            user_id,
            name=payload.name,
            type=payload.type,
            base_url=payload.base_url,
            api_key=payload.api_key,
            auth_file=payload.auth_file,
            priority=payload.priority,
            enabled=payload.enabled,
        )
        if not entity:
            raise ValueError("upstream not found")
        publish_config_reload()
        return self._out(entity)

    def delete(self, user_id: int, upstream_id: int) -> None:
        if not self._repo.delete(upstream_id, user_id):
            raise ValueError("upstream not found")
        publish_config_reload()

    @staticmethod
    def _out(entity) -> UpstreamOut:
        return UpstreamOut(
            id=entity.id,
            name=entity.name,
            type=entity.type,
            base_url=entity.base_url,
            api_key_masked=_mask_key(entity.api_key),
            auth_file=entity.auth_file,
            priority=entity.priority,
            enabled=entity.enabled,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

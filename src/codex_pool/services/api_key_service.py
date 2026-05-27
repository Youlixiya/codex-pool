from __future__ import annotations

from sqlalchemy.orm import Session

from ..domain.schemas import ApiKeyCreate, ApiKeyCreated, ApiKeyOut, ApiKeySecretOut, ApiKeyUpdate
from ..infrastructure.config_reload import publish_config_reload
from ..infrastructure.security import api_key_prefix, generate_api_key, hash_api_key
from ..repositories.api_key_repository import ApiKeyRepository


class ApiKeyService:
    def __init__(self, session: Session) -> None:
        self._repo = ApiKeyRepository(session)

    def list_keys(self, user_id: int) -> list[ApiKeyOut]:
        return [self._out(k) for k in self._repo.list_by_user(user_id)]

    def create(self, user_id: int, payload: ApiKeyCreate) -> ApiKeyCreated:
        raw = generate_api_key()
        entity = self._repo.create(
            user_id=user_id,
            name=payload.name,
            key_hash=hash_api_key(raw),
            key_prefix=api_key_prefix(raw),
            key_secret=raw,
        )
        publish_config_reload()
        return ApiKeyCreated(**self._out(entity).model_dump(), key=raw)

    def update(self, user_id: int, key_id: int, payload: ApiKeyUpdate) -> ApiKeyOut:
        if not self._repo.get_for_user(key_id, user_id):
            raise ValueError("api key not found")
        entity = self._repo.update(
            key_id,
            name=payload.name,
            enabled=payload.enabled,
        )
        if not entity:
            raise ValueError("api key not found")
        publish_config_reload()
        return self._out(entity)

    def delete(self, user_id: int, key_id: int) -> None:
        if not self._repo.get_for_user(key_id, user_id):
            raise ValueError("api key not found")
        if not self._repo.delete(key_id):
            raise ValueError("api key not found")
        publish_config_reload()

    def reveal_secret(self, user_id: int, key_id: int) -> ApiKeySecretOut:
        entity = self._repo.get_for_user(key_id, user_id)
        if not entity:
            raise ValueError("api key not found")
        if not entity.key_secret:
            raise ValueError("此 Key 创建于旧版本，无法读取完整密钥，请新建或删除后重新创建")
        return ApiKeySecretOut(key=entity.key_secret)

    @staticmethod
    def _out(entity) -> ApiKeyOut:
        return ApiKeyOut(
            id=entity.id,
            name=entity.name,
            key_prefix=entity.key_prefix,
            enabled=entity.enabled,
            created_at=entity.created_at,
            has_secret=bool(entity.key_secret),
        )

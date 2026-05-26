from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..infrastructure.orm_models import SettingORM


class SettingsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, key: str, default: str = "") -> str:
        row = self._session.get(SettingORM, key)
        return row.setting_value if row else default

    def set(self, key: str, value: str) -> None:
        row = self._session.get(SettingORM, key)
        if row:
            row.setting_value = value
        else:
            self._session.add(SettingORM(setting_key=key, setting_value=value))

    def get_all(self) -> dict[str, str]:
        rows = self._session.scalars(select(SettingORM)).all()
        return {r.setting_key: r.setting_value for r in rows}

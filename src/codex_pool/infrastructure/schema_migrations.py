from __future__ import annotations

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

_USER_PROFILE_COLUMNS: tuple[tuple[str, str], ...] = (
    ("display_name", "VARCHAR(64)"),
    ("email", "VARCHAR(128)"),
    ("bio", "TEXT"),
    ("phone", "VARCHAR(32)"),
    ("avatar_path", "VARCHAR(255)"),
)


def ensure_user_profile_schema(engine: Engine) -> None:
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("users")}
    for name, col_type in _USER_PROFILE_COLUMNS:
        if name in existing:
            continue
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE users ADD COLUMN {name} {col_type}"))
        logger.info("added users.%s", name)

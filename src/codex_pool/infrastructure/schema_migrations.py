from __future__ import annotations

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from .settings import get_settings

logger = logging.getLogger(__name__)

_USER_PROFILE_COLUMNS: tuple[tuple[str, str], ...] = (
    ("display_name", "VARCHAR(64) NULL"),
    ("email", "VARCHAR(128) NULL"),
    ("bio", "TEXT NULL"),
    ("phone", "VARCHAR(32) NULL"),
    ("avatar_path", "VARCHAR(255) NULL"),
)


def ensure_user_profile_schema(engine: Engine) -> None:
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("users")}
    additions = [
        f"ADD COLUMN {name} {definition}"
        for name, definition in _USER_PROFILE_COLUMNS
        if name not in existing
    ]
    if not additions:
        return
    stmt = text(f"ALTER TABLE users {', '.join(additions)}")
    with engine.begin() as conn:
        conn.execute(stmt)
    logger.info("applied user profile schema migration (%d columns)", len(additions))


def ensure_upstream_user_schema(engine: Engine) -> None:
    inspector = inspect(engine)
    if "upstreams" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("upstreams")}
    if "user_id" in columns:
        return

    settings = get_settings()
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE upstreams ADD COLUMN user_id BIGINT NULL AFTER id"))
        conn.execute(
            text(
                """
                UPDATE upstreams u
                JOIN users admin ON admin.username = :admin_username
                SET u.user_id = admin.id
                WHERE u.user_id IS NULL
                """
            ),
            {"admin_username": settings.admin_username},
        )
        conn.execute(
            text(
                """
                UPDATE upstreams u
                JOIN (SELECT id FROM users ORDER BY id ASC LIMIT 1) fallback ON 1 = 1
                SET u.user_id = fallback.id
                WHERE u.user_id IS NULL
                """
            )
        )
        conn.execute(
            text(
                """
                ALTER TABLE upstreams
                MODIFY COLUMN user_id BIGINT NOT NULL,
                ADD INDEX idx_upstreams_user (user_id)
                """
            )
        )
        try:
            conn.execute(
                text(
                    """
                    ALTER TABLE upstreams
                    ADD CONSTRAINT fk_upstreams_user
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                    """
                )
            )
        except Exception:
            pass
        for idx in inspector.get_indexes("upstreams"):
            if idx.get("unique") and idx["column_names"] == ["name"]:
                conn.execute(text(f"ALTER TABLE upstreams DROP INDEX `{idx['name']}`"))
                break
        else:
            try:
                conn.execute(text("ALTER TABLE upstreams DROP INDEX name"))
            except Exception:
                pass
        indexes = {idx["name"] for idx in inspect(engine).get_indexes("upstreams")}
        if "uq_upstreams_user_name" not in indexes:
            conn.execute(
                text(
                    "ALTER TABLE upstreams ADD UNIQUE KEY uq_upstreams_user_name (user_id, name)"
                )
            )
    logger.info("applied upstream user_id schema migration")

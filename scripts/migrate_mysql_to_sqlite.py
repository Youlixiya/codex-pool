#!/usr/bin/env python3
"""Migrate codex-pool data from MySQL to SQLite.

Usage:
  uv run --with pymysql python scripts/migrate_mysql_to_sqlite.py
  uv run --with pymysql python scripts/migrate_mysql_to_sqlite.py \\
    --mysql-url 'mysql+pymysql://codex:codex@127.0.0.1:3307/codex_pool' \\
    --sqlite-path ~/.codex-pool/codex_pool.db
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def _row_dict(row) -> dict:
    return dict(row._mapping)


def _fetch_all(engine: Engine, sql: str) -> list[dict]:
    with engine.connect() as conn:
        return [_row_dict(r) for r in conn.execute(text(sql))]


def _backup_sqlite(path: Path) -> Path | None:
    if not path.is_file():
        return None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = path.with_name(f"{path.name}.bak.{stamp}")
    shutil.copy2(path, backup)
    return backup


def _clear_sqlite(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        for table in ("usage_logs", "api_keys", "upstreams", "users", "settings"):
            conn.execute(text(f"DELETE FROM {table}"))
        if engine.dialect.has_table(conn, "sqlite_sequence"):
            conn.execute(text("DELETE FROM sqlite_sequence"))
        conn.execute(text("PRAGMA foreign_keys=ON"))


def _insert_users(conn, rows: list[dict]) -> None:
    for r in rows:
        conn.execute(
            text(
                """
                INSERT INTO users (
                    id, username, password_hash, balance_usd,
                    display_name, email, bio, phone, avatar_path, created_at
                ) VALUES (
                    :id, :username, :password_hash, :balance_usd,
                    :display_name, :email, :bio, :phone, :avatar_path, :created_at
                )
                """
            ),
            {
                **r,
                "balance_usd": float(r["balance_usd"]) if r.get("balance_usd") is not None else 50.0,
            },
        )


def _insert_api_keys(conn, rows: list[dict]) -> None:
    for r in rows:
        conn.execute(
            text(
                """
                INSERT INTO api_keys (
                    id, user_id, name, key_hash, key_prefix, key_secret, enabled, created_at
                ) VALUES (
                    :id, :user_id, :name, :key_hash, :key_prefix, :key_secret, :enabled, :created_at
                )
                """
            ),
            {**r, "enabled": bool(r.get("enabled", 1))},
        )


def _insert_upstreams(conn, rows: list[dict]) -> None:
    for r in rows:
        conn.execute(
            text(
                """
                INSERT INTO upstreams (
                    id, user_id, name, type, base_url, api_key, auth_file,
                    priority, enabled, created_at, updated_at
                ) VALUES (
                    :id, :user_id, :name, :type, :base_url, :api_key, :auth_file,
                    :priority, :enabled, :created_at, :updated_at
                )
                """
            ),
            {**r, "enabled": bool(r.get("enabled", 1))},
        )


def _insert_usage_logs(conn, rows: list[dict]) -> None:
    for r in rows:
        conn.execute(
            text(
                """
                INSERT INTO usage_logs (
                    id, api_key_id, upstream_name, model, input_tokens, output_tokens,
                    cached_tokens, cost_usd, status_code, path, created_at
                ) VALUES (
                    :id, :api_key_id, :upstream_name, :model, :input_tokens, :output_tokens,
                    :cached_tokens, :cost_usd, :status_code, :path, :created_at
                )
                """
            ),
            {
                **r,
                "cost_usd": float(r.get("cost_usd") or 0),
            },
        )


def _insert_settings(conn, rows: list[dict]) -> None:
    for r in rows:
        conn.execute(
            text(
                "INSERT INTO settings (setting_key, setting_value) VALUES (:setting_key, :setting_value)"
            ),
            r,
        )


def migrate(*, mysql_url: str, sqlite_path: Path, force: bool) -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

    from codex_pool.infrastructure.database import _engine_kwargs, _expand_sqlite_url, init_db
    from codex_pool.infrastructure.orm_models import Base

    sqlite_path = sqlite_path.expanduser().resolve()
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    sqlite_url = f"sqlite:///{sqlite_path.as_posix()}"

    mysql_engine = create_engine(mysql_url, pool_pre_ping=True)
    sqlite_engine = create_engine(
        _expand_sqlite_url(sqlite_url),
        **_engine_kwargs(sqlite_url),
    )

    users = _fetch_all(mysql_engine, "SELECT * FROM users ORDER BY id")
    api_keys = _fetch_all(mysql_engine, "SELECT * FROM api_keys ORDER BY id")
    upstreams = _fetch_all(mysql_engine, "SELECT * FROM upstreams ORDER BY id")
    usage_logs = _fetch_all(mysql_engine, "SELECT * FROM usage_logs ORDER BY id")
    settings = _fetch_all(mysql_engine, "SELECT * FROM settings ORDER BY setting_key")

    print("MySQL source:")
    print(f"  users:       {len(users)}")
    print(f"  api_keys:    {len(api_keys)}")
    print(f"  upstreams:   {len(upstreams)}")
    print(f"  usage_logs:  {len(usage_logs)}")
    print(f"  settings:    {len(settings)}")

    if not users and not force:
        print("No users in MySQL; aborting (use --force to migrate anyway).", file=sys.stderr)
        sys.exit(1)

    backup = _backup_sqlite(sqlite_path)
    if backup:
        print(f"Backed up existing SQLite -> {backup}")

    Base.metadata.create_all(sqlite_engine)
    _clear_sqlite(sqlite_engine)

    with sqlite_engine.begin() as conn:
        _insert_users(conn, users)
        _insert_api_keys(conn, api_keys)
        _insert_upstreams(conn, upstreams)
        _insert_usage_logs(conn, usage_logs)
        _insert_settings(conn, settings)

    print(f"\nSQLite target: {sqlite_path}")
    print("Migration complete.")
    print("Restart codex-pool-admin if it is running.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate codex-pool MySQL data to SQLite")
    parser.add_argument(
        "--mysql-url",
        default="mysql+pymysql://codex:codex@127.0.0.1:3307/codex_pool",
        help="Source MySQL SQLAlchemy URL",
    )
    parser.add_argument(
        "--sqlite-path",
        default="~/.codex-pool/codex_pool.db",
        help="Target SQLite database file",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Migrate even when source has zero users",
    )
    args = parser.parse_args()
    migrate(mysql_url=args.mysql_url, sqlite_path=Path(args.sqlite_path), force=args.force)


if __name__ == "__main__":
    main()

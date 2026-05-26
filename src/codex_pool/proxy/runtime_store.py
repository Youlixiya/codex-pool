from __future__ import annotations

import hashlib
import logging
import os
import threading
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from .billing import BillingConfig, ModelPrice, cost_usd
from .config import AppConfig, Upstream

logger = logging.getLogger(__name__)


@dataclass
class ApiKeyRecord:
    id: int
    user_id: int
    key_hash: str
    enabled: bool


class DbStore:
    def __init__(self, database_url: str) -> None:
        self._engine = create_engine(database_url, pool_pre_ping=True, pool_recycle=3600)
        self._session_factory = sessionmaker(bind=self._engine)
        self._lock = threading.Lock()
        self._api_keys: dict[str, ApiKeyRecord] = {}
        self._upstreams_by_user: dict[int, list[Upstream]] = {}
        self._strategy = "failover"
        self._billing = BillingConfig(
            enabled=True,
            budget_usd=50.0,
            state_path=__import__("pathlib").Path("~/.codex-pool/usage.json").expanduser(),
            default_price=ModelPrice(5.0, 30.0, 0.5),
            model_prices={},
        )

    def reload(self) -> AppConfig | None:
        with self._lock:
            try:
                with self._session_factory() as session:
                    self._load_api_keys(session)
                    self._load_upstreams(session)
                    self._load_settings(session)
            except Exception as exc:
                logger.error("db reload failed: %s", exc)
                return None
            if not self._api_keys:
                logger.warning("no api keys in database")
            if not self._upstreams_by_user:
                logger.warning("no upstreams in database")
            total_upstreams = sum(len(v) for v in self._upstreams_by_user.values())
            return AppConfig(
                pool_api_key="db-managed-keys",
                strategy=self._strategy,
                upstreams=[u for ups in self._upstreams_by_user.values() for u in ups],
            )

    def lookup_api_key(self, raw_key: str) -> ApiKeyRecord | None:
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        with self._lock:
            record = self._api_keys.get(key_hash)
            if record and record.enabled:
                return record
            return None

    def verify_api_key(self, raw_key: str) -> bool:
        return self.lookup_api_key(raw_key) is not None

    def config_for_user(self, user_id: int) -> AppConfig:
        with self._lock:
            upstreams = list(self._upstreams_by_user.get(user_id, []))
            return AppConfig(
                pool_api_key="db-managed-keys",
                strategy=self._strategy,
                upstreams=upstreams,
            )

    def log_usage(
        self,
        *,
        raw_key: str | None,
        upstream_name: str,
        model: str | None,
        usage: dict | None,
        status_code: int,
        path: str,
    ) -> None:
        if not usage:
            return
        key_id = None
        if raw_key:
            record = self.lookup_api_key(raw_key)
            key_id = record.id if record else None
        cost = cost_usd(self._billing, model, usage)
        input_tokens = int(usage.get("input_tokens") or 0)
        output_tokens = int(usage.get("output_tokens") or 0)
        cached = 0
        details = usage.get("input_tokens_details")
        if isinstance(details, dict):
            cached = int(details.get("cached_tokens") or 0)

        def _write():
            try:
                with self._session_factory() as session:
                    session.execute(
                        text(
                            """
                            INSERT INTO usage_logs
                            (api_key_id, upstream_name, model, input_tokens, output_tokens,
                             cached_tokens, cost_usd, status_code, path)
                            VALUES (:api_key_id, :upstream_name, :model, :input_tokens,
                                    :output_tokens, :cached_tokens, :cost_usd, :status_code, :path)
                            """
                        ),
                        {
                            "api_key_id": key_id,
                            "upstream_name": upstream_name,
                            "model": model,
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                            "cached_tokens": cached,
                            "cost_usd": float(cost),
                            "status_code": status_code,
                            "path": path,
                        },
                    )
                    session.commit()
                try:
                    import redis

                    r = redis.Redis.from_url(
                        os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0"),
                        decode_responses=True,
                    )
                    pipe = r.pipeline()
                    pipe.incr("metrics:rpm:window")
                    pipe.incrby("metrics:tpm:window", input_tokens + output_tokens)
                    pipe.expire("metrics:rpm:window", 60)
                    pipe.expire("metrics:tpm:window", 60)
                    pipe.execute()
                except Exception:
                    pass
            except Exception as exc:
                logger.warning("usage log write failed: %s", exc)

        threading.Thread(target=_write, daemon=True).start()

    def credit_grants_payload(self, user_id: int) -> dict:
        import time

        granted = Decimal("50")
        used = Decimal("0")
        try:
            with self._session_factory() as session:
                budget_row = session.execute(
                    text("SELECT balance_usd FROM users WHERE id = :user_id"),
                    {"user_id": user_id},
                ).one_or_none()
                if budget_row is not None:
                    granted = Decimal(str(budget_row[0] or 0))
                used_row = session.execute(
                    text(
                        """
                        SELECT COALESCE(SUM(ul.cost_usd), 0)
                        FROM usage_logs ul
                        INNER JOIN api_keys ak ON ul.api_key_id = ak.id
                        WHERE ak.user_id = :user_id
                        """
                    ),
                    {"user_id": user_id},
                ).one()
                used = Decimal(str(used_row[0] or 0))
        except Exception as exc:
            logger.warning("credit_grants query failed: %s", exc)
        available = max(Decimal("0"), granted - used)
        now = time.time()
        return {
            "object": "credit_summary",
            "total_granted": float(granted),
            "total_used": float(used),
            "total_available": float(available),
            "grants": {
                "object": "list",
                "data": [
                    {
                        "object": "credit_grant",
                        "id": "codex-pool-simulated",
                        "grant_amount": float(granted),
                        "used_amount": float(used),
                        "effective_at": now - 86400.0,
                        "expires_at": now + 86400.0 * 365,
                    }
                ],
            },
        }

    def _load_api_keys(self, session: Session) -> None:
        rows = session.execute(
            text("SELECT id, user_id, key_hash, enabled FROM api_keys")
        ).all()
        self._api_keys = {
            r[2]: ApiKeyRecord(id=r[0], user_id=r[1], key_hash=r[2], enabled=bool(r[3]))
            for r in rows
        }

    def _load_upstreams(self, session: Session) -> None:
        rows = session.execute(
            text(
                """
                SELECT user_id, name, type, base_url, api_key, auth_file, priority
                FROM upstreams WHERE enabled = 1
                ORDER BY priority ASC
                """
            )
        ).all()
        by_user: dict[int, list[Upstream]] = {}
        for r in rows:
            upstream = Upstream(
                name=r[1],
                type=r[2],
                priority=int(r[6]),
                base_url=r[3],
                api_key=r[4],
                auth_file=r[5],
            )
            by_user.setdefault(int(r[0]), []).append(upstream)
        self._upstreams_by_user = by_user

    def _load_settings(self, session: Session) -> None:
        rows = session.execute(text("SELECT setting_key, setting_value FROM settings")).all()
        settings = {r[0]: r[1] for r in rows}
        self._strategy = settings.get("strategy", "failover")
        try:
            self._billing.budget_usd = float(settings.get("billing_budget_usd", "50"))
        except ValueError:
            pass


_db_store: DbStore | None = None


def get_db_store() -> DbStore | None:
    global _db_store
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        return None
    if _db_store is None:
        _db_store = DbStore(url)
    return _db_store

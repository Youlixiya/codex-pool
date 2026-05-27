from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..domain.schemas import ModelUsageRow
from ..infrastructure.orm_models import ApiKeyORM, UsageLogORM


class UsageRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _user_scope(user_id: int):
        key_ids = select(ApiKeyORM.id).where(ApiKeyORM.user_id == user_id)
        return UsageLogORM.api_key_id.in_(key_ids)

    def today_stats(self, user_id: int) -> dict:
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        q = select(
            func.count(UsageLogORM.id),
            func.coalesce(func.sum(UsageLogORM.cost_usd), 0),
            func.coalesce(func.sum(UsageLogORM.input_tokens), 0),
            func.coalesce(func.sum(UsageLogORM.output_tokens), 0),
        ).where(UsageLogORM.created_at >= today_start, self._user_scope(user_id))
        row = self._session.execute(q).one()
        return {
            "requests": int(row[0] or 0),
            "cost_usd": Decimal(str(row[1] or 0)),
            "input_tokens": int(row[2] or 0),
            "output_tokens": int(row[3] or 0),
        }

    def total_token_stats(self, user_id: int) -> tuple[int, int]:
        q = select(
            func.coalesce(func.sum(UsageLogORM.input_tokens), 0),
            func.coalesce(func.sum(UsageLogORM.output_tokens), 0),
        ).where(self._user_scope(user_id))
        row = self._session.execute(q).one()
        return int(row[0] or 0), int(row[1] or 0)

    def total_cost(self, user_id: int) -> Decimal:
        q = select(func.coalesce(func.sum(UsageLogORM.cost_usd), 0)).where(
            self._user_scope(user_id)
        )
        row = self._session.execute(q).scalar()
        return Decimal(str(row or 0))

    def platform_breakdown(self, user_id: int, limit: int = 20) -> list[dict]:
        q = (
            select(
                UsageLogORM.upstream_name,
                func.count(UsageLogORM.id),
                func.coalesce(func.sum(UsageLogORM.input_tokens), 0),
                func.coalesce(func.sum(UsageLogORM.output_tokens), 0),
                func.coalesce(func.sum(UsageLogORM.cost_usd), 0),
            )
            .where(self._user_scope(user_id))
            .group_by(UsageLogORM.upstream_name)
            .order_by(func.sum(UsageLogORM.cost_usd).desc())
            .limit(limit)
        )
        rows = self._session.execute(q).all()
        return [
            {
                "platform": r[0] or "unknown",
                "requests": int(r[1]),
                "input_tokens": int(r[2]),
                "output_tokens": int(r[3]),
                "cost_usd": Decimal(str(r[4])),
            }
            for r in rows
        ]

    def usage_trend(self, user_id: int, *, days: int = 7) -> list[dict]:
        start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
            days=max(1, days) - 1
        )
        day_expr = func.date(UsageLogORM.created_at)
        q = (
            select(
                day_expr,
                func.count(UsageLogORM.id),
                func.coalesce(func.sum(UsageLogORM.input_tokens), 0),
                func.coalesce(func.sum(UsageLogORM.output_tokens), 0),
                func.coalesce(func.sum(UsageLogORM.cost_usd), 0),
            )
            .where(UsageLogORM.created_at >= start, self._user_scope(user_id))
            .group_by(day_expr)
            .order_by(day_expr)
        )
        rows = self._session.execute(q).all()
        by_day: dict[str, dict] = {}
        for r in rows:
            key = str(r[0])
            by_day[key] = {
                "date": key,
                "requests": int(r[1]),
                "input_tokens": int(r[2]),
                "output_tokens": int(r[3]),
                "cost_usd": Decimal(str(r[4])),
            }
        result: list[dict] = []
        for i in range(max(1, days)):
            day = (start + timedelta(days=i)).date().isoformat()
            result.append(
                by_day.get(
                    day,
                    {
                        "date": day,
                        "requests": 0,
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "cost_usd": Decimal("0"),
                    },
                )
            )
        return result

    def model_breakdown(self, user_id: int, limit: int = 20) -> list[ModelUsageRow]:
        q = (
            select(
                UsageLogORM.model,
                func.count(UsageLogORM.id),
                func.coalesce(func.sum(UsageLogORM.input_tokens), 0),
                func.coalesce(func.sum(UsageLogORM.output_tokens), 0),
                func.coalesce(func.sum(UsageLogORM.cost_usd), 0),
            )
            .where(UsageLogORM.model.isnot(None), self._user_scope(user_id))
            .group_by(UsageLogORM.model)
            .order_by(func.sum(UsageLogORM.cost_usd).desc())
            .limit(limit)
        )
        rows = self._session.execute(q).all()
        return [
            ModelUsageRow(
                model=r[0] or "unknown",
                requests=int(r[1]),
                input_tokens=int(r[2]),
                output_tokens=int(r[3]),
                cost_usd=Decimal(str(r[4])),
            )
            for r in rows
        ]


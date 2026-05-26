from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from ..domain.schemas import DashboardStats, ModelUsageRow, PlatformUsageRow, UsageTrendPoint
from ..infrastructure.redis_client import get_realtime_metrics
from ..repositories.api_key_repository import ApiKeyRepository
from ..repositories.usage_repository import UsageRepository
from ..repositories.user_repository import UserRepository


class DashboardService:
    def __init__(self, session: Session) -> None:
        self._users = UserRepository(session)
        self._keys = ApiKeyRepository(session)
        self._usage = UsageRepository(session)

    def stats(self, user_id: int) -> DashboardStats:
        user = self._users.get_by_id(user_id)
        if not user:
            raise ValueError("user not found")
        total_keys, enabled_keys = self._keys.count_stats(user_id)
        today = self._usage.today_stats(user_id)
        total_in, total_out = self._usage.total_token_stats(user_id)
        rpm, tpm = get_realtime_metrics()
        budget = user.balance_usd
        total_used = self._usage.total_cost(user_id)
        return DashboardStats(
            balance_usd=max(Decimal("0"), budget - total_used),
            api_keys_total=total_keys,
            api_keys_enabled=enabled_keys,
            today_requests=today["requests"],
            today_cost_usd=today["cost_usd"],
            today_input_tokens=today["input_tokens"],
            today_output_tokens=today["output_tokens"],
            total_input_tokens=total_in,
            total_output_tokens=total_out,
            rpm=rpm,
            tpm=tpm,
            avg_latency_ms=0.0,
        )

    def model_usage(self, user_id: int) -> list[ModelUsageRow]:
        return self._usage.model_breakdown(user_id)

    def platform_usage(self, user_id: int) -> list[PlatformUsageRow]:
        return [
            PlatformUsageRow(
                platform=r["platform"],
                requests=r["requests"],
                input_tokens=r["input_tokens"],
                output_tokens=r["output_tokens"],
                cost_usd=r["cost_usd"],
            )
            for r in self._usage.platform_breakdown(user_id)
        ]

    def usage_trend(self, user_id: int, *, days: int = 7) -> list[UsageTrendPoint]:
        return [
            UsageTrendPoint(
                date=r["date"],
                requests=r["requests"],
                input_tokens=r["input_tokens"],
                output_tokens=r["output_tokens"],
                cost_usd=r["cost_usd"],
            )
            for r in self._usage.usage_trend(user_id, days=days)
        ]

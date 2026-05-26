from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_MODEL_PRICES: dict[str, dict[str, float]] = {
    "gpt-5.5": {"input": 5.0, "cached": 0.5, "output": 30.0},
    "gpt-5.5-pro": {"input": 30.0, "cached": 0.0, "output": 180.0},
    "gpt-5.4": {"input": 2.5, "cached": 0.25, "output": 15.0},
    "gpt-5.3-codex": {"input": 1.75, "cached": 0.175, "output": 14.0},
    "gpt-5.1-codex-mini": {"input": 0.75, "cached": 0.075, "output": 4.5},
}


@dataclass
class ModelPrice:
    input_per_1m: float
    output_per_1m: float
    cached_per_1m: float


@dataclass
class BillingConfig:
    enabled: bool
    budget_usd: float
    state_path: Path
    default_price: ModelPrice
    model_prices: dict[str, ModelPrice] = field(default_factory=dict)


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _parse_float(value: str | None, default: float) -> float:
    if value is None or not str(value).strip():
        return default
    return float(value)


def load_billing_config() -> BillingConfig:
    default_price = ModelPrice(
        input_per_1m=_parse_float(os.environ.get("BILLING_DEFAULT_INPUT_PER_1M"), 5.0),
        output_per_1m=_parse_float(os.environ.get("BILLING_DEFAULT_OUTPUT_PER_1M"), 30.0),
        cached_per_1m=_parse_float(os.environ.get("BILLING_DEFAULT_CACHED_PER_1M"), 0.5),
    )

    model_prices: dict[str, ModelPrice] = {}
    for model, prices in DEFAULT_MODEL_PRICES.items():
        model_prices[model] = ModelPrice(
            input_per_1m=prices["input"],
            output_per_1m=prices["output"],
            cached_per_1m=prices.get("cached", default_price.cached_per_1m),
        )

    raw_prices = os.environ.get("BILLING_MODEL_PRICES", "").strip()
    if raw_prices:
        overrides = json.loads(raw_prices)
        if isinstance(overrides, dict):
            for model, prices in overrides.items():
                if not isinstance(prices, dict):
                    continue
                base = model_prices.get(model, default_price)
                model_prices[model] = ModelPrice(
                    input_per_1m=float(prices.get("input", base.input_per_1m)),
                    output_per_1m=float(prices.get("output", base.output_per_1m)),
                    cached_per_1m=float(
                        prices.get("cached", prices.get("cached_input", base.cached_per_1m))
                    ),
                )

    state_path = Path(
        os.environ.get("BILLING_STATE_FILE", "~/.codex-pool/usage.json")
    ).expanduser()

    return BillingConfig(
        enabled=_parse_bool(os.environ.get("BILLING_STUB_ENABLED"), False),
        budget_usd=_parse_float(os.environ.get("BILLING_BUDGET_USD"), 50.0),
        state_path=state_path,
        default_price=default_price,
        model_prices=model_prices,
    )


def _price_for(config: BillingConfig, model: str | None) -> ModelPrice:
    if model and model in config.model_prices:
        return config.model_prices[model]
    return config.default_price


def _usage_numbers(usage: dict) -> tuple[int, int, int]:
    input_tokens = int(usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0)
    cached = 0
    details = usage.get("input_tokens_details")
    if isinstance(details, dict):
        cached = int(details.get("cached_tokens") or 0)
    cached = int(usage.get("cached_input_tokens") or cached)
    return input_tokens, output_tokens, cached


def cost_usd(config: BillingConfig, model: str | None, usage: dict) -> float:
    price = _price_for(config, model)
    input_tokens, output_tokens, cached = _usage_numbers(usage)
    non_cached_input = max(0, input_tokens - cached)
    return (
        non_cached_input * price.input_per_1m
        + cached * price.cached_per_1m
        + output_tokens * price.output_per_1m
    ) / 1_000_000.0


def parse_model_from_request(body: bytes) -> str | None:
    if not body:
        return None
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None
    model = payload.get("model")
    return str(model) if model else None


def extract_usage_from_json(content: bytes) -> dict | None:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return None

    if isinstance(data, dict):
        usage = data.get("usage")
        if isinstance(usage, dict):
            return usage
        response = data.get("response")
        if isinstance(response, dict):
            usage = response.get("usage")
            if isinstance(usage, dict):
                return usage
    return None


def extract_usage_from_sse(content: bytes) -> dict | None:
    usage: dict | None = None
    text = content.decode("utf-8", errors="replace")
    for line in text.splitlines():
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if not payload or payload == "[DONE]":
            continue
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        if isinstance(event.get("usage"), dict):
            usage = event["usage"]
        response = event.get("response")
        if isinstance(response, dict) and isinstance(response.get("usage"), dict):
            usage = response["usage"]
    return usage


def is_credit_grants_path(path: str) -> bool:
    path = path.split("?", 1)[0]
    return path in (
        "/v1/dashboard/billing/credit_grants",
        "/dashboard/billing/credit_grants",
    )


def should_record_usage(path: str) -> bool:
    path = path.split("?", 1)[0]
    return path in ("/v1/responses", "/v1/responses/compact")


class UsageStore:
    def __init__(self, config: BillingConfig) -> None:
        self._config = config
        self._lock = threading.Lock()
        self._total_used_usd: float = 0.0
        self._request_count: int = 0
        self._load()

    def _load(self) -> None:
        path = self._config.state_path
        if not path.is_file():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("billing state load failed: %s", exc)
            return
        self._total_used_usd = float(data.get("total_used_usd", 0.0))
        self._request_count = int(data.get("request_count", 0))

    def _save(self) -> None:
        path = self._config.state_path
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "total_used_usd": self._total_used_usd,
            "total_granted_usd": self._config.budget_usd,
            "request_count": self._request_count,
            "updated_at": time.time(),
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def record(self, model: str | None, usage: dict) -> float:
        delta = cost_usd(self._config, model, usage)
        with self._lock:
            self._total_used_usd += delta
            self._request_count += 1
            self._save()
        logger.info(
            "billing: model=%s cost=$%.6f total_used=$%.4f",
            model or "unknown",
            delta,
            self._total_used_usd,
        )
        return delta

    def credit_grants_payload(self) -> dict:
        with self._lock:
            granted = self._config.budget_usd
            used = self._total_used_usd
        available = max(0.0, granted - used)
        now = time.time()
        return {
            "object": "credit_summary",
            "total_granted": round(granted, 6),
            "total_used": round(used, 6),
            "total_available": round(available, 6),
            "grants": {
                "object": "list",
                "data": [
                    {
                        "object": "credit_grant",
                        "id": "codex-pool-simulated",
                        "grant_amount": round(granted, 6),
                        "used_amount": round(used, 6),
                        "effective_at": now - 86400.0,
                        "expires_at": now + 86400.0 * 365,
                    }
                ],
            },
        }

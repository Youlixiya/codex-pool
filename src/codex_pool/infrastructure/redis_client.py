from __future__ import annotations

import json
from functools import lru_cache

import redis

from .settings import get_settings


@lru_cache
def get_redis() -> redis.Redis:
    return redis.Redis.from_url(get_settings().redis_url, decode_responses=True)


def incr_realtime_metrics(input_tokens: int, output_tokens: int) -> None:
    r = get_redis()
    pipe = r.pipeline()
    pipe.incr("metrics:rpm:window")
    pipe.incrby("metrics:tpm:window", input_tokens + output_tokens)
    pipe.expire("metrics:rpm:window", 60)
    pipe.expire("metrics:tpm:window", 60)
    pipe.execute()


def get_realtime_metrics() -> tuple[int, int]:
    r = get_redis()
    rpm = int(r.get("metrics:rpm:window") or 0)
    tpm = int(r.get("metrics:tpm:window") or 0)
    return rpm, tpm


def publish_config_reload() -> None:
    get_redis().publish("codex-pool:reload", json.dumps({"action": "reload"}))

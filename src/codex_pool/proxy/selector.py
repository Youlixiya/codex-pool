from __future__ import annotations

import itertools
import logging
import threading

from .config import AppConfig, Upstream

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = frozenset({401, 403, 429, 502, 503, 504})

_lock = threading.Lock()
_rr_counter = itertools.count()


class UpstreamSelector:
    def __init__(self, config: AppConfig) -> None:
        self._config = config

    def order(self) -> list[Upstream]:
        upstreams = list(self._config.upstreams)
        if self._config.strategy == "failover":
            return upstreams

        with _lock:
            start = next(_rr_counter) % len(upstreams)
        return upstreams[start:] + upstreams[:start]

    @staticmethod
    def is_retryable(status_code: int) -> bool:
        return status_code in RETRYABLE_STATUS

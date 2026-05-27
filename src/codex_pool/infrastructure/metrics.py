from __future__ import annotations

import threading
import time

_lock = threading.Lock()
_window_start = time.time()
_rpm = 0
_tpm = 0


def _maybe_reset_window(now: float) -> None:
    global _window_start, _rpm, _tpm
    if now - _window_start >= 60:
        _window_start = now
        _rpm = 0
        _tpm = 0


def incr_realtime_metrics(input_tokens: int, output_tokens: int) -> None:
    with _lock:
        now = time.time()
        _maybe_reset_window(now)
        _rpm += 1
        _tpm += input_tokens + output_tokens


def get_realtime_metrics() -> tuple[int, int]:
    with _lock:
        _maybe_reset_window(time.time())
        return _rpm, _tpm

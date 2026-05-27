from __future__ import annotations

import json
import threading
import time
from typing import Any

_lock = threading.Lock()
_sessions: dict[str, tuple[dict[str, Any], float]] = {}
_state_to_session: dict[str, tuple[str, float]] = {}


def _purge_expired(now: float) -> None:
    expired_sessions = [sid for sid, (_, exp) in _sessions.items() if exp <= now]
    for sid in expired_sessions:
        _sessions.pop(sid, None)
    expired_states = [st for st, (_, exp) in _state_to_session.items() if exp <= now]
    for st in expired_states:
        _state_to_session.pop(st, None)


def save_session(session_id: str, data: dict[str, Any], *, ttl: int) -> None:
    expires = time.time() + ttl
    with _lock:
        _purge_expired(time.time())
        _sessions[session_id] = (data, expires)


def load_session(session_id: str) -> dict[str, Any] | None:
    with _lock:
        now = time.time()
        _purge_expired(now)
        entry = _sessions.get(session_id)
        if not entry:
            return None
        data, expires = entry
        if expires <= now:
            _sessions.pop(session_id, None)
            return None
        return data


def bind_state(state: str, session_id: str, *, ttl: int) -> None:
    expires = time.time() + ttl
    with _lock:
        _purge_expired(time.time())
        _state_to_session[state] = (session_id, expires)


def session_id_for_state(state: str) -> str | None:
    with _lock:
        now = time.time()
        _purge_expired(now)
        entry = _state_to_session.get(state)
        if not entry:
            return None
        session_id, expires = entry
        if expires <= now:
            _state_to_session.pop(state, None)
            return None
        return session_id

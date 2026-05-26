from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_token_cache: dict[Path, tuple[float, str]] = {}


def verify_pool_key(authorization: str | None, expected: str) -> bool:
    if not authorization:
        return False
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        return False
    return authorization[len(prefix) :].strip() == expected


def _extract_access_token(data: object) -> str | None:
    if not isinstance(data, dict):
        return None
    for key in ("access_token", "accessToken"):
        val = data.get(key)
        if isinstance(val, str) and val:
            return val
    tokens = data.get("tokens")
    if isinstance(tokens, dict):
        for key in ("access_token", "accessToken"):
            val = tokens.get(key)
            if isinstance(val, str) and val:
                return val
    account = data.get("account")
    if isinstance(account, dict):
        return _extract_access_token(account)
    return None


def load_access_token(auth_file: Path) -> str:
    try:
        mtime = auth_file.stat().st_mtime
    except OSError as exc:
        raise RuntimeError(f"cannot read auth file {auth_file}: {exc}") from exc

    cached = _token_cache.get(auth_file)
    if cached and cached[0] == mtime:
        return cached[1]

    try:
        data = json.loads(auth_file.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RuntimeError(f"cannot read auth file {auth_file}: {exc}") from exc

    token = _extract_access_token(data)
    if not token:
        raise RuntimeError(f"no access_token in {auth_file}")

    _token_cache[auth_file] = (mtime, token)
    return token

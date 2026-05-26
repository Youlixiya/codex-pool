from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..proxy.auth import load_access_token


@dataclass(frozen=True)
class ChatgptCredentials:
    access_token: str
    account_id: str | None
    email: str | None
    plan_type: str | None


def _decode_jwt_payload(token: str) -> dict[str, Any] | None:
    parts = token.split(".")
    if len(parts) < 2:
        return None
    try:
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))
    except (json.JSONDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _auth_claims(data: dict[str, Any]) -> dict[str, Any]:
    for token_key in ("id_token", "access_token"):
        tokens = data.get("tokens")
        if isinstance(tokens, dict):
            token = tokens.get(token_key)
        else:
            token = data.get(token_key)
        if isinstance(token, str) and token:
            claims = _decode_jwt_payload(token)
            if claims:
                auth = claims.get("https://api.openai.com/auth")
                if isinstance(auth, dict):
                    return auth
    return {}


def load_chatgpt_credentials(auth_file: str | Path) -> ChatgptCredentials:
    path = Path(auth_file).expanduser().resolve()
    access_token = load_access_token(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RuntimeError(f"cannot read auth file {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"invalid auth file {path}")

    auth = _auth_claims(data)
    account_id = data.get("chatgpt_account_id") or auth.get("chatgpt_account_id")
    if isinstance(account_id, str):
        account_id = account_id.strip() or None
    else:
        account_id = None

    email = data.get("email")
    if not isinstance(email, str):
        profile = _decode_jwt_payload(
            (data.get("tokens") or {}).get("id_token", "")
            if isinstance(data.get("tokens"), dict)
            else ""
        )
        if profile:
            email = profile.get("email")
    if not isinstance(email, str):
        email = None

    plan_type = data.get("plan_type") or auth.get("chatgpt_plan_type")
    if not isinstance(plan_type, str):
        plan_type = None

    return ChatgptCredentials(
        access_token=access_token,
        account_id=account_id,
        email=email,
        plan_type=plan_type,
    )

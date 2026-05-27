from __future__ import annotations

import base64
import hashlib
import json
import logging
import re
import secrets
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
from fastapi import APIRouter, Request
from starlette.responses import HTMLResponse

from ..infrastructure.oauth_store import (
    bind_state,
    load_session,
    save_session,
    session_id_for_state,
)
from ..infrastructure.settings import get_settings

logger = logging.getLogger(__name__)

_SESSION_TTL = 600


@dataclass(frozen=True)
class OAuthSession:
    session_id: str
    authorization_url: str


@dataclass(frozen=True)
class OAuthStatus:
    status: str
    auth_file: str | None = None
    email: str | None = None
    error: str | None = None


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _generate_pkce() -> tuple[str, str]:
    verifier = _b64url(secrets.token_bytes(32))
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


def _slug(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", name.strip()).strip("-").lower()
    return slug[:64] or "upstream"


def _auth_dir() -> Path:
    path = Path(get_settings().chatgpt_auth_dir).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _load_session(session_id: str) -> dict[str, Any] | None:
    return load_session(session_id)


def _save_session(session_id: str, data: dict[str, Any]) -> None:
    save_session(session_id, data, ttl=_SESSION_TTL)


def _decode_jwt_email(id_token: str | None) -> str | None:
    if not id_token:
        return None
    parts = id_token.split(".")
    if len(parts) < 2:
        return None
    try:
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
    except (json.JSONDecodeError, ValueError):
        return None
    email = claims.get("email")
    return email if isinstance(email, str) else None


def _build_authorization_url(*, state: str, code_challenge: str) -> str:
    settings = get_settings()
    params = {
        "response_type": "code",
        "client_id": settings.chatgpt_oauth_client_id,
        "redirect_uri": settings.chatgpt_oauth_redirect_uri,
        "scope": "openid profile email offline_access",
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "state": state,
        "id_token_add_organizations": "true",
        "codex_cli_simplified_flow": "true",
    }
    return f"{settings.chatgpt_oauth_authorize_url}?{urlencode(params)}"


def _write_auth_file(path: Path, token_payload: dict[str, Any]) -> None:
    from .chatgpt_usage import enrich_auth_file_body

    access = token_payload.get("access_token")
    if not isinstance(access, str) or not access:
        raise RuntimeError("token response missing access_token")

    body = enrich_auth_file_body(token_payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, indent=2), encoding="utf-8")
    path.chmod(0o600)


def _exchange_code(code: str, code_verifier: str) -> dict[str, Any]:
    settings = get_settings()
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            settings.chatgpt_oauth_token_url,
            data={
                "grant_type": "authorization_code",
                "client_id": settings.chatgpt_oauth_client_id,
                "code": code,
                "redirect_uri": settings.chatgpt_oauth_redirect_uri,
                "code_verifier": code_verifier,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if resp.status_code >= 400:
        detail = resp.text[:500]
        raise RuntimeError(f"token exchange failed ({resp.status_code}): {detail}")
    data = resp.json()
    if not isinstance(data, dict):
        raise RuntimeError("invalid token response")
    return data


def start_oauth_session(*, user_id: int, upstream_name: str | None = None) -> OAuthSession:
    session_id = secrets.token_urlsafe(16)
    state = secrets.token_urlsafe(16)
    code_verifier, code_challenge = _generate_pkce()

    slug = _slug(upstream_name) if upstream_name else session_id[:12]
    auth_path = _auth_dir() / f"{slug}.json"

    data = {
        "user_id": user_id,
        "state": state,
        "code_verifier": code_verifier,
        "auth_path": str(auth_path.resolve()),
        "status": "pending",
        "email": None,
        "error": None,
        "created_at": time.time(),
    }
    bind_state(state, session_id, ttl=_SESSION_TTL)
    _save_session(session_id, data)

    url = _build_authorization_url(state=state, code_challenge=code_challenge)
    return OAuthSession(session_id=session_id, authorization_url=url)


def get_oauth_status(session_id: str, *, user_id: int) -> OAuthStatus | None:
    data = _load_session(session_id)
    if not data or data.get("user_id") != user_id:
        return None
    return OAuthStatus(
        status=data.get("status", "pending"),
        auth_file=data.get("auth_path") if data.get("status") == "completed" else None,
        email=data.get("email"),
        error=data.get("error"),
    )


def _complete_session(session_id: str, *, status: str, email: str | None = None, error: str | None = None) -> None:
    data = _load_session(session_id)
    if not data:
        return
    data["status"] = status
    if email:
        data["email"] = email
    if error:
        data["error"] = error
    _save_session(session_id, data)


def oauth_redirect_port() -> int:
    parsed = urlparse(get_settings().chatgpt_oauth_redirect_uri)
    if parsed.port:
        return parsed.port
    return 443 if parsed.scheme == "https" else 80


def oauth_callback_path() -> str:
    return urlparse(get_settings().chatgpt_oauth_redirect_uri).path or "/auth/callback"


def uses_integrated_oauth_callback() -> bool:
    """True when the redirect URI is served on the main admin/proxy port (e.g. SSH -L 1455:127.0.0.1:8790)."""
    return oauth_redirect_port() == get_settings().admin_listen_port


def remote_oauth_setup_hint(*, request_host: str | None = None) -> dict[str, str] | None:
    """Instructions when the admin UI is opened remotely; OAuth still redirects to loopback."""
    host = (request_host or "").strip().lower()
    if not host or host in ("localhost", "127.0.0.1", "::1"):
        return None
    port = oauth_redirect_port()
    listen = get_settings().admin_listen_port
    tunnel = f"ssh -L {port}:127.0.0.1:{listen} user@your-server"
    return {
        "message": (
            "远程访问时，浏览器授权后会跳转到您本机的 localhost，"
            f"需先将本机 {port} 端口转发到服务器上的服务端口 {listen}。"
        ),
        "ssh_tunnel_command": tunnel,
        "redirect_uri": get_settings().chatgpt_oauth_redirect_uri,
    }


def _handle_oauth_callback(query: dict[str, list[str]]) -> None:
    state_list = query.get("state", [])
    code_list = query.get("code", [])
    error_list = query.get("error", [])

    if error_list:
        err = error_list[0]
        desc = (query.get("error_description") or [""])[0]
        logger.warning("oauth callback error: %s %s", err, desc)
        if state_list:
            sid = session_id_for_state(state_list[0])
            if sid:
                _complete_session(sid, status="failed", error=desc or err)
        return

    if not state_list or not code_list:
        logger.warning("oauth callback missing state or code")
        return

    state = state_list[0]
    code = code_list[0]

    session_id = session_id_for_state(state)
    if not session_id:
        logger.warning("oauth callback unknown state")
        return

    data = _load_session(session_id)
    if not data or data.get("state") != state:
        logger.warning("oauth callback session mismatch")
        return

    if data.get("status") != "pending":
        return

    try:
        token_payload = _exchange_code(code, data["code_verifier"])
        auth_path = Path(data["auth_path"])
        _write_auth_file(auth_path, token_payload)
        email = _decode_jwt_email(token_payload.get("id_token") if isinstance(token_payload.get("id_token"), str) else None)
        _complete_session(session_id, status="completed", email=email)
        logger.info("chatgpt oauth completed for session %s -> %s", session_id, auth_path)
    except Exception as exc:
        logger.exception("oauth token exchange failed")
        _complete_session(session_id, status="failed", error=str(exc))


_CALLBACK_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>授权完成</title>
  <style>
    body { font-family: system-ui, sans-serif; display: flex; align-items: center;
           justify-content: center; min-height: 100vh; margin: 0; background: #f5f7fa; }
    .card { background: #fff; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 24px rgba(0,0,0,.08);
            text-align: center; max-width: 360px; }
    h1 { font-size: 1.25rem; margin: 0 0 .5rem; color: #1a1a1a; }
    p { color: #666; margin: 0; }
  </style>
</head>
<body>
  <div class="card">
    <h1>授权成功</h1>
    <p>可以关闭此窗口，返回管理后台。</p>
  </div>
  <script>
    if (window.opener) {
      window.opener.postMessage({ type: "codex-pool-oauth-done" }, "*");
    }
    setTimeout(function() { window.close(); }, 1500);
  </script>
</body>
</html>
"""

_ERROR_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8" /><title>授权失败</title></head>
<body><p>授权失败，请关闭窗口后重试。</p></body>
</html>
"""


def _oauth_callback_response(query: dict[str, list[str]]) -> HTMLResponse:
    if query.get("error"):
        return HTMLResponse(_ERROR_HTML, status_code=400)
    _handle_oauth_callback(query)
    return HTMLResponse(_CALLBACK_HTML)


def register_oauth_callback_routes(router: APIRouter) -> None:
    path = oauth_callback_path()

    @router.get(path, response_class=HTMLResponse, include_in_schema=False)
    async def oauth_callback(request: Request) -> HTMLResponse:
        query = {k: request.query_params.getlist(k) for k in request.query_params}
        return _oauth_callback_response(query)


class _OAuthCallbackHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        logger.debug("oauth callback: " + format, *args)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        expected_path = oauth_callback_path()

        if parsed.path != expected_path:
            self.send_response(404)
            self.end_headers()
            return

        query = parse_qs(parsed.query)
        if query.get("error"):
            body = _ERROR_HTML.encode("utf-8")
            self.send_response(400)
        else:
            _handle_oauth_callback(query)
            body = _CALLBACK_HTML.encode("utf-8")
            self.send_response(200)

        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


_callback_server: HTTPServer | None = None
_callback_thread: threading.Thread | None = None
_server_lock = threading.Lock()


def ensure_callback_server() -> None:
    """Start loopback callback server when redirect URI port differs from the main app port."""
    if uses_integrated_oauth_callback():
        return

    global _callback_server, _callback_thread
    with _server_lock:
        if _callback_thread is not None and _callback_thread.is_alive():
            return

        settings = get_settings()
        host, port = "127.0.0.1", oauth_redirect_port()

        def run() -> None:
            global _callback_server
            try:
                _callback_server = HTTPServer((host, port), _OAuthCallbackHandler)
                logger.info("chatgpt oauth callback listening on http://%s:%s", host, port)
                _callback_server.serve_forever()
            except OSError as exc:
                logger.error("cannot start oauth callback server on port %s: %s", port, exc)

        _callback_thread = threading.Thread(target=run, name="chatgpt-oauth-callback", daemon=True)
        _callback_thread.start()


def stop_callback_server() -> None:
    global _callback_server, _callback_thread
    with _server_lock:
        if _callback_server is not None:
            _callback_server.shutdown()
            _callback_server = None
        _callback_thread = None

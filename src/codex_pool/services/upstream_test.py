from __future__ import annotations

import time
from urllib.parse import urlparse

import httpx

from ..infrastructure.settings import get_settings
from ..infrastructure.http_client import build_client


def _loopback_test_base_url(base_url: str, *, public_base_url: str | None = None) -> str:
    """When Base URL points at this pool's public URL, probe via 127.0.0.1 (avoids NAT hairpin on VPS)."""
    settings = get_settings()
    public = (public_base_url or settings.public_base_url or "").strip().rstrip("/")
    if not public:
        return base_url

    base = urlparse(base_url.strip())
    pub = urlparse(public)
    if not base.hostname or not pub.hostname:
        return base_url

    hosts_match = base.hostname.lower() == pub.hostname.lower()
    if not hosts_match and base.hostname in ("127.0.0.1", "localhost"):
        return base_url

    if not hosts_match:
        return base_url

    port = settings.admin_listen_port
    path = base.path or "/v1"
    if not path.startswith("/"):
        path = f"/{path}"
    return f"http://127.0.0.1:{port}{path.rstrip('/')}"


def test_openai_upstream(
    *,
    base_url: str,
    api_key: str,
    public_base_url: str | None = None,
) -> dict:
    """Probe an OpenAI-compatible upstream via GET /models."""
    effective = _loopback_test_base_url(base_url, public_base_url=public_base_url)
    url = effective.rstrip("/") + "/models"
    started = time.perf_counter()
    try:
        with build_client(timeout=15.0, follow_redirects=True) as client:
            resp = client.get(url, headers={"Authorization": f"Bearer {api_key}"})
    except httpx.TimeoutException:
        return {"ok": False, "message": "连接超时，请检查 Base URL 或网络", "latency_ms": None}
    except httpx.RequestError as exc:
        return {
            "ok": False,
            "message": f"无法连接：{exc}",
            "latency_ms": None,
        }

    latency_ms = int((time.perf_counter() - started) * 1000)
    if resp.status_code == 200:
        msg = f"连接成功（{latency_ms} ms）"
        if effective.rstrip("/") != base_url.strip().rstrip("/"):
            msg += "（经本机回环地址探测）"
        return {"ok": True, "message": msg, "latency_ms": latency_ms}
    if resp.status_code in (401, 403):
        return {"ok": False, "message": "API Key 无效或无权访问", "latency_ms": latency_ms}
    if resp.status_code == 404:
        return {
            "ok": False,
            "message": "端点不存在，请确认 Base URL 是否以 /v1 结尾",
            "latency_ms": latency_ms,
        }
    detail = resp.text.strip()[:200] if resp.text else ""
    suffix = f"：{detail}" if detail else ""
    return {
        "ok": False,
        "message": f"上游返回 HTTP {resp.status_code}{suffix}",
        "latency_ms": latency_ms,
    }

from __future__ import annotations

import time

import httpx


def test_openai_upstream(*, base_url: str, api_key: str) -> dict:
    """Probe an OpenAI-compatible upstream via GET /models."""
    url = base_url.rstrip("/") + "/models"
    started = time.perf_counter()
    try:
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
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
        return {"ok": True, "message": f"连接成功（{latency_ms} ms）", "latency_ms": latency_ms}
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

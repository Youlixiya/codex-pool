from __future__ import annotations

from .auth import load_access_token
from .config import Upstream, auth_file_path

CHATGPT_BASE = "https://chatgpt.com/backend-api/codex"

SKIP_REQUEST_HEADERS = frozenset(
    {
        "host",
        "authorization",
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
        "content-length",
    }
)

SKIP_RESPONSE_HEADERS = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
        "content-length",
        "content-encoding",
    }
)


def target_url(upstream: Upstream, path: str) -> str:
    suffix = path.removeprefix("/v1")
    if upstream.type == "openai":
        if not upstream.base_url:
            raise ValueError(f"upstream {upstream.name} missing base_url")
        return upstream.base_url.rstrip("/") + suffix
    return CHATGPT_BASE + suffix


def upstream_authorization(upstream: Upstream) -> str:
    if upstream.type == "openai":
        if not upstream.api_key:
            raise ValueError(f"upstream {upstream.name} missing api_key")
        return f"Bearer {upstream.api_key}"
    token = load_access_token(auth_file_path(upstream))
    return f"Bearer {token}"


def filter_request_headers(headers: list[tuple[bytes, bytes]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key_b, val_b in headers:
        key = key_b.decode("latin-1").lower()
        if key in SKIP_REQUEST_HEADERS:
            continue
        out[key] = val_b.decode("latin-1")
    return out


def filter_response_headers(headers) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, val in headers.items():
        if key.lower() in SKIP_RESPONSE_HEADERS:
            continue
        out[key] = val
    return out


def stream_media_type(headers) -> str:
    content_type = headers.get("content-type", "")
    if content_type:
        return content_type.split(";")[0].strip()
    return "text/event-stream"

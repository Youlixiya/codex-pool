from __future__ import annotations

import asyncio
import json
import logging

import httpx
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse

from ..infrastructure.http_client import build_async_client
from ..infrastructure.settings import get_settings
from .billing import (
    extract_usage_from_json,
    extract_usage_from_sse,
    parse_model_from_request,
    should_record_usage,
)
from .config import AppConfig
from .runtime_store import DbStore
from .selector import UpstreamSelector
from .upstream import (
    filter_request_headers,
    filter_response_headers,
    stream_media_type,
    target_url,
    upstream_authorization,
)

logger = logging.getLogger(__name__)

TIMEOUT = httpx.Timeout(connect=30.0, read=600.0, write=120.0, pool=30.0)

_TRANSIENT_MSG = (
    "disconnected",
    "connection reset",
    "connection refused",
    "broken pipe",
    "eof occurred",
    "timed out",
    "timeout",
    "incomplete read",
    "server closed",
)


def is_transient_upstream_error(exc: BaseException) -> bool:
    if isinstance(
        exc,
        (
            httpx.RemoteProtocolError,
            httpx.ConnectError,
            httpx.ReadError,
            httpx.WriteError,
            httpx.PoolTimeout,
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
        ),
    ):
        return True
    if isinstance(exc, httpx.HTTPError):
        msg = str(exc).lower()
        return any(needle in msg for needle in _TRANSIENT_MSG)
    return False


def is_streaming_body(body: bytes) -> bool:
    if not body:
        return False
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return False
    return bool(payload.get("stream"))


def _build_client() -> httpx.AsyncClient:
    settings = get_settings()
    limits = (
        httpx.Limits(max_keepalive_connections=0, max_connections=100)
        if settings.proxy_upstream_disable_keepalive
        else httpx.Limits(max_keepalive_connections=20, max_connections=100, keepalive_expiry=30.0)
    )
    return build_async_client(
        timeout=TIMEOUT,
        follow_redirects=True,
        http2=False,
        limits=limits,
    )


async def _send_upstream(
    client: httpx.AsyncClient,
    *,
    upstream_name: str,
    method: str,
    url: str,
    headers: dict[str, str],
    body: bytes | None,
    stream: bool,
) -> httpx.Response:
    settings = get_settings()
    max_attempts = max(1, settings.proxy_upstream_max_retries)
    backoff = max(0.0, settings.proxy_upstream_retry_backoff_seconds)
    last_exc: httpx.HTTPError | None = None

    for attempt in range(max_attempts):
        try:
            req = client.build_request(
                method,
                url,
                headers=headers,
                content=body if body else None,
            )
            return await client.send(req, stream=stream)
        except httpx.HTTPError as exc:
            last_exc = exc
            if attempt + 1 >= max_attempts or not is_transient_upstream_error(exc):
                raise
            delay = backoff * (2**attempt)
            logger.warning(
                "%s: %s (retry %d/%d in %.1fs)",
                upstream_name,
                exc,
                attempt + 1,
                max_attempts,
                delay,
            )
            await asyncio.sleep(delay)

    assert last_exc is not None
    raise last_exc


async def forward_request(
    request: Request,
    config: AppConfig,
    *,
    db_store: DbStore,
    raw_api_key: str | None = None,
) -> Response:
    body = await request.body()
    stream = is_streaming_body(body)
    selector = UpstreamSelector(config)
    path = request.url.path
    if request.url.query:
        path = f"{path}?{request.url.query}"
    errors: list[str] = []
    record_usage = should_record_usage(request.url.path)
    model = parse_model_from_request(body) if record_usage else None

    client = _build_client()
    try:
        for upstream in selector.order():
            url = target_url(upstream, path)
            try:
                auth = upstream_authorization(upstream)
            except (RuntimeError, ValueError) as exc:
                msg = f"{upstream.name}: {exc}"
                logger.warning(msg)
                errors.append(msg)
                continue

            headers = filter_request_headers(request.scope["headers"])
            headers["authorization"] = auth

            try:
                resp = await _send_upstream(
                    client,
                    upstream_name=upstream.name,
                    method=request.method,
                    url=url,
                    headers=headers,
                    body=body if body else None,
                    stream=stream,
                )
            except httpx.HTTPError as exc:
                msg = f"{upstream.name}: {exc}"
                logger.warning(msg)
                errors.append(msg)
                continue

            if selector.is_retryable(resp.status_code):
                detail = await _peek_error(resp)
                msg = f"{upstream.name}: HTTP {resp.status_code} {detail}"
                logger.warning(msg)
                errors.append(msg)
                await resp.aclose()
                continue

            if stream:
                return StreamingResponse(
                    _stream_chunks(
                        resp,
                        client,
                        model,
                        record_usage and resp.status_code == 200,
                        db_store=db_store,
                        raw_api_key=raw_api_key,
                        upstream_name=upstream.name,
                        path=request.url.path,
                        status_code=resp.status_code,
                    ),
                    status_code=resp.status_code,
                    headers=filter_response_headers(resp.headers),
                    media_type=stream_media_type(resp.headers),
                )

            try:
                content = await resp.aread()
            finally:
                await resp.aclose()

            if resp.status_code == 200:
                usage = extract_usage_from_json(content)
                if usage:
                    db_store.log_usage(
                        raw_key=raw_api_key,
                        upstream_name=upstream.name,
                        model=model,
                        usage=usage,
                        status_code=resp.status_code,
                        path=request.url.path,
                    )
                elif record_usage:
                    logger.debug("billing: no usage in non-stream response")

            await client.aclose()
            return Response(
                content=content,
                status_code=resp.status_code,
                headers=filter_response_headers(resp.headers),
                media_type=resp.headers.get("content-type"),
            )
    except Exception:
        await client.aclose()
        raise

    await client.aclose()
    return JSONResponse(
        {"error": "all upstreams failed", "details": errors},
        status_code=503,
    )


async def _peek_error(resp: httpx.Response) -> str:
    try:
        text = (await resp.aread())[:500]
        return text.decode("utf-8", errors="replace")
    except Exception:
        return ""


async def _stream_chunks(
    resp: httpx.Response,
    client: httpx.AsyncClient,
    model: str | None,
    record: bool,
    *,
    db_store: DbStore,
    raw_api_key: str | None = None,
    upstream_name: str = "",
    path: str = "",
    status_code: int = 200,
):
    buffer = bytearray()
    try:
        async for chunk in resp.aiter_bytes():
            if record:
                buffer.extend(chunk)
            yield chunk
    except httpx.HTTPError as exc:
        logger.warning(
            "%s: upstream stream read error: %s (received %d bytes)",
            upstream_name,
            exc,
            len(buffer),
        )
    finally:
        try:
            await resp.aclose()
        finally:
            await client.aclose()
        if record and buffer:
            usage = extract_usage_from_sse(bytes(buffer))
            if usage:
                db_store.log_usage(
                    raw_key=raw_api_key,
                    upstream_name=upstream_name,
                    model=model,
                    usage=usage,
                    status_code=status_code,
                    path=path,
                )
            else:
                logger.debug("billing: no usage in stream response")

from __future__ import annotations

import json
import logging

import httpx
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse

from .billing import (
    UsageStore,
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


def is_streaming_body(body: bytes) -> bool:
    if not body:
        return False
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return False
    return bool(payload.get("stream"))


def _build_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=TIMEOUT,
        follow_redirects=True,
        http2=False,
    )


async def forward_request(
    request: Request,
    config: AppConfig,
    usage_store: UsageStore | None = None,
    *,
    db_store: DbStore | None = None,
    raw_api_key: str | None = None,
) -> Response:
    body = await request.body()
    stream = is_streaming_body(body)
    selector = UpstreamSelector(config)
    path = request.url.path
    if request.url.query:
        path = f"{path}?{request.url.query}"
    errors: list[str] = []
    record_usage = (usage_store is not None or db_store is not None) and should_record_usage(
        request.url.path
    )
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
                req = client.build_request(
                    request.method,
                    url,
                    headers=headers,
                    content=body if body else None,
                )
                resp = await client.send(req, stream=stream)
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
                # Client must stay open until StreamingResponse finishes consuming resp.
                return StreamingResponse(
                    _stream_chunks(
                        resp,
                        client,
                        usage_store,
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
                    if usage_store is not None:
                        usage_store.record(model, usage)
                    if db_store is not None:
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
    usage_store: UsageStore | None,
    model: str | None,
    record: bool,
    *,
    db_store: DbStore | None = None,
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
        logger.warning("upstream stream read error: %s", exc)
    finally:
        try:
            await resp.aclose()
        finally:
            await client.aclose()
        if record and buffer:
            usage = extract_usage_from_sse(bytes(buffer))
            if usage:
                if usage_store is not None:
                    usage_store.record(model, usage)
                if db_store is not None:
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

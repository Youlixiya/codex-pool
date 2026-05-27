from __future__ import annotations

import logging

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, Response
from starlette.routing import Route

from .forward import forward_request
from .runtime_store import DbStore

logger = logging.getLogger(__name__)

_PROXY_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


async def healthz(_: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


def _extract_bearer(request: Request) -> str | None:
    auth = request.headers.get("authorization")
    if not auth or not auth.startswith("Bearer "):
        return None
    return auth[7:].strip()


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",", 1)[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    if request.client:
        return request.client.host
    return "unknown"


def _key_hint(raw: str) -> str:
    if not raw:
        return ""
    if raw.startswith("sk-cp-"):
        return raw[:12] + "..."
    # Avoid logging secrets; only a short hash prefix.
    import hashlib

    return "sha256:" + hashlib.sha256(raw.encode()).hexdigest()[:10]


def _check_auth(request: Request) -> JSONResponse | None:
    auth = request.headers.get("authorization") or ""
    raw = _extract_bearer(request)
    if not raw:
        reason = "missing_authorization" if not auth else "non_bearer_authorization"
        logger.info(
            "proxy unauthorized (%s) ip=%s method=%s path=%s",
            reason,
            _client_ip(request),
            request.method,
            request.url.path,
        )
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    db_store: DbStore = request.app.state.db_store
    record = db_store.lookup_api_key(raw)
    if not record:
        logger.info(
            "proxy unauthorized (unknown_key) ip=%s method=%s path=%s key=%s",
            _client_ip(request),
            request.method,
            request.url.path,
            _key_hint(raw),
        )
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    request.state.api_key = raw
    request.state.api_key_record = record
    return None


async def billing_credit_grants(request: Request) -> Response:
    denied = _check_auth(request)
    if denied is not None:
        return denied
    db_store: DbStore = request.app.state.db_store
    record = request.state.api_key_record
    return JSONResponse(db_store.credit_grants_payload(record.user_id))


async def proxy_handler(request: Request) -> Response:
    denied = _check_auth(request)
    if denied is not None:
        return denied
    db_store: DbStore = request.app.state.db_store
    record = request.state.api_key_record
    config = db_store.config_for_user(record.user_id)
    return await forward_request(
        request,
        config,
        db_store=db_store,
        raw_api_key=request.state.api_key,
    )


def create_app(*, db_store: DbStore) -> Starlette:
    routes: list[Route] = [
        Route("/healthz", healthz, methods=["GET"]),
        Route(
            "/v1/dashboard/billing/credit_grants",
            billing_credit_grants,
            methods=["GET"],
        ),
        Route(
            "/dashboard/billing/credit_grants",
            billing_credit_grants,
            methods=["GET"],
        ),
        Route("/{full_path:path}", proxy_handler, methods=_PROXY_METHODS),
    ]
    app = Starlette(routes=routes)
    app.state.db_store = db_store
    return app

from __future__ import annotations

import logging

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, Response
from starlette.routing import Route

from .auth import verify_pool_key
from .billing import UsageStore, load_billing_config
from .config import AppConfig
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


def _check_auth(request: Request) -> JSONResponse | None:
    raw = _extract_bearer(request)
    if not raw:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    db_store: DbStore | None = request.app.state.db_store
    if db_store is not None:
        record = db_store.lookup_api_key(raw)
        if not record:
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        request.state.api_key = raw
        request.state.api_key_record = record
        return None

    config: AppConfig = request.app.state.config
    if not verify_pool_key(request.headers.get("authorization"), config.pool_api_key):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    request.state.api_key = raw
    return None


async def billing_credit_grants(request: Request) -> Response:
    denied = _check_auth(request)
    if denied is not None:
        return denied
    db_store: DbStore | None = request.app.state.db_store
    if db_store is not None:
        record = getattr(request.state, "api_key_record", None)
        if record is None:
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return JSONResponse(db_store.credit_grants_payload(record.user_id))
    store: UsageStore = request.app.state.usage_store
    return JSONResponse(store.credit_grants_payload())


async def proxy_handler(request: Request) -> Response:
    denied = _check_auth(request)
    if denied is not None:
        return denied
    usage_store: UsageStore | None = request.app.state.usage_store
    db_store: DbStore | None = request.app.state.db_store
    raw_key = getattr(request.state, "api_key", None)
    if db_store is not None:
        record = getattr(request.state, "api_key_record", None)
        if record is None:
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        config = db_store.config_for_user(record.user_id)
    else:
        config = request.app.state.config
    return await forward_request(
        request,
        config,
        usage_store,
        db_store=db_store,
        raw_api_key=raw_key,
    )


def create_app(
    config: AppConfig,
    *,
    db_store: DbStore | None = None,
) -> Starlette:
    billing = load_billing_config()
    usage_store: UsageStore | None = None
    if db_store is None and billing.enabled:
        usage_store = UsageStore(billing)
        logger.info(
            "billing simulation enabled: budget=$%.2f state=%s",
            billing.budget_usd,
            billing.state_path,
        )

    routes: list[Route] = [Route("/healthz", healthz, methods=["GET"])]
    if usage_store is not None or db_store is not None:
        routes.extend(
            [
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
            ]
        )
    routes.append(Route("/{full_path:path}", proxy_handler, methods=_PROXY_METHODS))
    app = Starlette(routes=routes)
    app.state.config = config
    app.state.usage_store = usage_store
    app.state.db_store = db_store
    return app

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import ASGIApp, Receive, Scope, Send

from .api.controllers import (
    api_key_controller,
    auth_controller,
    dashboard_controller,
    upstream_controller,
    upstream_oauth_controller,
)
from .services.chatgpt_oauth import (
    ensure_callback_server,
    oauth_callback_path,
    register_oauth_callback_routes,
    stop_callback_server,
)
from .infrastructure.database import get_engine, init_db, session_scope
from .infrastructure.schema_migrations import ensure_user_profile_schema
from .infrastructure.settings import get_settings
from .proxy.bootstrap import build_proxy_app
from .services.auth_service import AuthService

logger = logging.getLogger(__name__)

_ADMIN_PREFIX = "/api/v1"
_PROXY_PREFIXES = ("/v1", "/dashboard")
_ADMIN_PATHS = {"/healthz", "/docs", "/openapi.json", "/redoc"}


def _web_dist_dir() -> Path | None:
    env = os.environ.get("WEB_DIST", "").strip()
    candidates: list[Path] = []
    if env:
        candidates.append(Path(env).expanduser())
    repo_root = Path(__file__).resolve().parents[2]
    candidates.append(repo_root / "web" / "dist")
    for path in candidates:
        if (path / "index.html").is_file():
            return path
    return None


def _is_proxy_path(path: str) -> bool:
    return path.startswith(_PROXY_PREFIXES)


def _is_admin_path(path: str) -> bool:
    if path == oauth_callback_path():
        return True
    return path.startswith(_ADMIN_PREFIX) or path in _ADMIN_PATHS or path.startswith("/docs/")


def _looks_like_asset_path(path: str) -> bool:
    """Paths with a file extension are static assets, not Vue router paths."""
    segment = path.rstrip("/").rsplit("/", 1)[-1]
    return "." in segment and not segment.startswith(".")


class SPAStaticFiles(StaticFiles):
    """Serve built Vue assets; unknown paths without extensions fall back to index.html."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            if exc.status_code != 404 or _looks_like_asset_path(path):
                raise
            return await super().get_response("index.html", scope)


def _create_admin_api() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Codex Pool", version="0.1.0")
    origins = settings.resolved_cors_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth_controller.router, prefix=_ADMIN_PREFIX)
    app.include_router(dashboard_controller.router, prefix=_ADMIN_PREFIX)
    app.include_router(api_key_controller.router, prefix=_ADMIN_PREFIX)
    app.include_router(upstream_controller.router, prefix=_ADMIN_PREFIX)
    app.include_router(upstream_oauth_controller.router, prefix=_ADMIN_PREFIX)
    oauth_router = APIRouter()
    register_oauth_callback_routes(oauth_router)
    app.include_router(oauth_router)

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    return app


class CombinedASGI:
    """Single-port ASGI: admin API, Codex proxy, optional web UI static files."""

    def __init__(
        self,
        *,
        enable_proxy: bool = True,
        web_dist: Path | None = None,
    ) -> None:
        self.enable_proxy = enable_proxy
        self.web_dist = web_dist
        self.admin = _create_admin_api()
        self._proxy: ASGIApp | None = None
        self._static: ASGIApp | None = None
        if web_dist is not None:
            self._static = SPAStaticFiles(directory=web_dist, html=True)
        self._lifespan_stack: Any = None

    @asynccontextmanager
    async def _lifespan(self):
        init_db()
        ensure_user_profile_schema(get_engine())
        with session_scope() as session:
            AuthService(session).ensure_admin()
        if self.enable_proxy:
            self._proxy = build_proxy_app()
            config = self._proxy.state.db_store.reload()
            logger.info(
                "codex proxy ready (%d upstreams, strategy=%s)",
                len(config.upstreams) if config else 0,
                config.strategy if config else "failover",
            )
        if self.web_dist is not None:
            logger.info("serving web UI from %s", self.web_dist)
        ensure_callback_server()
        async with self.admin.router.lifespan_context(self.admin):
            yield
        stop_callback_server()

    async def _handle_lifespan(self, scope: Scope, receive: Receive, send: Send) -> None:
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                try:
                    self._lifespan_stack = self._lifespan()
                    await self._lifespan_stack.__aenter__()
                except Exception as exc:
                    await send({"type": "lifespan.startup.failed", "message": str(exc)})
                    return
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                if self._lifespan_stack is not None:
                    await self._lifespan_stack.__aexit__(None, None, None)
                await send({"type": "lifespan.shutdown.complete"})
                return

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            await self._handle_lifespan(scope, receive, send)
            return
        if scope["type"] != "http":
            await self.admin(scope, receive, send)
            return

        path = scope.get("path", "")
        if _is_admin_path(path):
            await self.admin(scope, receive, send)
            return
        if self.enable_proxy and _is_proxy_path(path):
            if self._proxy is None:
                raise RuntimeError("proxy not initialized")
            await self._proxy(scope, receive, send)
            return
        if self._static is not None:
            await self._static(scope, receive, send)
            return
        await self.admin(scope, receive, send)


def create_combined_app(*, enable_proxy: bool = True) -> CombinedASGI:
    web_dist = _web_dist_dir()
    return CombinedASGI(enable_proxy=enable_proxy, web_dist=web_dist)

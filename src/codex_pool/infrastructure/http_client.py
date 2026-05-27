from __future__ import annotations

import os
from typing import Any

import httpx


def _proxy_config() -> dict[str, str] | None:
    """
    Only honor HTTP(S) proxy variables explicitly.

    We intentionally ignore ALL_PROXY to avoid accidentally enabling SOCKS proxies,
    which requires optional dependencies (e.g. socksio) and is not desired here.
    """

    http_proxy = (os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy") or "").strip()
    https_proxy = (os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or "").strip()

    proxies: dict[str, str] = {}
    if http_proxy:
        proxies["http://"] = http_proxy
    if https_proxy:
        proxies["https://"] = https_proxy

    return proxies or None


def build_client(**kwargs: Any) -> httpx.Client:
    proxies = _proxy_config()
    base_kwargs: dict[str, Any] = {"trust_env": False, **kwargs}

    if not proxies:
        return httpx.Client(**base_kwargs)

    # httpx versions differ: some accept `proxies=`, others only accept `proxy=`.
    try:
        return httpx.Client(**base_kwargs, proxies=proxies)
    except TypeError:
        # Best-effort fallback: if only a single proxy is supported, use HTTPS proxy
        # when available, else HTTP proxy.
        single = proxies.get("https://") or proxies.get("http://")
        if not single:
            return httpx.Client(**base_kwargs)
        return httpx.Client(**base_kwargs, proxy=single)


def build_async_client(**kwargs: Any) -> httpx.AsyncClient:
    proxies = _proxy_config()
    base_kwargs: dict[str, Any] = {"trust_env": False, **kwargs}

    if not proxies:
        return httpx.AsyncClient(**base_kwargs)

    try:
        return httpx.AsyncClient(**base_kwargs, proxies=proxies)
    except TypeError:
        single = proxies.get("https://") or proxies.get("http://")
        if not single:
            return httpx.AsyncClient(**base_kwargs)
        return httpx.AsyncClient(**base_kwargs, proxy=single)


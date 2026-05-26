from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

Strategy = Literal["failover", "round_robin"]
UpstreamType = Literal["openai", "chatgpt"]


@dataclass
class Upstream:
    name: str
    type: UpstreamType
    priority: int = 100
    base_url: str | None = None
    api_key: str | None = None
    auth_file: str | None = None


@dataclass
class AppConfig:
    pool_api_key: str
    strategy: Strategy
    upstreams: list[Upstream] = field(default_factory=list)


def _expand(path: str) -> Path:
    return Path(path).expanduser().resolve()


def auth_file_path(upstream: Upstream) -> Path:
    if not upstream.auth_file:
        raise ValueError(f"upstream {upstream.name} missing auth_file")
    return _expand(upstream.auth_file)

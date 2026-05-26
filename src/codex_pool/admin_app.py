from __future__ import annotations

import os

from .combined_asgi import create_combined_app

app = create_combined_app(enable_proxy=os.environ.get("CODEX_POOL_NO_PROXY") != "1")

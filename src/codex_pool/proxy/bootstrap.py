from __future__ import annotations

import logging
import sys

from .app import create_app
from .reload import start_config_reload_listener
from .runtime_store import get_db_store

logger = logging.getLogger(__name__)


def build_proxy_app():
    db_store = get_db_store()
    if db_store is None:
        print("DATABASE_URL is required to run the Codex proxy", file=sys.stderr)
        sys.exit(1)
    config = db_store.reload()
    if not config:
        print("failed to load proxy config from database", file=sys.stderr)
        sys.exit(1)
    app = create_app(config, db_store=db_store)
    start_config_reload_listener(app, db_store)
    return app

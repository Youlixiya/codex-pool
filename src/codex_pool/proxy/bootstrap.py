from __future__ import annotations

import logging
import sys

from .app import create_app
from .runtime_store import get_db_store

logger = logging.getLogger(__name__)


def build_proxy_app():
    db_store = get_db_store()
    config = db_store.reload()
    if not config:
        print("failed to load proxy config from database", file=sys.stderr)
        sys.exit(1)
    return create_app(db_store=db_store)

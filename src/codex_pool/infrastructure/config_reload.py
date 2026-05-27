from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def publish_config_reload() -> None:
    """Reload in-memory proxy cache after admin changes API keys or upstreams."""
    from ..proxy.runtime_store import get_db_store

    config = get_db_store().reload()
    if config is None:
        logger.warning("proxy config reload failed")
        return
    logger.debug("proxy config reloaded from database")

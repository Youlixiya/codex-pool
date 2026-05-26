from __future__ import annotations

import json
import logging
import os
import threading

logger = logging.getLogger(__name__)


def start_config_reload_listener(app, db_store) -> None:
    redis_url = os.environ.get("REDIS_URL", "").strip()
    if not redis_url:
        return

    def _listen():
        try:
            import redis

            client = redis.Redis.from_url(redis_url, decode_responses=True)
            pubsub = client.pubsub()
            pubsub.subscribe("codex-pool:reload")
            for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                config = db_store.reload()
                if config:
                    app.state.config = config
                    logger.info("config reloaded from database")
        except Exception as exc:
            logger.warning("reload listener stopped: %s", exc)

    threading.Thread(target=_listen, daemon=True).start()
    logger.info("listening for config reload on codex-pool:reload")

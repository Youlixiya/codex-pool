from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Codex Pool — admin UI, API, and Codex CLI proxy on one port",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to .env (default: .env in current directory)",
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8790)
    parser.add_argument("--reload", action="store_true")
    parser.add_argument("--log-level", default="info")
    parser.add_argument(
        "--no-proxy",
        action="store_true",
        help="Disable Codex proxy (admin API / UI only)",
    )
    args = parser.parse_args()
    env_path = Path(args.env_file)
    if env_path.is_file():
        load_dotenv(env_path)

    if args.no_proxy:
        os.environ["CODEX_POOL_NO_PROXY"] = "1"
    else:
        os.environ.pop("CODEX_POOL_NO_PROXY", None)

    os.environ["ADMIN_LISTEN_PORT"] = str(args.port)

    uvicorn.run(
        "codex_pool.admin_app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()

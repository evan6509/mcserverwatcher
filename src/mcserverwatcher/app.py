"""Flask application for Minecraft Server Watcher."""

from __future__ import annotations

import argparse
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template

from .config import AppConfig, ConfigurationError, ServerConfig, load_config
from .monitor import MinecraftMonitor


def _default_config_path() -> Path:
    return Path(os.environ.get("MCSW_CONFIG", "servers.json"))


def create_app(
    config_path: str | Path | None = None,
    *,
    monitor: MinecraftMonitor | None = None,
) -> Flask:
    """Create and configure the Flask application."""

    app_config = load_config(config_path or _default_config_path())
    status_monitor = monitor or MinecraftMonitor(app_config.request_timeout_seconds)

    app = Flask(__name__)
    app.config["MCSW_SETTINGS"] = app_config
    app.config["MCSW_MONITOR"] = status_monitor

    @app.get("/")
    def index() -> str:
        return render_template(
            "index.html",
            refresh_seconds=app_config.refresh_seconds,
        )

    @app.get("/api/health")
    def health() -> Any:
        return jsonify({"ok": True})

    @app.get("/api/servers")
    def all_servers() -> Any:
        servers = app_config.servers
        workers = min(8, len(servers))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            snapshots = list(pool.map(status_monitor.check, servers))
        return jsonify({"servers": snapshots})

    @app.get("/api/servers/<server_id>")
    def one_server(server_id: str) -> Any:
        server = _find_server(app_config, server_id)
        if server is None:
            return jsonify({"error": "Unknown server id"}), 404
        return jsonify(status_monitor.check(server))

    @app.errorhandler(404)
    def not_found(_error: Exception) -> Any:
        return jsonify({"error": "Not found"}), 404

    return app


def _find_server(config: AppConfig, server_id: str) -> ServerConfig | None:
    return next((server for server in config.servers if server.id == server_id), None)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Monitor Minecraft Java servers")
    parser.add_argument(
        "--config",
        type=Path,
        default=_default_config_path(),
        help="path to servers.json (default: servers.json or MCSW_CONFIG)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="web interface to bind")
    parser.add_argument("--port", default=5000, type=int, help="web port to bind")
    parser.add_argument("--debug", action="store_true", help="enable Flask debug mode")
    return parser


def main() -> None:
    args = _parser().parse_args()
    try:
        app = create_app(args.config)
    except ConfigurationError as exc:
        raise SystemExit(f"Configuration error: {exc}") from exc
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()

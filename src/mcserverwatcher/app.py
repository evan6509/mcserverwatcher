"""Flask application for Minecraft Server Watcher."""

from __future__ import annotations

import argparse
import atexit
import os
import subprocess
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template

from .config import AppConfig, ConfigurationError, ServerConfig, load_config
from .monitor import MinecraftMonitor
from .watcher import BackgroundWatcher


_BUILD_COMMIT_ENV_VARS = (
    "MCSW_BUILD_COMMIT",
    "SOURCE_VERSION",
    "RENDER_GIT_COMMIT",
    "RAILWAY_GIT_COMMIT_SHA",
    "GITHUB_SHA",
    "GIT_COMMIT",
)


def _default_config_path() -> Path:
    return Path(os.environ.get("MCSW_CONFIG", "servers.json"))


def _build_commit() -> str:
    """Return the commit supplied by the build environment or local Git."""

    for variable in _BUILD_COMMIT_ENV_VARS:
        if value := os.environ.get(variable, "").strip():
            return value

    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parent,
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"

    return result.stdout.strip() or "unknown"


def create_app(
    config_path: str | Path | None = None,
    *,
    monitor: MinecraftMonitor | None = None,
    start_background: bool = True,
) -> Flask:
    """Create and configure the Flask application."""

    app_config = load_config(config_path or _default_config_path())
    status_monitor = monitor or MinecraftMonitor(app_config.request_timeout_seconds)
    watcher = BackgroundWatcher(
        app_config.servers,
        status_monitor,
        app_config.refresh_seconds,
    )

    app = Flask(__name__)
    app.config["MCSW_SETTINGS"] = app_config
    app.config["MCSW_MONITOR"] = status_monitor
    app.config["MCSW_BUILD_COMMIT"] = _build_commit()
    app.extensions["mcserverwatcher"] = watcher

    if start_background:
        watcher.start()
        atexit.register(watcher.stop)

    @app.get("/")
    def index() -> str:
        return render_template(
            "index.html",
            build_commit=app.config["MCSW_BUILD_COMMIT"],
            build_commit_short=app.config["MCSW_BUILD_COMMIT"][:12],
            refresh_seconds=app_config.refresh_seconds,
        )

    @app.get("/api/health")
    def health() -> Any:
        return jsonify({"ok": True})

    @app.get("/api/servers")
    def all_servers() -> Any:
        return jsonify({"servers": watcher.latest()})

    @app.post("/api/servers/refresh")
    def refresh_servers() -> Any:
        return jsonify({"servers": watcher.refresh()})

    @app.get("/api/servers/<server_id>")
    def one_server(server_id: str) -> Any:
        server = _find_server(app_config, server_id)
        if server is None:
            return jsonify({"error": "Unknown server id"}), 404
        snapshots = watcher.latest()
        snapshot = next(item for item in snapshots if item["id"] == server.id)
        return jsonify(snapshot)

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
    start_background = not args.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    try:
        app = create_app(args.config, start_background=start_background)
    except ConfigurationError as exc:
        raise SystemExit(f"Configuration error: {exc}") from exc
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()

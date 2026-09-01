"""Minecraft Server Watcher package."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from flask import Flask


def create_app(config_path: str | Path | None = None, **kwargs: Any) -> Flask:
    """Create an app without importing Flask during package discovery."""

    from .app import create_app as app_factory

    return app_factory(config_path, **kwargs)


__all__ = ["create_app"]

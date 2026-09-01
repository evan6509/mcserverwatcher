"""Configuration loading and validation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class ConfigurationError(ValueError):
    """Raised when the server configuration is invalid."""


@dataclass(frozen=True, slots=True)
class ServerConfig:
    """A Minecraft server exposed by the dashboard."""

    id: str
    name: str
    address: str
    enable_query: bool = False


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Validated application configuration."""

    refresh_seconds: int
    request_timeout_seconds: float
    servers: tuple[ServerConfig, ...]


def _require_mapping(value: Any, location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigurationError(f"{location} must be a JSON object")
    return value


def _parse_server(value: Any, index: int) -> ServerConfig:
    raw = _require_mapping(value, f"servers[{index}]")
    server_id = raw.get("id")
    name = raw.get("name")
    address = raw.get("address")
    enable_query = raw.get("enable_query", False)

    if not isinstance(server_id, str) or not ID_PATTERN.fullmatch(server_id):
        raise ConfigurationError(
            f"servers[{index}].id must contain lowercase letters, digits, and hyphens"
        )
    if not isinstance(name, str) or not name.strip():
        raise ConfigurationError(f"servers[{index}].name must be a non-empty string")
    if not isinstance(address, str) or not address.strip():
        raise ConfigurationError(f"servers[{index}].address must be a non-empty string")
    if not isinstance(enable_query, bool):
        raise ConfigurationError(f"servers[{index}].enable_query must be true or false")

    return ServerConfig(
        id=server_id,
        name=name.strip(),
        address=address.strip(),
        enable_query=enable_query,
    )


def load_config(path: str | Path) -> AppConfig:
    """Load and validate a JSON configuration file."""

    config_path = Path(path)
    try:
        raw_value = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigurationError(f"Configuration file not found: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigurationError(
            f"Invalid JSON in {config_path} at line {exc.lineno}, column {exc.colno}"
        ) from exc

    raw = _require_mapping(raw_value, "configuration")
    refresh = raw.get("refresh_seconds", 15)
    timeout = raw.get("request_timeout_seconds", 3)
    raw_servers = raw.get("servers")

    if not isinstance(refresh, int) or isinstance(refresh, bool) or not 5 <= refresh <= 3600:
        raise ConfigurationError("refresh_seconds must be an integer from 5 to 3600")
    if (
        not isinstance(timeout, (int, float))
        or isinstance(timeout, bool)
        or not 0.25 <= float(timeout) <= 30
    ):
        raise ConfigurationError("request_timeout_seconds must be from 0.25 to 30")
    if not isinstance(raw_servers, list) or not raw_servers:
        raise ConfigurationError("servers must be a non-empty JSON array")

    servers = tuple(_parse_server(value, index) for index, value in enumerate(raw_servers))
    server_ids = [server.id for server in servers]
    if len(server_ids) != len(set(server_ids)):
        raise ConfigurationError("Each server id must be unique")

    return AppConfig(
        refresh_seconds=refresh,
        request_timeout_seconds=float(timeout),
        servers=servers,
    )

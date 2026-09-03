"""Minecraft status and Query protocol integration."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Any, Callable

from mcstatus import JavaServer

from .config import ServerConfig


ServerFactory = Callable[..., JavaServer]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_error(exc: Exception) -> str:
    message = " ".join(str(exc).split())
    if not message:
        message = exc.__class__.__name__
    return message[:240]


class MinecraftMonitor:
    """Checks configured Minecraft Java Edition servers."""

    def __init__(
        self,
        timeout: float,
        server_factory: ServerFactory = JavaServer.lookup,
        clock: Callable[[], str] = _now_iso,
    ) -> None:
        self.timeout = timeout
        self.server_factory = server_factory
        self.clock = clock
        self._state_lock = Lock()
        self._online_players: dict[str, set[str]] = {}
        self._last_connections: dict[str, dict[str, Any]] = {}

    def _record_players(
        self,
        server_id: str,
        names: list[str],
        observed_at: str,
    ) -> dict[str, Any] | None:
        """Record players that appeared since this server's previous check."""

        with self._state_lock:
            previous_names = self._online_players.get(server_id, set())
            newly_seen = list(
                dict.fromkeys(name for name in names if name not in previous_names)
            )
            self._online_players[server_id] = set(names)
            if newly_seen:
                self._last_connections[server_id] = {
                    "names": newly_seen,
                    "observed_at": observed_at,
                }
            connection = self._last_connections.get(server_id)
            return dict(connection) if connection else None

    def _record_offline(self, server_id: str) -> dict[str, Any] | None:
        """Remember the prior connection while marking all players offline."""

        with self._state_lock:
            self._online_players[server_id] = set()
            connection = self._last_connections.get(server_id)
            return dict(connection) if connection else None

    def check(self, config: ServerConfig) -> dict[str, Any]:
        """Return a JSON-serializable snapshot for one server."""

        checked_at = self.clock()
        base: dict[str, Any] = {
            "id": config.id,
            "name": config.name,
            "address": config.address,
            "checked_at": checked_at,
        }

        try:
            server = self.server_factory(config.address, timeout=self.timeout)
            status = server.status(tries=1)
        except Exception as exc:
            return {
                **base,
                "online": False,
                "error": _safe_error(exc),
                "latency_ms": None,
                "motd": None,
                "version": None,
                "players": None,
                "last_connection": self._record_offline(config.id),
            }

        sample = status.players.sample or []
        names = [player.name for player in sample]
        list_source = "server_list_ping"
        list_complete = status.players.online == 0
        warning: str | None = None

        if config.enable_query:
            try:
                query = server.query(tries=1)
                names = list(query.players.list)
                list_source = "query"
                list_complete = True
            except Exception as exc:
                warning = (
                    "Query was unavailable; showing the server-list sample instead. "
                    f"{_safe_error(exc)}"
                )

        last_connection = self._record_players(config.id, names, checked_at)

        result: dict[str, Any] = {
            **base,
            "online": True,
            "error": None,
            "latency_ms": round(float(status.latency), 1),
            "motd": status.motd.to_plain(),
            "version": {
                "name": status.version.name,
                "protocol": status.version.protocol,
            },
            "players": {
                "online": status.players.online,
                "max": status.players.max,
                "names": names,
                "list_complete": list_complete,
                "source": list_source,
            },
            "last_connection": last_connection,
        }
        if warning:
            result["warning"] = warning
        return result

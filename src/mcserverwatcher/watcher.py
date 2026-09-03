"""Background polling and snapshot caching for configured servers."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Event, Lock, Thread
from typing import Any

from .config import ServerConfig
from .monitor import MinecraftMonitor


LOGGER = logging.getLogger(__name__)


class BackgroundWatcher:
    """Poll Minecraft servers in the background and cache their latest state."""

    def __init__(
        self,
        servers: tuple[ServerConfig, ...],
        monitor: MinecraftMonitor,
        refresh_seconds: float,
    ) -> None:
        self.servers = servers
        self.monitor = monitor
        self.refresh_seconds = refresh_seconds
        self._snapshots: list[dict[str, Any]] | None = None
        self._snapshot_lock = Lock()
        self._refresh_lock = Lock()
        self._stop_event = Event()
        self._thread: Thread | None = None

    def start(self) -> None:
        """Start polling immediately in a daemon thread."""

        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = Thread(
            target=self._run,
            name="minecraft-server-watcher",
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout: float = 1) -> None:
        """Ask the polling thread to stop."""

        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)

    def latest(self) -> list[dict[str, Any]]:
        """Return cached snapshots, checking synchronously before the first result."""

        with self._snapshot_lock:
            if self._snapshots is not None:
                return deepcopy(self._snapshots)
        return self.refresh(only_if_empty=True)

    def refresh(self, *, only_if_empty: bool = False) -> list[dict[str, Any]]:
        """Check all servers now and replace the cached snapshots."""

        with self._refresh_lock:
            with self._snapshot_lock:
                if only_if_empty and self._snapshots is not None:
                    return deepcopy(self._snapshots)

            workers = min(8, len(self.servers))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                snapshots = list(pool.map(self.monitor.check, self.servers))

            with self._snapshot_lock:
                self._snapshots = snapshots
                return deepcopy(snapshots)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.refresh()
            except Exception:
                LOGGER.exception("Unexpected error during background server check")
            self._stop_event.wait(self.refresh_seconds)

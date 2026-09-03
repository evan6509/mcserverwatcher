from threading import Event

from mcserverwatcher.config import ServerConfig
from mcserverwatcher.watcher import BackgroundWatcher


class RecordingMonitor:
    def __init__(self):
        self.check_count = 0
        self.checked_twice = Event()

    def check(self, config):
        self.check_count += 1
        if self.check_count >= 2:
            self.checked_twice.set()
        return {"id": config.id, "online": True}


def test_background_watcher_checks_repeatedly_without_api_requests():
    monitor = RecordingMonitor()
    server = ServerConfig("test", "Test", "example.test")
    watcher = BackgroundWatcher((server,), monitor, refresh_seconds=0.01)

    watcher.start()
    try:
        assert monitor.checked_twice.wait(timeout=1)
    finally:
        watcher.stop()

    assert monitor.check_count >= 2


def test_latest_uses_cached_snapshot():
    monitor = RecordingMonitor()
    server = ServerConfig("test", "Test", "example.test")
    watcher = BackgroundWatcher((server,), monitor, refresh_seconds=15)

    first = watcher.latest()
    second = watcher.latest()

    assert first == second == [{"id": "test", "online": True}]
    assert monitor.check_count == 1

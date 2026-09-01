from types import SimpleNamespace

from mcserverwatcher.config import ServerConfig
from mcserverwatcher.monitor import MinecraftMonitor


def namespace(**kwargs):
    return SimpleNamespace(**kwargs)


class FakeServer:
    def __init__(self, *, query_error=None):
        self.query_error = query_error

    def status(self, *, tries):
        assert tries == 1
        return namespace(
            latency=23.456,
            motd=namespace(to_plain=lambda: "A test server"),
            version=namespace(name="1.21.8", protocol=772),
            players=namespace(
                online=2,
                max=20,
                sample=[namespace(name="Alex")],
            ),
        )

    def query(self, *, tries):
        assert tries == 1
        if self.query_error:
            raise self.query_error
        return namespace(players=namespace(list=["Alex", "Steve"]))


def test_status_uses_full_query_player_list():
    monitor = MinecraftMonitor(2, server_factory=lambda *_args, **_kwargs: FakeServer())
    config = ServerConfig("test", "Test", "example.test", enable_query=True)

    result = monitor.check(config)

    assert result["online"] is True
    assert result["latency_ms"] == 23.5
    assert result["players"] == {
        "online": 2,
        "max": 20,
        "names": ["Alex", "Steve"],
        "list_complete": True,
        "source": "query",
    }


def test_status_falls_back_to_sample_when_query_fails():
    fake = FakeServer(query_error=TimeoutError("timed out"))
    monitor = MinecraftMonitor(2, server_factory=lambda *_args, **_kwargs: fake)
    config = ServerConfig("test", "Test", "example.test", enable_query=True)

    result = monitor.check(config)

    assert result["online"] is True
    assert result["players"]["names"] == ["Alex"]
    assert result["players"]["list_complete"] is False
    assert "Query was unavailable" in result["warning"]


def test_offline_server_returns_a_snapshot():
    def fail(*_args, **_kwargs):
        raise OSError("connection refused")

    monitor = MinecraftMonitor(2, server_factory=fail)
    config = ServerConfig("test", "Test", "example.test")

    result = monitor.check(config)

    assert result["online"] is False
    assert result["error"] == "connection refused"
    assert result["players"] is None

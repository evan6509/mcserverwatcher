import json

from mcserverwatcher.app import create_app


class FakeMonitor:
    def __init__(self):
        self.check_count = 0

    def check(self, config):
        self.check_count += 1
        return {
            "id": config.id,
            "name": config.name,
            "address": config.address,
            "online": False,
            "error": "test",
        }


def make_app(tmp_path):
    path = tmp_path / "servers.json"
    path.write_text(
        json.dumps(
            {
                "servers": [
                    {"id": "one", "name": "Server One", "address": "localhost"}
                ]
            }
        ),
        encoding="utf-8",
    )
    app = create_app(path, monitor=FakeMonitor(), start_background=False)
    app.testing = True
    return app


def test_dashboard_loads(tmp_path):
    response = make_app(tmp_path).test_client().get("/")

    assert response.status_code == 200
    assert b"Minecraft Server Watcher" in response.data


def test_dashboard_shows_build_commit(tmp_path, monkeypatch):
    monkeypatch.setenv("MCSW_BUILD_COMMIT", "0123456789abcdef")

    response = make_app(tmp_path).test_client().get("/")

    assert b"Build 0123456789ab" in response.data
    assert b"Full commit: 0123456789abcdef" in response.data


def test_all_servers_api(tmp_path):
    response = make_app(tmp_path).test_client().get("/api/servers")

    assert response.status_code == 200
    assert response.get_json()["servers"][0]["id"] == "one"


def test_one_server_api_and_unknown_id(tmp_path):
    client = make_app(tmp_path).test_client()

    assert client.get("/api/servers/one").get_json()["name"] == "Server One"
    missing = client.get("/api/servers/missing")
    assert missing.status_code == 404
    assert missing.get_json() == {"error": "Unknown server id"}


def test_api_uses_background_cache_and_supports_manual_refresh(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    monitor = app.config["MCSW_MONITOR"]

    client.get("/api/servers")
    client.get("/api/servers")
    assert monitor.check_count == 1

    response = client.post("/api/servers/refresh")
    assert response.status_code == 200
    assert monitor.check_count == 2

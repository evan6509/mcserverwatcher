import json

from mcserverwatcher.app import create_app


class FakeMonitor:
    def check(self, config):
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
    app = create_app(path, monitor=FakeMonitor())
    app.testing = True
    return app


def test_dashboard_loads(tmp_path):
    response = make_app(tmp_path).test_client().get("/")

    assert response.status_code == 200
    assert b"Minecraft Server Watcher" in response.data


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

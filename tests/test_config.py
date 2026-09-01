import json

import pytest

from mcserverwatcher.config import ConfigurationError, load_config


def write_config(tmp_path, value):
    path = tmp_path / "servers.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_load_config(tmp_path):
    path = write_config(
        tmp_path,
        {
            "refresh_seconds": 20,
            "request_timeout_seconds": 1.5,
            "servers": [
                {
                    "id": "survival",
                    "name": "Survival",
                    "address": "example.test:25565",
                    "enable_query": True,
                }
            ],
        },
    )

    config = load_config(path)

    assert config.refresh_seconds == 20
    assert config.request_timeout_seconds == 1.5
    assert config.servers[0].id == "survival"
    assert config.servers[0].enable_query is True


@pytest.mark.parametrize(
    "change, message",
    [
        ({"servers": []}, "non-empty"),
        ({"refresh_seconds": 2}, "refresh_seconds"),
        ({"request_timeout_seconds": 0}, "request_timeout_seconds"),
    ],
)
def test_invalid_top_level_config(tmp_path, change, message):
    value = {
        "servers": [{"id": "one", "name": "One", "address": "localhost"}]
    }
    value.update(change)
    path = write_config(tmp_path, value)

    with pytest.raises(ConfigurationError, match=message):
        load_config(path)


def test_duplicate_server_ids_are_rejected(tmp_path):
    server = {"id": "same", "name": "One", "address": "localhost"}
    path = write_config(tmp_path, {"servers": [server, {**server, "name": "Two"}]})

    with pytest.raises(ConfigurationError, match="unique"):
        load_config(path)

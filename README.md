# Minecraft Server Watcher

A small Python web server that displays the status of one or more Minecraft
Java Edition servers. It includes a browser dashboard and a JSON API for player
counts, player names, latency, version, and MOTD.

## Set up

Python 3.10 or newer is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

Edit `servers.json` and replace `localhost:25565` with the address you would
enter in Minecraft. Add more objects to the `servers` array to monitor multiple
servers.

```json
{
  "refresh_seconds": 15,
  "request_timeout_seconds": 3,
  "servers": [
    {
      "id": "survival",
      "name": "Survival Server",
      "address": "play.example.com:25565",
      "enable_query": false
    }
  ]
}
```

Start the app:

```bash
mcserverwatcher
```

Then open <http://127.0.0.1:5000>. Use `--host 0.0.0.0` if the dashboard
should be reachable by other devices on your network.

```bash
mcserverwatcher --host 0.0.0.0 --port 8080
```

The configuration path can be changed with `--config` or the `MCSW_CONFIG`
environment variable.

## Player names and Query

Every modern Java server exposes a player count through Server List Ping. The
player names returned by that protocol are only a sample, and server software
or plugins may hide or replace them.

For a complete player list, enable the Query protocol in the Minecraft server's
`server.properties`:

```properties
enable-query=true
query.port=25565
```

Open that UDP port in the server firewall, restart Minecraft, and then set
`"enable_query": true` for that server in `servers.json`. Do not enable the
option when Query is unavailable, because each refresh will wait for its
timeout before falling back to the status sample.

## API

- `GET /api/servers` checks every configured server.
- `GET /api/servers/<id>` checks one server.
- `GET /api/health` verifies that the web process is running.

Example:

```bash
curl http://127.0.0.1:5000/api/servers/local
```

An offline Minecraft server still returns HTTP 200 with `"online": false`.
Unknown IDs and invalid web routes return normal HTTP 404 responses.

## Development

```bash
python -m pip install '.[dev]'
pytest
```

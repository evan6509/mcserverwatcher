const serverContainer = document.querySelector("#servers");
const summaryContainer = document.querySelector("#summary");
const refreshButton = document.querySelector("#refresh");
const updatedLabel = document.querySelector("#last-updated");
const refreshSeconds = Number(document.body.dataset.refreshSeconds || 15);

function escapeHtml(value) {
  const element = document.createElement("span");
  element.textContent = String(value ?? "");
  return element.innerHTML;
}

function playerMarkup(players) {
  if (!players || players.online === 0) {
    return '<p class="empty-list">No players online</p>';
  }
  if (players.names.length === 0) {
    return '<p class="empty-list">Player names are hidden by this server.</p>';
  }
  const names = players.names
    .map((name) => `<li>${escapeHtml(name)}</li>`)
    .join("");
  const note = players.list_complete
    ? "Complete list from Query"
    : "Names shown are the server-list sample and may be incomplete";
  return `<ul class="player-list">${names}</ul><p class="list-note">${note}</p>`;
}

function serverCard(server) {
  if (!server.online) {
    return `
      <article class="server-card offline">
        <div class="card-heading">
          <div><p class="address">${escapeHtml(server.address)}</p><h2>${escapeHtml(server.name)}</h2></div>
          <span class="status-pill">Offline</span>
        </div>
        <p class="error-message">${escapeHtml(server.error || "The server did not respond.")}</p>
      </article>`;
  }

  const players = server.players;
  const percent = players.max > 0 ? Math.min(100, (players.online / players.max) * 100) : 0;
  const warning = server.warning
    ? `<p class="warning-message">${escapeHtml(server.warning)}</p>`
    : "";
  return `
    <article class="server-card online">
      <div class="card-heading">
        <div><p class="address">${escapeHtml(server.address)}</p><h2>${escapeHtml(server.name)}</h2></div>
        <span class="status-pill">Online</span>
      </div>
      <p class="motd">${escapeHtml(server.motd)}</p>
      <div class="count-row">
        <div><strong>${players.online}</strong><span> online</span></div>
        <span>${players.max} slots</span>
      </div>
      <div class="meter" aria-label="${players.online} of ${players.max} player slots used">
        <span style="width: ${percent}%"></span>
      </div>
      <dl class="details">
        <div><dt>Version</dt><dd>${escapeHtml(server.version.name)}</dd></div>
        <div><dt>Latency</dt><dd>${server.latency_ms} ms</dd></div>
      </dl>
      <h3>Players</h3>
      ${playerMarkup(players)}
      ${warning}
    </article>`;
}

function renderSummary(servers) {
  const online = servers.filter((server) => server.online);
  const players = online.reduce((sum, server) => sum + server.players.online, 0);
  summaryContainer.innerHTML = `
    <div><strong>${online.length}</strong><span> of ${servers.length} servers online</span></div>
    <div><strong>${players}</strong><span> players online</span></div>`;
}

async function loadServers() {
  refreshButton.disabled = true;
  refreshButton.textContent = "Refreshing…";
  try {
    const response = await fetch("/api/servers", { cache: "no-store" });
    if (!response.ok) throw new Error(`The API returned HTTP ${response.status}.`);
    const data = await response.json();
    renderSummary(data.servers);
    serverContainer.innerHTML = data.servers.map(serverCard).join("");
    updatedLabel.textContent = `Updated ${new Date().toLocaleTimeString()}`;
  } catch (error) {
    summaryContainer.innerHTML = "";
    serverContainer.innerHTML = `
      <article class="server-card offline">
        <h2>Dashboard unavailable</h2>
        <p class="error-message">${escapeHtml(error.message)}</p>
      </article>`;
    updatedLabel.textContent = "Refresh failed";
  } finally {
    refreshButton.disabled = false;
    refreshButton.textContent = "Refresh now";
  }
}

refreshButton.addEventListener("click", loadServers);
loadServers();
window.setInterval(loadServers, refreshSeconds * 1000);

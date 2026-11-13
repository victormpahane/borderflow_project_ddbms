import json
import os
from datetime import datetime
from urllib.error import URLError
from urllib.request import Request, urlopen

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import text

from shared.auth.rbac import (
    AuthContext,
    CONTROL_TOWER_READERS,
    INTERNAL_READERS,
    TRACKING_READERS,
    require_actors,
)
from shared.db.session import get_database_health, get_session
from shared.db.sites import SITE_IDS
from shared.messaging.health import get_rabbitmq_health


SITE_THEME = {
    "DEPOT": {"accent": "#b85c38", "soft": "rgba(184,92,56,0.12)"},
    "BORDER": {"accent": "#1d6f8a", "soft": "rgba(29,111,138,0.12)"},
    "PORT": {"accent": "#2f855a", "soft": "rgba(47,133,90,0.12)"},
    "DESTINATION": {"accent": "#7c5e99", "soft": "rgba(124,94,153,0.12)"},
}


BASE_CSS = """
  :root {
    --bg: #f5efe4;
    --panel: rgba(255, 251, 244, 0.94);
    --ink: #1f2933;
    --muted: #5b6470;
    --accent: #0f766e;
    --line: rgba(31, 41, 51, 0.1);
    --ok: #1f8a4c;
    --warn: #b76e00;
    --bad: #b42318;
    --shadow: 0 20px 60px rgba(59, 52, 37, 0.12);
  }

  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: Georgia, "Times New Roman", serif;
    color: var(--ink);
    background:
      radial-gradient(circle at top left, rgba(15,118,110,0.14), transparent 32%),
      radial-gradient(circle at top right, rgba(191,90,36,0.12), transparent 28%),
      linear-gradient(180deg, #f7f2e8 0%, #efe5d2 100%);
    min-height: 100vh;
  }

  .shell {
    width: min(1260px, calc(100% - 32px));
    margin: 24px auto 40px;
  }

  .topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    margin-bottom: 16px;
    flex-wrap: wrap;
  }

  .brand {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .brand-mark {
    width: 44px;
    height: 44px;
    border-radius: 14px;
    background: linear-gradient(135deg, var(--accent), #d17a2e);
    box-shadow: 0 12px 28px rgba(15, 118, 110, 0.2);
  }

  .brand-copy strong {
    display: block;
    letter-spacing: -0.03em;
    font-size: 1.05rem;
  }

  .brand-copy span {
    display: block;
    font-family: "Trebuchet MS", Arial, sans-serif;
    color: var(--muted);
    font-size: 0.9rem;
  }

  .role-badge {
    padding: 8px 12px;
    border-radius: 999px;
    background: rgba(255,255,255,0.72);
    border: 1px solid var(--line);
    font-family: "Trebuchet MS", Arial, sans-serif;
    color: var(--muted);
  }

  .nav {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 18px;
  }

  .nav a {
    text-decoration: none;
    color: var(--ink);
    border: 1px solid var(--line);
    background: rgba(255,255,255,0.7);
    padding: 10px 14px;
    border-radius: 999px;
    font-family: "Trebuchet MS", Arial, sans-serif;
    font-size: 0.92rem;
  }

  .nav a.active {
    background: var(--accent);
    color: white;
    border-color: var(--accent);
  }

  .panel {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 24px;
    box-shadow: var(--shadow);
    backdrop-filter: blur(10px);
  }

  .hero {
    display: grid;
    grid-template-columns: 1.15fr 0.85fr;
    gap: 18px;
    margin-bottom: 18px;
  }

  .hero-main,
  .hero-side,
  .section {
    padding: 22px;
  }

  .eyebrow {
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.14em;
    font-size: 0.76rem;
    margin-bottom: 12px;
    display: inline-block;
    font-family: "Trebuchet MS", Arial, sans-serif;
  }

  h1 {
    margin: 0 0 12px;
    font-size: clamp(2rem, 5vw, 3.6rem);
    line-height: 0.95;
    letter-spacing: -0.05em;
    max-width: 12ch;
  }

  .copy {
    font-family: "Trebuchet MS", Arial, sans-serif;
    max-width: 56ch;
    line-height: 1.55;
    color: #334155;
  }

  .hero-side {
    display: grid;
    gap: 12px;
  }

  .stat {
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 16px 18px;
    background: rgba(255,255,255,0.66);
  }

  .stat-label {
    font-family: "Trebuchet MS", Arial, sans-serif;
    font-size: 0.76rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--muted);
  }

  .stat-value {
    font-size: 2rem;
    margin-top: 8px;
  }

  .grid {
    display: grid;
    grid-template-columns: 1.1fr 0.9fr;
    gap: 18px;
  }

  .section h2 {
    margin: 0 0 14px;
    font-size: 1.18rem;
  }

  .sites,
  .feed,
  .stack {
    display: grid;
    gap: 12px;
  }

  .site-card,
  .event,
  .stack-card,
  .tracking-card {
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 16px;
    background: rgba(255,255,255,0.68);
  }

  .site-card {
    transition: transform 180ms ease, box-shadow 180ms ease;
  }

  .site-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 28px rgba(31, 41, 51, 0.08);
  }

  .site-head,
  .chip-row,
  .event-top,
  .stack-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    flex-wrap: wrap;
  }

  .site-name,
  .stack-title {
    font-size: 1.08rem;
    font-weight: 700;
  }

  .chip {
    padding: 6px 10px;
    border-radius: 999px;
    font-family: "Trebuchet MS", Arial, sans-serif;
    font-size: 0.78rem;
    border: 1px solid transparent;
  }

  .chip.ok { background: rgba(31,138,76,0.12); color: var(--ok); border-color: rgba(31,138,76,0.18); }
  .chip.warn { background: rgba(183,110,0,0.12); color: var(--warn); border-color: rgba(183,110,0,0.18); }
  .chip.bad { background: rgba(180,35,24,0.12); color: var(--bad); border-color: rgba(180,35,24,0.18); }

  .metrics {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
  }

  .metric {
    border-top: 1px solid var(--line);
    padding-top: 10px;
  }

  .metric-key {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--muted);
    font-family: "Trebuchet MS", Arial, sans-serif;
  }

  .metric-value {
    margin-top: 4px;
    font-size: 1rem;
  }

  .event-type {
    font-weight: 700;
    letter-spacing: 0.02em;
  }

  .event-meta,
  .muted {
    color: var(--muted);
    font-family: "Trebuchet MS", Arial, sans-serif;
    font-size: 0.92rem;
  }

  .empty {
    color: var(--muted);
    font-style: italic;
    padding: 12px 0;
  }

  .button,
  button {
    border: none;
    background: var(--accent);
    color: white;
    font: inherit;
    padding: 12px 16px;
    border-radius: 999px;
    cursor: pointer;
    box-shadow: 0 8px 24px rgba(15,118,110,0.22);
  }

  .toolbar {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-top: 14px;
    align-items: center;
  }

  .toolbar input {
    flex: 1 1 260px;
    min-width: 180px;
    border-radius: 14px;
    border: 1px solid var(--line);
    background: rgba(255,255,255,0.9);
    padding: 12px 14px;
    font: inherit;
  }

  .link-button {
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: white;
    background: var(--accent);
    padding: 11px 14px;
    border-radius: 999px;
    font-family: "Trebuchet MS", Arial, sans-serif;
  }

  .timeline {
    display: grid;
    gap: 10px;
    margin-top: 14px;
  }

  .timeline-item {
    padding: 14px;
    border-radius: 16px;
    background: rgba(255,255,255,0.68);
    border: 1px solid var(--line);
  }

  .site-banner {
    display: inline-block;
    padding: 8px 12px;
    border-radius: 999px;
    font-family: "Trebuchet MS", Arial, sans-serif;
    background: var(--site-soft, rgba(15,118,110,0.1));
    color: var(--site-accent, var(--accent));
    border: 1px solid var(--site-soft, rgba(15,118,110,0.2));
    margin-bottom: 14px;
  }

  @media (max-width: 900px) {
    .hero,
    .grid { grid-template-columns: 1fr; }
    .metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  }

  @media (max-width: 560px) {
    .shell { width: min(100% - 18px, 100%); margin: 10px auto 24px; }
    .hero-main, .hero-side, .section { padding: 16px; }
    .metrics { grid-template-columns: 1fr 1fr; }
    h1 { max-width: none; }
  }
"""


app = FastAPI(title="BorderFlow Control Tower")


def build_shell(title: str, eyebrow: str, body: str, script: str, actor: str, active: str, accent: str = "#0f766e", site_soft: str = "rgba(15,118,110,0.12)"):
    nav_links = [
        ("Control Tower", "/", "tower"),
        ("Client Tracking", "/tracking", "tracking"),
        ("Depot", "/sites/DEPOT", "DEPOT"),
        ("Border", "/sites/BORDER", "BORDER"),
        ("Port", "/sites/PORT", "PORT"),
        ("Destination", "/sites/DESTINATION", "DESTINATION"),
    ]
    nav_html = "".join(
        f'<a class="{"active" if active == key else ""}" href="{path}?api_key={actor}">{label}</a>'
        for label, path, key in nav_links
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
{BASE_CSS}
  </style>
</head>
<body style="--accent:{accent};--site-accent:{accent};--site-soft:{site_soft};">
  <div class="shell">
    <div class="topbar">
      <div class="brand">
        <div class="brand-mark"></div>
        <div class="brand-copy">
          <strong>{title}</strong>
          <span>{eyebrow}</span>
        </div>
      </div>
      <div class="role-badge">Active actor key: <strong>{actor}</strong></div>
    </div>
    <nav class="nav">{nav_html}</nav>
    {body}
  </div>
  <script>
    const params = new URLSearchParams(window.location.search);
    const incomingApiKey = params.get("api_key") || "";
    const storedApiKey = window.localStorage.getItem("borderflow_api_key") || "";
    const apiKey = incomingApiKey || storedApiKey || "{actor}";
    window.localStorage.setItem("borderflow_api_key", apiKey);
    function withApiKey(path) {{
      const url = new URL(path, window.location.origin);
      url.searchParams.set("api_key", apiKey);
      return url.toString();
    }}
{script}
  </script>
</body>
</html>"""


def overview_page(default_key: str):
    body = """
    <section class="hero">
      <div class="panel hero-main">
        <div class="eyebrow">Control Tower</div>
        <h1>Distributed cargo visibility.</h1>
        <div class="copy">
          A cross-site operational surface for the Depot, Border, Port, and Destination nodes.
          It shows health, replication pressure, and the latest synchronized movement history.
        </div>
        <div class="toolbar">
          <button id="refreshButton">Refresh Now</button>
          <a class="link-button" id="trackingLink" href="#">Open Client Tracking</a>
        </div>
      </div>
      <div class="panel hero-side">
        <div class="stat"><div class="stat-label">Healthy Sites</div><div class="stat-value" id="healthySites">-</div></div>
        <div class="stat"><div class="stat-label">Total Events</div><div class="stat-value" id="totalEvents">-</div></div>
        <div class="stat"><div class="stat-label">Pending Outbox</div><div class="stat-value" id="pendingOutbox">-</div></div>
      </div>
    </section>
    <section class="grid">
      <div class="panel section">
        <h2>Site Operations</h2>
        <div class="sites" id="sites"></div>
      </div>
      <div class="panel section">
        <h2>Recent Global Events</h2>
        <div class="feed" id="events"></div>
      </div>
    </section>
    """
    script = """
    const state = { overview: null };
    document.getElementById("trackingLink").href = withApiKey("/tracking");

    function statusChipClass(status) {
      if (status === "ok") return "ok";
      if (status === "degraded") return "warn";
      return "bad";
    }

    function number(value) {
      if (value === null || value === undefined) return "n/a";
      return String(value);
    }

    function render() {
      const overview = state.overview;
      if (!overview) return;

      document.getElementById("healthySites").textContent = `${overview.healthy_sites}/${overview.total_sites}`;
      document.getElementById("totalEvents").textContent = number(overview.total_events);
      document.getElementById("pendingOutbox").textContent = number(overview.total_pending_outbox);

      const sitesRoot = document.getElementById("sites");
      sitesRoot.innerHTML = "";

      overview.sites.forEach((site) => {
        const detailUrl = withApiKey(`/sites/${site.site_id}`);
        const card = document.createElement("a");
        card.className = "site-card";
        card.href = detailUrl;
        card.style.textDecoration = "none";
        card.style.color = "inherit";
        card.innerHTML = `
          <div class="site-head">
            <div class="site-name">${site.site_id}</div>
            <span class="chip ${statusChipClass(site.status)}">${site.status}</span>
          </div>
          <div class="chip-row">
            <span class="chip ${site.database.ok ? "ok" : "bad"}">DB ${site.database.ok ? "online" : "down"}</span>
            <span class="chip ${site.rabbitmq.ok ? "ok" : "bad"}">MQ ${site.rabbitmq.ok ? "online" : "down"}</span>
            <span class="chip ${site.service_health.ok ? "ok" : "warn"}">API ${site.service_health.ok ? "reachable" : "unreachable"}</span>
          </div>
          <div class="metrics">
            <div class="metric"><div class="metric-key">Events</div><div class="metric-value">${number(site.event_count)}</div></div>
            <div class="metric"><div class="metric-key">Pending Outbox</div><div class="metric-value">${number(site.pending_outbox)}</div></div>
            <div class="metric"><div class="metric-key">Inbox</div><div class="metric-value">${number(site.inbox_count)}</div></div>
            <div class="metric"><div class="metric-key">Last Event</div><div class="metric-value">${site.last_event_type || "n/a"}</div></div>
          </div>
        `;
        sitesRoot.appendChild(card);
      });

      const eventsRoot = document.getElementById("events");
      eventsRoot.innerHTML = "";
      if (!overview.recent_events.length) {
        eventsRoot.innerHTML = '<div class="empty">No events captured yet. Create one from a site API to populate the tower.</div>';
        return;
      }

      overview.recent_events.forEach((event) => {
        const item = document.createElement("div");
        item.className = "event";
        item.innerHTML = `
          <div class="event-top">
            <div class="event-type">${event.event_type}</div>
            <div class="event-meta">${event.timestamp || "unknown time"}</div>
          </div>
          <div class="event-meta">Container ${event.container_id} · Site ${event.site_id} · Sync ${event.sync_status}</div>
          <div class="event-meta" style="margin-top:6px;">Event ID ${event.event_id}</div>
        `;
        eventsRoot.appendChild(item);
      });
    }

    async function loadOverview() {
      const response = await fetch(withApiKey("/api/overview"));
      state.overview = await response.json();
      render();
    }

    document.getElementById("refreshButton").addEventListener("click", loadOverview);
    loadOverview();
    setInterval(loadOverview, 12000);
    """
    return build_shell("BorderFlow Control Tower", "Audit, health, and cross-site synchronization", body, script, default_key, "tower")


def tracking_page(default_key: str):
    body = """
    <section class="hero">
      <div class="panel hero-main">
        <div class="eyebrow">Client Tracking</div>
        <h1>Read-only shipment timeline.</h1>
        <div class="copy">
          A client-facing tracking surface for customer service and external visibility.
          Enter a container ID to fetch its synchronized movement timeline across all sites.
        </div>
        <div class="toolbar">
          <input id="containerInput" placeholder="e.g. CONT-001">
          <button id="trackingButton">Track Container</button>
        </div>
      </div>
      <div class="panel hero-side">
        <div class="stat"><div class="stat-label">Actor Scope</div><div class="stat-value" style="font-size:1.15rem;" id="actorName">-</div></div>
        <div class="stat"><div class="stat-label">Timeline Events</div><div class="stat-value" id="timelineCount">0</div></div>
        <div class="stat"><div class="stat-label">Current Container</div><div class="stat-value" style="font-size:1.15rem;" id="activeContainer">n/a</div></div>
      </div>
    </section>
    <section class="panel section">
      <h2>Container Timeline</h2>
      <div class="timeline" id="timeline"></div>
    </section>
    """
    script = """
    function renderTimeline(payload) {
      document.getElementById("actorName").textContent = payload.actor;
      document.getElementById("timelineCount").textContent = String(payload.timeline.length);
      document.getElementById("activeContainer").textContent = payload.container_id;

      const timelineRoot = document.getElementById("timeline");
      timelineRoot.innerHTML = "";

      if (!payload.timeline.length) {
        timelineRoot.innerHTML = '<div class="empty">No synchronized events found for this container yet.</div>';
        return;
      }

      payload.timeline.forEach((event) => {
        const item = document.createElement("div");
        item.className = "timeline-item";
        item.innerHTML = `
          <div class="event-top">
            <div class="event-type">${event.event_type}</div>
            <div class="event-meta">${event.timestamp}</div>
          </div>
          <div class="event-meta">Site ${event.site_id} · Sync ${event.sync_status}</div>
          <div class="event-meta" style="margin-top:6px;">Event ID ${event.event_id}</div>
        `;
        timelineRoot.appendChild(item);
      });
    }

    async function loadTracking() {
      const containerId = document.getElementById("containerInput").value.trim();
      if (!containerId) return;
      const response = await fetch(withApiKey(`/api/tracking/${encodeURIComponent(containerId)}`));
      const payload = await response.json();
      renderTimeline(payload);
    }

    document.getElementById("trackingButton").addEventListener("click", loadTracking);
    document.getElementById("containerInput").addEventListener("keydown", (event) => {
      if (event.key === "Enter") loadTracking();
    });
    """
    return build_shell("BorderFlow Client Tracking", "Read-only customer service and client view", body, script, default_key, "tracking", "#8c5e3c", "rgba(140,94,60,0.12)")


def site_page(default_key: str, site_id: str):
    body = f"""
    <section class="hero">
      <div class="panel hero-main">
        <div class="site-banner">{site_id} Operational Surface</div>
        <h1>{site_id.title()} node dashboard.</h1>
        <div class="copy">
          A dedicated operational dashboard for the {site_id} site, focused on local event flow,
          synchronization state, queue pressure, and recent movement activity.
        </div>
        <div class="toolbar">
          <button id="refreshButton">Refresh Site</button>
        </div>
      </div>
      <div class="panel hero-side">
        <div class="stat"><div class="stat-label">Site Status</div><div class="stat-value" id="siteStatus">-</div></div>
        <div class="stat"><div class="stat-label">Events</div><div class="stat-value" id="siteEvents">-</div></div>
        <div class="stat"><div class="stat-label">Pending Outbox</div><div class="stat-value" id="siteOutbox">-</div></div>
      </div>
    </section>
    <section class="grid">
      <div class="panel section">
        <h2>Operational Snapshot</h2>
        <div class="stack" id="snapshot"></div>
      </div>
      <div class="panel section">
        <h2>Recent Site Events</h2>
        <div class="feed" id="events"></div>
      </div>
    </section>
    """
    script = f"""
    const siteId = "{site_id}";

    function statusChipClass(status) {{
      if (status === "ok") return "ok";
      if (status === "degraded") return "warn";
      return "bad";
    }}

    function number(value) {{
      if (value === null || value === undefined) return "n/a";
      return String(value);
    }}

    function render(payload) {{
      document.getElementById("siteStatus").textContent = payload.snapshot.status;
      document.getElementById("siteEvents").textContent = number(payload.snapshot.event_count);
      document.getElementById("siteOutbox").textContent = number(payload.snapshot.pending_outbox);

      const snapshotRoot = document.getElementById("snapshot");
      snapshotRoot.innerHTML = `
        <div class="stack-card">
          <div class="stack-head">
            <div class="stack-title">${{payload.snapshot.site_id}}</div>
            <span class="chip ${{statusChipClass(payload.snapshot.status)}}">${{payload.snapshot.status}}</span>
          </div>
          <div class="metrics">
            <div class="metric"><div class="metric-key">Inbox</div><div class="metric-value">${{number(payload.snapshot.inbox_count)}}</div></div>
            <div class="metric"><div class="metric-key">DB</div><div class="metric-value">${{payload.snapshot.database.ok ? "online" : "down"}}</div></div>
            <div class="metric"><div class="metric-key">RabbitMQ</div><div class="metric-value">${{payload.snapshot.rabbitmq.ok ? "online" : "down"}}</div></div>
            <div class="metric"><div class="metric-key">Last Event</div><div class="metric-value">${{payload.snapshot.last_event_type || "n/a"}}</div></div>
          </div>
        </div>
      `;

      const eventsRoot = document.getElementById("events");
      eventsRoot.innerHTML = "";
      if (!payload.recent_events.length) {{
        eventsRoot.innerHTML = '<div class="empty">No events recorded for this site yet.</div>';
        return;
      }}

      payload.recent_events.forEach((event) => {{
        const item = document.createElement("div");
        item.className = "event";
        item.innerHTML = `
          <div class="event-top">
            <div class="event-type">${{event.event_type}}</div>
            <div class="event-meta">${{event.timestamp}}</div>
          </div>
          <div class="event-meta">Container ${{event.container_id}} · Sync ${{event.sync_status}}</div>
          <div class="event-meta" style="margin-top:6px;">Event ID ${{event.event_id}}</div>
        `;
        eventsRoot.appendChild(item);
      }});
    }}

    async function loadSite() {{
      const response = await fetch(withApiKey(`/api/sites/${{siteId}}`));
      const payload = await response.json();
      render(payload);
    }}

    document.getElementById("refreshButton").addEventListener("click", loadSite);
    loadSite();
    setInterval(loadSite, 12000);
    """
    theme = SITE_THEME.get(site_id, {"accent": "#0f766e", "soft": "rgba(15,118,110,0.12)"})
    return build_shell(
        f"{site_id.title()} Dashboard",
        f"{site_id} local operations and synchronization view",
        body,
        script,
        default_key,
        site_id,
        theme["accent"],
        theme["soft"],
    )


def get_service_url(site_id: str) -> str:
    return os.getenv(
        f"{site_id.upper()}_SERVICE_URL",
        f"http://127.0.0.1:{8000 + SITE_IDS.index(site_id.upper())}/health",
    )


def get_internal_api_key() -> str:
    return os.getenv("CONTROL_TOWER_INTERNAL_API_KEY", "management-demo-key")


def get_service_health(site_id: str):
    service_url = get_service_url(site_id)
    try:
        request = Request(
            service_url,
            headers={"X-API-Key": get_internal_api_key()},
        )
        with urlopen(request, timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return {
                "ok": True,
                "url": service_url,
                "payload": payload,
            }
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "url": service_url,
            "error": str(exc),
        }


def get_site_snapshot(site_id: str):
    database = get_database_health(site_id)
    rabbitmq = get_rabbitmq_health()
    service_health = get_service_health(site_id)

    if not database["ok"]:
        return {
            "site_id": site_id,
            "status": "degraded",
            "database": database,
            "rabbitmq": rabbitmq,
            "service_health": service_health,
            "event_count": None,
            "inbox_count": None,
            "pending_outbox": None,
            "last_event_type": None,
            "last_event_time": None,
        }

    db = get_session(site_id)
    try:
        event_count = db.execute(text("SELECT COUNT(*) FROM events")).scalar_one()
        inbox_count = db.execute(text("SELECT COUNT(*) FROM inbox_events")).scalar_one()
        pending_outbox = db.execute(
            text("SELECT COUNT(*) FROM outbox_events WHERE status = 'PENDING'")
        ).scalar_one()
        last_event = db.execute(text("""
            SELECT event_type, timestamp
            FROM events
            ORDER BY timestamp DESC
            LIMIT 1
        """)).mappings().first()
    finally:
        db.close()

    status = "ok" if database["ok"] and rabbitmq["ok"] and service_health["ok"] else "degraded"
    return {
        "site_id": site_id,
        "status": status,
        "database": database,
        "rabbitmq": rabbitmq,
        "service_health": service_health,
        "event_count": event_count,
        "inbox_count": inbox_count,
        "pending_outbox": pending_outbox,
        "last_event_type": last_event["event_type"] if last_event else None,
        "last_event_time": last_event["timestamp"].isoformat() if last_event else None,
    }


def get_recent_events(limit: int = 12):
    merged_events = []
    for site_id in SITE_IDS:
        db = get_session(site_id)
        try:
            rows = db.execute(text("""
                SELECT event_id, container_id, site_id, event_type, sync_status, timestamp
                FROM events
                ORDER BY timestamp DESC
                LIMIT :limit
            """), {"limit": limit}).mappings().all()
            for row in rows:
                merged_events.append({
                    **dict(row),
                    "timestamp": row["timestamp"].isoformat() if isinstance(row["timestamp"], datetime) else str(row["timestamp"]),
                })
        finally:
            db.close()
    merged_events.sort(key=lambda item: item["timestamp"], reverse=True)
    return merged_events[:limit]


def get_site_recent_events(site_id: str, limit: int = 12):
    db = get_session(site_id)
    try:
        rows = db.execute(text("""
            SELECT event_id, container_id, site_id, event_type, sync_status, timestamp
            FROM events
            ORDER BY timestamp DESC
            LIMIT :limit
        """), {"limit": limit}).mappings().all()
        return [
            {
                **dict(row),
                "timestamp": row["timestamp"].isoformat() if isinstance(row["timestamp"], datetime) else str(row["timestamp"]),
            }
            for row in rows
        ]
    finally:
        db.close()


@app.get("/", response_class=HTMLResponse)
def dashboard(auth: AuthContext = Depends(require_actors(*CONTROL_TOWER_READERS))):
    return overview_page(auth.api_key)


@app.get("/tracking", response_class=HTMLResponse)
def tracking_ui(auth: AuthContext = Depends(require_actors(*TRACKING_READERS))):
    return tracking_page(auth.api_key)


@app.get("/sites/{site_id}", response_class=HTMLResponse)
def site_dashboard(site_id: str, auth: AuthContext = Depends(require_actors(*INTERNAL_READERS))):
    normalized_site_id = site_id.upper()
    if normalized_site_id not in SITE_IDS:
        raise HTTPException(status_code=404, detail="Unknown site")
    return site_page(auth.api_key, normalized_site_id)


@app.get("/health")
def health(auth: AuthContext = Depends(require_actors(*CONTROL_TOWER_READERS))):
    sites = [get_site_snapshot(site_id) for site_id in SITE_IDS]
    healthy_sites = sum(1 for site in sites if site["status"] == "ok")
    return {
        "status": "ok" if healthy_sites == len(SITE_IDS) else "degraded",
        "service": "CONTROL_TOWER",
        "actor": auth.actor,
        "healthy_sites": healthy_sites,
        "total_sites": len(SITE_IDS),
    }


@app.get("/api/overview")
def overview(
    limit: int = Query(default=12, ge=1, le=50),
    auth: AuthContext = Depends(require_actors(*CONTROL_TOWER_READERS)),
):
    sites = [get_site_snapshot(site_id) for site_id in SITE_IDS]
    recent_events = get_recent_events(limit)
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "actor": auth.actor,
        "healthy_sites": sum(1 for site in sites if site["status"] == "ok"),
        "total_sites": len(SITE_IDS),
        "total_events": sum((site["event_count"] or 0) for site in sites),
        "total_pending_outbox": sum((site["pending_outbox"] or 0) for site in sites),
        "sites": sites,
        "recent_events": recent_events,
    }


@app.get("/api/events")
def events(
    limit: int = Query(default=20, ge=1, le=100),
    auth: AuthContext = Depends(require_actors(*CONTROL_TOWER_READERS)),
):
    return {"actor": auth.actor, "events": get_recent_events(limit)}


@app.get("/api/sites/{site_id}")
def site_data(
    site_id: str,
    limit: int = Query(default=12, ge=1, le=50),
    auth: AuthContext = Depends(require_actors(*INTERNAL_READERS)),
):
    normalized_site_id = site_id.upper()
    if normalized_site_id not in SITE_IDS:
        raise HTTPException(status_code=404, detail="Unknown site")
    return {
        "actor": auth.actor,
        "snapshot": get_site_snapshot(normalized_site_id),
        "recent_events": get_site_recent_events(normalized_site_id, limit),
    }


@app.get("/api/tracking/{container_id}")
def tracking(
    container_id: str,
    auth: AuthContext = Depends(require_actors(*TRACKING_READERS)),
):
    timeline_by_event_id = {}
    for site_id in SITE_IDS:
        db = get_session(site_id)
        try:
            rows = db.execute(text("""
                SELECT event_id, container_id, site_id, event_type, sync_status, timestamp
                FROM events
                WHERE container_id = :container_id
                ORDER BY timestamp ASC
            """), {"container_id": container_id}).mappings().all()
            for row in rows:
                event = {
                    **dict(row),
                    "timestamp": row["timestamp"].isoformat() if isinstance(row["timestamp"], datetime) else str(row["timestamp"]),
                }
                existing = timeline_by_event_id.get(event["event_id"])
                if existing is None:
                    timeline_by_event_id[event["event_id"]] = event
                    continue
                if existing["sync_status"] != "SENT" and event["sync_status"] == "SENT":
                    timeline_by_event_id[event["event_id"]] = event
        finally:
            db.close()

    timeline = list(timeline_by_event_id.values())
    timeline.sort(key=lambda item: item["timestamp"])
    return {
        "actor": auth.actor,
        "container_id": container_id,
        "timeline": timeline,
    }

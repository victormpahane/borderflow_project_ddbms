import json
import os
from datetime import datetime
from urllib.error import URLError
from urllib.request import urlopen

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import text

from shared.db.session import get_database_health, get_session
from shared.db.sites import SITE_IDS
from shared.messaging.health import get_rabbitmq_health


CONTROL_TOWER_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>BorderFlow Control Tower</title>
  <style>
    :root {
      --bg: #f5efe4;
      --panel: rgba(255, 251, 244, 0.92);
      --ink: #1f2933;
      --muted: #5b6470;
      --accent: #0f766e;
      --accent-soft: #c8f1eb;
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
      width: min(1200px, calc(100% - 32px));
      margin: 28px auto 40px;
    }

    .hero {
      display: grid;
      grid-template-columns: 1.2fr 0.8fr;
      gap: 18px;
      align-items: stretch;
      margin-bottom: 18px;
    }

    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 24px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(10px);
    }

    .hero-main {
      padding: 28px;
      overflow: hidden;
      position: relative;
    }

    .hero-main::after {
      content: "";
      position: absolute;
      right: -50px;
      top: -40px;
      width: 180px;
      height: 180px;
      border-radius: 999px;
      background: linear-gradient(135deg, rgba(15,118,110,0.18), rgba(255,255,255,0));
    }

    h1 {
      margin: 0 0 10px;
      font-size: clamp(2.2rem, 5vw, 4rem);
      line-height: 0.95;
      letter-spacing: -0.05em;
      max-width: 10ch;
    }

    .eyebrow, .muted { color: var(--muted); }
    .eyebrow {
      text-transform: uppercase;
      letter-spacing: 0.14em;
      font-size: 0.78rem;
      margin-bottom: 14px;
      display: inline-block;
    }

    .hero-copy {
      font-family: "Trebuchet MS", Arial, sans-serif;
      max-width: 52ch;
      line-height: 1.55;
      font-size: 1rem;
      color: #334155;
    }

    .hero-side {
      padding: 20px;
      display: grid;
      gap: 12px;
    }

    .stat {
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px 18px;
      background: rgba(255,255,255,0.62);
    }

    .stat-label {
      font-family: "Trebuchet MS", Arial, sans-serif;
      font-size: 0.78rem;
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

    .section {
      padding: 20px;
    }

    .section h2 {
      margin: 0 0 14px;
      font-size: 1.2rem;
    }

    .sites {
      display: grid;
      gap: 12px;
    }

    .site-card {
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px;
      background: rgba(255,255,255,0.62);
      display: grid;
      gap: 12px;
      transition: transform 180ms ease, box-shadow 180ms ease;
    }

    .site-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 10px 28px rgba(31, 41, 51, 0.08);
    }

    .site-head, .chip-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
    }

    .site-name {
      font-size: 1.1rem;
      font-weight: 600;
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
      font-size: 1.05rem;
    }

    .feed {
      display: grid;
      gap: 10px;
    }

    .event {
      padding: 14px 14px 12px;
      border-radius: 16px;
      border: 1px solid var(--line);
      background: linear-gradient(180deg, rgba(255,255,255,0.8), rgba(255,255,255,0.6));
    }

    .event-top {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 8px;
      flex-wrap: wrap;
    }

    .event-type {
      font-weight: 700;
      letter-spacing: 0.02em;
    }

    .event-meta {
      color: var(--muted);
      font-family: "Trebuchet MS", Arial, sans-serif;
      font-size: 0.9rem;
    }

    .empty {
      color: var(--muted);
      font-style: italic;
      padding: 12px 0;
    }

    .refresh {
      margin-top: 16px;
      border: none;
      background: var(--accent);
      color: white;
      font: inherit;
      padding: 12px 16px;
      border-radius: 999px;
      cursor: pointer;
      box-shadow: 0 8px 24px rgba(15,118,110,0.22);
    }

    @media (max-width: 900px) {
      .hero, .grid { grid-template-columns: 1fr; }
      .metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }

    @media (max-width: 560px) {
      .shell { width: min(100% - 18px, 100%); margin: 10px auto 24px; }
      .hero-main, .hero-side, .section { padding: 16px; }
      .metrics { grid-template-columns: 1fr 1fr; }
      h1 { max-width: none; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div class="panel hero-main">
        <div class="eyebrow">BorderFlow Control Tower</div>
        <h1>Distributed cargo visibility.</h1>
        <div class="hero-copy">
          A live command surface for the Depot, Border, Port, and Destination sites.
          It tracks local health, cross-site event flow, outbox pressure, and the latest
          synchronized movement history from the distributed backend.
        </div>
        <button class="refresh" id="refreshButton">Refresh Now</button>
      </div>
      <div class="panel hero-side">
        <div class="stat">
          <div class="stat-label">Healthy Sites</div>
          <div class="stat-value" id="healthySites">-</div>
        </div>
        <div class="stat">
          <div class="stat-label">Total Events</div>
          <div class="stat-value" id="totalEvents">-</div>
        </div>
        <div class="stat">
          <div class="stat-label">Pending Outbox</div>
          <div class="stat-value" id="pendingOutbox">-</div>
        </div>
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
  </div>

  <script>
    const state = { overview: null };

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
        const card = document.createElement("div");
        card.className = "site-card";
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
      const response = await fetch("/api/overview");
      state.overview = await response.json();
      render();
    }

    document.getElementById("refreshButton").addEventListener("click", loadOverview);
    loadOverview();
    setInterval(loadOverview, 12000);
  </script>
</body>
</html>
"""


app = FastAPI(title="BorderFlow Control Tower")


def get_service_url(site_id: str) -> str:
    return os.getenv(
        f"{site_id.upper()}_SERVICE_URL",
        f"http://127.0.0.1:{8000 + SITE_IDS.index(site_id.upper())}/health",
    )


def get_service_health(site_id: str):
    service_url = get_service_url(site_id)
    try:
        with urlopen(service_url, timeout=2) as response:
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


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return CONTROL_TOWER_HTML


@app.get("/health")
def health():
    sites = [get_site_snapshot(site_id) for site_id in SITE_IDS]
    healthy_sites = sum(1 for site in sites if site["status"] == "ok")
    return {
        "status": "ok" if healthy_sites == len(SITE_IDS) else "degraded",
        "service": "CONTROL_TOWER",
        "healthy_sites": healthy_sites,
        "total_sites": len(SITE_IDS),
    }


@app.get("/api/overview")
def overview(limit: int = Query(default=12, ge=1, le=50)):
    sites = [get_site_snapshot(site_id) for site_id in SITE_IDS]
    recent_events = get_recent_events(limit)
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "healthy_sites": sum(1 for site in sites if site["status"] == "ok"),
        "total_sites": len(SITE_IDS),
        "total_events": sum(site["event_count"] for site in sites),
        "total_pending_outbox": sum(site["pending_outbox"] for site in sites),
        "sites": sites,
        "recent_events": recent_events,
    }


@app.get("/api/events")
def events(limit: int = Query(default=20, ge=1, le=100)):
    return {"events": get_recent_events(limit)}

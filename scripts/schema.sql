CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    container_id TEXT NOT NULL,
    site_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    timestamp TIMESTAMPTZ NOT NULL,
    sync_status TEXT NOT NULL,
    sequence_number INTEGER
);

CREATE TABLE IF NOT EXISTS container_state (
    container_id TEXT PRIMARY KEY,
    current_location TEXT NOT NULL,
    last_event TEXT NOT NULL,
    last_updated TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS outbox_events (
    event_id TEXT PRIMARY KEY,
    source_site_id TEXT NOT NULL,
    routing_key TEXT NOT NULL,
    payload JSONB NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    sent_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS inbox_events (
    event_id TEXT PRIMARY KEY,
    source_site_id TEXT NOT NULL,
    payload JSONB NOT NULL,
    received_at TIMESTAMPTZ NOT NULL
);
